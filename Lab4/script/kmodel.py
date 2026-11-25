"""Integer tree-model evaluator and bpftool batch writer (stdlib only; host and IDS image).

Python twin of the kernel walk in ``xdp/lab4_xdp.bpf.c`` (CLAUDE.md 5.2 to 5.4).
A node is ``[feature, threshold, left, right, leaf]``; a leaf has feature -1.
Left iff ``x[feature] <= threshold``.
"""
from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Any, Sequence

from common import (MAX_NODES, MAX_TREE_DEPTH, MAX_TREES, MODE_ALL, MODE_DT, MODE_XGB, N_FEATURES,
                    V_NONE)

NODE_FMT = "<qiIIi"  # threshold, feature, left, right, leaf: struct tree_node, 24 B
CONFIG_FMT = "<IIqQ"  # mode, n_xgb_trees, xgb_base_margin, block_ns: struct ids_config, 24 B
ROOT_FMT = "<I"
LEAF_FEATURE = -1
KEY_FMT = "<I"


def _check_depth(nodes: Sequence[Sequence[int]], root: int) -> None:
    """Check that no path from a root has more than MAX_TREE_DEPTH internal nodes.

    Args:
        nodes: All nodes of the model.
        root: Index of the tree root.

    Raises:
        ValueError: The tree is too deep (a cycle also exceeds the bound).
    """
    stack = [(root, 0)]
    while stack:
        idx, depth = stack.pop()
        if nodes[idx][0] == LEAF_FEATURE:
            continue
        if depth >= MAX_TREE_DEPTH:
            raise ValueError(f"tree at root {root} deeper than {MAX_TREE_DEPTH}")
        stack += [(nodes[idx][2], depth + 1), (nodes[idx][3], depth + 1)]


def _check_node(node: Sequence[int], n_nodes: int) -> None:
    """Check one node's feature and child indices.

    Args:
        node: Model node.
        n_nodes: Total node count.

    Raises:
        ValueError: Feature or child index out of range.
    """
    if not LEAF_FEATURE <= node[0] < N_FEATURES:
        raise ValueError(f"feature index {node[0]} out of range")
    if node[0] != LEAF_FEATURE and not all(0 <= c < n_nodes for c in node[2:4]):
        raise ValueError(f"child index out of range in node {node}")


def validate(model: dict[str, Any]) -> None:
    """Check a kernel model against the kernel limits.

    Args:
        model: Parsed kernel_model.json.

    Raises:
        ValueError: Too many nodes or trees, bad root, feature or child index, or depth too big.
    """
    nodes = model["nodes"]
    roots = [model["dt_root"], *model["xgb_roots"]]
    if len(nodes) > MAX_NODES:
        raise ValueError(f"{len(nodes)} nodes > MAX_NODES {MAX_NODES}")
    if len(roots) > MAX_TREES + 1:
        raise ValueError(f"{len(roots)} roots > MAX_TREES + 1")
    for node in nodes:
        _check_node(node, len(nodes))
    if not all(0 <= r < len(nodes) for r in roots):
        raise ValueError("root index out of range")
    for root in roots:
        _check_depth(nodes, root)


def load(path: Path) -> dict[str, Any]:
    """Read and validate a kernel model.

    Args:
        path: kernel_model.json.

    Returns:
        The validated model dict.
    """
    model = json.loads(Path(path).read_text(encoding="utf-8"))
    validate(model)
    return model


def save(model: dict[str, Any], path: Path) -> None:
    """Validate a kernel model and write it as JSON.

    Args:
        model: Kernel model dict.
        path: Output file; parent directories are created.
    """
    validate(model)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(model), encoding="utf-8")


def walk(nodes: Sequence[Sequence[int]], root: int, x_int: Sequence[int]) -> int:
    """Walk one tree like the kernel: bounded steps, exhausted bound gives leaf 0 (fail open).

    Args:
        nodes: All nodes of the model.
        root: Index of the tree root.
        x_int: Feature vector in kernel units.

    Returns:
        The leaf value.
    """
    idx = root
    for _ in range(MAX_TREE_DEPTH + 1):
        feature, threshold, left, right, leaf = nodes[idx]
        if feature == LEAF_FEATURE:
            return leaf
        idx = left if x_int[feature] <= threshold else right
    return 0


def dt_verdict(model: dict[str, Any], x_int: Sequence[int]) -> int:
    """Decision Tree verdict (the leaf is the class).

    Args:
        model: Kernel model.
        x_int: Feature vector in kernel units.

    Returns:
        0 (Normal) or 1 (Malicious).
    """
    return walk(model["nodes"], model["dt_root"], x_int)


def xgb_margin(model: dict[str, Any], x_int: Sequence[int]) -> int:
    """XGBoost margin: base margin plus all tree leaves (fixed point, 2**LEAF_SHIFT).

    Args:
        model: Kernel model.
        x_int: Feature vector in kernel units.

    Returns:
        Integer margin.
    """
    leaves = (walk(model["nodes"], r, x_int) for r in model["xgb_roots"])
    return model["xgb_base_margin"] + sum(leaves)


def xgb_verdict(margin: int) -> int:
    """Map a margin to a verdict; exactly 0 is Normal.

    Args:
        margin: Integer margin.

    Returns:
        0 or 1.
    """
    return int(margin > 0)


def final_verdict(mode: int, dt: int, xgb: int) -> int:
    """Combine the verdicts for a mode (ALL = both must say Malicious).

    Args:
        mode: MODE_DT, MODE_XGB or MODE_ALL.
        dt: DT verdict.
        xgb: XGB verdict.

    Returns:
        0, 1, or V_NONE for MODE_OFF or an unknown mode.
    """
    return {MODE_DT: dt, MODE_XGB: xgb, MODE_ALL: int(dt == 1 and xgb == 1)}.get(mode, V_NONE)


def pack_node(node: Sequence[int]) -> bytes:
    """Pack ``[feature, threshold, left, right, leaf]``.

    Args:
        node: Model node.

    Returns:
        24 bytes, ``struct tree_node``.
    """
    feature, threshold, left, right, leaf = node
    return struct.pack(NODE_FMT, threshold, feature, left, right, leaf)


def _line(pin_dir: str, name: str, key: int, value: bytes) -> str:
    """Format one bpftool batch ``map update`` line.

    Args:
        pin_dir: Pin directory.
        name: Map name.
        key: Array index.
        value: Packed value.

    Returns:
        The batch line.
    """
    return (f"map update pinned {pin_dir}/maps/{name} key hex "
            f"{struct.pack(KEY_FMT, key).hex(' ')} value hex {value.hex(' ')}")


def batch_lines(model: dict[str, Any], pin_dir: str) -> list[str]:
    """Build the batch lines for the ``nodes`` and ``roots`` maps.

    Args:
        model: Kernel model.
        pin_dir: Pin directory of the loaded program.

    Returns:
        One line per node, then roots[0] = DT and roots[1..n] = XGB trees.
    """
    lines = [_line(pin_dir, "nodes", i, pack_node(n)) for i, n in enumerate(model["nodes"])]
    roots = [model["dt_root"], *model["xgb_roots"]]
    root_lines = [_line(pin_dir, "roots", i, struct.pack(ROOT_FMT, r)) for i, r in enumerate(roots)]
    return lines + root_lines


def config_line(mode: int, model: dict[str, Any], block_ns: int, pin_dir: str) -> str:
    """Build the batch line for ``config[0]``.

    Args:
        mode: MODE_OFF..MODE_ALL.
        model: Kernel model.
        block_ns: Block duration in ns.
        pin_dir: Pin directory.

    Returns:
        The batch line.
    """
    value = struct.pack(CONFIG_FMT, mode, len(model["xgb_roots"]), model["xgb_base_margin"],
                        block_ns)
    return _line(pin_dir, "config", 0, value)
