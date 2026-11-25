"""T4.2: evaluation (reports, confusion matrices, timings)."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support,
)

from ddosids.config import ATTACK_NAME, BENIGN  # noqa: E402

BINARY_NAMES = [BENIGN, ATTACK_NAME]
INFER_REPEATS = 5


def class_spec(target: str) -> tuple[list, list[str], list[str]]:
    """(class values in order, report names, short tick labels)."""
    if target != "binary":
        raise ValueError(f"Unknown target: {target}")
    return [0, 1], list(BINARY_NAMES), list(BINARY_NAMES)


def evaluate_model(pipe, x_test: pd.DataFrame, y_test: pd.Series, target: str) -> dict[str, Any]:
    classes, names, _ = class_spec(target)
    pred = pipe.predict(x_test)  # untimed warm-up
    runs_ms = []
    for _ in range(INFER_REPEATS):
        t0 = time.perf_counter()
        pipe.predict(x_test)
        runs_ms.append((time.perf_counter() - t0) / len(x_test) * 1000 * 1000)
    p, r, f, s = precision_recall_fscore_support(
        y_test, pred, labels=classes, zero_division=0)
    per_class = {
        n: {"precision": float(p[i]), "recall": float(r[i]), "f1": float(f[i]),
            "support": int(s[i])} for i, n in enumerate(names)}
    cm = confusion_matrix(y_test, pred, labels=classes)
    return {
        "classes": names,
        "class_values": [int(c) for c in classes],
        "per_class": per_class,
        "accuracy": float(accuracy_score(y_test, pred)),
        "macro_f1": float(f1_score(y_test, pred, labels=classes, average="macro", zero_division=0)),
        "weighted_f1": float(
            f1_score(y_test, pred, labels=classes, average="weighted", zero_division=0)),
        "confusion_matrix": cm.tolist(),
        "infer_ms_per_1k": float(np.median(runs_ms)),
        "infer_ms_per_1k_runs": runs_ms,
        "n_test": int(len(x_test)),
    }


def report_table(m: dict[str, Any]) -> pd.DataFrame:
    rows = [{"class": n, **v} for n, v in m["per_class"].items()]
    rows.append({"class": "macro avg",
                 "precision": np.mean([v["precision"] for v in m["per_class"].values()]),
                 "recall": np.mean([v["recall"] for v in m["per_class"].values()]),
                 "f1": m["macro_f1"], "support": m["n_test"]})
    rows.append({"class": "weighted avg", "precision": np.nan, "recall": np.nan,
                 "f1": m["weighted_f1"], "support": m["n_test"]})
    rows.append({"class": "accuracy", "precision": np.nan, "recall": np.nan,
                 "f1": m["accuracy"], "support": m["n_test"]})
    return pd.DataFrame(rows)


def plot_confusion(cm: list[list[int]], short: list[str], key: str, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    a = np.array(cm)
    row = a.sum(axis=1, keepdims=True)
    pct = np.divide(a, row, out=np.zeros(a.shape, dtype=float), where=row > 0) * 100
    n = len(short)
    fig, ax = plt.subplots(figsize=(4 + 0.5 * n, 3.6 + 0.5 * n))
    ax.imshow(pct, cmap="Blues", vmin=0, vmax=100)
    for i in range(n):
        for j in range(n):
            ax.text(j, i, f"{a[i, j]:,}\n{pct[i, j]:.1f}%", ha="center", va="center",
                    color="white" if pct[i, j] > 50 else "black", fontsize=9)
    ax.set_xticks(range(n), short)
    ax.set_yticks(range(n), short)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title(key)
    fig.tight_layout()
    fig.savefig(out_dir / f"cm_{key}.png", dpi=200)
    fig.savefig(out_dir / f"cm_{key}.pdf")
    plt.close(fig)


def comparison_row(key: str, target: str, model: str, m: dict[str, Any]) -> dict[str, Any]:
    pc = m["per_class"]
    return {
        "key": key, "target": target, "model": model, "accuracy": m["accuracy"],
        "macro_f1": m["macro_f1"], "weighted_f1": m["weighted_f1"],
        f"f1_{BENIGN}": pc[BENIGN]["f1"], f"f1_{ATTACK_NAME}": pc[ATTACK_NAME]["f1"],
        "ddos_precision": pc[ATTACK_NAME]["precision"],
        "ddos_recall": pc[ATTACK_NAME]["recall"],
        "fit_s": m["fit_s"], "infer_ms_per_1k": m["infer_ms_per_1k"],
    }
