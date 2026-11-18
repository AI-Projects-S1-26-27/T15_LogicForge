"""Programme stages must prevent a fresh plan front-loading year-three cores."""

import pytest
from backend.services.scoped_planner import prepare, curriculum_response
from backend.services.scoped_api import plan_payload

BRANCHES = ["cse", "eee", "ece", "e_and_i"]


@pytest.mark.parametrize("branch", BRANCHES)
@pytest.mark.parametrize("solver", ["csp", "astar"])
@pytest.mark.parametrize("route", ["thesis", "thesis_coursework", "practice_school"])
def test_none_generates_stage_correct_degree(branch, solver, route):
    request = dict(
        branch=branch,
        solver=solver,
        current_semester=0,
        target_semester=8,
        max_credits=22,
        completed_courses=[],
        project_route=route,
        allow_unconfirmed=True,
        auto_fill=True,
    )
    result = plan_payload(request)
    assert result["status"] == "PLAN"
    assert result["verification_valid"]
    state = prepare(request)
    for semester, term in result["semesters"].items():
        assert term["credits"] <= 22
        for course in term["courses"]:
            source = state["catalogue"][course["code"]]
            if source["category"] in (
                "Discipline Core",
                "Institutional Core",
                "General Awareness",
            ):
                assert semester >= (source.get("recommended_semester") or 1)
    # Year-three CDCs must no longer disappear into the first two years.
    assert result["semesters"][5]["courses"]
    assert result["semesters"][6]["courses"]


@pytest.mark.parametrize("branch", BRANCHES)
def test_stages_are_lower_bounds_not_fixed_dates(branch):
    done = curriculum_response(branch)["reference_completed_by_semester"]["2"]
    state = prepare(
        dict(
            branch=branch,
            current_semester=4,
            target_semester=8,
            completed_courses=done,
            allow_unconfirmed=True,
            auto_fill=False,
        )
    )
    core = next(
        c
        for c in state["major"]
        if state["catalogue"][c].get("recommended_semester") == 3
    )
    assert state["problem"].courses[core]["earliest_semester"] == 3
    assert all(term > 4 for term in state["problem"].initial_domains()[core])
