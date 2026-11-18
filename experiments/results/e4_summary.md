# E4: independent verification of solver plans

Every SAT plan was re-checked by `backend/verification/plan_checker.py`, which imports no solver code. Rates are means with 95% bootstrap CIs.

## ASTAR

- Instances: 30 (SAT 16, UNSAT 13, TIMEOUT 1)
- Plan validity rate: **100.0%** (95% CI 100.0% to 100.0%, n=16)
- Time per solved instance: 0.942s (95% CI 0.194 to 2.048)
- Violations caught: none
- Sensitivity check: 53/53 deliberately broken plans caught with the right rule (core_not_taken 13/13, credit_cap 15/15, parity 13/13, prereq 12/12)

| stratum | value | n | SAT | valid |
|---|---|---|---|---|
| slack | loose | 10 | 9 | 9 |
| slack | medium | 10 | 5 | 5 |
| slack | tight | 10 | 2 | 2 |
| profile | accelerated | 6 | 4 | 4 |
| profile | behind_one | 6 | 3 | 3 |
| profile | failed_prereq | 6 | 3 | 3 |
| profile | late_minor | 6 | 2 | 2 |
| profile | on_track | 6 | 4 | 4 |
| minor | False | 12 | 8 | 8 |
| minor | True | 18 | 8 | 8 |
| chain | long | 13 | 6 | 6 |
| chain | medium | 13 | 6 | 6 |
| chain | short | 4 | 4 | 4 |

## CSP

- Instances: 30 (SAT 21, UNSAT 7, TIMEOUT 2)
- Plan validity rate: **100.0%** (95% CI 100.0% to 100.0%, n=21)
- Time per solved instance: 0.002s (95% CI 0.001 to 0.002)
- Violations caught: none
- Sensitivity check: 74/74 deliberately broken plans caught with the right rule (core_not_taken 18/18, credit_cap 21/21, parity 18/18, prereq 17/17)

| stratum | value | n | SAT | valid |
|---|---|---|---|---|
| slack | loose | 10 | 9 | 9 |
| slack | medium | 10 | 10 | 10 |
| slack | tight | 10 | 2 | 2 |
| profile | accelerated | 6 | 5 | 5 |
| profile | behind_one | 6 | 4 | 4 |
| profile | failed_prereq | 6 | 4 | 4 |
| profile | late_minor | 6 | 4 | 4 |
| profile | on_track | 6 | 4 | 4 |
| minor | False | 12 | 9 | 9 |
| minor | True | 18 | 12 | 12 |
| chain | long | 13 | 9 | 9 |
| chain | medium | 13 | 8 | 8 |
| chain | short | 4 | 4 | 4 |
