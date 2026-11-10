"""Tests for the plan explainer (Pair D)."""

import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.explanations.plan_explainer import explain_plan  # noqa: E402
from backend.verification import NOT_TAKEN  # noqa: E402

CORE, ELECTIVE = "Discipline Core", "Discipline Elective"


def course(credits=4, category=CORE, parity=None, formula=None):
    return {"credits": credits, "category": category, "parity": parity, "formula": formula}


def pre(code):
    return {"kind": "leaf", "course": code, "relation": "PRE"}


def problem(courses, **kw):
    base = {"courses": courses, "completed": set(), "current_semester": 0,
            "target_semester": 4, "max_credits": 8, "min_credits": 0,
            "category_minimums": {}, "assume_out_of_scope_satisfied": True}
    base.update(kw)
    return base


def test_prerequisite_and_dependant_are_named():
    p = problem({"A": course(), "B": course(formula=pre("A"))})
    exp = explain_plan(p, {"A": 1, "B": 2}).by_course()
    assert "A (semester 1)" in exp["B"].text()
    assert "Needed before: B (semester 2)" in exp["A"].text()
    assert "earliest semester" in exp["B"].text()


def test_or_prerequisite_names_the_option_used():
    formula = {"kind": "or", "items": [pre("X"), pre("Y")]}
    p = problem({"X": course(2, ELECTIVE), "Y": course(2, ELECTIVE), "Z": course(formula=formula)})
    exp = explain_plan(p, {"X": NOT_TAKEN, "Y": 1, "Z": 2}).by_course()
    assert "Y (semester 1) (one of the allowed options)" in exp["Z"].text()
    assert "optional" in exp["X"].text()


def test_full_semester_explains_delay():
    p = problem({"A": course(), "B": course(), "C": course()})
    exp = explain_plan(p, {"A": 1, "B": 1, "C": 2}).by_course()
    assert "semester 1, but that semester was full (8/8 credits)" in exp["C"].text()


def test_free_choice_is_admitted_honestly():
    p = problem({"A": course()})
    exp = explain_plan(p, {"A": 3}).by_course()
    assert "Could also go in semester 1" in exp["A"].text()


def test_completed_and_parity_reasons():
    p = problem({"A": course(), "B": course(parity="even", formula=pre("A"))}, completed={"A"})
    exp = explain_plan(p, {"B": 2})
    text = exp.by_course()["B"].text()
    assert "A (already completed)" in text and "even semesters" in text
    assert exp.graduation_semester == 2
    assert "Semester 2: 4 credits" in exp.text()
