"""xdp/lab4_common.h and script/common.py must agree (CLAUDE.md 5.3)."""
import re
from pathlib import Path

import common

HEADER = Path(__file__).resolve().parents[1] / "xdp" / "lab4_common.h"
STAT_COUNT = 7
V_NONE_VALUE = 255


def parse_defines() -> dict[str, int]:
    """Returns the integer #define values of the header."""
    text = HEADER.read_text(encoding="utf-8")
    return {m[0]: int(m[1]) for m in re.findall(r"^#define\s+(\w+)\s+(\d+)", text, re.M)}


def parse_enums() -> dict[str, int]:
    """Returns every enumerator with its value; entries without '=' continue the count."""
    text = re.sub(r"/\*.*?\*/", "", HEADER.read_text(encoding="utf-8"), flags=re.S)
    values: dict[str, int] = {}
    for body in re.findall(r"enum\s+\w+\s*\{(.*?)\}", text, re.S):
        nxt = 0
        for item in (i.strip() for i in body.split(",")):
            if not item:
                continue
            name, _, val = (p.strip() for p in item.partition("="))
            nxt = int(val) if val else nxt
            values[name] = nxt
            nxt += 1
    return values


def test_defines_match_common() -> None:
    """Every numeric constant of the header equals its common.py mirror."""
    defines = parse_defines()
    assert set(defines) == {
        "N_FEATURES", "MAX_NODES", "MAX_TREES", "MAX_TREE_DEPTH", "LEAF_SHIFT",
        "CLASSIFY_MIN_PKTS", "MAX_FLOWS", "MAX_BLOCKED", "N_TEST_VECS"}
    for name, value in defines.items():
        assert getattr(common, name) == value, name


def test_modes_match_common() -> None:
    """The mode enum equals MODEL_MODES (plus OFF = 0)."""
    enums = parse_enums()
    assert enums["MODE_OFF"] == 0
    got = {"DT": enums["MODE_DT"], "XGB": enums["MODE_XGB"], "ALL": enums["MODE_ALL"]}
    assert got == common.MODEL_MODES


def test_verdicts_and_stats_match_common() -> None:
    """Verdict values and the stat order equal common.py."""
    enums = parse_enums()
    assert (enums["V_NORMAL"], enums["V_MALICIOUS"], enums["V_NONE"]) == (
        common.V_NORMAL, common.V_MALICIOUS, common.V_NONE)
    assert enums["V_NONE"] == V_NONE_VALUE
    assert enums["N_STATS"] == common.N_STATS == STAT_COUNT
    for name in common.STAT_NAMES:
        assert enums[name] == common.STAT_NAMES.index(name), name


def test_kernel_features_match_header() -> None:
    """Feature count and scales (CLAUDE.md 5.1)."""
    assert len(common.KERNEL_FEATURES) == parse_defines()["N_FEATURES"]
    assert [s for _, s in common.KERNEL_FEATURES] == [1, 1, 1, 1, 1000, 1000, 1000, 1000, 1000, 1]
