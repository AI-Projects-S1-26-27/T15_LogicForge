"""Measure live CSP, composite A* and learned-guided A* on the same scoped cases."""

import argparse, csv, json, statistics, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.services.scoped_planner import DATA
from backend.services.scoped_api import plan_payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument(
        "--output", type=Path, default=Path("docs/submission/benchmark.csv")
    )
    args = parser.parse_args()
    if not 1 <= args.repeats <= 30:
        parser.error("Choose 1–30 repeats.")
    rows = []
    for branch in DATA["branches"]:
        for solver, heuristic in [
            ("csp", "composite"),
            ("astar", "composite"),
            ("astar", "learned"),
        ]:
            results = [
                plan_payload(
                    dict(
                        branch=branch,
                        current_semester=2,
                        completed_courses=DATA["common"],
                        target_semester=8,
                        max_credits=22,
                        project_route="thesis",
                        allow_unconfirmed=True,
                        solver=solver,
                        heuristic=heuristic,
                    )
                )
                for _ in range(args.repeats)
            ]
            rows.append(
                {
                    "branch": branch,
                    "solver": solver,
                    "heuristic": heuristic,
                    "repeats": args.repeats,
                    "statuses": ",".join(sorted({r["status"] for r in results})),
                    "median_ms": round(
                        statistics.median(r["stats"]["time_s"] * 1000 for r in results),
                        3,
                    ),
                    "median_nodes": statistics.median(
                        r["stats"]["nodes"] for r in results
                    ),
                    "offering_assumptions": len(
                        results[0]["audit"]["offering_assumptions"]
                    ),
                    "verified_all": all(
                        r["verification_valid"] and r["audit"]["requirements_met"]
                        for r in results
                    ),
                }
            )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
