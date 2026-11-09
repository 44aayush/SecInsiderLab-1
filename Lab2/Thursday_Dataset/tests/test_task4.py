"""Unit tests (fixture only) and e2e test for Task 4."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import confusion_matrix, f1_score

from lab2ids import config
from lab2ids.evaluate import class_spec
from lab2ids.models import build_pipeline, load_data, model_keys, selected_features

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "sample_iscx.csv"
TARGETS = ["binary", "multiclass"]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


task3 = _load("task3_preprocess")
task4 = _load("task4_train")


def _run(tmp_path: Path, data: Path) -> None:
    common = ["--artifacts-dir", str(tmp_path / "artifacts"), "--outputs-dir", str(tmp_path / "outputs")]
    assert task3.main(["--data", str(data), *common]) == 0
    assert task4.main(common) == 0


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("t4")
    _run(tmp, FIXTURE)
    return tmp


def test_outputs_exist(run):
    models = run / "artifacts" / "models"
    out = run / "outputs" / "task4"
    keys = [k for k, _, _ in model_keys(TARGETS)]
    assert len(keys) == 8
    for k in keys:
        assert (models / f"{k}.joblib").exists()
        assert (out / f"report_{k}.csv").exists()
        for ext in ("png", "pdf"):
            assert (out / "figures" / f"cm_{k}.{ext}").exists()
    for f in (models / "meta.json", out / "metrics.json", out / "comparison.csv", out / "run_log.txt"):
        assert f.exists()
    meta = json.loads((models / "meta.json").read_text())
    assert "realtime_model" not in meta
    assert len(meta["input_features"]) >= 50
    assert len(pd.read_csv(out / "comparison.csv")) == 8


def test_selected_features_match_task3(run):
    for key, target, _ in model_keys(TARGETS):
        pipe = joblib.load(run / "artifacts" / "models" / f"{key}.joblib")
        want = json.loads((run / "artifacts" / f"selected_features_{target}.json").read_text())
        assert set(selected_features(pipe)) == set(want["features"])


def test_round_trip_and_known_classes(run):
    arts = run / "artifacts"
    df, x, split = load_data(arts)
    te = np.asarray(split["test_idx"])
    metrics = json.loads((run / "outputs" / "task4" / "metrics.json").read_text())
    meta = json.loads((arts / "models" / "meta.json").read_text())
    assert list(x.columns) == meta["input_features"]
    for key, target, _ in model_keys(TARGETS):
        pipe = joblib.load(arts / "models" / f"{key}.joblib")
        assert list(pipe.feature_names_in_) == meta["input_features"]
        y = df[config.TARGETS[target]].iloc[te]
        pred = pipe.predict(x.iloc[te])
        classes = class_spec(target)[0]
        assert set(pred) <= set(classes)
        assert confusion_matrix(y, pred, labels=classes).tolist() == metrics[key]["confusion_matrix"]
        assert f1_score(y, pred, labels=classes, average="macro", zero_division=0) == metrics[key]["macro_f1"]


def test_build_pipeline_structure():
    from sklearn.tree import DecisionTreeClassifier
    pipe = build_pipeline(DecisionTreeClassifier(), k=5)
    assert [n for n, _ in pipe.steps] == ["scale", "select", "clf"]
    assert pipe.named_steps["scale"].clip is True


@pytest.mark.e2e
def test_e2e_full(tmp_path):
    _run(tmp_path, config.DATA_CSV)
    comp = pd.read_csv(tmp_path / "outputs" / "task4" / "comparison.csv").set_index("key")
    dt_f1 = max(comp.loc["binary_dt_default", "f1_ATTACK"], comp.loc["binary_dt_balanced", "f1_ATTACK"])
    assert dt_f1 >= 0.95
    assert comp.loc["binary_lr_balanced", "attack_recall"] >= 0.90
    assert comp.loc["multiclass_dt_default", "macro_f1"] >= 0.50
    for key, target, _ in model_keys(TARGETS):
        pipe = joblib.load(tmp_path / "artifacts" / "models" / f"{key}.joblib")
        want = json.loads((tmp_path / "artifacts" / f"selected_features_{target}.json").read_text())
        assert set(selected_features(pipe)) == set(want["features"])
