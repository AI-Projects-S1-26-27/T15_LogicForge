"""Benchmark generator (Pair D): ~200 synthetic student states.

Each student is *simulated* on the real CSE curriculum: semester by
semester they take courses whose prerequisites they already have and
whose term matches, up to a credit cap. That gives realistic transcripts
instead of random course sets.

Students are stratified (proposal §3, Benchmark) by:
- ``profile``: on_track, behind_one, failed_prereq, late_minor, accelerated
- ``slack``:   tight / medium / loose credit budget for what is left
- ``minor``:   with or without a (synthetic) minor
- ``chain``:   short / medium / long remaining prerequisite chain

The minor is SYNTHETIC: the repo has no real minor data yet. Its courses
use the made-up prefix "MNR" so they can never be confused with real ones.

Usage:
    python experiments/benchmark.py            # writes experiments/benchmarks/benchmark_v1.json
    python experiments/benchmark.py --n 50 --seed 7 --out my.json
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import random
import sys
from collections import Counter

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.services.problem_builder import build_problem_for_student  # noqa: E402

PROFILES = ["on_track", "behind_one", "failed_prereq", "late_minor", "accelerated"]
SLACK_FACTORS = {"tight": (0.95, 1.1), "medium": (1.25, 1.5), "loose": (1.7, 2.2)}
MINOR_CATEGORY = "Minor (synthetic)"
DEFAULT_OUT = os.path.join(os.path.dirname(__file__), "benchmarks", "benchmark_v1.json")


def _leaf(code):
    return {"kind": "leaf", "course": code, "relation": "PRE"}


def synthetic_minor() -> tuple[dict, int]:
    """Five made-up minor courses with a short chain, 15 credits required."""
    courses = {
        "MNR F201": {"credits": 3, "category": MINOR_CATEGORY, "parity": "odd", "formula": None},
        "MNR F202": {"credits": 3, "category": MINOR_CATEGORY, "parity": "even",
                     "formula": _leaf("MNR F201")},
        "MNR F301": {"credits": 3, "category": MINOR_CATEGORY, "parity": None,
                     "formula": _leaf("MNR F202")},
        "MNR F302": {"credits": 3, "category": MINOR_CATEGORY, "parity": None, "formula": None},
        "MNR F311": {"credits": 3, "category": MINOR_CATEGORY, "parity": "odd",
                     "formula": {"kind": "or", "items": [_leaf("MNR F202"), _leaf("MNR F302")]}},
    }
    return courses, 12


# ── helpers on plain course dicts ───────────────────────────────────────────

def _satisfied(formula, done: set, courses: dict) -> bool:
    if not formula:
        return True
    kind = formula["kind"]
    if kind == "leaf":
        return formula["course"] in done or formula["course"] not in courses
    results = [_satisfied(item, done, courses) for item in formula["items"]]
    return all(results) if kind == "and" else any(results)


def _parity_ok(parity, sem):
    return parity not in ("odd", "even") or (sem % 2 == 1) == (parity == "odd")


def chain_depth(courses: dict, completed: set) -> int:
    """Longest chain of outstanding courses linked by prerequisites."""
    memo: dict[str, int] = {}

    def deps(formula):
        if not formula:
            return set()
        if formula["kind"] == "leaf":
            return {formula["course"]}
        out = set()
        for item in formula["items"]:
            out |= deps(item)
        return out

    def depth(code, seen=()):
        if code in memo:
            return memo[code]
        if code in seen:
            return 0
        best = 0
        for dep in deps(courses[code].get("formula")):
            if dep in courses and dep not in completed:
                best = max(best, depth(dep, seen + (code,)))
        memo[code] = best + 1
        return memo[code]

    outstanding = [c for c in courses if c not in completed]
    return max((depth(c) for c in outstanding), default=0)


def simulate_transcript(rng, courses, semesters, cap, skip=()):
    """Take courses term by term like a real student would."""
    done: set[str] = set()
    for sem in range(1, semesters + 1):
        open_now = [
            c for c, info in courses.items()
            if c not in done and c not in skip
            and _parity_ok(info.get("parity"), sem)
            and _satisfied(info.get("formula"), done, courses)
        ]
        # Cores (and minor courses) first; an elective only now and then.
        eligible = [c for c in open_now if "elective" not in courses[c]["category"].lower()]
        electives = [c for c in open_now if "elective" in courses[c]["category"].lower()]
        rng.shuffle(eligible)
        if electives and rng.random() < 0.4:
            eligible.append(rng.choice(electives))
        load, taken = 0, []
        for code in eligible:
            credits = courses[code]["credits"]
            if load + credits <= cap:
                taken.append(code)
                load += credits
        done |= set(taken)
    return done


def _drop_with_dependants(completed: set, code: str, courses: dict) -> None:
    """Remove ``code`` and every completed course that no longer has its prerequisites."""
    completed.discard(code)
    changed = True
    while changed:
        changed = False
        for c in sorted(completed):
            if not _satisfied(courses[c].get("formula"), completed - {c}, courses):
                completed.discard(c)
                changed = True


def _required_credits(courses, completed, minimums):
    need = sum(info["credits"] for c, info in courses.items()
               if c not in completed and "elective" not in info["category"].lower()
               and not info["category"].startswith("Minor"))
    for category, minimum in minimums.items():
        if "elective" in category.lower() or category == MINOR_CATEGORY:
            have = sum(info["credits"] for c, info in courses.items()
                       if c in completed and info["category"] == category)
            need += max(0, minimum - have)
    return need


def _chain_label(depth):
    return "short" if depth <= 1 else ("medium" if depth == 2 else "long")


def make_student(rng, base, index, profile, slack, with_minor):
    courses = copy.deepcopy(base.courses)
    minimums = dict(base.category_minimums)
    if with_minor:
        minor_courses, minor_min = synthetic_minor()
        courses.update(minor_courses)
        minimums[MINOR_CATEGORY] = minor_min

    current = rng.randint(2, 5)
    target = 7 if profile == "accelerated" else 8
    skip: set[str] = set()
    if profile == "late_minor":
        skip |= {c for c in courses if c.startswith("MNR")}
    sim_courses = courses if profile != "late_minor" else {
        c: i for c, i in courses.items() if not c.startswith("MNR")}
    completed = simulate_transcript(rng, sim_courses, current, cap=rng.choice([16, 18, 20]))

    if profile == "behind_one" and completed:
        _drop_with_dependants(completed, rng.choice(sorted(completed)), courses)
    if profile == "failed_prereq":
        # Fail a completed course that something else depends on.
        needed = [c for c in sorted(completed)
                  if any(c in json.dumps(i.get("formula")) for i in courses.values())]
        if needed:
            _drop_with_dependants(completed, rng.choice(needed), courses)

    remaining = target - current
    need = _required_credits(courses, completed, minimums)
    low, high = SLACK_FACTORS[slack]
    factor = rng.uniform(low, high)
    max_credits = max(6, min(30, math.ceil(factor * need / max(remaining, 1))))
    largest = max(info["credits"] for c, info in courses.items() if c not in completed)
    max_credits = max(max_credits, largest)

    depth = chain_depth(courses, completed)
    return {
        "id": f"S{index:03d}",
        "profile": profile,
        "slack": slack,
        "minor": with_minor,
        "chain": _chain_label(depth),
        "chain_depth": depth,
        "problem": {
            "courses": courses,
            "completed": sorted(completed),
            "current_semester": current,
            "target_semester": target,
            "max_credits": max_credits,
            "min_credits": 0,
            "category_minimums": minimums,
            "assume_out_of_scope_satisfied": True,
        },
    }


def generate(n: int = 200, seed: int = 42, branch: str = "cse") -> list[dict]:
    """Generate ``n`` students, cycling through every profile x slack x minor cell."""
    rng = random.Random(seed)
    base = build_problem_for_student(branch, completed=[], current_semester=0)
    cells = [(p, s, m) for p in PROFILES for s in SLACK_FACTORS for m in (False, True)]
    students = []
    for i in range(n):
        profile, slack, minor = cells[i % len(cells)]
        if profile == "late_minor":
            minor = True
        students.append(make_student(rng, base, i, profile, slack, minor))
    return students


def to_problem(entry: dict):
    """Turn a saved benchmark entry back into the shared ``Problem``."""
    from backend.csp.model import Problem

    data = dict(entry["problem"] if "problem" in entry else entry)
    data["completed"] = set(data["completed"])
    return Problem(**data)


def load(path: str = DEFAULT_OUT) -> list[dict]:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)["students"]


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--branch", default="cse")
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    students = generate(args.n, args.seed, args.branch)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump({"seed": args.seed, "branch": args.branch, "n": len(students),
                   "note": "Synthetic students. Minor courses (MNR) are made up.",
                   "students": students}, handle, indent=1)
    print(f"Wrote {len(students)} students to {args.out}")
    for key in ("profile", "slack", "minor", "chain"):
        print(f"  {key}: {dict(Counter(s[key] for s in students))}")


if __name__ == "__main__":
    main()
