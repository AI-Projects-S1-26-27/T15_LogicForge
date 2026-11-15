"""Infeasibility analyser (Pair D).

When no plan exists, this finds *which* rules clash and *what to relax*,
instead of returning nothing.

How it works
------------
1. Every rule the student could ask to bend is a "unit":

   ``horizon``            graduate by ``target_semester``
   ``credit_cap``         at most ``max_credits`` per semester
   ``credit_floor``       at least ``min_credits`` per semester
   ``prereq:<COURSE>``    that course's prerequisite formula
   ``parity:<COURSE>``    that course is only offered in odd/even terms
   ``category_min:<CAT>`` that category's credit minimum

   (A core course still has to be taken; that rule is never relaxed.)

2. Deletion-based conflict extraction (Junker 2004, the "deletion"
   variant): start with every unit switched on, then try switching each
   one off. If the problem is *still* impossible without it, it is not
   part of the conflict and stays off. What is left is a conflict set
   where every unit is needed: switch any one off and a plan exists.
   That makes the set *minimal* (no smaller subset of it conflicts),
   not necessarily the smallest conflict overall.

3. For each unit in the conflict, find a concrete relaxation (e.g. "allow
   22 credits", "graduate 1 semester later") and re-solve to check it
   really works.

Relaxing a unit builds a modified copy of the problem (e.g. no formula,
no parity, a higher cap), so the analyser works with *any* solver: pass
an ``oracle`` that takes a problem and returns "SAT", "UNSAT" or
"TIMEOUT". The default oracle is Pair B's CSP solver.
"""

from __future__ import annotations

import copy
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

Oracle = Callable[[Any], str]

SAT, UNSAT, TIMEOUT = "SAT", "UNSAT", "TIMEOUT"

# How far the analyser looks when searching for a concrete relaxation.
EXTRA_SEMESTERS_TRIED = 6
EXTRA_CREDITS_TRIED = 12
# A relaxed horizon / cap is "big enough to never bind".
_UNBOUNDED_CREDITS = 10_000


# ── result types ─────────────────────────────────────────────────────────────

@dataclass
class Relaxation:
    """One concrete change that would make a plan possible (or help)."""

    unit: str
    description: str
    fixes_alone: bool | None  # True = re-solved and a plan exists; None = solver timed out


@dataclass
class InfeasibilityReport:
    status: str                      # "feasible", "infeasible" or "unknown"
    conflict: list[str] = field(default_factory=list)
    explanations: list[str] = field(default_factory=list)
    relaxations: list[Relaxation] = field(default_factory=list)
    minimal: bool = True             # False if a solver timeout forced a guess
    solver_calls: int = 0
    time_s: float = 0.0

    def summary(self) -> str:
        if self.status == "feasible":
            return "A valid plan exists; nothing to diagnose."
        if self.status == "unknown":
            return "The solver timed out on the full problem, so it is unknown whether a plan exists."
        lines = ["No valid plan exists. These rules clash with each other:"]
        lines += [f"- {text}" for text in self.explanations]
        if not self.minimal:
            lines.append("(Some checks timed out, so this list may contain an extra rule.)")
        if self.relaxations:
            lines.append("Any one of these changes would help:")
            for r in self.relaxations:
                tag = "" if r.fixes_alone else " (needed, but not enough on its own)"
                if r.fixes_alone is None:
                    tag = " (not confirmed: solver timed out)"
                lines.append(f"- {r.description}{tag}")
        return "\n".join(lines)


# ── reading the problem without caring about its exact class ─────────────────

def _get(problem: Any, name: str, default: Any = None) -> Any:
    if isinstance(problem, dict):
        return problem.get(name, default)
    return getattr(problem, name, default)


def _set(problem: Any, name: str, value: Any) -> None:
    if isinstance(problem, dict):
        problem[name] = value
    else:
        setattr(problem, name, value)


def _outstanding(problem: Any) -> list[str]:
    completed = set(_get(problem, "completed", set()) or set())
    return sorted(code for code in _get(problem, "courses", {}) if code not in completed)


def candidate_units(problem: Any) -> list[str]:
    """All the rules the analyser may switch off, in a stable order."""
    courses = _get(problem, "courses", {})
    units = ["horizon", "credit_cap"]
    if int(_get(problem, "min_credits", 0) or 0) > 0:
        units.append("credit_floor")
    for category in sorted(_get(problem, "category_minimums", {}) or {}):
        units.append(f"category_min:{category}")
    for code in _outstanding(problem):
        info = courses[code]
        if info.get("formula"):
            units.append(f"prereq:{code}")
        if info.get("parity") in ("odd", "even"):
            units.append(f"parity:{code}")
    return units


def relaxed_problem(
    problem: Any,
    enabled: Iterable[str],
    *,
    extra_semesters: int = EXTRA_SEMESTERS_TRIED,
    overrides: dict[str, Any] | None = None,
) -> Any:
    """Copy of ``problem`` where every unit NOT in ``enabled`` is switched off.

    ``overrides`` lets a caller set a specific relaxed value instead of
    "off", e.g. ``{"max_credits": 22}``.
    """
    enabled = set(enabled)
    variant = copy.deepcopy(problem)
    courses = _get(variant, "courses")
    for unit in candidate_units(problem):
        if unit in enabled:
            continue
        kind, _, target = unit.partition(":")
        if kind == "horizon":
            _set(variant, "target_semester", int(_get(problem, "target_semester")) + extra_semesters)
        elif kind == "credit_cap":
            _set(variant, "max_credits", _UNBOUNDED_CREDITS)
        elif kind == "credit_floor":
            _set(variant, "min_credits", 0)
        elif kind == "category_min":
            minimums = dict(_get(variant, "category_minimums") or {})
            minimums.pop(target, None)
            _set(variant, "category_minimums", minimums)
        elif kind == "prereq":
            courses[target] = {**courses[target], "formula": None}
        elif kind == "parity":
            courses[target] = {**courses[target], "parity": None}
    for name, value in (overrides or {}).items():
        _set(variant, name, value)
    return variant


# ── default oracle: Pair B's CSP solver ──────────────────────────────────────

def csp_oracle(timeout_s: float = 10.0) -> Oracle:
    """Feasibility check using the CSP solver with all its speed-ups on."""
    from backend.csp.solver import SolverConfig, solve

    config = SolverConfig(mrv=True, forward_checking=True, ac3=True,
                          degree_tiebreak=True, timeout_s=timeout_s)

    def oracle(problem: Any) -> str:
        return solve(problem, config).status

    return oracle


# ── the analyser ─────────────────────────────────────────────────────────────

def analyze(problem: Any, oracle: Oracle | None = None) -> InfeasibilityReport:
    """Explain why ``problem`` has no plan, and suggest relaxations."""
    oracle = oracle or csp_oracle()
    started = time.perf_counter()
    calls = 0

    def status_with(enabled: Iterable[str], **kw) -> str:
        nonlocal calls
        calls += 1
        return oracle(relaxed_problem(problem, enabled, **kw))

    units = candidate_units(problem)
    first = status_with(units)
    if first != UNSAT:
        report = InfeasibilityReport("feasible" if first == SAT else "unknown")
        report.solver_calls, report.time_s = calls, time.perf_counter() - started
        return report

    # If the problem is impossible even with every unit relaxed, the clash is
    # in the rules we never relax (a required course that cannot be placed).
    if status_with([]) == UNSAT:
        report = InfeasibilityReport(
            "infeasible",
            conflict=["required_courses"],
            explanations=["Some required course cannot be scheduled even with every "
                          "other rule relaxed (check its data, e.g. credits above any cap)."],
        )
        report.solver_calls, report.time_s = calls, time.perf_counter() - started
        return report

    # Deletion pass: drop every unit whose removal keeps the problem impossible.
    # Course-level rules are tried first and the student's own settings
    # (credit cap, graduation semester) last, so when several conflicts
    # exist the one reported is the one the student can act on.
    core = list(units)
    minimal = True
    for unit in sorted(core, key=_deletion_priority):
        trial = [u for u in core if u != unit]
        result = status_with(trial)
        if result == UNSAT:
            core = trial
        elif result == TIMEOUT:
            minimal = False  # cannot tell, so keep it to stay safe

    relaxations = [_relaxation_for(problem, unit, core, status_with) for unit in core]
    report = InfeasibilityReport(
        "infeasible",
        conflict=core,
        explanations=[_explain(problem, unit) for unit in core],
        relaxations=relaxations,
        minimal=minimal,
    )
    report.solver_calls, report.time_s = calls, time.perf_counter() - started
    return report


_PRIORITY = {"prereq": 0, "parity": 1, "category_min": 2, "credit_floor": 3,
             "credit_cap": 4, "horizon": 5}


def _deletion_priority(unit: str) -> int:
    return _PRIORITY.get(unit.partition(":")[0], 0)


# ── plain-English text ───────────────────────────────────────────────────────

def _describe_formula(formula: dict | None) -> str:
    if not formula:
        return "nothing"
    if formula.get("kind") == "leaf":
        return formula["course"] + (" (same term allowed)" if formula.get("relation") == "CO" else "")
    joiner = " AND " if formula.get("kind") == "and" else " OR "
    inner = joiner.join(_describe_formula(item) for item in formula.get("items", []))
    return f"({inner})"


def _explain(problem: Any, unit: str) -> str:
    kind, _, target = unit.partition(":")
    courses = _get(problem, "courses", {})
    if kind == "horizon":
        return f"You must graduate by semester {_get(problem, 'target_semester')}."
    if kind == "credit_cap":
        return f"Each semester allows at most {_get(problem, 'max_credits')} credits."
    if kind == "credit_floor":
        return f"Each semester until graduation needs at least {_get(problem, 'min_credits')} credits."
    if kind == "category_min":
        minimum = (_get(problem, "category_minimums") or {}).get(target)
        return f"{target} needs at least {minimum} credits."
    if kind == "prereq":
        return f"{target} needs {_describe_formula(courses[target].get('formula'))} first."
    if kind == "parity":
        return f"{target} is only offered in {courses[target].get('parity')} semesters."
    return unit


def _relaxation_for(problem: Any, unit: str, core: list[str], status_with) -> Relaxation:
    """Find the gentlest version of relaxing ``unit`` that gives a plan.

    Everything except ``unit`` stays switched on (all original units, not
    just the core), so a suggestion marked as fixing it really does.
    """
    everything = candidate_units(problem)
    others = [u for u in everything if u != unit]
    kind, _, target = unit.partition(":")

    if kind == "horizon":
        target_sem = int(_get(problem, "target_semester"))
        for extra in range(1, EXTRA_SEMESTERS_TRIED + 1):
            result = status_with(everything, overrides={"target_semester": target_sem + extra})
            if result == SAT:
                return Relaxation(unit, f"Graduate {extra} semester(s) later "
                                        f"(by semester {target_sem + extra}).", True)
        return _fallback(unit, "Graduate later.", status_with, others)

    if kind == "credit_cap":
        cap = int(_get(problem, "max_credits"))
        for extra in range(1, EXTRA_CREDITS_TRIED + 1):
            result = status_with(everything, overrides={"max_credits": cap + extra})
            if result == SAT:
                return Relaxation(unit, f"Allow up to {cap + extra} credits in a semester "
                                        f"(an overload of {extra}).", True)
        return _fallback(unit, "Allow a credit overload.", status_with, others)

    if kind == "credit_floor":
        floor = int(_get(problem, "min_credits"))
        for lower in range(floor - 1, -1, -1):
            if status_with(everything, overrides={"min_credits": lower}) == SAT:
                return Relaxation(unit, f"Allow a lighter semester (at least {lower} "
                                        f"credits instead of {floor}).", True)
        return _fallback(unit, "Allow a lighter semester.", status_with, others)

    if kind == "category_min":
        minimum = int((_get(problem, "category_minimums") or {})[target])
        for lower in range(minimum - 1, -1, -1):
            minimums = dict(_get(problem, "category_minimums"))
            minimums[target] = lower
            if status_with(everything, overrides={"category_minimums": minimums}) == SAT:
                return Relaxation(unit, f"Reduce the {target} requirement from {minimum} "
                                        f"to {lower} credits (e.g. via a substitution approved "
                                        f"by the department).", True)
        return _fallback(unit, f"Reduce the {target} requirement.", status_with, others)

    if kind == "prereq":
        return _fallback(unit, f"Get a prerequisite waiver for {target}, or take it "
                               f"alongside its prerequisite with permission.", status_with, others)
    if kind == "parity":
        parity = _get(problem, "courses")[target].get("parity")
        other = "even" if parity == "odd" else "odd"
        return _fallback(unit, f"Take {target} in an {other} semester (e.g. a special "
                               f"or summer offering).", status_with, others)
    return _fallback(unit, f"Relax {unit}.", status_with, others)


def _fallback(unit: str, text: str, status_with, others: list[str]) -> Relaxation:
    """Switch ``unit`` fully off and check whether that alone is enough."""
    result = status_with(others)
    return Relaxation(unit, text, True if result == SAT else (None if result == TIMEOUT else False))
