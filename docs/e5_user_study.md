# E5 — End-user evaluation guide (Pair D)

Goal: 6–10 volunteer students (team members and classmates) run GraphMind on
their **own** transcripts and rate the plan. This is the Application track's
realistic-user requirement.

## Privacy (from the proposal)

- Only volunteers, using their own records.
- The app stores **no transcript**. The feedback form saves only: time,
  planner used, outcome, "is it correct?" (Yes / Mostly / No), a 1–5
  usefulness rating, and an optional comment.
- Feedback is saved to `experiments/results/e5_feedback.csv` only if the
  volunteer ticks the consent box.

## Running a session (about 10 minutes per person)

1. `pip install streamlit`, then from the repo root: `streamlit run frontend/app.py`
2. The volunteer picks their branch, ticks the courses they have passed,
   and sets their last finished semester and target graduation semester.
3. Press **Make my plan**. Let them read the plan and open a few course
   explanations.
4. Ask them to compare it with what they actually plan to take. Things to
   look for:
   - a course placed before its prerequisite or in the wrong odd/even term,
   - a required course missing,
   - a plan that is valid but unrealistic (note it in the comment).
5. They fill in the feedback form at the bottom and submit.
6. Optional: try once with the other planner (CSP vs A*) and once with a
   setting that makes planning impossible (e.g. 12 credits max), to see the
   "why no plan" explanation.

## Reporting

- Correctness: share of "Yes" (and "Mostly") answers, with a 95% bootstrap
  CI from `experiments/stats.py` (`summarize([1, 0, 1, ...])`).
- Usefulness: mean rating with a 95% bootstrap CI.
- Quote 2–3 comments (no names) and list any rule violations volunteers found
  that the verifier missed. Each one is a bug to fix before the demo.
