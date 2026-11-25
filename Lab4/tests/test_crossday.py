"""Tests for script/crossday.py (synthetic multi-label data, no Wednesday CSV)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import crossday
import kmodel
from common import KERNEL_FEATURES, LEAF_SHIFT

ONE = 1 << LEAF_SHIFT
LEN_MAX = 2  # index of Fwd Packet Length Max
N_ROWS = 90
LABELS = ("BENIGN", "DoS Hulk", "Heartbleed")
# DT splits Fwd Packet Length Max at 100, XGB (one tree) at 150: DT=1, XGB=0 in between.
HAND = {"format": 1, "features": [n for n, _ in KERNEL_FEATURES],
        "scales": [s for _, s in KERNEL_FEATURES], "leaf_shift": LEAF_SHIFT,
        "nodes": [[LEN_MAX, 100, 1, 2, 0], [-1, 0, 0, 0, 0], [-1, 0, 0, 0, 1],
                  [LEN_MAX, 150, 4, 5, 0], [-1, 0, 0, 0, -ONE], [-1, 0, 0, 0, ONE]],
        "dt_root": 0, "xgb_roots": [3], "xgb_base_margin": 0, "meta": {}}


def _frame() -> pd.DataFrame:
    """Build a synthetic frame: 10 kernel columns, one extra column, Label."""
    rng = np.random.default_rng(0)
    df = pd.DataFrame(rng.integers(1, 50, (N_ROWS, len(KERNEL_FEATURES))).astype(float),
                      columns=[n for n, _ in KERNEL_FEATURES])
    df.iloc[:, LEN_MAX] = np.arange(N_ROWS) * 4.0
    df["Constant"] = 1.0  # must survive: no column is dropped
    df["Label"] = [LABELS[i % 3] for i in range(N_ROWS)]
    return df


def test_binary_labels() -> None:
    """Every non-BENIGN label maps to 1."""
    y = crossday.binary_labels(pd.Series(["BENIGN", "DoS Hulk", "Heartbleed"]))
    assert y.tolist() == [0, 1, 1]


def test_scores_and_per_label() -> None:
    """Per-label counts add up, ALL <= min(DT, XGB), and a constant column is kept."""
    df = _frame()
    cleaned, summary = crossday.clean_rows(df)
    assert cleaned.shape[1] == df.shape[1] and summary["clean_shape"][1] == df.shape[1] - 1
    x_int = np.floor(cleaned[[n for n, _ in KERNEL_FEATURES]].to_numpy() * np.array(
        [s for _, s in KERNEL_FEATURES])).astype(np.int64)
    scored = crossday.score(HAND, x_int)
    rows = crossday.per_label(cleaned["Label"], scored)
    assert [r["label"] for r in rows][0] == "BENIGN"
    assert sum(r["n"] for r in rows) == len(cleaned)
    for r in rows:
        assert r["detected_ALL"] <= min(r["detected_DT"], r["detected_XGB"])
    assert sum(r["detected_DT"] for r in rows) > sum(r["detected_ALL"] for r in rows)
    metrics = crossday.mode_metrics(crossday.binary_labels(cleaned["Label"]), scored)
    assert metrics["ALL"]["tp"] + metrics["ALL"]["fn"] == (cleaned["Label"] != "BENIGN").sum()


def test_main_writes_outputs(tmp_path: Path) -> None:
    """main on a small CSV writes every listed file."""
    csv_path, model_path, out = tmp_path / "w.csv", tmp_path / "m.json", tmp_path / "out"
    _frame().to_csv(csv_path, index=False)
    kmodel.save(HAND, model_path)
    assert crossday.main(["--csv", str(csv_path), "--model-file", str(model_path),
                          "--out", str(out)]) == 0
    names = {"run.log", "preprocess_summary.json", "metrics.json", "comparison.csv",
             "comparison.md", "per_label.csv", "per_label.md", "test_vectors.json"}
    assert names <= {p.name for p in out.iterdir()}
    vecs = json.loads((out / "test_vectors.json").read_text(encoding="utf-8"))
    assert set(vecs) == {"x", "dt", "xgb_margin"} and len(vecs["x"]) == len(vecs["dt"])


def test_main_missing_kernel_feature(tmp_path: Path) -> None:
    """A CSV without a kernel feature fails loudly."""
    csv_path, model_path = tmp_path / "w.csv", tmp_path / "m.json"
    _frame().drop(columns=["Fwd IAT Max"]).to_csv(csv_path, index=False)
    kmodel.save(HAND, model_path)
    with pytest.raises(KeyError):
        crossday.main(["--csv", str(csv_path), "--model-file", str(model_path),
                       "--out", str(tmp_path / "o")])
