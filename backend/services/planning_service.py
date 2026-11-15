"""Planning service (Pair D): the one entry point the app calls.

transcript -> Problem -> solver (CSP or A*) -> independent verifier
           -> plan explanation, or infeasibility diagnosis if no plan exists

A solver's plan is only shown as valid if the verifier agrees. If they
disagree the response says so instead of showing a wrong plan.

Command line (handy without the Streamlit app):
    python -m backend.services.planning_service --branch cse --current 3 \
        --completed "CS F111,CS F222,CS F214,CS F215" --max-credits 20
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, field
from typing import Any, Iterable

from backend.explanations.infeasibility_analyzer import InfeasibilityReport, analyze
from backend.explanations.plan_explainer import PlanExplanation, explain_plan
from backend.services.problem_builder import DEFAULT_CURRICULUM_DIR, build_problem_for_student
from backend.verification import NOT_TAKEN, VerificationReport, verify_plan

SOLVERS = ("csp", "astar")


@dataclass
class PlanResponse:
    status: str                       # "PLAN", "NO_PLAN", "TIMEOUT", "SOLVER_BUG"
    solver: str
    message: str
    problem: Any = None
    assignment: dict | None = None
    semesters: dict[int, list[dict]] = field(default_factory=dict)
    not_taken: list[str] = field(default_factory=list)
    verification: VerificationReport | None = None
    explanation: PlanExplanation | None = None
    infeasibility: InfeasibilityReport | None = None
    warnings: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    def text(self) -> str:
        lines = [self.message]
        lines += [f"Warning: {w}" for w in self.warnings]
        if self.status == "PLAN" and self.explanation:
            lines += ["", self.explanation.text()]
        if self.infeasibility:
            lines += ["", self.infeasibility.summary()]
        if self.status == "SOLVER_BUG" and self.verification:
            lines += ["", self.verification.summary()]
        return "\n".join(lines)


def available_branches(curriculum_dir: str = DEFAULT_CURRICULUM_DIR) -> list[str]:
    """Branches whose course file actually has courses in it."""
    root = os.path.join(curriculum_dir, "branches")
    found = []
    for name in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        path = os.path.join(root, name, "courses.json")
        if os.path.isfile(path) and os.path.getsize(path) > 4:
            found.append(name)
    return found


def _solver(name: str, timeout_s: float):
    if name == "csp":
        from backend.csp.solver import SolverConfig, solve

        config = SolverConfig(mrv=True, forward_checking=True, ac3=True,
                              degree_tiebreak=True, timeout_s=timeout_s)
        return lambda problem: solve(problem, config)
    if name == "astar":
        try:
            from backend.astar import AStarConfig, solve
        except ImportError as exc:
            raise RuntimeError("The A* planner is not available in this checkout yet.") from exc
        config = AStarConfig(heuristic="composite", timeout_seconds=timeout_s)
        return lambda problem: solve(problem, config)
    raise ValueError(f"Unknown solver {name!r}; choose one of {SOLVERS}.")


def make_plan(
    branch: str,
    completed: Iterable[str],
    current_semester: int,
    target_semester: int = 8,
    *,
    max_credits: int = 20,
    min_credits: int = 0,
    solver: str = "csp",
    minor: str | None = None,
    timeout_s: float = 20.0,
    diagnose: bool = True,
    curriculum_dir: str | None = None,
) -> PlanResponse:
    completed = {c.strip() for c in completed if c and c.strip()}
    problem = build_problem_for_student(
        branch, completed, current_semester, target_semester,
        minor=minor, curriculum_dir=curriculum_dir,
        max_credits=max_credits, min_credits=min_credits,
    )
    warnings = [f"{code} is not in the {branch} curriculum; it is kept as completed "
                f"but not counted towards any category."
                for code in sorted(completed - set(problem.courses))]
    if current_semester >= target_semester:
        warnings.append("Current semester is not before the target semester, so no "
                        "semesters are left to plan.")

    solve = _solver(solver, timeout_s)
    result = solve(problem)
    stats = dict(result.stats or {})

    if result.status == "SAT":
        report = verify_plan(problem, result.assignment)
        if not report.valid:
            return PlanResponse(
                "SOLVER_BUG", solver,
                f"The {solver} solver returned a plan, but the independent verifier found "
                f"{len(report.violations)} broken rule(s), so it is not shown as valid.",
                problem, result.assignment, verification=report, warnings=warnings, stats=stats,
            )
        explanation = explain_plan(problem, result.assignment)
        semesters: dict[int, list[dict]] = {}
        for code, sem in sorted(result.assignment.items(), key=lambda kv: str(kv[1])):
            if sem == NOT_TAKEN:
                continue
            info = problem.courses[code]
            semesters.setdefault(sem, []).append(
                {"code": code, "title": info.get("title") or "", "credits": info["credits"],
                 "category": info.get("category") or ""})
        semesters = {s: sorted(v, key=lambda c: c["code"]) for s, v in sorted(semesters.items())}
        not_taken = sorted(c for c, s in result.assignment.items() if s == NOT_TAKEN)
        grad = explanation.graduation_semester
        message = (f"Plan found and verified: graduate in semester {grad}."
                   if grad else "Nothing left to schedule: all requirements are already met.")
        return PlanResponse("PLAN", solver, message, problem, result.assignment, semesters,
                            not_taken, report, explanation, warnings=warnings, stats=stats)

    if result.status == "UNSAT":
        diag = analyze(problem) if diagnose else None
        return PlanResponse("NO_PLAN", solver,
                            "No plan satisfies every rule with these settings.",
                            problem, infeasibility=diag, warnings=warnings, stats=stats)

    return PlanResponse("TIMEOUT", solver,
                        f"The {solver} solver ran out of time ({timeout_s:.0f}s). Try a "
                        f"higher credit cap or a later target semester.",
                        problem, warnings=warnings, stats=stats)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Make a verified degree plan.")
    parser.add_argument("--branch", default="cse")
    parser.add_argument("--completed", default="", help="comma-separated course codes")
    parser.add_argument("--current", type=int, required=True, help="last finished semester")
    parser.add_argument("--target", type=int, default=8)
    parser.add_argument("--max-credits", type=int, default=20)
    parser.add_argument("--min-credits", type=int, default=0)
    parser.add_argument("--solver", choices=SOLVERS, default="csp")
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args(argv)
    response = make_plan(args.branch, args.completed.split(","), args.current, args.target,
                         max_credits=args.max_credits, min_credits=args.min_credits,
                         solver=args.solver, timeout_s=args.timeout)
    print(response.text())


if __name__ == "__main__":
    main()
