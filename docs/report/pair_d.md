# Pair D — Verification, diagnosis, evaluation and integration

*Mohammad Mubeen Mazar Khan, Vedant Shah*

Pair D owns the parts of GraphMind that do not plan: they check, explain,
measure and connect the planners built by Pairs B and C. Pair D implements
neither solver, so the verifier can catch the solvers' bugs instead of
sharing them.

## 1. Independent plan verifier

`backend/verification/plan_checker.py` takes a planning problem and a plan
(`{course: semester | NOT_TAKEN}`) and re-checks every rule from scratch:

| Rule | Constraint name |
|---|---|
| Required (non-elective) courses are scheduled | `core_not_taken:<C>` |
| Semesters lie in `(current_semester, target_semester]` | `horizon:<C>` |
| Odd/even-only courses sit in matching semesters | `parity:<C>` |
| Prerequisites strictly earlier, corequisites same term or earlier; AND/OR formulas evaluated recursively | `prereq:<C>` |
| No semester above `max_credits` | `credit_cap:<S>` |
| Every semester up to graduation at least `min_credits` | `credit_floor:<S>` |
| Each category reaches its credit minimum (completed + planned) | `category_min:<CAT>` |
| No unknown or already-completed course is scheduled | `unknown_course`, `already_completed` |

It reports **every** violation with a plain-English message, not just the
first. It imports nothing from `backend/csp`, `backend/astar` or
`backend/models`; a test parses its source and fails if that ever changes.
It accepts Pair B's `Problem` object or a plain dict, so it works for any
solver.

**Testing.** 23 unit tests: one valid and one or more broken plans per
rule, the OR-prerequisite case, out-of-catalogue prerequisites, the
graduation-only credit floor, and the independence test.

## 2. Infeasibility analyser

`backend/explanations/infeasibility_analyzer.py` explains *why* no plan
exists. Each rule a student could ask to bend is a unit: `horizon`,
`credit_cap`, `credit_floor`, `category_min:<CAT>`, `prereq:<C>`,
`parity:<C>`. Relaxing a unit builds a modified copy of the problem (no
formula, no parity restriction, a higher cap, …), so the analyser works
with any solver given as an oracle (default: Pair B's CSP solver).

**Algorithm (deletion-based, Junker 2004).** Start with all units on and
confirm the problem is UNSAT. Try switching each unit off. If the problem
is still UNSAT it is not needed and stays off. What remains is a conflict
in which every unit is necessary. The deletion order tries course-level
rules first and the student's own settings (credit cap, graduation
semester) last, so the conflict reported tends to be one the student can
act on. For each unit in the conflict a concrete relaxation is searched
for: the fewest extra semesters, the smallest credit overload, the
smallest category reduction. Each is re-solved, and marked "fixes it" only
if a plan then exists.

**Guarantee.** The returned set is *minimal* (irreducible), not
necessarily the *smallest* conflict. A solver timeout keeps the unit and
marks the report `minimal=False`.

**Testing.** 11 tests. On 80 random small problems the result is checked
against a brute-force oracle that enumerates every plan: the conflict is
UNSAT and removing any one unit makes it SAT. A side result: **Pair B's
CSP solver agreed with brute force on all 60 random small problems** tried.

## 3. Plan explainer

`backend/explanations/plan_explainer.py` gives every course a derivation
trace: which prerequisites allowed it and when they were done (for an OR,
which option was used), any odd/even restriction, the earliest semester it
could have gone in and why it is later (that semester was full, or simply
the planner's choice), and which later courses depend on it.

## 4. Integration and interface

- `backend/services/problem_builder.py` loads Pair A's curriculum data and
  a transcript into Pair B's `Problem`.
- `backend/services/planning_service.py` runs a solver, then the verifier.
  A plan is shown only if the verifier agrees. Otherwise the response is
  `SOLVER_BUG` with the violations. If there is no plan it runs the
  analyser. It also has a command-line interface.
- `frontend/app.py` is the Streamlit app, with the E5 feedback form.

## 5. Benchmark and statistics

`experiments/benchmark.py` generates 200 synthetic students (seed 42) on
the real CSE curriculum. Each transcript is *simulated* semester by
semester, so every completed course has its prerequisites. Strata:
profile (on track, behind by one, failed prerequisite, late minor,
accelerated), credit slack (tight, medium, loose), minor (yes or no; the
minor is synthetic, prefix `MNR`, because no real minor data exists yet),
and remaining chain depth.

`experiments/stats.py` implements percentile-bootstrap CIs and the
Wilcoxon signed-rank test (exact for n ≤ 25 without ties, otherwise
normal approximation with tie and continuity correction) in plain
Python. Checked against the Hollander & Wolfe textbook example (exact
p = 0.0391).

## 6. E4 — verification of solver plans

`experiments/e4_verification.py` runs every available solver on the 200
students, re-checks every plan with the verifier, and diagnoses every
UNSAT instance (`--diagnose`, 5 s solver limit). Full output:
`experiments/results/e4_summary.md` and `e4_verification.csv`.

**CSP solver (A* not yet on `main`):**

| | |
|---|---|
| Instances | 200: 161 SAT, 31 UNSAT, 8 TIMEOUT |
| Plan validity (verifier) | **161 / 161 = 100%** (95% bootstrap CI 100–100%) |
| Time per solved instance | 0.017 s (95% CI 0.001–0.046 s) |
| Sensitivity check | **563 / 563** deliberately broken plans caught with the right rule |

A 100% validity rate only means something if the verifier is sensitive.
So every valid plan was also broken on purpose in four ways (prerequisite
moved into the same term, odd/even course shifted, required course
dropped, all courses in one semester). The verifier flagged every one with
the correct rule: prereq 114/114, parity 144/144, core_not_taken 144/144,
credit_cap 161/161.

By stratum, failures concentrate where expected: tight credit budgets
(40/68 SAT vs 59/66 loose) and long remaining prerequisite chains (51/76
SAT vs 47/48 short).

**Diagnosis of the 31 UNSAT students.** All 31 got a conflict set
(sizes 2–21, most often 3–4 rules). The rules most often involved were
odd/even offerings (in 84 conflict entries), prerequisites (35), the
graduation semester (31), the credit cap (19) and category minimums (18).
The most common conflict (6 students) was the late-minor case: the minor's
two-step chain `MNR F201 → F202 → F301` with `F202` even-only cannot fit
before graduation. The second (5 students) was a tight credit cap together
with the elective credit minimum.

## 7. Limitations and open issues

- A* is not on `main` yet (Pair C's branch is missing `backend/models/course.py`),
  so E4 currently covers the CSP solver only. The runner includes A*
  automatically once it imports.
- The solvers and the verifier must agree on a few rules that are not
  written in the proposal: which categories are electives, that
  prerequisites outside the catalogue count as met, and the per-semester
  credit floor. On the last one, the CSP solver checks the floor in
  *every* semester up to the target, while the verifier and Pair C's A*
  check it only up to graduation. It does not matter while `min_credits = 0`
  (the default), but the team needs to pick one rule.
- The CSP solver has no objective, so its plans may include more electives
  than needed. They are valid, but not the shortest or lightest plan.
- E5 (6–10 real users) has not been run yet. See `docs/e5_user_study.md`.
