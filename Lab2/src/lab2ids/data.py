"""Loading, cleaning, splitting and scaling of the CIC-IDS2017 (ISCX) flow CSV."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler

from lab2ids.config import (
    BENIGN,
    BINARY_COL,
    LABEL_COL,
    LABELS,
    RANDOM_STATE,
    TEST_SIZE,
)

log = logging.getLogger(__name__)

DUP_HEADER_COL = "Fwd Header Length.1"


# ----------------------------------------------------------------- T3.1
def load_raw(path: str | Path) -> pd.DataFrame:
    """Read the raw CSV (broken label bytes become U+FFFD) and strip column names."""
    df = pd.read_csv(path, encoding="utf-8", encoding_errors="replace", low_memory=False)
    df.columns = df.columns.str.strip()
    return df


def normalize_labels(labels: pd.Series) -> pd.Series:
    """Replace U+FFFD with '-', collapse whitespace, strip; validate against LABELS."""
    out = (
        labels.astype(str)
        .str.replace("�", "-", regex=False)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    bad = sorted(set(out.unique()) - set(LABELS))
    if bad:
        raise ValueError(f"Unexpected labels: {bad}")
    return out


def label_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Count, percent and ratio-to-BENIGN per label."""
    counts = df[LABEL_COL].value_counts()
    counts = counts.reindex([lab for lab in LABELS if lab in counts.index])
    out = pd.DataFrame({"count": counts})
    out["percent"] = (100 * out["count"] / out["count"].sum()).round(4)
    benign = out.loc[BENIGN, "count"] if BENIGN in out.index else np.nan
    out["ratio_to_benign"] = (out["count"] / benign).round(6)
    out.index.name = LABEL_COL
    return out


# ----------------------------------------------------------------- T3.2
def _breakdown(labels: pd.Series) -> dict[str, int]:
    return {str(k): int(v) for k, v in labels.value_counts().items()}


def _summary_dict(df: pd.DataFrame) -> dict[str, Any]:
    return json.loads(label_summary(df).reset_index().to_json(orient="records"))


IDENTICAL_ATOL = 1e-6


def _identical_columns(df: pd.DataFrame, atol: float = IDENTICAL_ATOL) -> list[tuple[str, str]]:
    """Return (kept, dropped) pairs; columns equal within atol; first in column order is kept."""
    arrays = {c: df[c].to_numpy(dtype="float64") for c in df.columns}
    kept: list[str] = []
    pairs: list[tuple[str, str]] = []
    for col in df.columns:
        a = arrays[col]
        for k in kept:
            b = arrays[k]
            if np.allclose(a[:2000], b[:2000], rtol=0, atol=atol) and np.allclose(
                a, b, rtol=0, atol=atol
            ):
                pairs.append((k, col))
                break
        else:
            kept.append(col)
    return pairs


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Clean per CLAUDE.md 3.2. Returns (clean_df, JSON-serializable report)."""
    df = df.copy()
    df[LABEL_COL] = normalize_labels(df[LABEL_COL])
    steps: list[dict[str, Any]] = []
    report: dict[str, Any] = {"raw_label_summary": _summary_dict(df), "steps": steps}

    def step(name: str, before: tuple[int, int], after: tuple[int, int], **extra: Any) -> None:
        entry = {
            "step": name,
            "rows_before": before[0], "cols_before": before[1],
            "rows_after": after[0], "cols_after": after[1],
            **extra,
        }
        steps.append(entry)
        log.info("%s: rows %d -> %d, cols %d -> %d %s", name, before[0], after[0],
                 before[1], after[1], extra if extra else "")

    # 1. duplicate header column
    before = df.shape
    if DUP_HEADER_COL in df.columns:
        df = df.drop(columns=[DUP_HEADER_COL])
    step("drop_duplicate_header_column", before, df.shape, dropped=[DUP_HEADER_COL])

    # 2. inf -> NaN
    feats = [c for c in df.columns if c != LABEL_COL]
    num = df[feats]
    inf_counts = {c: int(v) for c, v in np.isinf(num).sum().items() if v}
    df[feats] = num.replace([np.inf, -np.inf], np.nan)
    nan_counts = {c: int(v) for c, v in df[feats].isna().sum().items() if v}
    inf_only = {c: inf_counts[c] for c in inf_counts}
    # NaN count as originally present = after-replacement NaN minus those from inf
    nan_orig = {c: nan_counts.get(c, 0) - inf_counts.get(c, 0) for c in nan_counts}
    nan_orig = {c: v for c, v in nan_orig.items() if v}
    step("replace_inf_with_nan", df.shape, df.shape,
         inf_per_column=inf_only, nan_per_column=nan_orig)
    report["inf_per_column"] = inf_only
    report["nan_per_column"] = nan_orig

    # 3. drop NaN rows
    before = df.shape
    mask = df[feats].isna().any(axis=1)
    bd = _breakdown(df.loc[mask, LABEL_COL])
    df = df.loc[~mask]
    step("drop_nan_rows", before, df.shape, dropped_rows=int(mask.sum()), dropped_by_label=bd)

    # 4. duplicates
    before = df.shape
    dup = df.duplicated()
    bd = _breakdown(df.loc[dup, LABEL_COL])
    df = df.loc[~dup]
    step("drop_duplicate_rows", before, df.shape, dropped_rows=int(dup.sum()), dropped_by_label=bd)

    # 5. constant columns
    before = df.shape
    feats = [c for c in df.columns if c != LABEL_COL]
    const = [c for c in feats if df[c].nunique(dropna=False) <= 1]
    df = df.drop(columns=const)
    step("drop_constant_columns", before, df.shape, dropped=const)

    # 6. identical columns
    before = df.shape
    feats = [c for c in df.columns if c != LABEL_COL]
    pairs = _identical_columns(df[feats])
    df = df.drop(columns=[b for _, b in pairs])
    step("drop_identical_columns", before, df.shape,
         dropped=[b for _, b in pairs], pairs=[list(p) for p in pairs],
         atol=IDENTICAL_ATOL)

    # 7. binary label
    df[BINARY_COL] = (df[LABEL_COL] != BENIGN).astype("int8")
    # 8. reset index
    df = df.reset_index(drop=True)
    report["final_shape"] = list(df.shape)
    report["n_features"] = len(feature_columns(df))
    report["final_label_summary"] = _summary_dict(df)
    return df, report


def feature_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in (LABEL_COL, BINARY_COL)]


# ----------------------------------------------------------------- T3.3
def make_split(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """One stratified (on multiclass Label) split; positional indices, reused for both targets."""
    idx = np.arange(len(df))
    train, test = train_test_split(
        idx, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=df[LABEL_COL]
    )
    return np.sort(train), np.sort(test)


def save_split(train: np.ndarray, test: np.ndarray, n_rows: int, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "random_state": RANDOM_STATE,
        "test_size": TEST_SIZE,
        "stratify": LABEL_COL,
        "n_rows": n_rows,
        "train_idx": [int(i) for i in train],
        "test_idx": [int(i) for i in test],
    }
    path.write_text(json.dumps(payload))


def scale_train(
    x_train: pd.DataFrame, outputs_dir: Path | None = None
) -> tuple[MinMaxScaler, pd.DataFrame]:
    """Fit MinMaxScaler(clip=True) on train only; optionally save describe() before/after."""
    scaler = MinMaxScaler(clip=True)
    scaled = pd.DataFrame(
        scaler.fit_transform(x_train), columns=x_train.columns, index=x_train.index
    )
    if outputs_dir is not None:
        outputs_dir.mkdir(parents=True, exist_ok=True)
        x_train.describe().T.to_csv(outputs_dir / "describe_train_before_scaling.csv")
        scaled.describe().T.to_csv(outputs_dir / "describe_train_after_scaling.csv")
    return scaler, scaled
