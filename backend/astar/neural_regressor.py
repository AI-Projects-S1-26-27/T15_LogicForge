"""GraphMind — Neural Regressor for Learned Heuristic (Pair C)

Implements a Multi-Layer Perceptron (MLP) regressor for predicting remaining
plan length from state features, per Arfaee, Zilles & Holte (2011).
Saves and loads model weights and feature scalers to/from JSON.
"""

from __future__ import annotations

import json
import math
import os
import random
from typing import List, Tuple, Optional


class NeuralRegressor:
    """A 2-hidden-layer MLP regressor with ReLU activations:
    Input (6) -> Dense(16, ReLU) -> Dense(8, ReLU) -> Dense(1, Linear)
    """

    def __init__(self, input_dim: int = 6, hidden1: int = 16, hidden2: int = 8):
        self.input_dim = input_dim
        self.hidden1 = hidden1
        self.hidden2 = hidden2

        # Feature normalization parameters
        self.means: List[float] = [0.0] * input_dim
        self.stds: List[float] = [1.0] * input_dim

        # Xavier / He initialization
        rng = random.Random(42)
        s1 = math.sqrt(2.0 / input_dim)
        self.W1: List[List[float]] = [
            [rng.gauss(0.0, s1) for _ in range(hidden1)] for _ in range(input_dim)
        ]
        self.b1: List[float] = [0.01] * hidden1

        s2 = math.sqrt(2.0 / hidden1)
        self.W2: List[List[float]] = [
            [rng.gauss(0.0, s2) for _ in range(hidden2)] for _ in range(hidden1)
        ]
        self.b2: List[float] = [0.01] * hidden2

        s3 = math.sqrt(2.0 / hidden2)
        self.W3: List[List[float]] = [
            [rng.gauss(0.0, s3) for _ in range(1)] for _ in range(hidden2)
        ]
        self.b3: List[float] = [0.5]

    def _normalize(self, x: List[float]) -> List[float]:
        return [
            (val - self.means[i]) / (self.stds[i] if self.stds[i] > 1e-6 else 1.0)
            for i, val in enumerate(x)
        ]

    def predict_one(self, x: List[float]) -> float:
        """Forward pass for a single 6-dimensional feature vector."""
        xn = self._normalize(x)

        # Layer 1 (hidden1, ReLU)
        h1 = [0.0] * self.hidden1
        for j in range(self.hidden1):
            s = self.b1[j]
            for i in range(self.input_dim):
                s += xn[i] * self.W1[i][j]
            h1[j] = max(0.0, s)

        # Layer 2 (hidden2, ReLU)
        h2 = [0.0] * self.hidden2
        for k in range(self.hidden2):
            s = self.b2[k]
            for j in range(self.hidden1):
                s += h1[j] * self.W2[j][k]
            h2[k] = max(0.0, s)

        # Layer 3 (Output, Linear)
        out = self.b3[0]
        for k in range(self.hidden2):
            out += h2[k] * self.W3[k][0]

        # Remaining terms must be non-negative
        return max(0.0, float(out))

    def fit(
        self,
        X: List[List[float]],
        y: List[float],
        epochs: int = 150,
        lr: float = 0.005,
        batch_size: int = 32,
        seed: int = 42,
    ) -> dict:
        """Train the MLP regressor using mini-batch gradient descent with momentum."""
        n = len(X)
        if n == 0:
            return {"loss": 0.0}

        # 1. Compute means and stds for feature normalization
        for i in range(self.input_dim):
            col = [X[r][i] for r in range(n)]
            m = sum(col) / n
            var = sum((v - m) ** 2 for v in col) / n
            self.means[i] = m
            self.stds[i] = math.sqrt(var) if var > 1e-6 else 1.0

        # Pre-normalize X
        X_norm = [self._normalize(row) for row in X]

        # Velocity matrices for momentum
        v_W1 = [[0.0] * self.hidden1 for _ in range(self.input_dim)]
        v_b1 = [0.0] * self.hidden1
        v_W2 = [[0.0] * self.hidden2 for _ in range(self.hidden1)]
        v_b2 = [0.0] * self.hidden2
        v_W3 = [[0.0] * 1 for _ in range(self.hidden2)]
        v_b3 = [0.0]

        momentum = 0.9
        rng = random.Random(seed)
        indices = list(range(n))

        final_loss = 0.0
        for epoch in range(epochs):
            rng.shuffle(indices)
            epoch_loss = 0.0

            for b_start in range(0, n, batch_size):
                b_idx = indices[b_start : b_start + batch_size]
                bsz = len(b_idx)

                # Accumulate gradients
                g_W1 = [[0.0] * self.hidden1 for _ in range(self.input_dim)]
                g_b1 = [0.0] * self.hidden1
                g_W2 = [[0.0] * self.hidden2 for _ in range(self.hidden1)]
                g_b2 = [0.0] * self.hidden2
                g_W3 = [[0.0] * 1 for _ in range(self.hidden2)]
                g_b3 = [0.0]

                for idx in b_idx:
                    xi = X_norm[idx]
                    yi = y[idx]

                    # Forward
                    z1 = [self.b1[j] + sum(xi[i] * self.W1[i][j] for i in range(self.input_dim))
                          for j in range(self.hidden1)]
                    h1 = [max(0.0, val) for val in z1]

                    z2 = [self.b2[k] + sum(h1[j] * self.W2[j][k] for j in range(self.hidden1))
                          for k in range(self.hidden2)]
                    h2 = [max(0.0, val) for val in z2]

                    pred = self.b3[0] + sum(h2[k] * self.W3[k][0] for k in range(self.hidden2))

                    diff = pred - yi
                    epoch_loss += diff ** 2

                    # Backprop
                    d_out = 2.0 * diff / bsz
                    g_b3[0] += d_out
                    for k in range(self.hidden2):
                        g_W3[k][0] += d_out * h2[k]

                    d_h2 = [d_out * self.W3[k][0] * (1.0 if z2[k] > 0 else 0.0) for k in range(self.hidden2)]
                    for k in range(self.hidden2):
                        g_b2[k] += d_h2[k]
                        for j in range(self.hidden1):
                            g_W2[j][k] += d_h2[k] * h1[j]

                    d_h1 = [sum(d_h2[k] * self.W2[j][k] for k in range(self.hidden2)) * (1.0 if z1[j] > 0 else 0.0)
                            for j in range(self.hidden1)]
                    for j in range(self.hidden1):
                        g_b1[j] += d_h1[j]
                        for i in range(self.input_dim):
                            g_W1[i][j] += d_h1[j] * xi[i]

                # Update with momentum
                for k in range(self.hidden2):
                    v_W3[k][0] = momentum * v_W3[k][0] - lr * g_W3[k][0]
                    self.W3[k][0] += v_W3[k][0]
                v_b3[0] = momentum * v_b3[0] - lr * g_b3[0]
                self.b3[0] += v_b3[0]

                for j in range(self.hidden1):
                    for k in range(self.hidden2):
                        v_W2[j][k] = momentum * v_W2[j][k] - lr * g_W2[j][k]
                        self.W2[j][k] += v_W2[j][k]
                    v_b1[j] = momentum * v_b1[j] - lr * g_b1[j]
                    self.b1[j] += v_b1[j]

                for i in range(self.input_dim):
                    for j in range(self.hidden1):
                        v_W1[i][j] = momentum * v_W1[i][j] - lr * g_W1[i][j]
                        self.W1[i][j] += v_W1[i][j]

            final_loss = epoch_loss / n

        return {"epochs": epochs, "final_mse": round(final_loss, 4), "n_samples": n}

    def save(self, filepath: str) -> None:
        """Save model parameters to JSON."""
        data = {
            "input_dim": self.input_dim,
            "hidden1": self.hidden1,
            "hidden2": self.hidden2,
            "means": self.means,
            "stds": self.stds,
            "W1": self.W1,
            "b1": self.b1,
            "W2": self.W2,
            "b2": self.b2,
            "W3": self.W3,
            "b3": self.b3,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> NeuralRegressor:
        """Load model parameters from JSON."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        model = cls(data["input_dim"], data["hidden1"], data["hidden2"])
        model.means = data["means"]
        model.stds = data["stds"]
        model.W1 = data["W1"]
        model.b1 = data["b1"]
        model.W2 = data["W2"]
        model.b2 = data["b2"]
        model.W3 = data["W3"]
        model.b3 = data["b3"]
        return model
