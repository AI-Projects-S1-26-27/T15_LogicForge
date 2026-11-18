"""Generate branch-scoped, independently verified schedule trajectories.

Labels are FEASIBLE remaining-term upper bounds, not certified optimal h*.
Prefixes from an episode stay together during evaluation. All four branches use
exactly the dashboard's curated courses, requirements and explicit assumptions.
"""

import argparse
import csv
import json
from pathlib import Path
from backend.services.scoped_planner import DATA, BRANCHES, prepare, CATALOGUE_SIGNATURE
from backend.services.planning_service import make_plan
from .features import FEATURE_NAMES, FEATURE_VERSION, extract_features_vector

ARTIFACTS = Path(__file__).with_name("artifacts")


def generate_dataset(
    output_dir=ARTIFACTS, branches=None, caps=(20, 22, 24, 25), minors=("", "finance")
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    records, failures = [], []
    for branch in branches or list(BRANCHES):
        for cap in caps:
            for minor in minors:
                episode = f'{branch}-{cap}-{minor or "major"}'
                request = dict(
                    branch=branch,
                    minor=minor,
                    current_semester=2,
                    target_semester=8,
                    completed_courses=DATA["common"],
                    max_credits=cap,
                    allow_unconfirmed=True,
                    solver="csp",
                )
                state = prepare(request)
                problem = state["problem"]
                result = make_plan(
                    branch,
                    DATA["common"],
                    2,
                    8,
                    solver="csp",
                    problem_override=problem,
                    timeout_s=3,
                    diagnose=False,
                )
                if (
                    result.status != "PLAN"
                    or not result.verification
                    or not result.verification.valid
                ):
                    failures.append(dict(episode=episode, status=result.status))
                    continue
                last = max(result.assignment.values(), default=2)
                for step in range(2, last + 1):
                    placed = {c: t for c, t in result.assignment.items() if t <= step}
                    records.append(
                        dict(
                            zip(
                                FEATURE_NAMES,
                                extract_features_vector(problem, placed, step + 1),
                            ),
                            remaining_terms=last - step,
                            episode=episode,
                            branch=branch,
                        )
                    )
    if not records:
        raise ValueError("No independently verified trajectories were generated.")
    with (output_dir / "training_data.csv").open("w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=FEATURE_NAMES + ["remaining_terms", "episode", "branch"]
        )
        writer.writeheader()
        writer.writerows(records)
    metadata = dict(
        feature_version=FEATURE_VERSION,
        features=FEATURE_NAMES,
        catalogue_signature=CATALOGUE_SIGNATURE,
        label_kind="verified_feasible_suffix_upper_bound",
        rows=len(records),
        episodes=len({r["episode"] for r in records}),
        branches=sorted({r["branch"] for r in records}),
        assumptions=[
            "Unlisted courses explicitly allowed in either semester as planning assumptions",
            "Current semester 2 with common first year passed",
        ],
        failures=failures,
        source="Corrected ml.zip pipeline using the submission CSP and independent plan checker",
    )
    (output_dir / "dataset.json").write_text(json.dumps(metadata, indent=2))
    return records, metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ARTIFACTS)
    args = parser.parse_args()
    _, report = generate_dataset(args.output_dir)
    print(json.dumps(report, indent=2))
