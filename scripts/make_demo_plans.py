"""Generate importable, clearly labeled hypothetical first-year-complete scenarios."""

import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.services.scoped_planner import DATA

rows = []
for index, (name, branch, minor, route, cap, fallback) in enumerate(
    [
        ("CSE: standard thesis", "cse", "", "thesis", 22, False),
        ("CSE: accelerated PS scenario", "cse", "", "practice_school", 25, False),
        ("CSE: Finance minor", "cse", "finance", "thesis", 22, False),
        (
            "EEE: Computing minor",
            "eee",
            "computing_and_intelligence",
            "thesis",
            22,
            False,
        ),
        (
            "ECE: Semiconductor minor",
            "ece",
            "semiconductor_devices_and_technology",
            "thesis",
            22,
            True,
        ),
        (
            "E&I: Robotics minor",
            "e_and_i",
            "robotics_and_automation",
            "thesis",
            22,
            False,
        ),
    ],
    1,
):
    rows.append(
        {
            "id": f"demo-{index}",
            "name": "Demo · " + name,
            "degreeType": "single",
            "branch": branch,
            "minor": minor,
            "currentSemester": 2,
            "targetSemester": 8,
            "maxCredits": cap,
            "completedCourses": DATA["common"],
            "selectedElectives": [],
            "excludedCourses": [],
            "solver": "astar",
            "heuristic": "composite",
            "projectRoute": route,
            "autoFill": True,
            "bulletinFallback": False,
            "allowUnconfirmed": True,
            "offeringOverrides": {},
            "projectAllocations": {},
            "demo_note": "Hypothetical transcript: the 15 reference first-year courses are assumed passed. Verify your own transcript before planning.",
        }
    )
path = Path(__file__).resolve().parents[1] / "docs/submission/demo_plans.json"
path.write_text(json.dumps({"schema_version": 1, "plans": rows}, indent=2))
print(path)
