"""End-to-end check on the full CSV (CLAUDE.md 3.2); run with -m e2e."""
from __future__ import annotations

import pytest

import common
import crossday
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


WEDNESDAY = {"BENIGN": 440_031, "DoS Hulk": 231_073, "DoS GoldenEye": 10_293,
             "DoS slowloris": 5_796, "DoS Slowhttptest": 5_499, "Heartbleed": 11}


def test_wednesday_raw_counts() -> None:
    """Raw shape and label counts of the Wednesday CSV match CLAUDE.md 2 D7."""
    if not crossday.DEFAULT_WED_CSV.exists():
        pytest.skip("Wednesday CSV absent")
    raw = pp.load_raw(crossday.DEFAULT_WED_CSV)
    assert raw.shape == (692_703, 79)
    assert raw[pp.LABEL_COL].value_counts().to_dict() == WEDNESDAY


def test_full_csv_split_class_counts() -> None:
    """Per-split class counts match CLAUDE.md 3.2."""
    _, s = pp.preprocess(common.DEFAULT_CSV)
    counts = s["split_class_counts"]
    assert counts["train"] == {"DDoS": 89_610, "BENIGN": 66_547}
    assert counts["val"] == {"DDoS": 19_202, "BENIGN": 14_260}
    assert counts["test"] == {"DDoS": 19_202, "BENIGN": 14_261}
