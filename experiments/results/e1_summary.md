# Experiment E1: Solver Comparison (CSP vs. A*)

Evaluation of CSP Backtracking (+FC +AC-3 +MRV +Degree +LCV) versus Informed A* Search (Composite Admissible Heuristic)
on identical planning instances, evaluated using paired Wilcoxon signed-rank tests and 95% bootstrap confidence intervals.

- **Instances evaluated**: 39
- **A* plan validity rate**: 100.0% (verified by independent verifier)
- **CSP plan validity rate**: 100.0% (verified by independent verifier)

## Statistical Comparisons (Paired Instances)

- **Search Nodes Expanded**:
  - A* Mean: 604.6 (95% CI: [119.8, 1446.5])
  - CSP Mean: 2884.3 (95% CI: [28.8, 7347.1])
  - Wilcoxon signed-rank test: W=215.0, p-value=6.4728e-02 (normal)

- **Wall-Clock Runtime (seconds)**:
  - A* Mean: 0.2729s (95% CI: [0.0647, 0.5951])
  - CSP Mean: 0.0648s (95% CI: [0.0018, 0.1607])
  - Wilcoxon signed-rank test: W=135.0, p-value=1.1195e-03 (normal)

## Selected Instance Comparison

| Instance | A* Status | A* Terms | A* Nodes | A* Time(s) | CSP Status | CSP Terms | CSP Nodes | CSP Time(s) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| chain3_cap4 | SAT | 3 | 4 | 0.000274 | SAT | 3 | 3 | 0.000307 |
| chain3_horizon2 | UNSAT | 0 | 1 | 2.5e-05 | UNSAT |  | 0 | 4.4e-05 |
| three_independent_cap4 | SAT | 3 | 11 | 0.000371 | SAT | 3 | 6 | 0.000134 |
| even_course_from_odd_term | SAT | 2 | 3 | 6.7e-05 | SAT | 2 | 1 | 4.1e-05 |
| S000 | UNSAT | 0 | 56 | 0.0356 | UNSAT |  | 6584 | 0.194061 |
| S005 | SAT | 2 | 3 | 0.000814 | SAT | 3 | 12 | 0.00088 |
| S010 | UNSAT | 0 | 1 | 0.000532 | UNSAT |  | 0 | 0.00011 |
| S015 | TIMEOUT | 0 | 14274 | 8.000324 | SAT | 6 | 28 | 0.003289 |
| S020 | UNSAT | 0 | 11 | 0.006759 | SAT | 4 | 23 | 0.001469 |
| S025 | UNSAT | 0 | 11 | 0.005181 | UNSAT |  | 33053 | 0.724209 |
| S030 | UNSAT | 0 | 230 | 0.124134 | TIMEOUT |  | 294308 | 8.000026 |
| S035 | SAT | 5 | 1544 | 0.909707 | SAT | 6 | 22 | 0.00278 |
| S040 | SAT | 4 | 254 | 0.120473 | SAT | 6 | 19 | 0.00218 |
| S045 | SAT | 4 | 134 | 0.079536 | SAT | 4 | 22 | 0.001834 |
| S050 | UNSAT | 0 | 1760 | 1.454332 | SAT | 6 | 29 | 0.003429 |