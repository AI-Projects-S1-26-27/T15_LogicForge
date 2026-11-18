import pytest
from backend.services.scoped_planner import (
    BRANCHES,
    catalogue_for,
    curriculum_response,
    prepare,
    assessment,
    apply_del_overflow,
)
from backend.services.scoped_api import plan_payload


def request(branch, **extra):
    return dict(
        branch=branch,
        current_semester=4,
        target_semester=8,
        max_credits=25,
        completed_courses=curriculum_response(branch)[
            "reference_completed_by_semester"
        ]["4"],
        allow_unconfirmed=True,
        **extra
    )


def five_dels(branch):
    cat, _ = catalogue_for(branch)
    codes = [
        c
        for c in BRANCHES[branch]["electives"]
        if cat[c]["credits"] >= 3
        and not cat[c].get("formula")
        and not cat[c].get("project_type")
    ][:5]
    assert len(codes) == 5
    return list(reversed(codes))


@pytest.mark.parametrize("branch", list(BRANCHES))
@pytest.mark.parametrize("solver", ["csp", "astar"])
def test_fifth_selected_del_counts_as_open_and_humanities_requires_nine(branch, solver):
    selected = five_dels(branch)
    result = plan_payload(
        request(
            branch,
            solver=solver,
            selected_electives=selected,
            semester_assignments={selected[4]: 5},
        )
    )
    assert result["verification_valid"], result["message"]
    categories = result["audit"]["categories"]
    assert categories["Humanities Elective"]["credit_minimum"] == 9
    assert categories["Humanities Elective"]["credits"] >= 9
    assert categories["Discipline Elective"]["courses"] == 4
    assert categories["Discipline Elective"]["credits"] >= 12
    assert categories["Open Elective"]["courses"] >= 5
    assert categories["Open Elective"]["credits"] >= 15
    assert all(result["effective_allocations"][c] == "discipline" for c in selected[:4])
    assert result["effective_allocations"][selected[4]] == "open"
    assert selected[4] in result["converted_del_courses"]
    rows = [c for term in result["semesters"].values() for c in term["courses"]]
    overflow = [c for c in rows if c["code"] == selected[4]]
    assert len(overflow) == 1 and overflow[0]["category"] == "Open Elective"
    assert overflow[0]["assigned_semester"] == 5


def test_del_credits_must_be_met_before_overflow_even_with_four_courses():
    cat = {
        c: dict(category="Discipline Elective", credits=u)
        for c, u in zip("ABCDEF", [2, 2, 2, 2, 4, 3])
    }
    req = dict(
        completed_courses=[], selected_electives=list("ABCDEF"), semester_assignments={}
    )
    apply_del_overflow(cat, set(cat), req)
    assert all(cat[c]["category"] == "Discipline Elective" for c in "ABCDE")
    assert cat["F"]["category"] == "Open Elective"
    apply_del_overflow(cat, set("ABCEF"), dict(req, selected_electives=list("ABCEF")))
    assert cat["F"]["category"] == "Discipline Elective"


def test_humanities_and_open_are_minimums_and_extra_courses_are_not_rejected():
    request_data = request(
        "cse",
        selected_electives=[
            "HSS F221",
            "HSS F222",
            "HSS F223",
            "HSS F224",
            "ECON F212",
            "FIN F315",
            "FIN F242",
            "FIN F243",
            "FIN F311",
            "FIN F312",
        ],
    )
    result = plan_payload(request_data)
    assert result["verification_valid"]
    assert result["audit"]["categories"]["Humanities Elective"]["credits"] >= 12
    assert result["audit"]["categories"]["Open Elective"]["courses"] >= 6


def test_minor_membership_is_preserved_when_degree_bucket_changes():
    selected = five_dels("eee")
    state = prepare(
        request("eee", minor="computing_and_intelligence", selected_electives=selected)
    )
    report = assessment(
        state["catalogue"],
        state["selected"],
        state["request"]["completed_courses"],
        state["major"],
        state["minor"],
        state["request"],
        verified=True,
        summer=state["summer"],
    )
    assert report["minor"]["coursework_met"]
    assert report["categories"]["Discipline Elective"]["courses"] == 4
    assert state["catalogue"][selected[4]]["category"] == "Open Elective"
