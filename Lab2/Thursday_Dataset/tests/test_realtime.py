"""Unit tests (fixture artifacts in tmp_path) and e2e parity test for the real-time part."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import f1_score

from lab2ids import config
from lab2ids.colmap import ISCX_FEATURES, ISCX_TO_V4, META_COLS, map_v4_to_iscx
from lab2ids.models import load_data
from lab2ids.realtime.detector import Detector, sort_by_timestamp, stream

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "sample_iscx.csv"
FLOWS = ROOT.parent / "task2_lab2.pcap_Flow.csv"
REAL_META = ROOT / "artifacts" / "models" / "meta.json"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


task3 = _load("task3_preprocess")
task4 = _load("task4_train")
rt = _load("realtime_detect")


def _ts(i: int) -> str:
    base = pd.Timestamp("2026-11-04 16:05:00") + pd.Timedelta(seconds=i)
    return base.strftime("%d/%m/%Y %I:%M:%S %p")


def _v4_frame(x: pd.DataFrame, protocol: int = 6) -> pd.DataFrame:
    v4 = x.rename(columns=ISCX_TO_V4).reset_index(drop=True)
    n = len(v4)
    meta = pd.DataFrame({
        "Flow ID": [f"f{i}" for i in range(n)], "Src IP": "10.0.0.1", "Src Port": 1234,
        "Dst IP": "10.0.0.2", "Protocol": protocol, "Timestamp": [_ts(i) for i in range(n)]})
    return pd.concat([meta, v4], axis=1)


# ---------- T5.1 ----------
def test_header_maps_all_features():
    hdr = pd.read_csv(FLOWS, nrows=0)
    mapped = set(map_v4_to_iscx(hdr).columns)
    assert set(ISCX_FEATURES) <= mapped
    assert mapped - set(ISCX_FEATURES) <= set(META_COLS) | {"Label"}
    assert set(ISCX_TO_V4.values()) <= set(hdr.columns)


def test_model_inputs_have_v4_source():
    if not REAL_META.exists():
        pytest.skip("real artifacts/models/meta.json missing")
    feats = json.loads(REAL_META.read_text())["input_features"]
    hdr = set(pd.read_csv(FLOWS, nrows=0).columns)
    assert all(ISCX_TO_V4[f] in hdr for f in feats)


# ---------- T5.2 ----------
@pytest.fixture(scope="module")
def art(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("rt")
    common = ["--artifacts-dir", str(tmp / "artifacts"), "--outputs-dir", str(tmp / "outputs")]
    assert task3.main(["--data", str(FIXTURE), *common]) == 0
    assert task4.main(common) == 0
    return tmp


@pytest.fixture(scope="module")
def det(art):
    return Detector(config.REALTIME_MODEL, art / "artifacts" / "models")


@pytest.fixture(scope="module")
def x_fix(art):
    _, x, _ = load_data(art / "artifacts")
    return x.head(30)


def test_inf_nan_replaced_and_counted(det, x_fix):
    v4 = _v4_frame(x_fix)
    col = ISCX_TO_V4[det.input_features[0]]
    col2 = ISCX_TO_V4[det.input_features[1]]
    v4[col] = v4[col].astype(float)
    v4.loc[0, col] = np.inf
    v4.loc[1, col] = -np.inf
    v4.loc[2, col2] = np.nan
    res, st = det.process(v4)
    assert st["cells_replaced"] == 3
    assert len(res) == 30


def test_protocol0_dropped(det, x_fix):
    v4 = _v4_frame(x_fix)
    v4.loc[[3, 7], "Protocol"] = 0
    res, st = det.process(v4)
    assert st["protocol0_dropped"] == 2 and len(res) == 28 and st["rows_in"] == 30


def test_missing_feature_raises(det, x_fix):
    v4 = _v4_frame(x_fix)
    gone = ISCX_TO_V4[det.input_features[5]]
    with pytest.raises(ValueError) as e:
        det.process(v4.drop(columns=[gone]))
    assert gone in str(e.value) or det.input_features[5] in str(e.value)


def test_output_columns_and_types(det, x_fix):
    res, _ = det.process(_v4_frame(x_fix))
    for c in META_COLS + ["pred", "p_attack", "is_alert"]:
        assert c in res.columns
    assert set(res["pred"]) <= {"BENIGN", "ATTACK"}
    assert res["p_attack"].dtype == float and res["p_attack"].between(0, 1).all()
    assert res["is_alert"].dtype == bool
    assert (res["is_alert"] == (res["pred"] == "ATTACK")).all()


def test_stream_sorts_by_timestamp(det, x_fix):
    v4 = _v4_frame(x_fix.head(10))
    shuffled = v4.iloc[::-1].reset_index(drop=True)
    assert list(sort_by_timestamp(shuffled)["Flow ID"]) == list(v4["Flow ID"])
    out = pd.concat(list(stream(shuffled, det, batch_size=4)), ignore_index=True)
    assert list(out["Flow ID"]) == list(v4["Flow ID"])
    assert len(det.latencies_ms) >= 3


def test_cli_writes_outputs(art, x_fix, tmp_path):
    csv = tmp_path / "flows.csv"
    v4 = _v4_frame(x_fix.head(12))
    v4.loc[0, "Protocol"] = 0
    v4.to_csv(csv, index=False)
    outs = tmp_path / "outputs"
    rc = rt.main([str(csv), "--models-dir", str(art / "artifacts" / "models"), "--outputs-dir", str(outs)])
    assert rc == 0
    pred = pd.read_csv(outs / "realtime" / "predictions.csv")
    assert len(pred) == 11 and {"pred", "p_attack", "is_alert"} <= set(pred.columns)
    log = (outs / "realtime" / "run_log.txt").read_text()
    assert "Protocol-0 rows dropped  : 1" in log and "flows classified         : 11" in log


# ---------- T5.3 ----------
@pytest.mark.e2e
def test_parity_with_offline_predict():
    art = config.ARTIFACTS_DIR
    mpath = art / "models" / f"{config.REALTIME_MODEL}.joblib"
    metrics_path = config.OUTPUTS_DIR / "task4" / "metrics.json"
    for f in (art / "clean.parquet", art / "split_indices.json", mpath, metrics_path):
        if not f.exists():
            pytest.skip(f"real artifact missing: {f}")
    df, x, split = load_data(art)
    te = np.asarray(split["test_idx"])
    x_test, y_test = x.iloc[te], df[config.BINARY_COL].iloc[te]
    pipe = joblib.load(mpath)
    offline = np.where(pipe.predict(x_test) == 1, "ATTACK", "BENIGN")

    det = Detector(config.REALTIME_MODEL)
    v4 = _v4_frame(x_test[det.input_features])
    v4["Flow ID"] = np.arange(len(v4))  # Timestamps from _v4_frame are unique and increasing
    streamed = pd.concat(list(stream(v4, det, batch_size=1000)), ignore_index=True)
    assert len(streamed) == len(x_test)
    streamed = streamed.sort_values("Flow ID", kind="stable").reset_index(drop=True)
    assert (streamed["pred"].to_numpy() == offline).all()

    one = pd.concat(list(stream(v4.head(500), det, batch_size=1)), ignore_index=True)
    assert (one["pred"].to_numpy() == offline[:500]).all()

    f1 = f1_score(y_test.to_numpy() == 1, streamed["pred"].to_numpy() == "ATTACK")
    ref = json.loads(metrics_path.read_text())[config.REALTIME_MODEL]["per_class"]["ATTACK"]["f1"]
    assert f1 == pytest.approx(ref, abs=1e-12)
