"""Cleaning, 70/15/15 splitting and scaling of the CIC-IDS2017 Friday DDoS CSV.

Serves Tasks 1-3 (it produces the ``DataSplits`` every model trains on).
Cleaning logic is ported from ``../Lab2/src/ddosids/data.py``
(copied and adapted, never imported); see CLAUDE.md 4.4-4.7.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

import common

log = logging.getLogger(__name__)

LABEL_COL = "Label"
SplitIndices = tuple[np.ndarray, np.ndarray, np.ndarray]


def _label_counts(labels: pd.Series) -> dict[str, int]:
    """Count rows per class name.

    Args:
        labels: Series of string labels.

    Returns:
        Plain dict {label: count}.
    """
    return {str(k): int(v) for k, v in labels.value_counts().items()}


def _nonzero(counts: pd.Series) -> dict[str, int]:
    """Keep only the entries of a per-column count Series that are above zero.

    Args:
        counts: Series indexed by column name.

    Returns:
        Plain dict {column: count} without zero entries.
    """
    return {str(c): int(v) for c, v in counts.items() if v > 0}


def load_raw(csv_path: Path) -> pd.DataFrame:
    """Step 1: read the CSV and strip column names and label values.

    Args:
        csv_path: Path of the flow CSV.

    Returns:
        Raw DataFrame with clean header and label strings.
    """
    df = pd.read_csv(csv_path, low_memory=False)
    # 65 header names carry stray spaces (CLAUDE.md 3).
    df.columns = df.columns.str.strip()
    df[LABEL_COL] = df[LABEL_COL].astype(str).str.strip()
    return df


def drop_inf_nan_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Steps 2-3: treat +-inf as NaN and drop every affected row.

    Args:
        df: Raw DataFrame including Label.

    Returns:
        The filtered DataFrame and a dict with inf_counts, nan_counts, inf_nan_rows.
    """
    feats = df.drop(columns=[LABEL_COL])
    # Count inf and pre-existing NaN separately, before inf is turned into NaN.
    inf_counts = _nonzero(np.isinf(feats).sum())
    nan_counts = _nonzero(feats.isna().sum())
    bad = feats.replace([np.inf, -np.inf], np.nan).isna().any(axis=1)
    rows = {"n": int(bad.sum()), "by_class": _label_counts(df.loc[bad, LABEL_COL])}
    info = {"inf_counts": inf_counts, "nan_counts": nan_counts, "inf_nan_rows": rows}
    log.info("inf/NaN rows dropped: %s (inf %s, NaN %s)", rows, inf_counts, nan_counts)
    return df.loc[~bad], info


def drop_duplicate_rows(df: pd.DataFrame, enabled: bool) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Step 4: drop duplicate rows (full row including Label), if enabled.

    Args:
        df: DataFrame including Label.
        enabled: False keeps every row (n = 0 in the summary).

    Returns:
        The filtered DataFrame and {"n": int, "by_class": {...}}.
    """
    dup = df.duplicated() if enabled else pd.Series(False, index=df.index)
    info = {"n": int(dup.sum()), "by_class": _label_counts(df.loc[dup, LABEL_COL])}
    log.info("duplicate rows dropped: %s", info)
    return df.loc[~dup], info


def drop_constant_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Step 5: drop feature columns with at most one distinct value.

    Args:
        df: DataFrame including Label (never inspected here).

    Returns:
        The reduced DataFrame and the dropped column names.
    """
    feats = [c for c in df.columns if c != LABEL_COL]
    const = [c for c in feats if df[c].nunique(dropna=False) <= 1]
    log.info("constant columns dropped (%d): %s", len(const), const)
    return df.drop(columns=const), const


def drop_identical_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    """Step 6: drop feature columns equal to an earlier kept column within atol.

    Args:
        df: DataFrame including Label (never inspected here).

    Returns:
        The reduced DataFrame and {dropped: kept twin}; the first column in CSV order is kept.
    """
    kept: list[str] = []
    dropped: dict[str, str] = {}
    for col in (c for c in df.columns if c != LABEL_COL):
        values = df[col].to_numpy(dtype="float64")
        # atol (not exact equality): Avg Bwd Segment Size differs by < 1e-6 in 2 rows.
        twin = next((k for k in kept if np.allclose(
            values, df[k].to_numpy(dtype="float64"), rtol=0, atol=common.IDENTICAL_ATOL)), None)
        if twin is None:
            kept.append(col)
        else:
            dropped[col] = twin
    log.info("identical columns dropped (%d): %s", len(dropped), dropped)
    return df.drop(columns=list(dropped)), dropped


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Run cleaning steps 2-6 and collect their part of the summary.

    Args:
        df: Output of ``load_raw`` (or an equivalent hand-built frame with Label).

    Returns:
        The cleaned DataFrame (Label kept as string) and the summary fragment.
    """
    # Flag read at call time so tests can monkeypatch common.DROP_DUPLICATES.
    df, summary = drop_inf_nan_rows(df)
    df, summary["duplicate_rows"] = drop_duplicate_rows(df, common.DROP_DUPLICATES)
    df, summary["constant_columns"] = drop_constant_columns(df)
    df, summary["identical_columns"] = drop_identical_columns(df)
    df = df.reset_index(drop=True)
    summary["clean_shape"] = [len(df), df.shape[1] - 1]  # Label excluded
    summary["clean_class_counts"] = _label_counts(df[LABEL_COL])
    return df, summary


def encode_labels(labels: pd.Series) -> np.ndarray:
    """Encode BENIGN -> 0 and DDoS -> 1.

    Args:
        labels: Series of label strings.

    Returns:
        int64 array.

    Raises:
        ValueError: If any other label value occurs.
    """
    mapping = {common.NEGATIVE_LABEL: 0, common.POSITIVE_LABEL: 1}
    unknown = sorted(set(labels.unique()) - set(mapping))
    if unknown:
        raise ValueError(f"Unexpected labels: {unknown}")
    return labels.map(mapping).to_numpy(dtype=np.int64)


def split_data(y: np.ndarray) -> SplitIndices:
    """Two-stage stratified split into train / val / test positional indices.

    Args:
        y: Encoded labels, used for stratification.

    Returns:
        (train_idx, val_idx, test_idx), disjoint.
    """
    idx = np.arange(len(y))
    holdout = common.VAL_FRAC + common.TEST_FRAC
    train, temp = train_test_split(idx, test_size=holdout, stratify=y, random_state=common.SEED)
    # Second stage splits the holdout 50/50 and stays stratified on its own labels.
    val, test = train_test_split(temp, test_size=common.TEST_FRAC / holdout,
                                 stratify=y[temp], random_state=common.SEED)
    return train, val, test


def scale_splits(features: pd.DataFrame, y: np.ndarray,
                 indices: SplitIndices) -> common.DataSplits:
    """Standardise features with a scaler fitted on the training rows only.

    Args:
        features: Cleaned feature columns (no Label).
        y: Encoded labels.
        indices: (train_idx, val_idx, test_idx).

    Returns:
        DataSplits with float32 features and int64 labels.
    """
    train, val, test = indices
    values = features.to_numpy(dtype="float64")
    # Fit on train only: fitting on val/test would leak their statistics.
    scaler = StandardScaler().fit(values[train])
    x_train, x_val, x_test = (
        scaler.transform(values[i]).astype(np.float32) for i in (train, val, test))
    return common.DataSplits(x_train, x_val, x_test, y[train], y[val], y[test],
                             list(features.columns))


def _class_counts(y: np.ndarray) -> dict[str, int]:
    """Count encoded labels per class name.

    Args:
        y: Encoded labels.

    Returns:
        {"BENIGN": n0, "DDoS": n1}.
    """
    return {common.NEGATIVE_LABEL: int((y == 0).sum()), common.POSITIVE_LABEL: int((y == 1).sum())}


def preprocess(csv_path: Path) -> tuple[common.DataSplits, dict[str, Any]]:
    """Load, clean, split and scale the CSV.

    Args:
        csv_path: Path of the flow CSV.

    Returns:
        The DataSplits and the full JSON-serialisable summary (CLAUDE.md 5).
    """
    raw = load_raw(csv_path)
    summary: dict[str, Any] = {"raw_shape": [int(n) for n in raw.shape],
                               "raw_class_counts": _label_counts(raw[LABEL_COL])}
    df, part = clean(raw)
    summary.update(part)
    y = encode_labels(df[LABEL_COL])
    features = df.drop(columns=[LABEL_COL])
    indices = split_data(y)
    splits = scale_splits(features, y, indices)
    summary["split_sizes"] = {name: len(i) for name, i in zip(("train", "val", "test"), indices)}
    summary["split_class_counts"] = {"train": _class_counts(splits.y_train),
                                     "val": _class_counts(splits.y_val),
                                     "test": _class_counts(splits.y_test)}
    summary["feature_names"] = splits.feature_names
    log.info("split sizes: %s", summary["split_sizes"])
    return splits, summary
