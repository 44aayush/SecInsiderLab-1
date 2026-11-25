"""Stream CICFlowMeter V4 flows through the persisted sklearn pipeline."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Iterator

import joblib
import numpy as np
import pandas as pd

from ddosids import config
from ddosids.colmap import META_COLS, map_v4_to_iscx

TS_FORMAT = "%d/%m/%Y %I:%M:%S %p"
DST_PORT = "Dst Port"


class Detector:
    """Loads one pipeline plus the ordered input features from meta.json."""

    def __init__(self, model_key: str = config.REALTIME_MODEL,
                 models_dir: Path = config.ARTIFACTS_DIR / "models") -> None:
        models_dir = Path(models_dir)
        self.model_key = model_key
        self.pipeline = joblib.load(models_dir / f"{model_key}.joblib")
        meta = json.loads((models_dir / "meta.json").read_text())
        self.input_features: list[str] = list(meta["input_features"])
        self.classes = list(self.pipeline.classes_)
        self.latencies_ms: list[float] = []  # per-flow latency of each processed batch

    def process(self, df_v4: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
        t0 = time.perf_counter()
        n_in = len(df_v4)
        df = map_v4_to_iscx(df_v4)
        # 2. drop Protocol-0 (non TCP/UDP / unparsed) rows
        n_proto0 = 0
        if "Protocol" in df.columns:
            keep = pd.to_numeric(df["Protocol"], errors="coerce").fillna(0) != 0
            n_proto0 = int((~keep).sum())
            df = df[keep]
        # 3. every feature must be present
        missing = [c for c in self.input_features if c not in df.columns]
        if missing:
            raise ValueError(f"missing required feature columns: {missing}")
        # 4. order
        x = df[self.input_features].apply(pd.to_numeric, errors="coerce").astype(float)
        # 5. inf/NaN -> 0
        bad = ~np.isfinite(x.to_numpy())
        n_replaced = int(bad.sum())
        x = x.mask(bad, 0.0)
        # 6. predict
        out = pd.DataFrame(index=df.index)
        for c in META_COLS:
            if c in df.columns:
                out[c] = df[c]
        if "Destination Port" in df.columns:
            out[DST_PORT] = df["Destination Port"]
        if len(x):
            pred = self.pipeline.predict(x)
            proba = self.pipeline.predict_proba(x)
            p_att = proba[:, self.classes.index(1)]
            labels = np.where(pred == 1, config.ATTACK_NAME, config.BENIGN)
            is_alert = np.asarray(pred == 1, dtype=bool)
        else:
            labels, p_att, is_alert = np.array([], dtype=object), np.array([], dtype=float), np.array([], dtype=bool)
        out["pred"] = labels
        out["p_attack"] = np.asarray(p_att, dtype=float)
        out["is_alert"] = is_alert
        out = out.reset_index(drop=True)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        stats = {"rows_in": n_in, "protocol0_dropped": n_proto0, "cells_replaced": n_replaced,
                 "classified": len(out), "latency_ms": elapsed_ms}
        return out, stats


def sort_by_timestamp(df_v4: pd.DataFrame) -> pd.DataFrame:
    """Stable sort by parsed Timestamp (unparseable values sort last)."""
    if "Timestamp" not in df_v4.columns:
        return df_v4.reset_index(drop=True)
    ts = pd.to_datetime(df_v4["Timestamp"], format=TS_FORMAT, errors="coerce")
    order = np.argsort(ts.to_numpy(), kind="stable")
    return df_v4.iloc[order].reset_index(drop=True)


def stream(df_v4: pd.DataFrame, detector: Detector, batch_size: int = 1,
           rate: float | None = None) -> Iterator[pd.DataFrame]:
    """Yield per-batch results in Timestamp order; throttle to ~rate flows/s if set.

    Per-flow latency of each batch is appended to detector.latencies_ms.
    """
    df = sort_by_timestamp(df_v4)
    start = time.perf_counter()
    sent = 0
    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i + batch_size]
        if rate:
            wait = start + sent / rate - time.perf_counter()
            if wait > 0:
                time.sleep(wait)
        res, st = detector.process(batch)
        detector.latencies_ms.append(st["latency_ms"] / max(len(batch), 1))
        res.attrs["stats"] = st
        sent += len(batch)
        yield res
