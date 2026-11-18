"""Acceptance tests for the submission dashboard's curated data and live planners."""

import copy
import pytest
from backend.services.scoped_planner import (
    DATA,
    BRANCHES,
    MINORS,
    prepare,
    assessment,
    InputError,
    catalogue_for,
    normalize_request,
)
from backend.services.scoped_api import plan_payload
from backend.verification import verify_plan
from scripts.ingest_offerings import extract


def request(branch="cse", **updates):
    return dict(
        branch=branch,
        current_semester=2,
        completed_courses=DATA["common"],
        bulletin_fallback=True,
        **updates
    )


def test_catalogue_is_only_scoped_screenshot_courses():
    assert len(DATA["courses"]) == 384
    assert all(" U" not in code for code in DATA["courses"])
    assert set(MINORS) == {
        "computing_and_intelligence",
        "data_science",
        "robotics_and_automation",
        "semiconductor_devices_and_technology",
        "finance",
    }
    assert len(BRANCHES["cse"]["core"]) == 14
    assert sum(DATA["courses"][c]["credits"] for c in BRANCHES["cse"]["core"]) == 48
    assert len(BRANCHES["eee"]["core"]) == 13
    assert BRANCHES["eee"]["alternative_core_groups"] == [["MATH F212", "ME F344"]]
    assert (
        len(MINORS["finance"]["core"]) == 2
        and len(MINORS["finance"]["electives"]) == 12
    )
    assert len(MINORS["data_science"]["core"]) == 3
    assert "BITS F453" in MINORS["data_science"]["electives"]


def test_timetable_parser_excludes_textbook_only_codes_without_standalone_heading():
    text = "TIMETABLE\n100 CS F211 Data Structures 3 1 4 L1\fCOM COD COURSE NO COURSE TITLE TEXT BOOK(S)\n101 CS F999 Book only\f102 CS F998 More bibliography"
    assert set(extract(text)) == {"CS F211"}


def test_actual_offering_can_differ_from_reference_pattern():
    assert DATA["branches"]["cse"]["patterns"]["CS F212"] == 4
    assert DATA["courses"]["CS F212"]["offered_terms"] == ["odd", "even"]
    assert DATA["courses"]["CS F211"]["offered_terms"] == ["even"]
    assert DATA["courses"]["HSS F221"]["offered_terms"] == []
    assert DATA["courses"]["FIN F315"]["offering_status"] == "odd"
    assert DATA["courses"]["BITS F421T"]["offered_terms"] == ["even"]
    assert all(
        "text book" not in e["excerpt"].lower()
        for c in DATA["courses"].values()
        for e in c["offering_evidence"].values()
    )


@pytest.mark.parametrize("branch", list(BRANCHES))
@pytest.mark.parametrize("solver", ["csp", "astar"])
def test_all_four_branches_complete_real_degree_requirements(branch, solver):
    out = plan_payload(request(branch, solver=solver))
    assert out["status"] == "PLAN", out["message"]
    assert out["verification_valid"]
    audit = out["audit"]
    assert audit["requirements_met"], audit["blockers"]
    assert audit["total_credits_planned"] >= 144 and audit["coursework_credits"] >= 129
    assert audit["coursework_count"] >= 41 and audit["total_course_count"] >= 42
    assert all(t["credits"] <= 22 for t in out["semesters"].values())
    assert list(out["semesters"][8]["courses"])[0]["code"] == "BITS F421T"
    for term in out["semesters"].values():
        parity = "odd" if term["semester"] % 2 else "even"
        assert all(parity in c["offered_terms"] for c in term["courses"])


@pytest.mark.parametrize("minor", list(MINORS))
def test_requested_minors_are_working_not_just_a_dropdown(minor):
    branch = "eee" if minor == "computing_and_intelligence" else "cse"
    out = plan_payload(request(branch, solver="astar", minor=minor))
    assert out["status"] == "PLAN"
    assert out["audit"]["minor"]["coursework_met"], out["audit"]["minor"]["issues"]
    assert out["audit"]["minor"]["count"] >= MINORS[minor]["minimum_courses"]
    assert out["audit"]["minor"]["credits"] >= MINORS[minor]["minimum_credits"]


def test_non_cse_restriction_enforced_in_backend():
    with pytest.raises(InputError, match="non-CSE"):
        prepare(request(minor="computing_and_intelligence"))


def test_unconfirmed_elective_never_gets_silently_offered():
    with pytest.raises(InputError, match="no confirmed offering"):
        prepare(request(selected_electives=["HSS F221"]))
    state = prepare(
        request(selected_electives=["HSS F221"], offering_overrides={"HSS F221": "odd"})
    )
    assert state["problem"].courses["HSS F221"]["parity"] == "odd"
    assert any(a["code"] == "HSS F221" for a in state["assumptions"])


def test_elective_exclusions_produce_new_recommendations():
    first = prepare(request())
    elective = first["auto_selected"][0]
    second = prepare(request(excluded_courses=[elective]))
    assert elective not in second["auto_selected"]
    assert elective not in second["problem"].courses


@pytest.mark.parametrize("route", ["thesis", "thesis_coursework", "practice_school"])
@pytest.mark.parametrize("solver", ["csp", "astar"])
def test_all_three_routes_work_with_real_solvers(route, solver):
    out = plan_payload(request(project_route=route, solver=solver))
    assert out["status"] == "PLAN"
    assert out["audit"]["requirements_met"]
    final = out["semesters"][8]
    if route == "thesis":
        assert len(final["courses"]) == 1 and final["credits"] == 16
    elif route == "thesis_coursework":
        assert 15 <= final["credits"] <= 18
        assert len(final["courses"]) >= 3
        assert (
            next(c["credits"] for c in final["courses"] if c["code"] == "BITS F421T")
            == 9
        )
    else:
        assert len(final["courses"]) == 1 and final["credits"] == 20
        assert out["summer_activities"][0]["credits"] == 5
        assert all(
            c["code"] != "BITS F221"
            for t in out["semesters"].values()
            for c in t["courses"]
        )


def test_project_caps_cannot_be_bypassed_by_allocating_everything_as_del():
    selected = ["CS F266", "CS F366", "CS F367", "CS F376"]
    with pytest.raises(InputError, match="Project allocation exceeds"):
        prepare(
            request(
                selected_electives=selected,
                offering_overrides={c: "both" for c in selected},
            )
        )


def test_open_projects_and_total_project_caps():
    selected = ["CS F266", "CS F366", "CS F367", "CS F376"]
    with pytest.raises(InputError, match="Project allocation exceeds"):
        prepare(
            request(
                selected_electives=selected,
                offering_overrides={c: "both" for c in selected},
                project_allocations={c: "open" for c in selected},
            )
        )


def test_minor_major_overlap_over_six_units_is_not_accepted():
    cat, m = catalogue_for("eee", "robotics_and_automation")
    from backend.services.scoped_planner import _minor_assessment

    # Three required major variants cannot all be used as minor credit.
    m = copy.deepcopy(m)
    m["core"] = ["EEE F211", "EEE F215", "EEE F242"]
    m["core_alternatives"] = []
    known = set(m["core"]) | {"BITS F312", "BITS F415"}
    major = set(m["core"])
    status = _minor_assessment(m, known, major, cat)
    assert any("overlap" in i for i in status["issues"])


@pytest.mark.parametrize(
    "bad",
    [
        {"max_credits": 22.5},
        {"current_semester": True},
        {"selected_electives": "CS F211"},
        {"offering_overrides": {"CS F211": "sometimes"}},
        {"branch": "civil"},
        {"minor": {"x": 1}},
    ],
)
def test_bad_api_inputs_are_actionable_not_500_errors(bad):
    with pytest.raises(InputError):
        state = normalize_request(bad)
        prepare(state)


def test_a_tampered_offering_and_thesis_schedule_is_rejected():
    state = prepare(request())
    problem = state["problem"]
    from backend.services.planning_service import make_plan

    result = make_plan(
        "cse",
        DATA["common"],
        2,
        8,
        solver="csp",
        problem_override=problem,
        diagnose=False,
    )
    assignment = dict(result.assignment)
    assignment["CS F211"] = 3
    assert not verify_plan(problem, assignment).valid
    assignment = dict(result.assignment)
    assignment["BITS F421T"] = 7
    assert not verify_plan(problem, assignment).valid


def test_astar_can_accelerate_the_same_ps_candidate_set():
    a = plan_payload(
        request(solver="astar", project_route="practice_school", max_credits=25)
    )
    c = plan_payload(
        request(solver="csp", project_route="practice_school", max_credits=25)
    )
    assert a["verification_valid"] and c["verification_valid"]
    assert max(a["semesters"]) == 7
    assert max(a["semesters"]) <= max(c["semesters"])


def test_learned_mode_actually_uses_neural_secondary_guidance():
    out = plan_payload(
        request(solver="astar", heuristic="learned", minor="finance", max_credits=24)
    )
    assert out["status"] == "PLAN"
    assert "equal-f" in out["stats"]["learned_policy"]
    assert out["stats"]["heuristic_details"]["model_available"]
    assert (
        out["stats"]["heuristic_details"]["used_estimate"]
        == out["stats"]["heuristic_details"]["composite_bound"]
    )
    assert out["stats"]["heuristic_details"]["learned_prediction"] is not None
