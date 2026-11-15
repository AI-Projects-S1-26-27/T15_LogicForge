# AI Tool Usage Disclosure

Per the course's academic-integrity policy (Project Guidelines, Section 6): AI tools (Claude, ChatGPT, Copilot, etc.) are allowed and can genuinely help, but every team member is fully responsible for the correctness of anything they submit — "the AI generated it" is not an excuse for a wrong result, a fabricated citation, or code that doesn't run. Each member must be able to explain, in the live viva, any part of the project's code, math, or writing they're associated with.

This file is the running log. Add an entry whenever you use an AI tool for something that ends up in the repo or report — in your PR, or shortly after.

## Log format

```
### YYYY-MM-DD — Pair X — <name>
- Tool: <Claude / ChatGPT / Copilot / etc.>
- Used for: <what it helped with, specifically>
- Verified by: <how you checked the output was correct — ran it, checked against the proposal/textbook, tested it, etc.>
```

## Log

<!-- Add entries below, most recent first. Keep this honest and specific — "used Claude for coding help" is not a disclosure; "used Claude to debug an off-by-one in the AC-3 queue implementation, verified against the worked example in Russell & Norvig Ch.6" is. -->

### 2026-11-10 — Pair D — Mohammad Mubeen Mazar Khan
- Tool: Claude (Claude Code)
- Used for: drafting Pair D's components: the independent plan verifier (`backend/verification/plan_checker.py`), the deletion-based infeasibility analyser and the plan explainer (`backend/explanations/`), the problem builder and planning service (`backend/services/`), the Streamlit app (`frontend/app.py`), the benchmark generator, statistics and E4 runner (`experiments/benchmark.py`, `stats.py`, `e4_verification.py`), their tests, and the Pair D report draft.
- Verified by: unit tests for every verifier rule plus a test that the verifier imports no solver code; infeasibility conflicts checked for minimality against a brute-force oracle on random small instances; Pair B's CSP solver cross-checked against brute force on 60 random small problems; the Wilcoxon implementation checked against the textbook example (Hollander & Wolfe, exact p = 0.0391); the service run end to end on the real CSE data. I still need to read through all of it so I can explain it in the viva.
