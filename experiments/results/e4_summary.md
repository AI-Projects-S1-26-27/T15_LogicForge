# E4: independent verification of solver plans

Every SAT plan was re-checked by `backend/verification/plan_checker.py`, which imports no solver code. Rates are means with 95% bootstrap CIs.

## CSP

- Instances: 200 (SAT 161, UNSAT 31, TIMEOUT 8)
- Plan validity rate: **100.0%** (95% CI 100.0% to 100.0%, n=161)
- Time per solved instance: 0.017s (95% CI 0.001 to 0.046)
- Violations caught: none
- Sensitivity check: 563/563 deliberately broken plans caught with the right rule (core_not_taken 144/144, credit_cap 161/161, parity 144/144, prereq 114/114)

| stratum | value | n | SAT | valid |
|---|---|---|---|---|
| slack | loose | 66 | 59 | 59 |
| slack | medium | 66 | 62 | 62 |
| slack | tight | 68 | 40 | 40 |
| profile | accelerated | 36 | 34 | 34 |
| profile | behind_one | 42 | 37 | 37 |
| profile | failed_prereq | 42 | 29 | 29 |
| profile | late_minor | 38 | 24 | 24 |
| profile | on_track | 42 | 37 | 37 |
| minor | False | 81 | 71 | 71 |
| minor | True | 119 | 90 | 90 |
| chain | long | 76 | 51 | 51 |
| chain | medium | 76 | 63 | 63 |
| chain | short | 48 | 47 | 47 |

Rules most often in the conflict of UNSAT instances: parity ×84, prereq ×35, horizon ×31, credit_cap ×19, category_min ×18
