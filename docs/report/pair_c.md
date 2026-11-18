# Pair C: Informed State-Space Search, Admissible Heuristics, and Deep Learning

**Authors:** Raj Parab, Jenil Karia

## 1. What We Built

Pair C owns the heuristic search planning formulation and learned heuristic components:
- `backend/astar/planner.py`: State-space A* planner formulating planning over semester course bundles.
- `backend/astar/heuristics.py`: Handcrafted admissible heuristics ($h_{\text{credit}}$, $h_{\text{chain}}$, $h_{\text{comp}}$) and the learned neural heuristic ($h_{\text{learned}}$).
- `backend/astar/features.py`: Feature extractor computing the 6 state-space features specified in Section 3 of the proposal.
- `backend/astar/neural_regressor.py`: Multi-Layer Perceptron (MLP) regressor architecture for predicting remaining plan length from state features.
- `experiments/train_learned_heuristic.py`: Self-supervised dataset generation and training pipeline.
- `experiments/solver_comparison.py`: Experiment E1 comparing A* and CSP on identical planning instances using paired Wilcoxon signed-rank tests and 95% bootstrap confidence intervals.
- `experiments/heuristic_comparison.py`: Experiment E3 evaluating search effort and optimality gap across all four heuristics.

---

## 2. A* Search Formulation

### State Space
A state $s$ is modeled as a tuple:
$$s = (\text{next\_term}, \text{completed\_and\_scheduled\_courses})$$
where:
- $\text{next\_term} \in \{1, \dots, \text{target\_semester} + 1\}$ is the index of the next semester to be planned.
- $\text{completed\_and\_scheduled\_courses}$ is the mapping of courses already completed or scheduled to their designated semesters.

### Actions
An action corresponds to choosing a valid, credit-feasible course bundle $B \subseteq \text{Variables}$ to be taken in $\text{next\_term}$. To be valid, a bundle $B$ must satisfy:
1. **Term Parity:** Each course $c \in B$ must allow offering in $\text{next\_term}$.
2. **Prerequisite Satisfaction:** All prerequisites of $c \in B$ must either be completed prior to $\text{next\_term}$ or (for corequisites `CO`) included within the same bundle $B$.
3. **Credit Limits:** $\text{min\_credits} \le \sum_{c \in B} \text{credits}(c) \le \text{max\_credits}$.

The empty bundle $B = \emptyset$ is valid when credit minimums permit, allowing the planner to wait across parity mismatches.

### Cost Function
Path cost $g(s)$ equals the number of planned semesters elapsed since `current_semester`.

---

## 3. Admissible Heuristics and Dominance

We derived two independent admissible lower bounds and their composite:

1. **Credit Bound ($h_{\text{credit}}$):**
   $$h_{\text{credit}}(s) = \left\lceil \frac{\text{remaining\_required\_credits}}{\text{max\_credits\_per\_term}} \right\rceil$$
   Admissible because no semester can supply more credits than the per-term ceiling.

2. **Critical-Path DAG Bound ($h_{\text{chain}}$):**
   $$h_{\text{chain}}(s) = \text{depth of longest remaining prerequisite chain}$$
   Admissible because a dependency chain of depth $k$ strictly requires at least $k$ distinct terms under the ordering constraint $s_{\text{dep}} < s_c$.

3. **Composite Bound ($h_{\text{comp}}$):**
   $$h_{\text{comp}}(s) = \max\left(h_{\text{credit}}(s), h_{\text{chain}}(s)\right)$$
   Because both bounds are admissible lower bounds on the same cost metric, their pointwise maximum is provably admissible and **dominates** each individual bound:
   $$\forall s, \quad h_{\text{comp}}(s) \ge h_{\text{credit}}(s) \quad \text{and} \quad h_{\text{comp}}(s) \ge h_{\text{chain}}(s)$$

---

## 4. Learned Heuristic (Deep Learning Component)

Per Arfaee, Zilles & Holte (2011), heuristic functions for large state spaces can be learned to predict search distance from state features.

### Feature Representation
For any partial plan state $s$, `backend/astar/features.py` extracts a 6-dimensional feature vector:
1. `outstanding_credits`: Total credits still required to satisfy remaining cores and category minimums.
2. `outstanding_course_count`: Count of remaining mandatory courses plus estimated elective count.
3. `max_remaining_chain_depth`: Topological depth of longest remaining prerequisite chain.
4. `parity_locked_course_count`: Number of unassigned courses restricted to odd or even semesters.
5. `terms_remaining`: Available semester headroom ($\text{target\_semester} - \text{next\_term} + 1$).
6. `unsatisfied_disjunction_count`: Number of unsatisfied OR-branches across remaining course prerequisites.

### Model Architecture and Training
- **Architecture:** 2-hidden-layer Multi-Layer Perceptron (Input 6 $\to$ Dense 16, ReLU $\to$ Dense 8, ReLU $\to$ Dense 1, Linear).
- **Self-Supervised Data:** `experiments/train_learned_heuristic.py` generated 598 state-outcome tuples by solving diverse student scenarios to optimality.
- **Training Results:** Converged in 120 epochs with a final MSE of **0.0897**, demonstrating high predictive accuracy for remaining semester plan length.

---

## 5. Experimental Results: E1 and E3

### Experiment E1: Solver Comparison (`experiments/results/e1_summary.md`)
Comparing A* search against CSP backtracking on identical instances across the benchmark:
- **Plan Validity:** Both solvers achieved **100.0% validity** against the independent verifier.
- **Search Effort:**
  - A* Mean Nodes Expanded: **604.6** (95% CI: [119.8, 1446.5])
  - CSP Mean Nodes Expanded: **2884.3** (95% CI: [28.8, 7347.1])
  - Wilcoxon signed-rank test on node counts: $W=215.0$, $p = 0.0647$.
- **Runtime:**
  - A* Mean Time: 0.2729s (95% CI: [0.0647, 0.5951])
  - CSP Mean Time: 0.0648s (95% CI: [0.0018, 0.1607])
  - Wilcoxon signed-rank test on runtime: $W=135.0$, $p = 1.1195 \times 10^{-3}$.

### Experiment E3: Heuristic Ablation (`experiments/results/heuristic_comparison.csv`)
Evaluating all four heuristics on canonical planning challenges:

| Instance | Heuristic | Status | Terms Used | Nodes Expanded | Gap vs. Composite |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `chain3_cap4` | credit_bound | SAT | 3 | 4 | 0 |
| `chain3_cap4` | critical_path | SAT | 3 | 4 | 0 |
| `chain3_cap4` | composite | SAT | 3 | 4 | 0 |
| `chain3_cap4` | **learned** | SAT | 3 | 4 | **0** |
| `three_independent_cap4` | credit_bound | SAT | 3 | 11 | 0 |
| `three_independent_cap4` | critical_path | SAT | 3 | 19 | 0 |
| `three_independent_cap4` | composite | SAT | 3 | 11 | 0 |
| `three_independent_cap4` | **learned** | SAT | 3 | 12 | **0** |
| `even_course_from_odd_term` | credit_bound | SAT | 2 | 3 | 0 |
| `even_course_from_odd_term` | critical_path | SAT | 2 | 3 | 0 |
| `even_course_from_odd_term` | composite | SAT | 2 | 3 | 0 |
| `even_course_from_odd_term` | **learned** | SAT | 2 | 3 | **0** |

Across all test instances, the learned heuristic achieved an **optimality gap of 0**, finding the minimum-term plan while maintaining compact search node expansions.
