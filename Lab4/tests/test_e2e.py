"""End-to-end check on the full CSV (CLAUDE.md 3.2); run with -m e2e."""
from __future__ import annotations

import pytest

import common
import preprocess as pp

pytestmark = pytest.mark.e2e


def test_full_csv_counts() -> None:
    """Raw, clean and split counts per class match CLAUDE.md 3.2."""
    splits, s = pp.preprocess(common.DEFAULT_CSV)
    assert s["raw_shape"][0] == 225_745 and s["raw_shape"][1] == 79
    assert s["raw_class_counts"] == {"DDoS": 128_027, "BENIGN": 97_718}
    assert s["clean_shape"][0] == 223_082
    assert s["clean_class_counts"] == {"DDoS": 128_014, "BENIGN": 95_068}
    assert s["split_sizes"] == {"train": 156_157, "val": 33_462, "test": 33_463}
    assert splits.x_test.shape == (33_463, common.N_FEATURES)
    assert splits.feature_names == [n for n, _ in common.KERNEL_FEATURES]


def test_full_csv_split_class_counts() -> None:
    """Per-split class counts match CLAUDE.md 3.2."""
    _, s = pp.preprocess(common.DEFAULT_CSV)
    counts = s["split_class_counts"]
    assert counts["train"] == {"DDoS": 89_610, "BENIGN": 66_547}
    assert counts["val"] == {"DDoS": 19_202, "BENIGN": 14_260}
    assert counts["test"] == {"DDoS": 19_202, "BENIGN": 14_261}
