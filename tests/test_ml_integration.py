import copy
import json
import math
import pytest
from backend.astar.features import extract_state_features
from backend.astar.heuristics import composite
from backend.astar.planner import AStarConfig, solve
from backend.csp.model import Problem
from backend.ml.features import (
    FEATURE_NAMES,
    extract_features_dict,
    extract_features_vector,
)
from backend.ml.predict import MODEL_PATH, learned_heuristic, model_info
from backend.ml.train_model import load_dataset, split_dataset, train_models
from backend.ml.generate_training_data import generate_dataset
from backend.services.scoped_api import plan_payload
from backend.services.scoped_planner import DATA, prepare


def small_problem():
    return Problem(
        courses={
            "A": dict(credits=3, category="Discipline Core", parity="odd"),
            "B": dict(
                credits=3,
                category="Discipline Core",
                parity="even",
                formula={"kind": "or", "items": [{"kind": "leaf", "course": "A"}]},
            ),
        },
        completed=set(),
        current_semester=0,
        target_semester=4,
        max_credits=6,
    )


def test_uploaded_feature_interface_matches_live_feature_contract():
    p = small_problem()
    assert extract_features_vector(p, {}, 1) == extract_state_features(p, {}, 1)
    assert list(extract_features_dict(p, {}, 1)) == FEATURE_NAMES
    assert extract_features_dict(p, {}, 1)["unsatisfied_disjunctions"] == 1
    assert extract_features_dict(p, {"A": 1}, 2)["unsatisfied_disjunctions"] == 0
    assert extract_features_vector(p, {"A": 1, "B": 2}, 3)[0:2] == [0, 0]


@pytest.mark.parametrize("contents", [None, "not json", "[]", '{"input_dim":5}'])
def test_missing_or_corrupt_model_falls_back_without_crashing(tmp_path, contents):
    path = tmp_path / "model.json"
    if contents is not None:
        path.write_text(contents)
    p = small_problem()
    assert learned_heuristic(p, {}, 1, model_path=path) == composite(p, {}, 1)
    assert not model_info(path)["available"]


@pytest.mark.parametrize("issue", ["feature_version", "shape", "nan", "scaler"])
def test_incompatible_model_is_rejected(tmp_path, issue):
    data = json.loads(MODEL_PATH.read_text())
    if issue == "feature_version":
        data["metadata"]["feature_version"] = "incompatible"
    if issue == "shape":
        data["W1"] = [[]]
    if issue == "nan":
        data["b1"][0] = math.nan
    if issue == "scaler":
        data["stds"][0] = 0
    path = tmp_path / "model.json"
    path.write_text(json.dumps(data))
    assert not model_info(path)["available"]


def test_large_learned_prediction_cannot_prune_a_valid_search(monkeypatch):
    import backend.astar.heuristics as heuristics

    monkeypatch.setattr(heuristics, "learned_prediction", lambda *args: 1000000.0)
    result = solve(
        small_problem(), AStarConfig(heuristic="learned", bundle_breadth_limit=None)
    )
    assert result.status == "SAT"
    assert result.assignment == {"A": 1, "B": 2}
    assert result.stats["root_h"] == 2


def test_branch_holdout_has_no_episode_or_feature_leakage():
    rows, meta = load_dataset()
    train, test = split_dataset(rows)
    assert not {r["episode"] for r in train} & {r["episode"] for r in test}
    assert not {tuple(r["x"]) for r in train} & {tuple(r["x"]) for r in test}
    assert meta["label_kind"] == "verified_feasible_suffix_upper_bound"
    assert set(meta["branches"]) == {"cse", "eee", "ece", "e_and_i"}


def test_data_generation_and_portable_training_use_the_current_backend(tmp_path):
    rows, meta = generate_dataset(
        tmp_path, branches=["cse", "e_and_i"], caps=[25], minors=[""]
    )
    assert meta["episodes"] == 2 and not meta["failures"]
    model = tmp_path / "model.json"
    report = train_models(tmp_path, model, epochs=2)
    assert report["train_rows"] > 0 and report["test_rows"] > 0
    assert model_info(model)["available"]
    assert math.isfinite(report["models"]["MLPRegressor"]["mae"])


def test_learned_api_uses_integrated_model_and_reports_provenance():
    request = dict(
        branch="ece",
        current_semester=2,
        completed_courses=DATA["common"],
        bulletin_fallback=True,
        solver="astar",
        heuristic="learned",
    )
    payload = plan_payload(request)
    assert payload["verification_valid"]
    details = payload["stats"]["heuristic_details"]
    assert details["model_available"]
    assert details["model"]["metadata"]["dataset_size"] == 3000
    assert details["model"]["metadata"]["label_kind"] == "exact_optimal_remaining_terms_small_instances"
    assert details["composite_bound"] is not None
    assert "tie-break" in details["model"]["policy"]


def test_launcher_preflight_allows_composite_fallback(monkeypatch, tmp_path):
    import backend.ml.predict as prediction
    from run import preflight

    monkeypatch.setattr(prediction, "MODEL_PATH", tmp_path / "missing.json")
    assert preflight()["status"] == "ready"
    assert not preflight()["learned_model_available"]
