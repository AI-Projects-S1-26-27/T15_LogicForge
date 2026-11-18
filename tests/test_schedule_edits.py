import pytest
from backend.services.scoped_planner import (
    DATA,
    BRANCHES,
    catalogue_for,
    prepare,
    InputError,
)
from backend.services.scoped_api import plan_payload, edit_payload


def req(branch="cse", **extra):
    return dict(
        branch=branch,
        current_semester=2,
        completed_courses=DATA["common"],
        bulletin_fallback=True,
        solver="csp",
        **extra
    )


@pytest.mark.parametrize("branch", list(BRANCHES))
def test_auto_fill_does_not_import_unapproved_foreign_cdcs(branch):
    state = prepare(req(branch))
    for code in state["problem"].variables:
        c = state["catalogue"][code]
        assert not c["manual_open_only"], code


@pytest.mark.parametrize(
    "minor,count,units",
    [
        ("finance", 2, 6),
        ("data_science", 3, 9),
        ("computing_and_intelligence", 3, 10),
        ("robotics_and_automation", 3, 9),
        ("semiconductor_devices_and_technology", 2, 7),
    ],
)
def test_minor_cdc_summary(minor, count, units):
    _, m = catalogue_for("eee", minor)
    assert m["required_core_courses"] == count
    assert m["required_core_credits_min"] == units
    assert all("degree_category" in c for c in m["courses"])


def test_moves_are_verified_and_input_assignment_is_not_mutated():
    request = req()
    plan = plan_payload(request)
    assert plan["verification_valid"]
    assignment = {
        c["code"]: int(term)
        for term, rows in plan["semesters"].items()
        for c in rows["courses"]
    }
    original = dict(assignment)
    accepted = None
    for code, source in assignment.items():
        for target in range(3, 9):
            if target == source:
                continue
            try:
                accepted = edit_payload(
                    dict(
                        plan=request,
                        assignment=assignment,
                        move=dict(course=code, target_semester=target),
                    )
                )
                break
            except InputError:
                pass
        if accepted:
            break
    assert accepted and accepted["verification_valid"]
    assert assignment == original
    with pytest.raises(InputError):
        edit_payload(
            dict(
                plan=request,
                assignment=assignment,
                move=dict(course=next(iter(assignment)), target_semester=2),
            )
        )
    with pytest.raises(InputError):
        edit_payload(dict(plan=request, assignment={}, move={}))


def test_swap_verifies_both_courses_and_rejects_offering_violation():
    request = req()
    plan = plan_payload(request)
    assignment = {
        c["code"]: int(term)
        for term, rows in plan["semesters"].items()
        for c in rows["courses"]
    }
    accepted = None
    for code, source in assignment.items():
        for other, target in assignment.items():
            if source == target:
                continue
            try:
                accepted = edit_payload(
                    dict(
                        plan=request,
                        assignment=assignment,
                        move=dict(course=code, target_semester=target, swap_with=other),
                    )
                )
                break
            except InputError:
                pass
        if accepted:
            break
    assert accepted and accepted["verification_valid"]
    with pytest.raises(InputError):
        edit_payload(
            dict(
                plan=request,
                assignment=assignment,
                move=dict(course="BITS F421T", target_semester=7),
            )
        )


def test_elective_category_is_explicit_and_own_cdc_cannot_be_reclassified():
    state = prepare(
        req(selected_electives=["GS F241"], elective_allocations={"GS F241": "open"})
    )
    assert state["catalogue"]["GS F241"]["category"] == "Open Elective"
    with pytest.raises(InputError):
        prepare(req(elective_allocations={"CS F211": "open"}))


@pytest.mark.parametrize("branch", list(BRANCHES))
def test_reference_transcript_contains_only_selected_branch_required_courses(branch):
    from backend.services.scoped_planner import curriculum_response

    data = curriculum_response(branch)
    rows = [
        c
        for term, courses in data["patterns"].items()
        if int(term) <= 4
        for c in courses
    ]
    assert rows
    for course in rows:
        assert course["category"] in (
            "Institutional Core",
            "Discipline Core",
            "General Awareness",
        )
        if course["cdc_branches"]:
            assert branch in course["cdc_branches"], course["code"]
    assert not any(c["code"] == "CS F213" for c in rows) if branch != "cse" else True


def test_minor_core_choice_does_not_survive_switch_as_general_elective():
    chosen = prepare(
        req(minor="robotics_and_automation", minor_core_choices=["EEE F242"])
    )
    assert "EEE F242" in chosen["minor_required"]
    assert "EEE F242" not in chosen["request"]["selected_electives"]
    changed = prepare(req(minor="finance"))
    assert "EEE F242" not in changed["problem"].courses
    with pytest.raises(InputError):
        prepare(req(minor="finance", minor_core_choices=["EEE F242"]))
    with pytest.raises(InputError):
        prepare(
            req(
                minor="robotics_and_automation",
                minor_core_choices=["EEE F242", "ECE F242"],
            )
        )


@pytest.mark.parametrize("branch", list(BRANCHES))
def test_automatic_completed_cores_are_branch_only_at_every_semester(branch):
    from backend.services.scoped_planner import curriculum_response

    data = curriculum_response(branch)
    cat = {c["code"]: c for c in data["all_courses"]}
    reference = data["reference_completed_by_semester"]
    assert reference["0"] == []
    assert "CS F111" in reference["2"]
    assert len(reference["2"]) == 15
    for semester in range(9):
        courses = set(reference[str(semester)])
        for code in courses:
            assert not cat[code]["foreign_cdc"], (branch, semester, code)
            assert cat[code]["recommended_semester"] <= semester
        for group in BRANCHES[branch]["alternative_core_groups"]:
            assert len(courses & set(group)) <= 1
        assert len(courses & {"ECON F211", "MGTS F211"}) <= 1
