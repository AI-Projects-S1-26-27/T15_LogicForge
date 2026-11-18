# Pair B: Constraint Satisfaction Problem Formulation, Backtracking, and Propagation

**Authors:** Aditya Sanadhaya, Kshitij Mathur

## 1. What We Built

Pair B owns the constraint satisfaction problem (CSP) planning engine for GraphMind:
- `backend/csp/model.py`: Formal CSP data model defining variables, variable domains, constraint scopes, and the `build_problem` adapter.
- `backend/csp/solver.py`: Backtracking search augmented with Forward Checking (FC), Generalized Arc Consistency (AC-3 / MAC), Minimum Remaining Values (MRV) variable ordering, degree heuristic tiebreaking, and Least Constraining Value (LCV) value ordering.
- `experiments/csp_ablation.py`: Comprehensive ablation experiment (E2) evaluating search effort across all constraint propagation and ordering configurations.
- `tests/test_csp.py`: 22 unit tests validating SAT/UNSAT correctness against independent brute force, cross-checking against Pair A's entailment resolver, and verifying trail undo consistency.

---

## 2. CSP Formulation

The curricular planning problem is formulated as a finite-domain CSP:
1. **Variables ($V$):** Every outstanding course $c \in \text{Curriculum} \setminus \text{Completed}$.
2. **Domains ($D$):** For each variable $c$, the domain initially contains all semester integers $s \in [\text{current\_semester} + 1, \text{target\_semester}]$ satisfying the course's term parity (`odd`, `even`, or `both`). For elective courses (Discipline Electives, Humanities Electives, Open Electives), the domain is augmented with the sentinel value `NOT_TAKEN`. Discipline Core and University Core courses must be completed and cannot take `NOT_TAKEN`.
3. **Constraints ($C$):**
   - **Prerequisite Ordering (`prereq:c`):** For each course $c$ with formula $F(c)$, prerequisite dependencies (`PRE`) must be scheduled in strictly earlier terms ($s_{\text{dep}} < s_c$), while corequisites (`CO`) may be scheduled concurrently in the same term ($s_{\text{dep}} \le s_c$).
   - **Semester Credit Windows (`credit_cap:s`):** The sum of credits scheduled in any semester $s$ cannot exceed `max_credits` ($\sum_{c: s_c = s} \text{credits}(c) \le \text{max\_credits}$). An optional floor `min_credits` enforces full-time enrollment up to graduation.
   - **Category Minimum Floors (`category_min:cat`):** The cumulative credits from completed and scheduled courses in each category must satisfy $\sum_{c \in \text{cat}} \text{credits}(c) \ge \text{credit\_minimum}(\text{cat})$.
   - **Graduation Horizon:** Enforced structurally by capping variable domains at `target_semester`.

---

## 3. Propagation and Ordering Algorithms

### Constraint Propagation
- **Forward Checking (FC):** When variable $X$ is assigned value $v$, FC removes conflicting values from the domains of all unassigned variables $Y$ connected to $X$ by active prerequisite or credit-window constraints.
- **Arc Consistency (AC-3 / MAC):** Enforces generalized arc consistency over monotone prerequisite Boolean trees. Because curriculum prerequisite trees consist exclusively of AND/OR connectives with positive leaf literals (no negation), support checking is exact, sound, and polynomial: a formula is satisfiable over variable domains iff each leaf literal has at least one supporting value in its variable's domain.
- **Bounds Checking:** Evaluates the $n$-ary sum constraints (credit caps and category credit floors) after each assignment. If the forced credits in semester $s$ exceed `max_credits`, or if the maximum possible remaining credits in a category cannot reach its required floor, the branch is pruned immediately.

### Variable and Value Ordering Heuristics
- **Minimum Remaining Values (MRV):** Chooses the unassigned variable with the smallest current domain size ($|D(v)|$), adhering to the fail-first principle.
- **Degree Heuristic Tiebreaker:** When multiple variables have equal domain sizes, ties are broken by picking the variable involved in the largest number of active constraints on remaining unassigned variables.
- **Least Constraining Value (LCV):** For an assigned variable $X$, evaluates candidate values $v \in D(X)$ and orders them by the number of choices they eliminate from the domains of neighboring unassigned variables, maximizing remaining search flexibility.

---

## 4. Experimental Results: E2 Propagation Ablation

We evaluated 8 representative curriculum instances across 7 solver configurations under a 30-second per-instance timeout:
1. `plain`: Chronological backtracking with static variable/value ordering.
2. `+fc`: Plain backtracking with Forward Checking.
3. `+ac3`: Plain backtracking with AC-3 root propagation and maintaining arc consistency.
4. `+mrv`: Chronological backtracking with MRV variable selection.
5. `+fc+mrv`: Forward checking combined with MRV variable selection.
6. `+mrv+lcv`: MRV variable selection combined with LCV value ordering.
7. `all`: Full solver pipeline (FC + AC-3 + MRV + Degree Tiebreak + LCV).

### Summary Statistics (`experiments/results/csp_ablation.csv`)

| Configuration | Mean Search Nodes | Mean Backtracks | Mean Checks | Mean Prunings | Mean Runtime (s) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **plain** | 13,378.5 | 13,366.8 | 18,841.0 | 14,071.8 | 0.0801s |
| **+fc** | 25.4 | 13.6 | 126.5 | 84.5 | 0.0010s |
| **+ac3** | 21.2 | 9.5 | 135.6 | 74.4 | 0.0010s |
| **+mrv** | 76.2 | 64.5 | 120.8 | 58.5 | 0.0009s |
| **+fc+mrv** | 26.0 | 14.2 | 134.0 | 84.8 | 0.0010s |
| **+mrv+lcv** | 26.0 | 14.2 | 44.0 | 38.5 | 0.0010s |
| **all** | **13.2** | **1.5** | 125.6 | 35.4 | **0.0011s** |

### Key Findings
1. **Massive Search Pruning:** Combining Forward Checking and AC-3 reduces search node expansions from **13,378.5 down to 13.2** — a **99.9% reduction in search space exploration**.
2. **Backtrack Elimination:** The combination of MRV, degree tiebreaking, and LCV slashes backtracks from 13,366.8 to just **1.5 backtracks on average**.
3. **Instant Infeasibility Detection:** On tightly constrained UNSAT instances (e.g. `real_target7_cap20` and `real_target6_cap20`), AC-3 prunes the empty domain at the root node in under 0.6 milliseconds, completely bypassing exponential tree exploration.
