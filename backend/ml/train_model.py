"""Corrected ml.zip training: branch holdout, duplicate removal, honest labels.

Standard-library MLP trains to portable JSON consumed by live A*. Optional GBDT
comparison requires numpy/scikit-learn and is research-only; it never replaces
the primary admissible bound or gets deserialized in the production server.
"""

import argparse
import csv
import json
import math
import time
from pathlib import Path
from backend.astar.neural_regressor import NeuralRegressor
from .features import FEATURE_NAMES, FEATURE_VERSION
from .generate_training_data import ARTIFACTS
from .predict import MODEL_PATH


def load_dataset(artifact_dir=ARTIFACTS):
    path = Path(artifact_dir)
    metadata = json.loads((path / "dataset.json").read_text())
    if (
        metadata.get("feature_version") != FEATURE_VERSION
        or metadata.get("features") != FEATURE_NAMES
    ):
        raise ValueError(
            "Feature contract mismatch; regenerate data using backend.ml.generate_training_data."
        )
    with (path / "training_data.csv").open() as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["x"] = [float(r[n]) for n in FEATURE_NAMES]
        r["y"] = float(r["remaining_terms"])
        if any(not math.isfinite(v) or v < 0 for v in r["x"] + [r["y"]]):
            raise ValueError("Training values must be finite and nonnegative.")
    return rows, metadata


def split_dataset(rows, held_out_branch="e_and_i"):
    test = [r for r in rows if r["branch"] == held_out_branch]
    test_features = {tuple(r["x"]) for r in test}
    train = [
        r
        for r in rows
        if r["branch"] != held_out_branch and tuple(r["x"]) not in test_features
    ]
    if not train or not test:
        raise ValueError("Need nonoverlapping train and holdout branches.")
    return train, test


def evaluate_model(predict, rows):
    expected = [r["y"] for r in rows]
    start = time.perf_counter()
    predicted = [max(0.0, float(predict(r["x"]))) for r in rows]
    latency = (time.perf_counter() - start) / len(rows) * 1e6
    if any(not math.isfinite(v) for v in predicted):
        raise ValueError("Non-finite model predictions.")
    errors = [a - b for a, b in zip(predicted, expected)]
    average = sum(expected) / len(expected)
    total = sum((v - average) ** 2 for v in expected)
    return dict(
        rmse=math.sqrt(sum(e * e for e in errors) / len(errors)),
        mae=sum(abs(e) for e in errors) / len(errors),
        r2=1 - sum(e * e for e in errors) / total if total else None,
        upper_bound_label_exceedance_rate=sum(e > 1e-4 for e in errors) / len(errors),
        latency_microseconds=latency,
        note="Labels are feasible upper bounds; this is not an empirical admissibility or optimality certificate.",
    )


def train_models(
    artifact_dir=ARTIFACTS,
    model_path=MODEL_PATH,
    epochs=250,
    held_out_branch="e_and_i",
    include_gbdt=False,
):
    rows, data_meta = load_dataset(artifact_dir)
    train, test = split_dataset(rows, held_out_branch)
    model = NeuralRegressor()
    fit = model.fit(
        [r["x"] for r in train],
        [r["y"] for r in train],
        epochs=epochs,
        lr=0.002,
        seed=42,
    )
    metrics = {"MLPRegressor": evaluate_model(model.predict_one, test)}
    if include_gbdt:
        from sklearn.ensemble import HistGradientBoostingRegressor

        gbdt = HistGradientBoostingRegressor(
            max_iter=150,
            learning_rate=0.08,
            max_leaf_nodes=15,
            min_samples_leaf=5,
            random_state=42,
        )
        gbdt.fit([r["x"] for r in train], [r["y"] for r in train])
        metrics["HistGradientBoostingRegressor"] = evaluate_model(
            lambda x: gbdt.predict([x])[0], test
        )
    report = dict(
        feature_version=FEATURE_VERSION,
        features=FEATURE_NAMES,
        dataset_size=len(rows),
        train_rows=len(train),
        test_rows=len(test),
        held_out_branch=held_out_branch,
        split="Entire branch held out; exact feature duplicates removed from training",
        label_kind=data_meta["label_kind"],
        catalogue_signature=data_meta["catalogue_signature"],
        models=metrics,
        usage="Secondary ordering among equal-f, equal-depth states only; composite remains the primary bound",
        fit=fit,
    )
    if data_meta["label_kind"] == "exact_optimal_remaining_terms_small_instances":
        report["split"] = "Held-out synthetic generator family; exact feature duplicates removed from training"
        report["held_out_branch"] = "synthetic family e_and_i (not a real branch evaluation)"
        for metric in metrics.values():
            metric["note"] = "Exact optimal labels on small synthetic instances; transfer to full curriculum is experimental."
    model_path = Path(model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(model_path))
    weights = json.loads(model_path.read_text())
    weights["metadata"] = report
    model_path.write_text(json.dumps(weights, indent=2, allow_nan=False))
    (Path(artifact_dir) / "metrics.json").write_text(
        json.dumps(report, indent=2, allow_nan=False)
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, default=ARTIFACTS)
    parser.add_argument("--model-output", type=Path, default=MODEL_PATH)
    parser.add_argument("--epochs", type=int, default=250)
    parser.add_argument("--include-gbdt", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            train_models(
                args.artifact_dir,
                args.model_output,
                args.epochs,
                include_gbdt=args.include_gbdt,
            ),
            indent=2,
        )
    )
