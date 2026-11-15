"""Tests for the infeasibility analyser (Pair D).

Small problems are checked against a brute-force oracle that tries every
possible plan, so "minimal" is proven, not assumed (proposal §3).
"""

import itertools
import os
import random
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.explanations.infeasibility_analyzer import (  # noqa: E402
    SAT, UNSAT, analyze, candidate_units, csp_oracle, relaxed_problem,
)
from backend.verification import NOT_TAKEN, verify_plan  # noqa: E402

CORE, ELECTIVE = "Discipline Core", "Discipline Elective"


def course(credits=4, category=CORE, parity=None, formula=None):
    return {"credits": credits, "category": category, "parity": parity, "formula": formula}


def pre(code):
    return {"kind": "leaf", "course": code, "relation": "PRE"}


def problem(courses, **overrides):
    base = {"courses": courses, "completed": set(), "current_semester": 0,
            "target_semester": 4, "max_credits": 8, "min_credits": 0,
            "category_minimums": {}, "assume_out_of_scope_satisfied": True}
    base.update(overrides)
    return base


def brute_force(p) -> str:
    """Try every assignment; SAT if any passes the independent verifier."""
    completed = set(p["completed"])
    codes = sorted(c for c in p["courses"] if c not in completed)
    semesters = list(range(p["current_semester"] + 1, p["target_semester"] + 1))
    options = []
    for code in codes:
        values = list(semesters)
        if "elective" in (p["courses"][code]["category"] or "").lower():
            values.append(NOT_TAKEN)
        options.append(values)
    for combo in itertools.product(*options):
        if verify_plan(p, dict(zip(codes, combo))).valid:
            return SAT
    return UNSAT


def assert_minimal(p, core):
    """Core is impossible, and dropping any single unit makes it possible."""
    assert brute_force(relaxed_problem(p, core)) == UNSAT
    for unit in core:
        rest = [u for u in core if u != unit]
        assert brute_force(relaxed_problem(p, rest)) == SAT, unit


# ── basic behaviour ─────────────────────────────────────────────────────────

def test_feasible_problem_needs_no_diagnosis():
    p = problem({"A": course(), "B": course(formula=pre("A"))})
    report = analyze(p, oracle=brute_force)
    assert report.status == "feasible"
    assert report.conflict == []


def test_chain_too_long_for_horizon():
    # A -> B -> C needs 3 semesters but only 2 are left.
    p = problem({"A": course(), "B": course(formula=pre("A")), "C": course(formula=pre("B"))},
                target_semester=2)
    report = analyze(p, oracle=brute_force)
    assert report.status == "infeasible"
    assert set(report.conflict) == {"horizon", "prereq:B", "prereq:C"}
    assert_minimal(p, report.conflict)
    horizon_fix = next(r for r in report.relaxations if r.unit == "horizon")
    assert horizon_fix.fixes_alone is True
    assert "1 semester" in horizon_fix.description


def test_credit_cap_too_low():
    # 3 courses x 4 credits, 1 semester, cap 8 -> need 12.
    p = problem({"A": course(), "B": course(), "C": course()}, target_semester=1)
    report = analyze(p, oracle=brute_force)
    assert set(report.conflict) == {"horizon", "credit_cap"}
    cap_fix = next(r for r in report.relaxations if r.unit == "credit_cap")
    assert cap_fix.fixes_alone is True
    assert "12 credits" in cap_fix.description


def test_parity_clash():
    # Even-only course, only semester 1 (odd) left.
    p = problem({"E": course(parity="even")}, target_semester=1)
    report = analyze(p, oracle=brute_force)
    assert set(report.conflict) == {"horizon", "parity:E"}
    assert_minimal(p, report.conflict)


def test_category_minimum_unreachable():
    p = problem({"A": course(), "X": course(3, category=ELECTIVE)},
                category_minimums={ELECTIVE: 6})
    report = analyze(p, oracle=brute_force)
    assert report.conflict == [f"category_min:{ELECTIVE}"]
    fix = report.relaxations[0]
    assert fix.fixes_alone is True and "to 3 credits" in fix.description


def test_no_semesters_left():
    # Already at the target semester with a core course outstanding.
    p = problem({"A": course()}, current_semester=4, target_semester=4)
    report = analyze(p, oracle=brute_force)
    assert report.conflict == ["horizon"]


def test_summary_is_readable():
    p = problem({"A": course(), "B": course(formula=pre("A"))}, target_semester=1)
    text = analyze(p, oracle=brute_force).summary()
    assert "No valid plan exists" in text
    assert "Graduate 1 semester(s) later" in text


def test_candidate_units_cover_every_rule():
    p = problem({"A": course(parity="odd", formula=pre("Z")), "B": course()},
                min_credits=3, category_minimums={CORE: 4})
    assert candidate_units(p) == ["horizon", "credit_cap", "credit_floor",
                                  f"category_min:{CORE}", "prereq:A", "parity:A"]


# ── random problems: minimality proven by brute force ───────────────────────

def _random_problem(rng):
    codes = [f"C{i}" for i in range(rng.randint(2, 4))]
    courses = {}
    for i, code in enumerate(codes):
        formula = pre(rng.choice(codes[:i])) if i and rng.random() < 0.6 else None
        courses[code] = course(
            credits=rng.choice([2, 3, 4]),
            category=rng.choice([CORE, CORE, ELECTIVE]),
            parity=rng.choice([None, "odd", "even"]),
            formula=formula,
        )
    return problem(courses, target_semester=rng.randint(1, 3),
                   max_credits=rng.choice([3, 4, 6, 8]),
                   category_minimums=rng.choice([{}, {ELECTIVE: 3}]))


def test_conflicts_are_minimal_on_random_problems():
    rng = random.Random(15)
    infeasible = 0
    for _ in range(80):
        p = _random_problem(rng)
        report = analyze(p, oracle=brute_force)
        if report.status != "infeasible" or report.conflict == ["required_courses"]:
            continue
        infeasible += 1
        assert report.minimal
        assert_minimal(p, report.conflict)
    assert infeasible >= 10  # make sure the test actually exercised something


# ── with the real CSP solver (Pair B) ───────────────────────────────────────

def test_csp_solver_agrees_with_brute_force():
    """Cross-check Pair B's solver on tiny problems (also helps E4)."""
    pytest.importorskip("backend.csp.solver")
    from backend.csp.model import Problem

    oracle = csp_oracle(timeout_s=5)
    rng = random.Random(4)
    disagreements = []
    for i in range(60):
        p = _random_problem(rng)
        expected = brute_force(p)
        got = oracle(Problem(**p))
        if got != expected:
            disagreements.append((i, expected, got))
    assert disagreements == []


def test_analyze_with_csp_solver():
    pytest.importorskip("backend.csp.solver")
    from backend.csp.model import Problem

    p = Problem(courses={"A": course(), "B": course(formula=pre("A")),
                         "C": course(formula=pre("B"))},
                completed=set(), current_semester=0, target_semester=2, max_credits=8)
    report = analyze(p)
    assert report.status == "infeasible"
    assert set(report.conflict) == {"horizon", "prereq:B", "prereq:C"}
