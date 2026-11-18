# GraphMind — Academic Degree Planner

A complete local dashboard for planning the four supplied B.E. programmes with CSP and A*, comparing their actual results, and checking the encoded degree/minor requirements against the provided course images and semester timetables.

## Project details

| Field | Details |
| --- | --- |
| Project Name | GraphMind |
| Team Name | LogicForge |
| Course | CS F407 / U407 — Artificial Intelligence, Sem I 2026–27 |
| Institution | BITS Pilani, Hyderabad Campus |
| Declared Topic Areas | Search & Problem Solving + Knowledge Representation & Reasoning |
| Declared Track | Application |

## Team members

| Member Name | Member ID |
| --- | --- |
| Vedant Shah | 2024A7PS0135H |
| Jenil Karia | 2024A7PS0100H |
| Pratham Singla | 2024A8PS0486H |
| Krishna Gupta | 2024A3PS0380H |
| Aditya Sanadhaya | 2024AAPS0263H |
| Mubeen Khan | 2024A8PS0489H |
| Kshitij Mathur | 2024A8PS0462H |
| Raj Parab | 2024A3PS0433H |

## Start the submitted app

Requires **Python 3.10+**. The ZIP includes the production React build and neural weights. No Node.js, PyTorch or separate server installation is required to run it.

```bash
cd LogicForge
python run.py --check
python run.py --open
```

The `--open` option opens the dashboard in your default browser. It tries the next free port when an older server occupies the requested port, so it does not open the older app. You can also double-click `START_MAC.command` on macOS, `START_WINDOWS.bat` on Windows, or run `START_LINUX.sh` on Linux.

Without `--open`, open **http://127.0.0.1:8000**. If that port is occupied, run `python run.py --port 8001` and open port 8001 instead. Stop the server with Ctrl+C.

The current entrypoint is `run.py` (or `python -m backend.api.server`).

## Using the planner

1. **Planning Model:** Choose **Full degree** (plans all semesters 1 through 7/8 with a 25-credit cap) or **Remaining degree** (enter your last completed semester and passed electives).
2. Choose CSE, EEE, ECE or E&I. In Remaining degree mode, required courses through **Last finished semester** are selected automatically for the chosen branch, with common first-year CS F111 and EEE F111 preserved across all branches.
3. Choose thesis (16 units), thesis with concurrent electives (9 + 6–9 units), or Practice School (5 summer + 20 regular-semester units). When Practice School is selected, you can flexibly place PS-II in Semester 7 or Semester 8. Choose an optional minor and any required elective preferences.
4. Leave **Auto-fill** enabled for a concrete recommendation set that meets remaining coursework requirements. Uncheck a suggested elective to exclude it and generate a replacement. Elective cards also permit pinning a course to a specific target semester.
5. **Elective Rules & DEL Overflow:** Minimums are enforced: HuEl 9 units/3 courses, DEL 12 units/4 courses, OpEl 15 units/5 courses. Extra DELs beyond requirements automatically cascade into Open Electives (`Extra DEL → OpEl`).
6. Review **Catalogue & offerings**. Each course has odd/even observations, a reference semester where available, prerequisite information and source evidence. Unlisted courses are allowed in either semester as labelled planning assumptions by default. Disable **Allow unlisted courses** for strict evidence-only planning. Observed odd/even restrictions still apply.
7. Generate with CSP or A*. Inspect the independent schedule verification separately from the graduation assessment.
8. Open **CSP vs A*** to run both actual algorithms on identical inputs after generating a verified plan. Inspect measured runtime, search nodes, backtracks, bundles, schedules and verification; apply either verified result.
9. **Saved plans** supports names, duplicates, deletion, JSON backups/import and regenerated results. A verified schedule can be exported as CSV. Results reload only when their input fingerprint and curriculum signature still match; imported results are never trusted as verified.
10. Open **`/evaluation.html`** in your browser to view the anonymous volunteer evaluation tasks (P01–P10) and empirical study results.

For a quick presentation, import `docs/submission/demo_plans.json` using Saved plans → Import plans JSON. These are explicitly labeled demo scenarios with an assumed completed first year, not real student records. See `docs/submission/DEMO.md` for a walkthrough.

## Exact curriculum scope and sources

The dashboard's authority is **`data/curriculum/scoped_catalogue.json`**:

- 384 distinct courses restricted to the supplied course images: four branch core/elective pools, common/institutional subjects, humanities, general awareness, projects and the five pictured minors.
- Minors: Computing and Intelligence (non-CSE only), Data Science, Robotics and Automation, Semiconductor Devices and Technology, Finance.
- Odd snapshot: **Hyderabad, Semester I 2026–27**.
- Even snapshot: **Hyderabad, Semester II 2024–25**.
- Observations: 67 odd-only, 103 even-only, 51 both-parity, 163 unconfirmed. Evidence includes page/excerpt and source PDF hashes.

The timetable snapshots are from different years. They are used as repeating-parity planning observations, not confirmation of future registration availability. Several first-year F-series subjects are absent from the newer U-series timetable; no U-series substitution is made. The recommended programme semester is displayed separately from observed offering parity. Textbook-only references are excluded from offering extraction.

Unlisted courses use an explicit both-semester planning assumption, enabled by default and recorded in the audit. Turn it off for strict planning or specify an individual availability confirmation. The older branch/minor JSON directories remain reproducible **research fixtures** for the original solvers and experiments; the dashboard does not select its courses from those broader legacy catalogues.

## What is checked

- Encoded prerequisite/corequisite formulas, odd/even offerings, horizon, credit caps, availability windows and final-semester project constraints.
- Degree: 144 total units, 129 coursework units, 41 coursework courses, 42 total courses, all institutional/discipline cores and alternatives, general awareness, HuEl 9 units/3 courses, DEL 12/4, OpEl 15/5, and the route.
- Minor: required cores/alternatives, total courses/units, at least 2 elective courses/6 units, at most 2 mandatory-major courses/6 units, at most one project. GPA ≥4.5 and declaration/approval remain external.
- Projects: at most 3 DEL, 3 open and 5 overall; DEL subtype caps study 1, laboratory 2, design 2, special 1. Allied-branch DEL permissions are not assumed.
- Thesis: either 16 units alone or 9 units with 6–9 concurrent elective units across at least two courses. PS-I is a separate summer placement with foundation completion checks, never regular-semester load or invented passed credit.

The app does not certify registration or a degree award. It does not infer missing official prerequisite rules, calculate GPA, resolve lecture/exam clashes, encode a second major, or grant campus approval. A* uses a production bundle limit of 10, so global optimality is not claimed. Elective recommendation is deterministic rather than exhaustive combination optimization.

## Learned guidance

The included six-feature MLP predicts remaining terms and is now trained on 3,000 small synthetic states with exact optimal-horizon labels. See backend/ml/optimal_artifacts for data, proof fixtures and held-out-family metrics. Transfer to full curricula is experimental. In learned A* mode, the **composite bound remains the primary f score**; the neural model orders states tied on f and depth. The page shows raw prediction, primary bound, features, timing and nodes. This avoids out-of-distribution neural predictions overriding a valid lower bound. It is an experimental guidance policy, not a promised speedup.

## Verification and development

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python scripts/benchmark_submission.py
```

The current suite has 379 passing tests, including exhaustive tiny-model checks, all four live branches, five minors, three routes, source parsing, HTTP validation, project quotas, DEL overflow, semester choices, and tampered-plan rejection. `docs/submission/benchmark.csv` contains measured five-run medians; timings are host-dependent and are not speedup guarantees. Browser acceptance covers real CSP/learned-A* requests, source uncertainty/overrides, Finance, comparison, JSON/CSV transfers, modals, saved-result signatures, animation and 320–1440px layout checks.

To edit the frontend, install Node.js 18+ and run two terminals:

```bash
# Repository root
python run.py
```

```bash
# Another terminal
cd frontend
npm ci
npm run dev
```

Open http://localhost:3000. Vite proxies `/api` to port 8000. Rebuild the included production UI with `npm run build` from `frontend/`.

To repeat browser acceptance checks against the running production app:

```bash
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python tests/browser/smoke.py --url http://127.0.0.1:8000
```

Use `--browser-executable /path/to/chromium` for an existing Chromium installation. Screenshots and the test export are written to `work/browser-checks/` (or `--output`). The test uses a fresh browser context and hypothetical demo transcript.

To repeat source extraction, install Poppler's `pdftotext` and run:

```bash
python scripts/ingest_offerings.py --odd "TIMETABLE FIRST SEMESTER 2026 -27 (2).pdf" --even "TIMETABLE - II SEMESTER 2024 -25 (1).pdf"
```

The app itself has no PDF dependency. The original heavy research/training dependencies are in `requirements-experiments.txt`; the submitted runtime uses the standard library.

## Submission material

- `docs/submission/REPORT.md`: model, evidence, algorithms, validation and limits.
- `docs/submission/DEMO.md`: presentation walkthrough.
- `docs/submission/demo_plans.json`: importable example scenarios.
- `docs/submission/benchmark.csv`: reproducible live measurements.
- `scripts/benchmark_submission.py`: comparison runner.
- `scripts/ingest_offerings.py`: evidence extraction with textbook-boundary regression coverage.
- `tests/test_scoped_submission.py`: acceptance checks for the delivered scope.

## Updated uploaded ML backend

`backend/ml/` contains the corrected and integrated `ml.zip` pipeline. Training,
API diagnostics and runtime inference share the canonical feature extractor.
Run `python -m backend.ml.generate_training_data` followed by
`python -m backend.ml.train_model` to regenerate portable JSON weights. The
optional GBDT research comparison uses `requirements-ml.txt` and
`python -m backend.ml.train_model --include-gbdt`.

Current data: 224 verified-trajectory states / 32 scenarios across all four
branches. The E&I branch is held out and exact train/test feature duplicates
are removed from training. Labels are feasible suffix upper bounds, not proven
optimal terms. See `backend/ml/README.md`, `artifacts/metrics.json` and the app's
Learned heuristic page for measured error and limitations. Missing or invalid
models fall back to composite guidance without blocking startup.

## Choose an elective semester

Each HuEl/DEL/OpEl card has **Schedule in semester**. Choose a future semester
to add the course and fix its placement, or choose **Automatic** to let the
planner place it. Existing degree categories are preserved. Confirmed parity,
prerequisites, credit caps and capstone rules still apply. Pins are saved with
plans and isolated by branch. Removing an elective removes its semester choice.
Marking it passed clears its future pin. An explicit verified move updates a
pinned course's semester choice.

Generate opens Semester plan immediately, then scrolls to the verified future
semesters. Completed semesters are collapsed behind **Show completed semesters**.
A failed request shows constraints or validation reasons instead of blank future
cards. A* generation retries a wider bundle search and can fall back to CSP;
the actual solver and attempts are recorded, and CSP fallback is labelled. The
CSP vs A* comparison disables fallback so it measures each algorithm separately.
A shorter horizon is never silently expanded; change the target explicitly.

## Elective minimums and additional DELs

HuEl requires at least 3 courses and 9 credits. DEL requires at least 4 courses
and 12 credits. OpEl requires at least 5 courses and 15 credits. These are
minimums, not selection caps; adding further courses does not trigger a credit
limit popup. Following the requested policy, once both DEL minimums are met,
additional DEL courses count as OpEls. Standard four 3-credit DELs meet the
requirement, so the fifth counts as open. If four lower-credit courses total
less than 12, more DEL credits are still needed before overflow begins.
Completed courses take priority, followed by explicit selection order. Each
course counts once toward a degree category; its minor membership and semester
choice are preserved. Removing an earlier DEL lets the next eligible DEL fill
the requirement. Automatic recommendations use converted DELs before adding
further open electives. Course cards show live category progress and conversion
badges, and the generated audit uses the same allocation policy.

## Proposal completion artifacts

- Optional Remaining degree mode accepts a private completed-course transcript and models backlogs. Full-degree mode remains the default.
- Every course card can display its placement derivation. Infeasible results include budgeted deletion-based conflict analysis with minimality/timeout flags.
- `experiments/proposal/run_evaluation.py`: 200 synthetic profiles, identical CSP/A* candidate models, propagation/order and heuristic ablations, independent verification, bootstrap CIs and paired Wilcoxon statistics. Search timeouts are unresolved, not UNSAT.
- `experiments/proposal/exact_validation.py`: 500 small-instance comparisons against a proved optimum and20 brute-force minimal-core checks. Includes direct-neural research mode in addition to safe production tie-breaking.
- `python -m backend.ml.generate_optimal_data`: reproduce3000 exact label states and complete shorter-horizon UNSAT proofs.
- `/evaluation.html` and `evaluation/README.md`: consent-based anonymous volunteer tasks and feedback export; `evaluation/analyse_feedback.py` analyses real returned files. E5 now includes10 user-supplied consenting responses and computed results in evaluation/volunteer_results.json.
