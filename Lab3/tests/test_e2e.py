"""End-to-end check: preprocessing the full CSV reproduces CLAUDE.md 3 / 5 (T5.7)."""
from __future__ import annotations

import pytest

import common
import preprocess

CONSTANT_COLUMNS = [
    "Bwd PSH Flags", "Fwd URG Flags", "Bwd URG Flags", "CWE Flag Count",
    "Fwd Avg Bytes/Bulk", "Fwd Avg Packets/Bulk", "Fwd Avg Bulk Rate",
    "Bwd Avg Bytes/Bulk", "Bwd Avg Packets/Bulk", "Bwd Avg Bulk Rate"]
# Lab 2's 8 identical columns plus the renamed duplicate header, each mapped to its kept twin.
IDENTICAL_COLUMNS = {
    "SYN Flag Count": "Fwd PSH Flags",
    "ECE Flag Count": "RST Flag Count",
    "Avg Fwd Segment Size": "Fwd Packet Length Mean",
    "Avg Bwd Segment Size": "Bwd Packet Length Mean",
    "Fwd Header Length.1": "Fwd Header Length",
    "Subflow Fwd Packets": "Total Fwd Packets",
    "Subflow Fwd Bytes": "Total Length of Fwd Packets",
    "Subflow Bwd Packets": "Total Backward Packets",
    "Subflow Bwd Bytes": "Total Length of Bwd Packets"}
N_FEATURES = 59


pytestmark = pytest.mark.e2e


@pytest.fixture(name="full", scope="module")
def _full() -> tuple[common.DataSplits, dict]:
    """Preprocess the full CSV once for all tests of this module.

    Returns:
        (splits, summary) from ``preprocess.preprocess``.
    """
    return preprocess.preprocess(common.DEFAULT_CSV)


def test_raw_and_dirty_counts(full) -> None:
    """Raw shape, class counts, inf/NaN counts and the dropped rows match CLAUDE.md 3."""
    summary = full[1]
    assert summary["raw_shape"] == [225745, 79]
    assert summary["raw_class_counts"] == {"BENIGN": 97718, "DDoS": 128027}
    assert summary["inf_counts"] == {"Flow Bytes/s": 30, "Flow Packets/s": 34}
    assert summary["nan_counts"] == {"Flow Bytes/s": 4}
    assert summary["inf_nan_rows"] == {"n": 34, "by_class": {"BENIGN": 32, "DDoS": 2}}
    assert summary["duplicate_rows"] == {"n": 2629, "by_class": {"BENIGN": 2618, "DDoS": 11}}


def test_dropped_columns(full) -> None:
    """The exact constant list and the identical-column mapping (incl. the .1 duplicate)."""
    summary = full[1]
    assert sorted(summary["constant_columns"]) == sorted(CONSTANT_COLUMNS)
    assert summary["identical_columns"] == IDENTICAL_COLUMNS


def test_clean_and_split_counts(full) -> None:
    """Clean shape, class counts, split sizes and per-split class counts."""
    splits, summary = full
    assert summary["clean_shape"] == [223082, N_FEATURES]
    assert summary["clean_class_counts"] == {"BENIGN": 95068, "DDoS": 128014}
    assert summary["split_sizes"] == {"train": 156157, "val": 33462, "test": 33463}
    assert summary["split_class_counts"] == {
        "train": {"BENIGN": 66547, "DDoS": 89610},
        "val": {"BENIGN": 14260, "DDoS": 19202},
        "test": {"BENIGN": 14261, "DDoS": 19202}}
    assert len(summary["feature_names"]) == N_FEATURES
    assert splits.x_train.shape == (156157, N_FEATURES)
