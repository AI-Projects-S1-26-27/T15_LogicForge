"""Plan explainer (Pair D): a derivation trace for every course in a plan.

For each course it says, in plain English:
- which prerequisites made it allowed, and when they were done
  (for an OR, which option was actually used),
- whether the term is restricted to odd/even semesters,
- the earliest semester it could have gone in, and if it was placed later,
  why (that semester was full, or simply the solver's choice),
- which later courses depend on it.

Like the verifier, it re-derives everything from the problem and the plan,
so it works for plans from either solver.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.verification.plan_checker import NOT_TAKEN


@dataclass
class CourseExplanation:
    course: str
    semester: Any
    reasons: list[str] = field(default_factory=list)

    def text(self) -> str:
        return f"{self.course} -> " + (
            "not taken" if self.semester == NOT_TAKEN else f"semester {self.semester}"
        ) + ": " + " ".join(self.reasons)


@dataclass
class PlanExplanation:
    courses: list[CourseExplanation]
    semester_loads: dict[int, int]
    graduation_semester: int | None

    def by_course(self) -> dict[str, CourseExplanation]:
        return {c.course: c for c in self.courses}

    def text(self) -> str:
        lines = []
        for sem, load in self.semester_loads.items():
            lines.append(f"Semester {sem}: {load} credits")
            lines += [f"  {c.text()}" for c in self.courses if c.semester == sem]
        skipped = [c for c in self.courses if c.semester == NOT_TAKEN]
        if skipped:
            lines.append("Not taken:")
            lines += [f"  {c.text()}" for c in skipped]
        return "\n".join(lines)


def _get(problem: Any, name: str, default: Any = None) -> Any:
    if isinstance(problem, dict):
        return problem.get(name, default)
    return getattr(problem, name, default)


def _is_sem(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _leaves(formula: dict | None) -> list[dict]:
    if not formula:
        return []
    if formula.get("kind") == "leaf":
        return [formula]
    out: list[dict] = []
    for item in formula.get("items", []):
        out += _leaves(item)
    return out


class _Context:
    def __init__(self, problem: Any, assignment: dict[str, Any]):
        self.courses = _get(problem, "courses", {}) or {}
        self.completed = set(_get(problem, "completed", set()) or set())
        self.current = int(_get(problem, "current_semester", 0) or 0)
        self.target = int(_get(problem, "target_semester", 0) or 0)
        self.max_credits = int(_get(problem, "max_credits", 0) or 0)
        self.out_of_scope_ok = bool(_get(problem, "assume_out_of_scope_satisfied", True))
        self.assignment = assignment

    def leaf_status(self, leaf: dict, semester: int) -> tuple[bool, str]:
        target = leaf["course"]
        same_ok = leaf.get("relation") == "CO"
        if target in self.completed:
            return True, f"{target} (already completed)"
        if target not in self.courses:
            return self.out_of_scope_ok, f"{target} (outside this curriculum, assumed done)"
        when = self.assignment.get(target)
        if _is_sem(when) and (when <= semester if same_ok else when < semester):
            same = " (same semester allowed)" if same_ok and when == semester else ""
            return True, f"{target} (semester {when}{same})"
        return False, f"{target} (not done in time)"

    def formula_ok(self, formula: dict | None, semester: int) -> bool:
        if not formula:
            return True
        kind = formula.get("kind")
        if kind == "leaf":
            return self.leaf_status(formula, semester)[0]
        results = [self.formula_ok(item, semester) for item in formula.get("items", [])]
        return all(results) if kind == "and" else any(results)

    def how_satisfied(self, formula: dict | None, semester: int) -> str:
        """Which parts of the formula were actually used."""
        if not formula:
            return ""
        kind = formula.get("kind")
        if kind == "leaf":
            return self.leaf_status(formula, semester)[1]
        items = formula.get("items", [])
        if kind == "and":
            return " and ".join(self.how_satisfied(i, semester) for i in items)
        for item in items:  # OR: report the first option that holds
            if self.formula_ok(item, semester):
                return self.how_satisfied(item, semester) + " (one of the allowed options)"
        return "no option satisfied"

    def earliest(self, code: str) -> int | None:
        parity = self.courses[code].get("parity")
        for sem in range(self.current + 1, self.target + 1):
            if parity == "odd" and sem % 2 == 0:
                continue
            if parity == "even" and sem % 2 == 1:
                continue
            if self.formula_ok(self.courses[code].get("formula"), sem):
                return sem
        return None


def explain_plan(problem: Any, plan: Any) -> PlanExplanation:
    """Build a readable explanation for every outstanding course in ``plan``."""
    assignment = dict(plan if isinstance(plan, dict) else getattr(plan, "assignment"))
    ctx = _Context(problem, assignment)

    loads: dict[int, int] = {}
    for code, sem in assignment.items():
        if _is_sem(sem) and code in ctx.courses:
            loads[sem] = loads.get(sem, 0) + int(ctx.courses[code].get("credits") or 0)
    loads = dict(sorted(loads.items()))

    dependants: dict[str, list[str]] = {}
    for code, info in ctx.courses.items():
        for leaf in _leaves(info.get("formula")):
            dependants.setdefault(leaf["course"], []).append(code)

    explanations: list[CourseExplanation] = []
    for code in sorted(c for c in ctx.courses if c not in ctx.completed):
        info = ctx.courses[code]
        sem = assignment.get(code, NOT_TAKEN)
        reasons: list[str] = []
        if not _is_sem(sem):
            reasons.append(f"{info.get('category') or 'This'} course is optional and the "
                           f"plan meets its requirements without it.")
            explanations.append(CourseExplanation(code, NOT_TAKEN, reasons))
            continue

        formula = info.get("formula")
        if formula:
            reasons.append(f"Allowed because of: {ctx.how_satisfied(formula, sem)}.")
        else:
            reasons.append("No prerequisites.")

        parity = info.get("parity")
        if parity in ("odd", "even"):
            reasons.append(f"Offered only in {parity} semesters.")

        earliest = ctx.earliest(code)
        if earliest is not None and earliest < sem:
            load = loads.get(earliest, 0)
            credits = int(info.get("credits") or 0)
            if ctx.max_credits and load + credits > ctx.max_credits:
                reasons.append(f"Could have gone in semester {earliest}, but that semester "
                               f"was full ({load}/{ctx.max_credits} credits).")
            else:
                reasons.append(f"Could also go in semester {earliest}; the planner chose "
                               f"{sem} to balance the load.")
        elif earliest == sem:
            reasons.append("This is the earliest semester it was possible.")

        later = sorted(
            d for d in dependants.get(code, [])
            if _is_sem(assignment.get(d)) and assignment[d] >= sem
        )
        if later:
            reasons.append("Needed before: " + ", ".join(
                f"{d} (semester {assignment[d]})" for d in later) + ".")
        explanations.append(CourseExplanation(code, sem, reasons))

    explanations.sort(key=lambda c: (c.semester == NOT_TAKEN,
                                     c.semester if _is_sem(c.semester) else 0, c.course))
    graduation = max(loads) if loads else None
    return PlanExplanation(explanations, loads, graduation)
