"""Independent plan verifier (Pair D).

Takes a planning problem and a proposed plan, and re-checks every rule
from scratch. It imports nothing from ``backend.csp``, ``backend.astar`` or
``backend.models``. Every rule is written again here on purpose, so a bug
in a solver or in the shared model cannot hide itself (experiment E4).

Input
-----
``problem`` can be the shared ``Problem`` object or a plain dict with the
same fields:

    courses              {code: {"credits", "category", "parity", "formula"}}
    completed            set of course codes already passed
    current_semester     last semester already finished
    target_semester      last semester the plan may use
    max_credits          per-semester credit cap
    min_credits          per-semester credit floor (0 = none)
    category_minimums    {category: credits needed}
    assume_out_of_scope_satisfied
                         prerequisites that are not in the catalogue count
                         as met when True

``plan`` can be an assignment dict ``{code: semester | "NOT_TAKEN"}``, a
``StudyPlan``, or a solver ``Result`` (anything with an ``.assignment``).

Rules checked (shared assumptions with Pairs B and C)
-----------------------------------------------------
- Every outstanding core course is scheduled. Electives may be NOT_TAKEN.
  A category counts as elective if its name contains "elective", except
  "Discipline Core" and "University Core (First Year)".
- Each scheduled semester is after ``current_semester`` and no later than
  ``target_semester``.
- Odd-only courses go in odd semesters, even-only courses in even ones.
- Prerequisites (relation "PRE") are in a strictly earlier semester or
  already completed. Corequisites ("CO") may be in the same semester.
- No semester goes over ``max_credits``.
- Every semester up to graduation (the last scheduled semester) has at
  least ``min_credits``.
- Each category reaches its credit minimum from completed + scheduled
  courses.
- The plan does not schedule unknown or already-completed courses.

The output is a ``VerificationReport`` listing every violation, not just
the first, using the same constraint names as the shared model
(``prereq:<COURSE>``, ``credit_cap:<SEM>``, ``category_min:<CATEGORY>``)
plus a few extra kinds for rules the model does not name.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

NOT_TAKEN = "NOT_TAKEN"

_ALWAYS_REQUIRED = {"Discipline Core", "University Core (First Year)"}


# ── result types ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Violation:
    """One broken rule.

    ``kind`` is the rule family, ``constraint`` the full constraint name
    (e.g. ``prereq:CS F212``), and ``message`` a plain-English sentence for
    the interface.
    """

    kind: str
    constraint: str
    message: str
    course: str | None = None
    semester: int | None = None


@dataclass
class VerificationReport:
    """Everything the verifier found about one plan."""

    valid: bool
    violations: list[Violation] = field(default_factory=list)
    checked: dict[str, int] = field(default_factory=dict)

    def kinds(self) -> set[str]:
        return {v.kind for v in self.violations}

    def summary(self) -> str:
        if self.valid:
            return "Plan is valid: every rule checked passed."
        lines = [f"Plan is NOT valid: {len(self.violations)} problem(s) found."]
        lines += [f"- {v.message}" for v in self.violations]
        return "\n".join(lines)


# ── reading the inputs without depending on solver classes ──────────────────

def _field(problem: Any, name: str, default: Any = None) -> Any:
    if isinstance(problem, Mapping):
        return problem.get(name, default)
    return getattr(problem, name, default)


def _assignment_of(plan: Any) -> dict[str, Any]:
    if plan is None:
        raise ValueError("No plan to verify (got None).")
    if isinstance(plan, Mapping):
        return dict(plan)
    assignment = getattr(plan, "assignment", None)
    if assignment is None:
        raise ValueError("This plan has no assignment, so it cannot be verified.")
    return dict(assignment)


def _is_elective(category: str | None) -> bool:
    name = category or ""
    if name in _ALWAYS_REQUIRED:
        return False
    return "elective" in name.lower()


def _parity_ok(parity: str | None, semester: int) -> bool:
    if parity == "odd":
        return semester % 2 == 1
    if parity == "even":
        return semester % 2 == 0
    return True


def _credits(info: Mapping[str, Any]) -> int:
    return int(info.get("credits") or 0)


# ── prerequisite formulas ───────────────────────────────────────────────────

def _leaf_met(
    leaf: Mapping[str, Any],
    semester: int,
    assignment: Mapping[str, Any],
    courses: Mapping[str, Any],
    completed: set[str],
    out_of_scope_ok: bool,
) -> bool:
    target = leaf.get("course")
    relation = leaf.get("relation", "PRE")
    if target in completed:
        return True
    if target not in courses:
        # Not in the catalogue at all: follow the problem's assumption.
        return out_of_scope_ok
    when = assignment.get(target)
    if not _is_semester(when):
        return False
    if relation == "CO":
        return when <= semester
    return when < semester


def _formula_met(formula, semester, assignment, courses, completed, out_of_scope_ok) -> bool:
    if not formula:
        return True
    kind = formula.get("kind")
    args = (semester, assignment, courses, completed, out_of_scope_ok)
    if kind == "leaf":
        return _leaf_met(formula, *args)
    if kind == "and":
        return all(_formula_met(item, *args) for item in formula.get("items", []))
    if kind == "or":
        return any(_formula_met(item, *args) for item in formula.get("items", []))
    raise ValueError(f"Unknown prerequisite node kind: {kind!r}")


def _describe(formula: Mapping[str, Any] | None) -> str:
    """Turn a formula tree back into readable text for messages."""
    if not formula:
        return "nothing"
    kind = formula.get("kind")
    if kind == "leaf":
        suffix = " (same term allowed)" if formula.get("relation") == "CO" else ""
        return f"{formula.get('course')}{suffix}"
    joiner = " AND " if kind == "and" else " OR "
    parts = [_describe(item) for item in formula.get("items", [])]
    inner = joiner.join(parts)
    return f"({inner})" if len(parts) > 1 else inner


def _is_semester(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


# ── the verifier ────────────────────────────────────────────────────────────

def verify_plan(problem: Any, plan: Any) -> VerificationReport:
    """Check ``plan`` against every rule of ``problem``. Never raises on a bad plan."""
    courses: Mapping[str, Mapping[str, Any]] = _field(problem, "courses", {}) or {}
    completed = set(_field(problem, "completed", set()) or set())
    current = int(_field(problem, "current_semester", 0) or 0)
    target = int(_field(problem, "target_semester", 0) or 0)
    max_credits = int(_field(problem, "max_credits", 0) or 0)
    min_credits = int(_field(problem, "min_credits", 0) or 0)
    minimums: Mapping[str, int] = _field(problem, "category_minimums", {}) or {}
    out_of_scope_ok = bool(_field(problem, "assume_out_of_scope_satisfied", True))

    assignment = _assignment_of(plan)
    violations: list[Violation] = []
    checked = {"courses": 0, "prerequisites": 0, "semesters": 0, "categories": 0}

    def add(kind, constraint, message, course=None, semester=None):
        violations.append(Violation(kind, constraint, message, course, semester))

    # 1. Courses the plan mentions that it should not.
    for code in sorted(assignment):
        if code not in courses:
            add("unknown_course", f"unknown_course:{code}",
                f"{code} is not in the curriculum, so it cannot be planned.", code)
        elif code in completed and assignment[code] != NOT_TAKEN:
            add("already_completed", f"already_completed:{code}",
                f"{code} is already completed but is scheduled again in "
                f"semester {assignment[code]}.", code, assignment[code])

    outstanding = sorted(code for code in courses if code not in completed)

    # 2. Every outstanding course: taken when it must be, in a legal semester.
    scheduled: dict[str, int] = {}
    for code in outstanding:
        info = courses[code]
        checked["courses"] += 1
        value = assignment.get(code, NOT_TAKEN)

        if value == NOT_TAKEN:
            if not _is_elective(info.get("category")):
                add("core_not_taken", f"core_not_taken:{code}",
                    f"{code} is a required ({info.get('category') or 'uncategorised'}) "
                    f"course but the plan never schedules it.", code)
            continue

        if not _is_semester(value):
            add("bad_semester", f"bad_semester:{code}",
                f"{code} has an invalid semester value {value!r}.", code)
            continue

        scheduled[code] = value
        if not (current < value <= target):
            add("horizon", f"horizon:{code}",
                f"{code} is in semester {value}, outside the allowed range "
                f"{current + 1} to {target}.", code, value)
        parity = info.get("parity")
        if not _parity_ok(parity, value):
            add("parity", f"parity:{code}",
                f"{code} is only offered in {parity} semesters but is planned "
                f"in semester {value}.", code, value)

    # 3. Prerequisites and corequisites of every scheduled course.
    for code, value in sorted(scheduled.items()):
        formula = courses[code].get("formula")
        if not formula:
            continue
        checked["prerequisites"] += 1
        if not _formula_met(formula, value, assignment, courses, completed, out_of_scope_ok):
            add("prereq", f"prereq:{code}",
                f"{code} in semester {value} needs {_describe(formula)} "
                f"done earlier, which the plan does not satisfy.", code, value)

    # 4. Credits per semester.
    load: dict[int, int] = {}
    for code, value in scheduled.items():
        load[value] = load.get(value, 0) + _credits(courses[code])
    graduation = max(scheduled.values(), default=current)
    for semester in range(current + 1, max(target, graduation) + 1):
        checked["semesters"] += 1
        credits = load.get(semester, 0)
        if max_credits and credits > max_credits:
            add("credit_cap", f"credit_cap:{semester}",
                f"Semester {semester} has {credits} credits, over the cap of "
                f"{max_credits}.", semester=semester)
        if min_credits > 0 and semester <= graduation and credits < min_credits:
            add("credit_floor", f"credit_floor:{semester}",
                f"Semester {semester} has only {credits} credits, under the "
                f"minimum of {min_credits}.", semester=semester)

    # 5. Category credit minimums.
    for category, minimum in sorted(minimums.items()):
        checked["categories"] += 1
        earned = sum(
            _credits(info)
            for code, info in courses.items()
            if info.get("category") == category
            and (code in completed or code in scheduled)
        )
        if earned < int(minimum):
            add("category_min", f"category_min:{category}",
                f"{category} reaches only {earned} of the {minimum} credits needed.")

    return VerificationReport(valid=not violations, violations=violations, checked=checked)


def verify_many(problem: Any, plans: Iterable[Any]) -> list[VerificationReport]:
    """Verify several plans for the same problem (handy for E4)."""
    return [verify_plan(problem, plan) for plan in plans]
