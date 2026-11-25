"""Export fitted sklearn / XGBoost trees to the integer kernel model (CLAUDE.md 5.2 to 5.4).

Float thresholds become integer thresholds in kernel units; the walk is "left iff x_int <= T"
(see ``kmodel.walk``). Host only (needs numpy and the fitted models).
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Any

import numpy as np

import kmodel
from common import KERNEL_FEATURES, LEAF_SHIFT, V_MALICIOUS, V_NORMAL

SCALES = np.array([s for _, s in KERNEL_FEATURES], dtype=np.float64)
LEAF = kmodel.LEAF_FEATURE
LEAF_ONE = 1 << LEAF_SHIFT
HALF = 0.5


def to_int_features(x: np.ndarray) -> np.ndarray:
    """Convert CIC feature values to kernel units: floor(x * s), computed in float64.

    Args:
        x: Array of shape (n, N_FEATURES).

    Returns:
        int64 array of the same shape.
    """
    return np.floor(np.asarray(x, dtype=np.float64) * SCALES).astype(np.int64)


def dt_threshold(t: float, scale: int) -> int:
    """sklearn goes left if x <= t, so T = floor(t * s).

    Args:
        t: Float threshold.
        scale: Feature scale s.

    Returns:
        Integer threshold in kernel units.
    """
    return math.floor(t * scale)


def xgb_threshold(t: float, scale: int) -> int:
    """XGBoost goes left if x < t, so T = ceil(t * s) - 1.

    Args:
        t: Float threshold.
        scale: Feature scale s.

    Returns:
        Integer threshold in kernel units.
    """
    return math.ceil(t * scale) - 1


def export_dt(model: Any) -> list[list[int]]:
    """Export a fitted DecisionTreeClassifier (node indices relative to the tree).

    Args:
        model: Fitted sklearn tree.

    Returns:
        Nodes ``[feature, threshold, left, right, leaf]``; a leaf has feature -1 and its class.
    """
    tree = model.tree_
    nodes = []
    for i in range(tree.node_count):
        left, right = int(tree.children_left[i]), int(tree.children_right[i])
        if left == -1:  # sklearn marks a leaf with -1 children
            # P(DDoS) > 0.5 is class 1 (works for counts and for proportions).
            value = tree.value[i][0]
            nodes.append([LEAF, 0, 0, 0, int(value[1] / value.sum() > HALF)])
            continue
        feature = int(tree.feature[i])
        nodes.append([feature, dt_threshold(float(tree.threshold[i]), KERNEL_FEATURES[feature][1]),
                      left, right, 0])
    return nodes


def _flatten_xgb(tree: dict[str, Any], nodes: list[list[int]]) -> int:
    """Append one XGBoost JSON tree to ``nodes`` in pre-order; the missing direction is ignored.

    Args:
        tree: Node dict from ``get_dump(dump_format="json")``.
        nodes: Output list (relative indices).

    Returns:
        Index of the appended node.
    """
    idx = len(nodes)
    if "leaf" in tree:
        nodes.append([LEAF, 0, 0, 0, round(tree["leaf"] * LEAF_ONE)])
        return idx
    feature = int(str(tree["split"]).lstrip("f"))
    t = xgb_threshold(float(tree["split_condition"]), KERNEL_FEATURES[feature][1])
    nodes.append([feature, t, 0, 0, 0])
    children = {c["nodeid"]: c for c in tree["children"]}
    nodes[idx][2] = _flatten_xgb(children[tree["yes"]], nodes)
    nodes[idx][3] = _flatten_xgb(children[tree["no"]], nodes)
    return idx


def parse_base_score(text: str) -> float:
    """Parse a base_score from ``save_config()``, e.g. "[5.6E-1]" or "0.56".

    Args:
        text: Config string.

    Returns:
        The probability as float.
    """
    return float(text.strip().strip("[]"))


def export_xgb(model: Any) -> tuple[int, list[list[list[int]]]]:
    """Export a fitted XGBClassifier.

    Args:
        model: Fitted XGBClassifier (binary:logistic).

    Returns:
        (base margin in fixed point, one node list per tree with relative indices).
    """
    booster = model.get_booster()
    config = json.loads(booster.save_config())
    base = parse_base_score(config["learner"]["learner_model_param"]["base_score"])
    base_margin = round(math.log(base / (1 - base)) * LEAF_ONE)
    trees = []
    for dump in booster.get_dump(dump_format="json"):
        nodes: list[list[int]] = []
        _flatten_xgb(json.loads(dump), nodes)
        trees.append(nodes)
    return base_margin, trees


def _shift(nodes: list[list[int]], offset: int) -> list[list[int]]:
    """Make child indices absolute.

    Args:
        nodes: Nodes with relative indices.
        offset: Index of the first node in the final list.

    Returns:
        Copy with offset children (leaves unchanged).
    """
    return [n if n[0] == LEAF else [n[0], n[1], n[2] + offset, n[3] + offset, n[4]] for n in nodes]


def build_kernel_model(dt: list[list[int]], xgb: tuple[int, list[list[list[int]]]],
                       meta: dict[str, Any]) -> dict[str, Any]:
    """Assemble kernel_model.json (DT nodes first, then the XGB trees; absolute indices).

    Args:
        dt: Output of ``export_dt``.
        xgb: Output of ``export_xgb``.
        meta: Extra meta entries (dt_depth, xgb_depth, csv_sha256, ...).

    Returns:
        The model dict (not yet validated).
    """
    base_margin, trees = xgb
    nodes = _shift(dt, 0)
    roots = []
    for tree in trees:
        roots.append(len(nodes))
        nodes += _shift(tree, len(nodes))
    full_meta = {"xgb_trees": len(trees), "n_nodes": len(nodes),
                 "created": datetime.now(timezone.utc).isoformat(timespec="seconds"), **meta}
    return {"format": 1, "features": [n for n, _ in KERNEL_FEATURES],
            "scales": [s for _, s in KERNEL_FEATURES], "leaf_shift": LEAF_SHIFT, "nodes": nodes,
            "dt_root": 0, "xgb_roots": roots, "xgb_base_margin": base_margin, "meta": full_meta}


def kernel_predictions(kmodel_dict: dict[str, Any],
                       x_int: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Evaluate the integer model on every row.

    Args:
        kmodel_dict: Kernel model.
        x_int: int64 features in kernel units.

    Returns:
        (DT verdicts, XGB margins) as int64 arrays.
    """
    rows = x_int.tolist()
    dt = [kmodel.dt_verdict(kmodel_dict, r) for r in rows]
    margin = [kmodel.xgb_margin(kmodel_dict, r) for r in rows]
    return np.array(dt, dtype=np.int64), np.array(margin, dtype=np.int64)


def parity(dt: Any, xgb: Any, kmodel_dict: dict[str, Any], x: np.ndarray,
           y: np.ndarray) -> dict[str, Any]:
    """Compare the float models with the integer kernel model on the same rows.

    Args:
        dt: Fitted sklearn tree.
        xgb: Fitted XGBClassifier.
        kmodel_dict: Kernel model.
        x: Float features (raw CIC units).
        y: True labels (copied into the mismatch rows).

    Returns:
        Dict with n, dt_agreement, xgb_agreement, max_margin_abs_err (agreeing rows only),
        n_dt_mismatch, n_xgb_mismatch and ``mismatches`` (rows: row, model, label, float, kernel).
    """
    dt_int, margin_int = kernel_predictions(kmodel_dict, to_int_features(x))
    dt_float = dt.predict(x).astype(np.int64)
    margin_float = xgb.predict(x, output_margin=True).astype(np.float64)
    xgb_float = (margin_float > 0).astype(np.int64)
    xgb_int = (margin_int > 0).astype(np.int64)
    margin_err = np.abs(margin_int / LEAF_ONE - margin_float)
    agree = xgb_float == xgb_int
    mismatches = [{"row": int(i), "model": "DT", "label": int(y[i]), "float": int(dt_float[i]),
                   "kernel": int(dt_int[i])} for i in np.flatnonzero(dt_float != dt_int)]
    mismatches += [{"row": int(i), "model": "XGB", "label": int(y[i]),
                    "float": float(margin_float[i]), "kernel": float(margin_int[i] / LEAF_ONE)}
                   for i in np.flatnonzero(~agree)]
    return {"n": len(x), "dt_agreement": float((dt_float == dt_int).mean()),
            "xgb_agreement": float(agree.mean()),
            "max_margin_abs_err": float(margin_err[agree].max()) if agree.any() else 0.0,
            "n_dt_mismatch": int((dt_float != dt_int).sum()), "n_xgb_mismatch": int((~agree).sum()),
            "mismatches": mismatches}


def sample_test_vectors(x_int: np.ndarray, y: np.ndarray, kmodel_dict: dict[str, Any], n: int,
                        seed: int) -> dict[str, list]:
    """Pick up to n rows per class and evaluate them with the integer model.

    Args:
        x_int: int64 features in kernel units.
        y: Labels.
        kmodel_dict: Kernel model.
        n: Rows per class (capped at the class size).
        seed: RNG seed.

    Returns:
        {"x": [[ints]], "dt": [...], "xgb_margin": [...]} (BENIGN rows first).
    """
    rng = np.random.default_rng(seed)
    picks = [np.sort(rng.choice(np.flatnonzero(y == label), min(n, int((y == label).sum())),
                                replace=False)) for label in (V_NORMAL, V_MALICIOUS)]
    x = x_int[np.concatenate(picks)]
    dt, margin = kernel_predictions(kmodel_dict, x)
    return {"x": x.tolist(), "dt": dt.tolist(), "xgb_margin": margin.tolist()}
