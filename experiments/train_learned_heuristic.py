"""GraphMind — Self-Supervised Training for Learned Heuristic (Pair C)

Generates student states across diverse curriculum conditions, solves each
to find true_remaining_terms, extracts the 6 state features, trains the neural
regressor, and saves weights to backend/astar/learned_model.json.
"""

from __future__ import annotations

import json
import math
import os
import random
import sys
import time

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from backend.csp.solver import SolverConfig, solve as csp_solve
from backend.astar import AStarConfig, solve as astar_solve
from backend.astar.features import extract_state_features
from backend.astar.neural_regressor import NeuralRegressor
from backend.services.problem_builder import build_problem_for_student, DEFAULT_CURRICULUM_DIR
from backend.data.loader import load_curriculum


def generate_training_data(n_samples: int = 150, seed: int = 42) -> tuple[list[list[float]], list[float]]:
    """Generate (state_features, true_remaining_terms) pairs."""
    rng = random.Random(seed)
    curr = load_curriculum(DEFAULT_CURRICULUM_DIR, branch="cse")
    all_codes = sorted(curr.courses.keys())

    X: list[list[float]] = []
    y: list[float] = []

    print(f"Generating and solving {n_samples} self-supervised training states...", flush=True)
    t0 = time.perf_counter()

    solved_count = 0
    attempts = 0
    csp_cfg = SolverConfig(mrv=True, forward_checking=True, ac3=True, degree_tiebreak=True, timeout_s=3.0)

    while solved_count < n_samples and attempts < n_samples * 4:
        attempts += 1
        current_sem = rng.randint(1, 5)
        target_sem = rng.randint(current_sem + 2, 8)
        max_cr = rng.choice([20, 22, 24])

        num_completed = rng.randint(current_sem * 2, min(len(all_codes) - 2, current_sem * 5))
        completed = set(rng.sample(all_codes, num_completed))

        try:
            problem = build_problem_for_student(
                branch="cse",
                completed=completed,
                current_semester=current_sem,
                target_semester=target_sem,
                max_credits=max_cr,
                min_credits=0,
            )
        except Exception:
            continue

        # Solve using CSP solver
        res = csp_solve(problem, csp_cfg)

        if res.status == "SAT" and res.assignment is not None:
            root_placed: dict[str, int] = {}
            feats = extract_state_features(problem, root_placed, current_sem + 1)

            scheduled_terms = [v for v in res.assignment.values() if isinstance(v, int)]
            true_terms = max(scheduled_terms) - current_sem if scheduled_terms else 0

            X.append(feats)
            y.append(float(true_terms))
            solved_count += 1

            # Intermediate states along path
            for term in range(current_sem + 1, max(scheduled_terms, default=current_sem)):
                intermediate_placed = {c: s for c, s in res.assignment.items() if isinstance(s, int) and s <= term}
                inter_feats = extract_state_features(problem, intermediate_placed, term + 1)
                rem_terms = max(0, max(scheduled_terms) - term)
                X.append(inter_feats)
                y.append(float(rem_terms))

            if solved_count % 30 == 0:
                print(f"  {solved_count}/{n_samples} scenarios solved ({len(X)} state tuples)...", flush=True)

    print(f"Dataset generated: {len(X)} samples in {time.perf_counter() - t0:.2f}s", flush=True)
    return X, y


def main():
    X, y = generate_training_data(n_samples=150, seed=123)
    if not X:
        print("Failed to generate training data.", flush=True)
        return

    print("Training NeuralRegressor (MLP)...", flush=True)
    model = NeuralRegressor(input_dim=6, hidden1=16, hidden2=8)
    metrics = model.fit(X, y, epochs=120, lr=0.008, batch_size=16)
    print(f"Training completed: {metrics}", flush=True)

    out_dir = os.path.join(_REPO_ROOT, "backend", "astar")
    out_path = os.path.join(out_dir, "learned_model.json")
    model.save(out_path)
    print(f"Model successfully saved to {out_path}", flush=True)

    sample_pred = model.predict_one(X[0])
    print(f"Sanity test on first sample: True={y[0]}, Predicted={sample_pred:.2f}", flush=True)


if __name__ == "__main__":
    main()
