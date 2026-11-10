"""Tests for the independent plan verifier (Pair D).

Each test builds a tiny problem by hand, gives the verifier a good or a
deliberately broken plan, and checks it catches exactly the right rule.
"""

import ast
import os
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.verification import NOT_TAKEN, verify_plan  # noqa: E402

CORE = "Discipline Core"
ELECTIVE = "Discipline Elective"


def course(credits=4, category=CORE, parity=None, formula=None):
    return {"credits": credits, "category": category, "parity": parity, "formula": formula}


def pre(code):
    return {"kind": "leaf", "course": code, "relation": "PRE"}


def co(code):
    return {"kind": "leaf", "course": code, "relation": "CO"}


def problem(courses, **overrides):
    base = {
        "courses": courses,
        "completed": set(),
        "current_semester": 0,
        "target_semester": 4,
        "max_credits": 8,
        "min_credits": 0,
        "category_minimums": {},
        "assume_out_of_scope_satisfied": True,
    }
    base.update(overrides)
    return base


@pytest.fixture
def chain():
    """A -> B -> C prerequisite chain plus one optional elective."""
    return problem({
        "A": course(),
        "B": course(formula=pre("A")),
        "C": course(formula=pre("B")),
        "E": course(category=ELECTIVE),
    })


# ── valid plans ──────────────────────────────────────────────────────────────

def test_valid_plan_passes(chain):
    report = verify_plan(chain, {"A": 1, "B": 2, "C": 3, "E": NOT_TAKEN})
    assert report.valid, report.summary()
    assert report.violations == []


def test_missing_elective_counts_as_not_taken(chain):
    assert verify_plan(chain, {"A": 1, "B": 2, "C": 3}).valid


def test_accepts_object_with_assignment(chain):
    class FakeResult:
        assignment = {"A": 1, "B": 2, "C": 3, "E": 4}

    assert verify_plan(chain, FakeResult()).valid


def test_completed_courses_satisfy_prerequisites(chain):
    chain["completed"] = {"A"}
    assert verify_plan(chain, {"B": 1, "C": 2}).valid


# ── each rule is caught ─────────────────────────────────────────────────────

def test_prereq_same_semester_is_caught(chain):
    report = verify_plan(chain, {"A": 1, "B": 1, "C": 3})
    assert report.kinds() == {"prereq"}
    assert report.violations[0].constraint == "prereq:B"


def test_prereq_in_wrong_order_is_caught(chain):
    report = verify_plan(chain, {"A": 3, "B": 2, "C": 4})
    assert [v.constraint for v in report.violations] == ["prereq:B"]


def test_corequisite_same_semester_is_allowed():
    p = problem({"LAB": course(2, formula=co("THEORY")), "THEORY": course(3)})
    assert verify_plan(p, {"LAB": 1, "THEORY": 1}).valid
    assert not verify_plan(p, {"LAB": 1, "THEORY": 2}).valid


def test_or_prerequisite_needs_only_one_branch():
    formula = {"kind": "and", "items": [
        pre("CS F211"),
        {"kind": "or", "items": [pre("MATH F211"), pre("MATH F213")]},
    ]}
    p = problem(
        {
            "CS F211": course(2),
            "MATH F211": course(2, category=ELECTIVE),
            "MATH F213": course(2, category=ELECTIVE),
            "CS F301": course(2, formula=formula),
        },
    )
    good = {"CS F211": 1, "MATH F213": 1, "MATH F211": NOT_TAKEN, "CS F301": 2}
    assert verify_plan(p, good).valid
    bad = {"CS F211": 1, "MATH F211": NOT_TAKEN, "MATH F213": NOT_TAKEN, "CS F301": 2}
    assert verify_plan(p, bad).kinds() == {"prereq"}


def test_out_of_scope_prerequisite_follows_problem_flag():
    p = problem({"X": course(formula=pre("NOT IN CATALOGUE"))})
    assert verify_plan(p, {"X": 1}).valid
    p["assume_out_of_scope_satisfied"] = False
    assert verify_plan(p, {"X": 1}).kinds() == {"prereq"}


def test_parity_is_caught():
    p = problem({"EVEN": course(parity="even"), "ODD": course(parity="odd")})
    report = verify_plan(p, {"EVEN": 1, "ODD": 2})
    assert {v.constraint for v in report.violations} == {"parity:EVEN", "parity:ODD"}
    assert verify_plan(p, {"EVEN": 2, "ODD": 1}).valid


def test_credit_cap_is_caught(chain):
    chain["max_credits"] = 4
    report = verify_plan(chain, {"A": 1, "B": 2, "C": 3, "E": 1})
    assert [v.constraint for v in report.violations] == ["credit_cap:1"]


def test_credit_floor_applies_only_until_graduation(chain):
    chain["min_credits"] = 4
    chain["target_semester"] = 6
    # Graduates in semester 3; semesters 4-6 are empty and that is fine.
    assert verify_plan(chain, {"A": 1, "B": 2, "C": 3}).valid
    # An empty semester before graduation is not fine.
    report = verify_plan(chain, {"A": 1, "B": 3, "C": 4})
    assert [v.constraint for v in report.violations] == ["credit_floor:2"]


def test_horizon_is_caught(chain):
    report = verify_plan(chain, {"A": 1, "B": 2, "C": 5})
    assert [v.constraint for v in report.violations] == ["horizon:C"]


def test_semester_already_finished_is_caught(chain):
    chain["current_semester"] = 2
    chain["target_semester"] = 6
    report = verify_plan(chain, {"A": 2, "B": 3, "C": 4})
    assert "horizon:A" in {v.constraint for v in report.violations}


def test_core_not_taken_is_caught(chain):
    report = verify_plan(chain, {"A": 1, "B": 2, "C": NOT_TAKEN})
    assert [v.constraint for v in report.violations] == ["core_not_taken:C"]


def test_category_minimum_is_caught(chain):
    chain["category_minimums"] = {ELECTIVE: 4}
    report = verify_plan(chain, {"A": 1, "B": 2, "C": 3, "E": NOT_TAKEN})
    assert [v.constraint for v in report.violations] == [f"category_min:{ELECTIVE}"]
    assert verify_plan(chain, {"A": 1, "B": 2, "C": 3, "E": 1}).valid


def test_category_minimum_counts_completed_courses(chain):
    chain["completed"] = {"E"}
    chain["category_minimums"] = {ELECTIVE: 4}
    assert verify_plan(chain, {"A": 1, "B": 2, "C": 3}).valid


def test_unknown_and_already_completed_courses_are_caught(chain):
    chain["completed"] = {"A"}
    report = verify_plan(chain, {"A": 1, "B": 2, "C": 3, "GHOST": 1})
    assert {v.kind for v in report.violations} == {"unknown_course", "already_completed"}


def test_bad_semester_value_is_caught(chain):
    report = verify_plan(chain, {"A": "1", "B": 2, "C": 3})
    assert "bad_semester" in report.kinds()


def test_reports_every_problem_not_just_the_first(chain):
    chain["max_credits"] = 4
    report = verify_plan(chain, {"A": 1, "B": 1, "C": NOT_TAKEN})
    assert report.kinds() == {"prereq", "credit_cap", "core_not_taken"}
    assert "3 problem(s)" in report.summary()


def test_none_plan_raises():
    with pytest.raises(ValueError):
        verify_plan(problem({}), None)


# ── independence from the solvers ───────────────────────────────────────────

def test_verifier_imports_no_solver_code():
    """The verifier must not reuse solver or shared-model code (proposal §3)."""
    folder = os.path.join(_ROOT, "backend", "verification")
    forbidden = ("backend.csp", "backend.astar", "backend.models", "backend.ml")
    for name in os.listdir(folder):
        if not name.endswith(".py"):
            continue
        with open(os.path.join(folder, name), encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
            elif isinstance(node, ast.Import):
                module = ",".join(alias.name for alias in node.names)
            else:
                continue
            assert not any(module.startswith(f) for f in forbidden), (name, module)
            assert not module.startswith(("csp", "astar", "models")), (name, module)


def test_works_with_shared_problem_object():
    """Same answer whether the problem is a dict or Pair B's Problem class."""
    model = pytest.importorskip("backend.csp.model")
    p = model.Problem(
        courses={"A": course(), "B": course(formula=pre("A"))},
        completed=set(),
        current_semester=0,
        target_semester=4,
        max_credits=8,
    )
    assert verify_plan(p, {"A": 1, "B": 2}).valid
    assert not verify_plan(p, {"A": 2, "B": 2}).valid
