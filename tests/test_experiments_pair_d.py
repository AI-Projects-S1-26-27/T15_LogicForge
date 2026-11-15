"""Tests for Pair D's benchmark generator, statistics and E4 runner."""

import os
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from experiments import stats  # noqa: E402


# ── statistics ──────────────────────────────────────────────────────────────

def test_wilcoxon_matches_textbook_example():
    # Hollander & Wolfe depression data (also the R / scipy docs example):
    # V = 40 (so min(W+, W-) = 5), exact two-sided p = 0.03906.
    x = [1.83, 0.50, 1.62, 2.48, 1.68, 1.88, 1.55, 3.06, 1.30]
    y = [0.878, 0.647, 0.598, 2.05, 1.06, 1.29, 1.06, 3.14, 1.29]
    result = stats.wilcoxon_signed_rank(x, y)
    assert result["method"] == "exact"
    assert result["statistic"] == 5
    assert result["p_value"] == pytest.approx(0.0390625)


def test_wilcoxon_identical_samples():
    assert stats.wilcoxon_signed_rank([1, 2, 3], [1, 2, 3])["p_value"] == 1.0


def test_wilcoxon_large_sample_uses_normal_and_detects_shift():
    x = list(range(40))
    y = [v + 3 + (v % 2) for v in x]
    result = stats.wilcoxon_signed_rank(x, y)
    assert result["method"] == "normal"
    assert result["p_value"] < 0.001


def test_bootstrap_ci_contains_mean_and_is_reproducible():
    data = [0, 1, 1, 1, 0, 1, 1, 1, 1, 1]
    low, high = stats.bootstrap_ci(data, iterations=2000)
    assert low <= stats.mean(data) <= high
    assert (low, high) == stats.bootstrap_ci(data, iterations=2000)
    assert stats.bootstrap_ci([5.0]) == (5.0, 5.0)


def test_ranks_handle_ties():
    assert stats._ranks([10, 20, 20, 30]) == [1, 2.5, 2.5, 4]


# ── benchmark + E4 (need the CSE data and Pair B's solver) ──────────────────

def test_benchmark_is_stratified_and_reproducible():
    benchmark = pytest.importorskip("experiments.benchmark")
    a = benchmark.generate(n=30, seed=1)
    b = benchmark.generate(n=30, seed=1)
    assert [s["problem"]["completed"] for s in a] == [s["problem"]["completed"] for s in b]
    assert {s["profile"] for s in a} == set(benchmark.PROFILES)
    assert {s["slack"] for s in a} == {"tight", "medium", "loose"}
    for s in a:
        p = s["problem"]
        assert p["current_semester"] < p["target_semester"]
        assert set(p["completed"]) <= set(p["courses"])
        assert s["chain_depth"] >= 0


def test_simulated_transcripts_respect_prerequisites():
    benchmark = pytest.importorskip("experiments.benchmark")
    for s in benchmark.generate(n=20, seed=3):
        p = s["problem"]
        done = set(p["completed"])
        for code in done:
            assert benchmark._satisfied(p["courses"][code].get("formula"), done, p["courses"]), code


def test_e4_runs_end_to_end(tmp_path):
    benchmark = pytest.importorskip("experiments.benchmark")
    e4 = pytest.importorskip("experiments.e4_verification")
    students = benchmark.generate(n=6, seed=5)
    rows = e4.run(students, timeout_s=5)
    assert len(rows) >= 6
    for row in rows:
        if row["status"] == "SAT":
            assert row["valid"] is True, row
            # Every deliberately broken copy of the plan must be caught.
            assert row["mutants"] and row["mutants_caught"] == row["mutants"], row
    text = e4.summary_markdown(rows)
    assert "Plan validity rate" in text or "SAT 0" in text
