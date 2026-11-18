"""GraphMind — State Feature Extractor for Learned Heuristic (Pair C)

Extracts the exact 6 state features defined in the proposal (Section 3):
1. Outstanding credits (per category / total required credits remaining)
2. Outstanding course count (unplaced courses still required)
3. Maximum remaining chain depth (longest remaining prerequisite DAG path)
4. Parity-locked course count (remaining courses restricted to odd or even semesters)
5. Terms remaining (target_semester - next_term + 1)
6. Unsatisfied disjunction count (remaining OR branches in prerequisite formulas)
"""

from __future__ import annotations

import math
from typing import Dict, List, Set, Tuple

from backend.models.planning_problem import (
    Problem,
    extract_formula_courses,
    is_elective_category,
)
from backend.astar.heuristics import minimum_required_credits, critical_path


def count_unsatisfied_disjunctions(formula: dict | None, satisfied_set: Set[str]) -> int:
    """Count unsatisfied OR-nodes in a prerequisite formula tree."""
    if not formula:
        return 0
    kind = formula.get("kind")
    if kind == "leaf":
        return 0
    items = formula.get("items", [])
    count = 0
    if kind == "or":
        # If none of the children are satisfied, this disjunction is unsatisfied
        children_sat = any(
            is_subformula_satisfied(child, satisfied_set) for child in items
        )
        if not children_sat:
            count += 1
    for child in items:
        count += count_unsatisfied_disjunctions(child, satisfied_set)
    return count


def is_subformula_satisfied(formula: dict | None, satisfied_set: Set[str]) -> bool:
    """Helper to check if a subformula is satisfied by satisfied_set."""
    if not formula:
        return True
    kind = formula.get("kind")
    if kind == "leaf":
        return formula.get("course") in satisfied_set
    items = formula.get("items", [])
    if kind == "and":
        return all(is_subformula_satisfied(child, satisfied_set) for child in items)
    if kind == "or":
        return any(is_subformula_satisfied(child, satisfied_set) for child in items)
    return False


def extract_state_features(
    problem: Problem,
    placed: Dict[str, int],
    next_term: int,
) -> List[float]:
    """Extract a normalized 6-dimensional feature vector for a search state.

    State is defined by:
      - placed: {course_code: semester}
      - next_term: the next semester index to be planned
    """
    all_done = set(problem.completed) | set(placed.keys())

    # 1. Outstanding required credits
    req_credits = minimum_required_credits(problem, placed)
    if math.isinf(req_credits):
        req_credits = 99.0

    # 2. Outstanding required course count
    unplaced_vars = [c for c in problem.variables if c not in placed]
    mandatory_unplaced = [
        c for c in unplaced_vars
        if not is_elective_category(problem.courses[c].get("category"))
    ]
    # For electives, estimate minimum count needed to meet category floors
    elective_unplaced_count = max(0, int(math.ceil(max(0, req_credits - sum(
        problem.courses[c].get("credits", 3) for c in mandatory_unplaced
    )) / 3.0)))
    course_count = float(len(mandatory_unplaced) + elective_unplaced_count)

    # 3. Maximum remaining chain depth
    chain_depth = critical_path(problem, placed, next_term)
    if math.isinf(chain_depth):
        chain_depth = 99.0

    # 4. Parity-locked course count
    parity_locked = sum(
        1 for c in mandatory_unplaced
        if problem.courses[c].get("parity") in ("odd", "even")
    )

    # 5. Terms remaining until graduation horizon
    terms_rem = max(0.0, float(problem.target_semester - next_term + 1))

    # 6. Unsatisfied disjunction count
    disjunctions = sum(
        count_unsatisfied_disjunctions(problem.courses[c].get("formula"), all_done)
        for c in mandatory_unplaced
    )

    return [
        float(req_credits),
        float(course_count),
        float(chain_depth),
        float(parity_locked),
        float(terms_rem),
        float(disjunctions),
    ]
