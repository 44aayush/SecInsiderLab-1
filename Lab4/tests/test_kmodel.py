"""Tests for script/kmodel.py (stdlib integer tree model)."""
from __future__ import annotations

import copy
import struct
from pathlib import Path

import pytest

import kmodel
from common import (MAX_NODES, MAX_TREE_DEPTH, MAX_TREES, MODE_ALL, MODE_DT, MODE_OFF, MODE_XGB,
                    V_NONE)

PIN = "/sys/fs/bpf/lab4"
LEAF0, LEAF1 = [-1, 0, 0, 0, 0], [-1, 0, 0, 0, 1]
HAND = {"nodes": [[2, 5, 1, 2, 0], LEAF0, LEAF1]}


def _model(nodes: list[list[int]], dt_root: int = 0, xgb_roots: list[int] | None = None,
           base: int = 0) -> dict:
    """Build a minimal model dict.

    Args:
        nodes: Node list.
        dt_root: DT root index.
        xgb_roots: XGB root indices.
        base: Base margin.

    Returns:
        Model dict.
    """
    return {"nodes": nodes, "dt_root": dt_root, "xgb_roots": xgb_roots or [],
            "xgb_base_margin": base}


def _chain(depth: int) -> list[list[int]]:
    """Build a left-leaning chain of ``depth`` internal nodes.

    Args:
        depth: Number of internal nodes.

    Returns:
        Node list; the last node is a leaf shared as right child.
    """
    leaf = depth
    return [[0, 0, i + 1, leaf, 0] for i in range(depth)] + [LEAF0]


def test_walk_hand_tree() -> None:
    """Threshold is inclusive on the left."""
    x = [0] * 10
    x[2] = 5
    assert kmodel.walk(HAND["nodes"], 0, x) == 0
    x[2] = 6
    assert kmodel.walk(HAND["nodes"], 0, x) == 1


def test_pack_node_is_24_bytes_and_roundtrips() -> None:
    """Packed node is 24 bytes and decodes to the same fields."""
    node = [3, -7, 11, 12, -65536]
    packed = kmodel.pack_node(node)
    assert len(packed) == 24
    threshold, feature, left, right, leaf = struct.unpack(kmodel.NODE_FMT, packed)
    assert [feature, threshold, left, right, leaf] == node


def _bad_models() -> list[dict]:
    """Build one invalid model per rejection rule.

    Returns:
        Invalid model dicts.
    """
    return [
        _model([LEAF0] * (MAX_NODES + 1)),
        _model(_chain(MAX_TREE_DEPTH + 1)),
        _model([[10, 0, 1, 1, 0], LEAF0]),
        _model([[0, 0, 1, 5, 0], LEAF0]),
        _model([LEAF0], xgb_roots=[0] * (MAX_TREES + 1)),
    ]


@pytest.mark.parametrize("model", _bad_models(),
                         ids=["nodes", "depth", "feature", "child", "roots"])
def test_validate_rejects(model: dict) -> None:
    """Each kernel-limit violation raises ValueError."""
    with pytest.raises(ValueError):
        kmodel.validate(model)


def test_validate_accepts_max_depth_and_rejects_cycle() -> None:
    """Depth 10 passes; a self-loop is caught by the depth bound."""
    kmodel.validate(_model(_chain(MAX_TREE_DEPTH)))
    with pytest.raises(ValueError):
        kmodel.validate(_model([[0, 0, 0, 0, 0]]))


def test_xgb_margin_sums_base_and_leaves() -> None:
    """Margin = base + every tree's leaf."""
    nodes = [[-1, 0, 0, 0, 100], [-1, 0, 0, 0, -30]]
    assert kmodel.xgb_margin(_model(nodes, xgb_roots=[0, 1, 0], base=7), [0] * 10) == 177


def test_xgb_verdict_zero_is_normal() -> None:
    """Only a positive margin is Malicious."""
    assert [kmodel.xgb_verdict(m) for m in (-1, 0, 1)] == [0, 0, 1]


def test_final_verdict_modes() -> None:
    """DT, XGB and ALL (AND) truth table; OFF gives V_NONE."""
    for dt in (0, 1):
        for xgb in (0, 1):
            assert kmodel.final_verdict(MODE_DT, dt, xgb) == dt
            assert kmodel.final_verdict(MODE_XGB, dt, xgb) == xgb
            assert kmodel.final_verdict(MODE_ALL, dt, xgb) == dt & xgb
            assert kmodel.final_verdict(MODE_OFF, dt, xgb) == V_NONE


def test_batch_lines_format() -> None:
    """Line count, exact first line, and config round trip."""
    model = _model(HAND["nodes"], xgb_roots=[1, 2], base=-5)
    lines = kmodel.batch_lines(model, PIN)
    assert len(lines) == 3 + 1 + 2
    first = kmodel.pack_node(HAND["nodes"][0]).hex(" ")
    head = f"map update pinned {PIN}/maps/"
    assert lines[0] == f"{head}nodes key hex 00 00 00 00 value hex {first}"
    assert lines[3] == f"{head}roots key hex 00 00 00 00 value hex 00 00 00 00"
    assert lines[5].endswith("key hex 02 00 00 00 value hex 02 00 00 00")
    line = kmodel.config_line(MODE_ALL, model, 60 * 10**9, PIN)
    prefix = f"map update pinned {PIN}/maps/config key hex 00 00 00 00 value hex "
    assert line.startswith(prefix)
    value = bytes.fromhex(line[len(prefix):])
    assert len(value) == 24
    assert struct.unpack(kmodel.CONFIG_FMT, value) == (MODE_ALL, 2, -5, 60 * 10**9)


def test_load_save_roundtrip(tmp_path: Path) -> None:
    """Saved model loads back identical; save validates."""
    model = copy.deepcopy(_model(HAND["nodes"], xgb_roots=[1], base=3))
    kmodel.save(model, tmp_path / "sub" / "m.json")
    assert kmodel.load(tmp_path / "sub" / "m.json") == model
    with pytest.raises(ValueError):
        kmodel.save(_model(_chain(MAX_TREE_DEPTH + 1)), tmp_path / "bad.json")


def test_always_malicious_fixture(always_malicious_path: Path) -> None:
    """The stub validates and says Malicious for any input."""
    model = kmodel.load(always_malicious_path)
    for x in ([0] * 10, [10**12] * 10, [-5] * 10):
        assert kmodel.dt_verdict(model, x) == 1
        assert kmodel.xgb_verdict(kmodel.xgb_margin(model, x)) == 1
