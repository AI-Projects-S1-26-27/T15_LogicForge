import copy
import pytest
from backend.services.scoped_planner import DATA, prepare, InputError
from backend.services.scoped_api import plan_payload
from scripts.ingest_offerings import update


def request(branch="cse", **extra):
    return dict(
        branch=branch,
        current_semester=2,
        completed_courses=DATA["common"],
        allow_unconfirmed=True,
        **extra
    )


def test_only_latest_pair_supplies_source_evidence():
    assert DATA["sources"]["odd"]["file"] == "TIMETABLE FIRST SEMESTER 2026 -27 (2).pdf"
    assert DATA["sources"]["even"]["file"] == "TIMETABLE - II SEMESTER 2024 -25 (1).pdf"
    assert DATA["sources"]["even"]["snapshot"] == "2024-25 Semester II"
    assert DATA["courses"]["BIO F110"]["offered_terms"] == ["even"]
    assert DATA["courses"]["FIN F315"]["offered_terms"] == ["odd"]
    data = update(
        copy.deepcopy(DATA), {"odd": "CS F211 Teaching", "even": "CS F212 Teaching"}
    )
    assert data["courses"]["FIN F315"]["offered_terms"] == []
    assert data["courses"]["FIN F315"]["offering_evidence"] == {}


def test_assumption_unblocks_unlisted_selected_course_but_does_not_change_observed_course():
    state = prepare(request(selected_electives=["HSS F221"]))
    unknown = state["catalogue"]["HSS F221"]
    assert unknown["offered_terms"] == []
    assert unknown["effective_terms"] == ["odd", "even"]
    assert "Planning assumption" in unknown["offering_basis"]
    assert state["catalogue"]["CS F211"]["effective_terms"] == ["even"]
    assert state["catalogue"]["FIN F315"]["effective_terms"] == ["odd"]
    assert any(a["code"] == "HSS F221" for a in state["assumptions"])
    with pytest.raises(InputError):
        prepare(dict(request(selected_electives=["HSS F221"]), allow_unconfirmed=False))


@pytest.mark.parametrize("branch", ["cse", "eee", "ece", "e_and_i"])
@pytest.mark.parametrize("solver", ["csp", "astar"])
def test_all_branches_generate_with_unconfirmed_courses_allowed(branch, solver):
    result = plan_payload(
        request(branch, solver=solver, selected_electives=["HSS F221"])
    )
    assert result["verification_valid"], result.get("message")
    assert result["audit"]["requirements_met"], result["audit"].get("blockers")
    assert any(
        c["code"] == "HSS F221"
        for term in result["semesters"].values()
        for c in term["courses"]
    )
