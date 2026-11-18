"""Portable learned guidance adapted from ml.zip, with no pickle/joblib runtime.

The primary A* score remains g + composite. A prediction only orders equal-f,
equal-depth states. max(composite, learned) is not an admissibility guarantee.
Invalid or missing JSON models fall back to the composite bound.
"""

import json
import math
from functools import lru_cache
from pathlib import Path
from backend.astar.neural_regressor import NeuralRegressor
from .features import FEATURE_NAMES, FEATURE_VERSION, extract_features_vector

MODEL_PATH = Path(__file__).resolve().parents[1] / "astar/learned_model.json"


@lru_cache(maxsize=8)
def _load(path, modified_ns, size):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        if data.get("input_dim") != 6:
            return None
        meta = data.get("metadata", {})
        if not isinstance(meta, dict):
            return None
        if meta.get("feature_version", FEATURE_VERSION) != FEATURE_VERSION:
            return None
        if meta.get("features", FEATURE_NAMES) != FEATURE_NAMES:
            return None
        dims = [data["input_dim"], data["hidden1"], data["hidden2"], 1]
        if any(type(n) is not int or not 1 <= n <= 128 for n in dims):
            return None
        for i in range(1, 4):
            weights, bias = data[f"W{i}"], data[f"b{i}"]
            if len(weights) != dims[i - 1] or len(bias) != dims[i]:
                return None
            if any(len(row) != dims[i] for row in weights):
                return None
            values = [v for row in weights for v in row] + bias
            if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
                return None
        if any(len(data[k]) != 6 for k in ("means", "stds")):
            return None
        if any(
            type(v) not in (int, float) or not math.isfinite(v)
            for k in ("means", "stds")
            for v in data[k]
        ):
            return None
        if any(v <= 0 for v in data["stds"]):
            return None
        return NeuralRegressor.load(path), meta
    except (OSError, ValueError, KeyError, TypeError, OverflowError):
        return None


def _model(path=None):
    path = Path(path or MODEL_PATH)
    try:
        stat = path.stat()
        return _load(str(path), stat.st_mtime_ns, stat.st_size)
    except OSError:
        return None


def model_info(path=None):
    loaded = _model(path)
    return {
        "available": loaded is not None,
        "kind": (
            f"MLP 6 → {loaded[0].hidden1} → {loaded[0].hidden2} → 1"
            if loaded
            else "Composite fallback"
        ),
        "policy": "equal-f, equal-depth tie-break only",
        "metadata": loaded[1] if loaded else {},
    }


def learned_heuristic(problem, placed, next_term, use_anchor=False, *, model_path=None):
    """Return secondary guidance. Legacy use_anchor is accepted but never alters f."""
    from backend.astar.heuristics import composite

    loaded = _model(model_path)
    if loaded:
        try:
            value = float(
                loaded[0].predict_one(
                    extract_features_vector(problem, placed, next_term)
                )
            )
            if math.isfinite(value):
                return max(0.0, value)
        except (ValueError, TypeError, OverflowError, IndexError):
            pass
    return composite(problem, placed, next_term)
