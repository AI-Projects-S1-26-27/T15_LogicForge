"""Experiment E4 (Pair D): are the solvers' plans actually valid?

Runs every available solver on the benchmark, re-checks every plan with
the independent verifier, and (optionally) diagnoses the impossible
instances with the infeasibility analyser.

Outputs (in experiments/results/):
    e4_verification.csv   one row per (student, solver)
    e4_summary.md         validity rate with 95% bootstrap CI, per stratum,
                          and every rule the verifier caught being broken

Usage:
    python experiments/e4_verification.py                 # CSP (+ A* if present)
    python experiments/e4_verification.py --limit 20      # quick run
    python experiments/e4_verification.py --diagnose      # also explain UNSAT ones
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from collections import Counter, defaultdict

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.verification import verify_plan  # noqa: E402
from experiments.benchmark import DEFAULT_OUT, load, to_problem  # noqa: E402
from experiments.stats import summarize  # noqa: E402

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def available_solvers(timeout_s: float) -> dict:
    """Every solver this checkout can run, as name -> fn(problem) -> result."""
    solvers = {}
    from backend.csp.solver import SolverConfig, solve as csp_solve

    config = SolverConfig(mrv=True, forward_checking=True, ac3=True,
                          degree_tiebreak=True, lcv=True, timeout_s=timeout_s)
    solvers["csp"] = lambda p: csp_solve(p, config)
    try:
        from backend.astar import AStarConfig, solve as astar_solve
        from config.settings import ASTAR

        a_config = AStarConfig(heuristic="composite", bundle_breadth_limit=ASTAR.bundle_breadth_limit, timeout_seconds=timeout_s)
        solvers["astar"] = lambda p: astar_solve(p, a_config)
    except Exception as exc:  # A* is not merged into main yet
        print(f"A* not available here ({type(exc).__name__}: {exc}); running CSP only.")
    return solvers


def _leaf_only_prereqs(formula) -> list[str]:
    """Courses that are ALWAYS required by an AND-only formula (no OR)."""
    if not formula:
        return []
    if formula["kind"] == "leaf":
        return [formula["course"]] if formula.get("relation", "PRE") == "PRE" else []
    if formula["kind"] == "and":
        out = []
        for item in formula["items"]:
            out += _leaf_only_prereqs(item)
        return out
    return []


def mutants(problem, assignment: dict, rng) -> list[tuple[str, dict]]:
    """Broken copies of a valid plan; each is invalid by construction.

    Used to show the verifier would actually catch bad plans (its 100% on
    real solver output is only meaningful if it is sensitive).
    """
    out = []
    courses = problem.courses
    scheduled = {c: s for c, s in assignment.items() if isinstance(s, int)}

    # 1. A course moved into the same semester as a prerequisite it must follow.
    pairs = [(c, p) for c in scheduled for p in _leaf_only_prereqs(courses[c].get("formula"))
             if p in scheduled]
    if pairs:
        course, prereq = rng.choice(pairs)
        out.append(("prereq", {**assignment, course: scheduled[prereq]}))

    # 2. An odd/even-only course shifted by one semester.
    locked = [c for c in scheduled if courses[c].get("parity") in ("odd", "even")]
    if locked:
        course = rng.choice(locked)
        sem = scheduled[course]
        shifted = sem + 1 if sem + 1 <= problem.target_semester else sem - 1
        out.append(("parity", {**assignment, course: shifted}))

    # 3. A required course dropped.
    required = [c for c in scheduled if "elective" not in (courses[c].get("category") or "").lower()]
    if required:
        out.append(("core_not_taken", {**assignment, rng.choice(required): "NOT_TAKEN"}))

    # 4. Everything crammed into the first planned semester.
    total = sum(courses[c]["credits"] for c in scheduled)
    if total > problem.max_credits:
        first = problem.current_semester + 1
        out.append(("credit_cap", {**assignment, **{c: first for c in scheduled}}))
    return out


def run(students: list[dict], timeout_s: float = 10.0, diagnose: bool = False) -> list[dict]:
    import random

    rng = random.Random(42)
    solvers = available_solvers(timeout_s)
    rows = []
    for i, student in enumerate(students, 1):
        problem = to_problem(student)
        for name, solve in solvers.items():
            started = time.perf_counter()
            result = solve(problem)
            row = {
                "id": student["id"], "solver": name, "profile": student["profile"],
                "slack": student["slack"], "minor": student["minor"], "chain": student["chain"],
                "status": result.status, "time_s": round(time.perf_counter() - started, 4),
                "nodes": (result.stats or {}).get("nodes", ""),
                "valid": "", "violations": "", "conflict": "",
                "mutants": "", "mutants_caught": "",
            }
            if result.status == "SAT":
                report = verify_plan(problem, result.assignment)
                row["valid"] = report.valid
                row["violations"] = ";".join(v.constraint for v in report.violations)
                if report.valid:
                    broken = mutants(problem, result.assignment, rng)
                    caught = [kind for kind, plan in broken
                              if kind in verify_plan(problem, plan).kinds()]
                    row["mutants"] = ";".join(kind for kind, _ in broken)
                    row["mutants_caught"] = ";".join(caught)
            elif result.status == "UNSAT" and diagnose and name == "csp":
                from backend.explanations.infeasibility_analyzer import analyze, csp_oracle

                diag = analyze(problem, oracle=csp_oracle(timeout_s))
                row["conflict"] = ";".join(diag.conflict)
            rows.append(row)
        if i % 25 == 0:
            print(f"  {i}/{len(students)} students done")
    return rows


def write_csv(rows: list[dict], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def summary_markdown(rows: list[dict]) -> str:
    lines = ["# E4: independent verification of solver plans", "",
             "Every SAT plan was re-checked by `backend/verification/plan_checker.py`, "
             "which imports no solver code. Rates are means with 95% bootstrap CIs.", ""]
    for solver in sorted({r["solver"] for r in rows}):
        mine = [r for r in rows if r["solver"] == solver]
        statuses = Counter(r["status"] for r in mine)
        sat = [r for r in mine if r["status"] == "SAT"]
        lines += [f"## {solver.upper()}", "",
                  f"- Instances: {len(mine)} (SAT {statuses['SAT']}, UNSAT {statuses['UNSAT']}, "
                  f"TIMEOUT {statuses['TIMEOUT']})"]
        if sat:
            s = summarize([1.0 if r["valid"] else 0.0 for r in sat])
            lines.append(f"- Plan validity rate: **{s['mean']:.1%}** "
                         f"(95% CI {s['ci_low']:.1%} to {s['ci_high']:.1%}, n={s['n']})")
            t = summarize([float(r["time_s"]) for r in sat])
            lines.append(f"- Time per solved instance: {t['mean']:.3f}s "
                         f"(95% CI {t['ci_low']:.3f} to {t['ci_high']:.3f})")
        caught = Counter(v.split(":")[0] for r in sat for v in r["violations"].split(";") if v)
        lines.append("- Violations caught: " + (", ".join(f"{k} x{n}" for k, n in caught.items())
                                                 if caught else "none"))
        made = Counter(k for r in sat for k in r["mutants"].split(";") if k)
        hit = Counter(k for r in sat for k in r["mutants_caught"].split(";") if k)
        if made:
            lines.append(f"- Sensitivity check: {sum(hit.values())}/{sum(made.values())} "
                         f"deliberately broken plans caught with the right rule ("
                         + ", ".join(f"{k} {hit[k]}/{n}" for k, n in sorted(made.items())) + ")")
        lines += ["", "| stratum | value | n | SAT | valid |", "|---|---|---|---|---|"]
        for key in ("slack", "profile", "minor", "chain"):
            groups = defaultdict(list)
            for r in mine:
                groups[r[key]].append(r)
            for value, group in sorted(groups.items(), key=lambda kv: str(kv[0])):
                n_sat = sum(r["status"] == "SAT" for r in group)
                n_valid = sum(r["valid"] is True for r in group)
                lines.append(f"| {key} | {value} | {len(group)} | {n_sat} | {n_valid} |")
        conflicts = Counter(u.split(":")[0] for r in mine for u in r["conflict"].split(";") if u)
        if conflicts:
            lines += ["", "Rules most often in the conflict of UNSAT instances: "
                      + ", ".join(f"{k} ×{n}" for k, n in conflicts.most_common())]
        lines.append("")
    return "\n".join(lines)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Experiment E4")
    parser.add_argument("--benchmark", default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--diagnose", action="store_true")
    parser.add_argument("--out-dir", default=RESULTS_DIR)
    args = parser.parse_args(argv)

    students = load(args.benchmark)[: args.limit]
    rows = run(students, args.timeout, args.diagnose)
    os.makedirs(args.out_dir, exist_ok=True)
    write_csv(rows, os.path.join(args.out_dir, "e4_verification.csv"))
    text = summary_markdown(rows)
    with open(os.path.join(args.out_dir, "e4_summary.md"), "w", encoding="utf-8") as handle:
        handle.write(text)
    print(text)


if __name__ == "__main__":
    main()
