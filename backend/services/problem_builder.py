"""Turn curriculum data + a student's transcript into a planning ``Problem``.

Pair D owns this as part of integration. It reads Pair A's loader output
and builds Pair B's ``Problem`` (the one both solvers consume).
"""

from __future__ import annotations

import os
from typing import Iterable

from backend.csp.model import Problem
from backend.data.loader import load_curriculum

DEFAULT_CURRICULUM_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "curriculum")
)


def _parity(term_parity: str | None) -> str | None:
    """The solvers only understand "odd", "even" or no restriction (None)."""
    if term_parity in ("odd", "even"):
        return term_parity
    return None


def problem_from_curriculum(
    curriculum,
    completed: Iterable[str],
    current_semester: int,
    target_semester: int,
    *,
    max_credits: int = 20,
    min_credits: int = 0,
    category_minimums: dict[str, int] | None = None,
    assume_out_of_scope_satisfied: bool = True,
    required_courses: Iterable[str] = (),
    additional_courses: Iterable[dict] = (),
) -> Problem:
    """Build a ``Problem`` from a loaded curriculum and a list of completed courses."""
    courses = {}
    for code, course in curriculum.courses.items():
        courses[code] = {
            "credits": int(course.credits or 0),
            "category": course.category or "",
            "parity": _parity(course.term_parity),
            "formula": course.parsed_prerequisites,
            "title": course.title,
        }
    for item in additional_courses:
        if item['code'] not in courses:
            courses[item['code']] = dict(credits=item['credits'], title=item['title'], category=item['category'], parity=None, formula=None, earliest_semester=item.get('earliest_semester', 1), exclusive_semester=item.get('exclusive_semester', False))
    if category_minimums is None:
        category_minimums = {
            category: int(req.credit_minimum)
            for category, req in curriculum.requirements.items()
        }
    # Keep each original category floor after moving forced choices to a mandatory category.
    category_minimums = dict(category_minimums)
    for code in set(required_courses):
        if code not in courses:
            raise ValueError(f"Unknown selected course: {code}")
        info = courses[code]
        category = info['category']
        category_minimums[category] = max(0, category_minimums.get(category, 0) - info['credits'])
        info['category'] = 'Required Choice'
    return Problem(
        courses=courses,
        completed=set(completed),
        current_semester=int(current_semester),
        target_semester=int(target_semester),
        max_credits=int(max_credits),
        min_credits=int(min_credits),
        category_minimums=dict(category_minimums),
        assume_out_of_scope_satisfied=assume_out_of_scope_satisfied,
    )


def build_problem_for_student(
    branch: str,
    completed: Iterable[str],
    current_semester: int,
    target_semester: int = 8,
    *,
    minor: str | None = None,
    curriculum_dir: str | None = None,
    **options,
) -> Problem:
    """Load a branch (and optional minor) from disk and build the problem."""
    curriculum = load_curriculum(curriculum_dir or DEFAULT_CURRICULUM_DIR, branch=branch, minor=minor)
    if not curriculum.courses:
        raise ValueError(f"No course data found for branch {branch!r}.")
    return problem_from_curriculum(curriculum, completed, current_semester, target_semester, **options)
