"""Statistics for the experiments (Pair D), in plain Python (no numpy/scipy needed).

- ``bootstrap_ci``: percentile bootstrap confidence interval of the mean.
- ``wilcoxon_signed_rank``: paired test for comparing two solvers on the
  same instances (node counts are skewed, so no t-test). Exact p-value for
  small samples without ties, normal approximation otherwise.
- ``summarize``: mean + CI in one dict, ready for a results table.
"""

from __future__ import annotations

import math
import random
from typing import Sequence


def mean(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("mean of an empty list")
    return sum(values) / len(values)


def bootstrap_ci(
    values: Sequence[float],
    level: float = 0.95,
    iterations: int = 10_000,
    seed: int = 42,
) -> tuple[float, float]:
    """Percentile bootstrap CI for the mean. Works for 0/1 values too (rates)."""
    data = list(values)
    if not data:
        raise ValueError("bootstrap of an empty list")
    if len(data) == 1:
        return (data[0], data[0])
    rng = random.Random(seed)
    n = len(data)
    means = sorted(sum(rng.choice(data) for _ in range(n)) / n for _ in range(iterations))
    alpha = (1 - level) / 2
    low = means[int(math.floor(alpha * (iterations - 1)))]
    high = means[int(math.ceil((1 - alpha) * (iterations - 1)))]
    return (low, high)


def summarize(values: Sequence[float], level: float = 0.95, **kw) -> dict:
    low, high = bootstrap_ci(values, level, **kw)
    return {"n": len(values), "mean": mean(values), "ci_low": low, "ci_high": high,
            "level": level}


def _ranks(values: Sequence[float]) -> list[float]:
    """Average ranks (1-based), ties share the mean of their positions."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def _exact_p(w_plus: float, n: int) -> float:
    """Two-sided exact p-value for W+ with n non-zero, untied differences."""
    total = n * (n + 1) // 2
    counts = [0] * (total + 1)
    counts[0] = 1
    for r in range(1, n + 1):
        for s in range(total, r - 1, -1):
            counts[s] += counts[s - r]
    paths = 2 ** n
    w = int(round(w_plus))
    low_tail = sum(counts[: w + 1]) / paths
    high_tail = sum(counts[w:]) / paths
    return min(1.0, 2 * min(low_tail, high_tail))


def wilcoxon_signed_rank(x: Sequence[float], y: Sequence[float]) -> dict:
    """Paired two-sided Wilcoxon signed-rank test of x vs y.

    Zero differences are dropped (Wilcoxon's method). Returns the statistic
    (the smaller of W+ and W-), the p-value and which method was used.
    """
    if len(x) != len(y):
        raise ValueError("x and y must be paired (same length)")
    diffs = [a - b for a, b in zip(x, y) if a != b]
    n = len(diffs)
    if n == 0:
        return {"statistic": 0.0, "p_value": 1.0, "n": 0, "method": "all differences zero"}
    ranks = _ranks([abs(d) for d in diffs])
    w_plus = sum(r for r, d in zip(ranks, diffs) if d > 0)
    w_minus = sum(r for r, d in zip(ranks, diffs) if d < 0)
    statistic = min(w_plus, w_minus)
    has_ties = len(set(abs(d) for d in diffs)) < n

    if n <= 25 and not has_ties:
        return {"statistic": statistic, "p_value": _exact_p(w_plus, n), "n": n,
                "method": "exact"}

    mean_w = n * (n + 1) / 4
    var_w = n * (n + 1) * (2 * n + 1) / 24
    # Tie correction.
    groups: dict[float, int] = {}
    for r in ranks:
        groups[r] = groups.get(r, 0) + 1
    var_w -= sum(t ** 3 - t for t in groups.values()) / 48
    if var_w <= 0:
        return {"statistic": statistic, "p_value": 1.0, "n": n, "method": "normal"}
    z = (abs(w_plus - mean_w) - 0.5) / math.sqrt(var_w)  # continuity correction
    p = math.erfc(max(z, 0) / math.sqrt(2))
    return {"statistic": statistic, "p_value": min(1.0, p), "n": n, "method": "normal"}
