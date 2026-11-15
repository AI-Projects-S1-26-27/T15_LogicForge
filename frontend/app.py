"""GraphMind web app (Pair D).

Run from the repo root:
    pip install streamlit
    streamlit run frontend/app.py

The app calls ``backend/services/planning_service.py`` directly (no API
server). The E5 feedback form at the bottom stores only ratings and an
optional comment, never the transcript (proposal §3: no academic records
are stored).
"""

from __future__ import annotations

import csv
import datetime as dt
import os
import sys

import streamlit as st

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.data.loader import load_curriculum  # noqa: E402
from backend.services.planning_service import (  # noqa: E402
    SOLVERS, available_branches, make_plan,
)
from backend.services.problem_builder import DEFAULT_CURRICULUM_DIR  # noqa: E402

FEEDBACK_PATH = os.path.join(_ROOT, "experiments", "results", "e5_feedback.csv")

st.set_page_config(page_title="GraphMind", page_icon="🎓", layout="wide")
st.title("GraphMind — degree plan generator")
st.caption("Enter what you have completed; GraphMind plans the rest, checks every rule "
           "independently, and explains each placement.")

# ── inputs ───────────────────────────────────────────────────────────────────
branches = available_branches()
with st.sidebar:
    st.header("Your situation")
    branch = st.selectbox("Branch", branches, index=branches.index("cse") if "cse" in branches else 0)
    curriculum = load_curriculum(DEFAULT_CURRICULUM_DIR, branch=branch)
    options = sorted(curriculum.courses)
    labels = {c: f"{c} — {curriculum.courses[c].title or ''}" for c in options}
    completed = st.multiselect("Courses you have passed", options, format_func=labels.get)
    pasted = st.text_input("…or paste codes (comma-separated)", "")
    current = st.number_input("Last semester you finished", 0, 10, 2)
    target = st.number_input("Graduate by semester", 1, 12, 8)
    max_credits = st.slider("Max credits per semester", 6, 30, 20)
    min_credits = st.slider("Min credits per semester (0 = none)", 0, 20, 0)
    solver = st.radio("Planner", SOLVERS, format_func={"csp": "CSP (backtracking)",
                                                       "astar": "A* search"}.get)
    go = st.button("Make my plan", type="primary", use_container_width=True)

if go:
    codes = set(completed) | {c.strip() for c in pasted.split(",") if c.strip()}
    with st.spinner("Planning and verifying…"):
        try:
            response = make_plan(branch, codes, int(current), int(target),
                                 max_credits=max_credits, min_credits=min_credits,
                                 solver=solver)
        except Exception as exc:  # show the error instead of a stack trace
            st.error(str(exc))
            st.stop()
    st.session_state["response"] = response

response = st.session_state.get("response")
if response is None:
    st.info("Fill in the sidebar and press **Make my plan**.")
    st.stop()

for warning in response.warnings:
    st.warning(warning)

# ── results ──────────────────────────────────────────────────────────────────
if response.status == "PLAN":
    st.success(response.message)
    st.caption(f"Independent verifier: all rules passed "
               f"({response.verification.checked['courses']} courses, "
               f"{response.verification.checked['prerequisites']} prerequisite checks).")
    explained = response.explanation.by_course()
    cols = st.columns(min(4, max(1, len(response.semesters))))
    for i, (sem, rows) in enumerate(response.semesters.items()):
        with cols[i % len(cols)]:
            total = sum(r["credits"] for r in rows)
            st.subheader(f"Semester {sem}")
            st.caption(f"{total} credits")
            for row in rows:
                with st.expander(f"{row['code']} · {row['credits']} cr"):
                    st.write(row["title"])
                    st.write(" ".join(explained[row["code"]].reasons))
    if response.not_taken:
        st.write("**Not needed:** " + ", ".join(response.not_taken))

elif response.status == "NO_PLAN":
    st.error(response.message)
    diag = response.infeasibility
    if diag and diag.status == "infeasible":
        st.subheader("Why")
        for line in diag.explanations:
            st.write(f"- {line}")
        st.subheader("What would fix it")
        for r in diag.relaxations:
            note = "" if r.fixes_alone else " *(helps, but not enough on its own)*"
            st.write(f"- {r.description}{note}")
        if not diag.minimal:
            st.caption("Some checks timed out, so this list may include an extra rule.")

elif response.status == "SOLVER_BUG":
    st.error(response.message)
    for v in response.verification.violations:
        st.write(f"- {v.message}")
else:
    st.warning(response.message)

with st.expander("Solver statistics"):
    st.json(response.stats)

# ── E5 feedback (no transcript stored) ──────────────────────────────────────
st.divider()
st.subheader("Help us evaluate GraphMind (E5)")
with st.form("feedback"):
    correct = st.radio("Is this plan correct for you?", ["Yes", "Mostly", "No"], horizontal=True)
    useful = st.slider("How useful is it? (1 = not at all, 5 = very)", 1, 5, 4)
    comment = st.text_area("Anything wrong or missing? (optional, no personal details)")
    consent = st.checkbox("I agree to my ratings and comment being stored for the course project.")
    if st.form_submit_button("Send feedback"):
        if not consent:
            st.warning("Please tick the consent box first.")
        else:
            os.makedirs(os.path.dirname(FEEDBACK_PATH), exist_ok=True)
            new_file = not os.path.exists(FEEDBACK_PATH)
            with open(FEEDBACK_PATH, "a", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                if new_file:
                    writer.writerow(["timestamp", "solver", "status", "correct", "useful", "comment"])
                writer.writerow([dt.datetime.now().isoformat(timespec="seconds"), response.solver,
                                 response.status, correct, useful, comment.strip()])
            st.success("Thanks! Saved.")
