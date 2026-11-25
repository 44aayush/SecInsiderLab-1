"""Unit tests (fixture only) and e2e test for Task 3 (Friday DDoS)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ddosids import config
from ddosids.data import (
    clean, feature_columns, label_summary, load_raw, make_split, normalize_labels,
    scale_train,
)
from ddosids.features import score_features

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "sample_ddos.csv"

_spec = importlib.util.spec_from_file_location("task3_preprocess", ROOT / "scripts" / "task3_preprocess.py")
cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cli)


@pytest.fixture(scope="module")
def raw() -> pd.DataFrame:
    return load_raw(FIXTURE)


@pytest.fixture(scope="module")
def cleaned(raw):
    return clean(raw)


@pytest.fixture(scope="module")
def split(cleaned):
    df, _ = cleaned
    train, test = make_split(df)
    feats = feature_columns(df)
    scaler, scaled = scale_train(df.iloc[train][feats])
    return df, train, test, feats, scaler, scaled


def test_load_strips_columns_and_keeps_dup_header(raw):
    assert all(c == c.strip() for c in raw.columns)
    assert "Fwd Header Length.1" in raw.columns


def test_fixture_keeps_crlf():
    data = FIXTURE.read_bytes()
    assert data.count(b"\r\n") == data.count(b"\n") > 3000


def test_labels_canonical(raw):
    out = normalize_labels(raw[config.LABEL_COL])
    assert set(out) == set(config.LABELS)
    summ = label_summary(pd.DataFrame({config.LABEL_COL: out}))
    assert summ.loc[config.BENIGN, "ratio_to_benign"] == 1.0
    assert summ.loc[config.ATTACK_NAME, "count"] > summ.loc[config.BENIGN, "count"] * 0.5


def test_bad_label_raises():
    with pytest.raises(ValueError):
        normalize_labels(pd.Series(["BENIGN", "Bogus"]))


def test_clean_steps(raw, cleaned):
    df, report = cleaned
    feats = feature_columns(df)
    assert "Fwd Header Length.1" not in df.columns
    assert np.isfinite(df[feats].to_numpy(dtype=float)).all()
    assert not df.duplicated().any()
    assert (df[feats].nunique() > 1).all()
    assert not df[feats].T.duplicated().any()
    assert (df[config.BINARY_COL] == (df[config.LABEL_COL] != config.BENIGN)).all()
    assert df.index.equals(pd.RangeIndex(len(df)))
    steps = {s["step"]: s for s in report["steps"]}
    assert steps["drop_nan_rows"]["dropped_rows"] > 0
    assert steps["drop_nan_rows"]["dropped_by_label"].get(config.ATTACK_NAME, 0) >= 1
    assert steps["drop_duplicate_rows"]["dropped_rows"] > 0
    assert steps["drop_duplicate_rows"]["dropped_by_label"].get(config.ATTACK_NAME, 0) >= 1
    # a 3k-row subsample can have extra constant/identical columns
    assert len(steps["drop_constant_columns"]["dropped"]) >= 10
    assert len(steps["drop_identical_columns"]["dropped"]) >= 7
    json.dumps(report)  # serializable


def test_split_stratified(split):
    df, train, test, *_ = split
    assert not set(train) & set(test)
    assert len(train) + len(test) == len(df)
    assert abs(len(test) / len(df) - 0.3) < 0.01
    for lab in config.LABELS:
        assert (df.iloc[train][config.LABEL_COL] == lab).any()
        assert (df.iloc[test][config.LABEL_COL] == lab).any()


def test_scaler_no_leakage(split):
    df, train, test, feats, scaler, scaled = split
    xt = df.iloc[train][feats]
    np.testing.assert_array_equal(scaler.data_min_, xt.min().to_numpy())
    np.testing.assert_array_equal(scaler.data_max_, xt.max().to_numpy())
    # train-only stats differ from full-data stats, so test rows were not used
    assert not np.array_equal(scaler.data_max_, df[feats].max().to_numpy())
    varying = (xt.max() > xt.min()).to_numpy()
    assert (scaled.min().to_numpy()[varying] == 0).all()
    # float rounding can leave the max a few ulps below 1
    np.testing.assert_allclose(scaled.max().to_numpy()[varying], 1.0, rtol=0, atol=1e-12)
    assert scaled.to_numpy().max() <= 1.0
    out = scaler.transform(df.iloc[test][feats])
    assert out.min() >= 0 and out.max() <= 1  # clip=True


def test_selection(split):
    df, train, _, feats, _, scaled = split
    for col in config.TARGETS.values():
        t = score_features(scaled, df.iloc[train][col], k=config.K)
        sel = t.loc[t["selected"], "feature"].tolist()
        assert len(sel) == len(set(sel)) == config.K
        assert set(sel) <= set(feats)


def test_json_matches_selectkbest_support(split, tmp_path):
    from sklearn.feature_selection import SelectKBest, chi2

    from ddosids.features import select_for_target

    df, train, _, _, _, scaled = split
    for target, col in config.TARGETS.items():
        y = df.iloc[train][col]
        select_for_target(scaled, y, target, config.K, tmp_path, tmp_path)
        feats = json.loads((tmp_path / f"selected_features_{target}.json").read_text())["features"]
        sup = scaled.columns[SelectKBest(chi2, k=config.K).fit(scaled, y).get_support()]
        assert set(feats) == set(sup) and len(feats) == config.K


def test_cli_fixture(tmp_path):
    art, outd = tmp_path / "art", tmp_path / "out"
    assert cli.main(["--data", str(FIXTURE), "--artifacts-dir", str(art), "--outputs-dir", str(outd)]) == 0
    for name in ["clean.parquet", "split_indices.json", "selected_features_binary.json"]:
        assert (art / name).exists(), name
    t3 = outd / "task3"
    for name in ["cleaning_report.json", "label_summary_raw.csv", "label_summary_clean.csv",
                 "describe_train_before_scaling.csv", "describe_train_after_scaling.csv",
                 "feature_scores_binary.csv", "run_log.txt"]:
        assert (t3 / name).exists(), name
    for tgt in config.TARGETS:
        for ext in ("png", "pdf"):
            assert (t3 / "figures" / f"feature_scores_{tgt}.{ext}").exists()
        sel = json.loads((art / f"selected_features_{tgt}.json").read_text())
        assert sel["target"] == tgt and sel["score_func"] == "chi2" and len(sel["features"]) == 20
    split = json.loads((art / "split_indices.json").read_text())
    assert {"random_state", "test_size", "stratify", "n_rows"} <= split.keys()


@pytest.mark.e2e
def test_e2e_full(tmp_path):
    art, outd = tmp_path / "art", tmp_path / "out"
    assert cli.main(["--data", str(config.DATA_CSV), "--artifacts-dir", str(art),
                     "--outputs-dir", str(outd)]) == 0
    rep = json.loads((outd / "task3" / "cleaning_report.json").read_text())
    raw = {r["Label"]: r["count"] for r in rep["raw_label_summary"]}
    assert raw == {"BENIGN": 97718, "DDoS": 128027}
    assert rep["inf_per_column"] == {"Flow Bytes/s": 30, "Flow Packets/s": 34}
    assert rep["nan_per_column"] == {"Flow Bytes/s": 4}
    steps = {s["step"]: s for s in rep["steps"]}
    assert steps["drop_nan_rows"]["dropped_rows"] == 34
    assert steps["drop_nan_rows"]["dropped_by_label"] == {"BENIGN": 32, "DDoS": 2}
    d = steps["drop_duplicate_rows"]
    assert d["dropped_rows"] == 2629
    assert d["dropped_by_label"] == {"BENIGN": 2618, "DDoS": 11}
    assert sorted(steps["drop_constant_columns"]["dropped"]) == sorted([
        "Bwd PSH Flags", "Fwd URG Flags", "Bwd URG Flags", "CWE Flag Count",
        "Fwd Avg Bytes/Bulk", "Fwd Avg Packets/Bulk", "Fwd Avg Bulk Rate",
        "Bwd Avg Bytes/Bulk", "Bwd Avg Packets/Bulk", "Bwd Avg Bulk Rate"])
    assert sorted(steps["drop_identical_columns"]["dropped"]) == sorted([
        "SYN Flag Count", "ECE Flag Count", "Avg Fwd Segment Size", "Avg Bwd Segment Size",
        "Subflow Fwd Packets", "Subflow Fwd Bytes", "Subflow Bwd Packets", "Subflow Bwd Bytes"])
    assert steps["drop_identical_columns"]["atol"] == 1e-6
    assert rep["final_shape"] == [223082, 61]
    assert rep["n_features"] == 59
    fin = {r["Label"]: r["count"] for r in rep["final_label_summary"]}
    assert fin == {"BENIGN": 95068, "DDoS": 128014}
    df = pd.read_parquet(art / "clean.parquet")
    assert df.shape == (223082, 61)
    split = json.loads((art / "split_indices.json").read_text())
    assert (len(split["train_idx"]), len(split["test_idx"])) == (156157, 66925)
    for tgt in config.TARGETS:
        sel = json.loads((art / f"selected_features_{tgt}.json").read_text())["features"]
        assert len(sel) == len(set(sel)) == 20
