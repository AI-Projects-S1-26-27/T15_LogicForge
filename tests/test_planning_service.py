"""Integration tests for the planning service (Pair D): real CSE data, real CSP solver."""

import os
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

pytest.importorskip("backend.csp.solver")
from backend.services.planning_service import available_branches, make_plan  # noqa: E402

SECOND_YEAR = ["CS F111", "EEE F111", "CS F222", "CS F214", "CS F215", "CS F213", "CS F372"]


def test_cse_branch_is_available():
    assert "cse" in available_branches()


def test_end_to_end_plan_is_verified_and_explained():
    response = make_plan("cse", SECOND_YEAR, current_semester=3, max_credits=20)
    assert response.status == "PLAN", response.text()
    assert response.verification.valid
    assert response.explanation.graduation_semester <= 8
    planned = {c["code"] for rows in response.semesters.values() for c in rows}
    assert "CS F211" in planned
    assert planned.isdisjoint(SECOND_YEAR)
    assert "Plan found and verified" in response.text()


def test_impossible_request_is_diagnosed():
    from backend.services.problem_builder import build_problem_for_student
    catalogue = build_problem_for_student('cse', [], 0)
    # The remaining even-semester core cannot fit in the odd-only horizon.
    completed = [code for code in catalogue.courses if code != 'CS F211']
    response = make_plan('cse', completed, current_semester=6, target_semester=7, max_credits=12)
    assert response.status == 'NO_PLAN'
    diag = response.infeasibility
    assert diag.status == 'infeasible' and diag.conflict
    assert any(r.fixes_alone for r in diag.relaxations)


def test_unknown_codes_are_warned_about():
    response = make_plan("cse", SECOND_YEAR + ["XYZ F999"], current_semester=3)
    assert any("XYZ F999" in w for w in response.warnings)


def test_unknown_solver_is_rejected():
    with pytest.raises(ValueError):
        make_plan("cse", [], current_semester=1, solver="magic")
