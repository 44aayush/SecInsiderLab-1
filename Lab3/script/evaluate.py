"""Metric computation for Lab 3 (Task 3: comparison of Accuracy, F-score, Precision, Recall, ROC).

Every model delivers P(DDoS) as its score; DDoS is the positive class
(CLAUDE.md 4.10-4.11). All returned values are plain ints, floats and strs so
the result is JSON-serialisable.
"""
from __future__ import annotations

import numpy as np
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score)

import common

THRESHOLD = 0.5


def compute_metrics(y_true: np.ndarray, y_score: np.ndarray) -> dict[str, float | int]:
    """Compute the scores and the confusion matrix for one split.

    Args:
        y_true: Labels (1 = DDoS).
        y_score: P(DDoS) per sample.

    Returns:
        Dict with accuracy, precision, recall, f1, macro_f1, roc_auc and tn/fp/fn/tp.
    """
    # Strict ">" matches sklearn predict: an exact 0.5 is BENIGN.
    y_pred = (y_score > THRESHOLD).astype(np.int64)
    # labels=[0, 1] keeps a 2x2 matrix even when a class is absent from y_pred.
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_score)),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
    }


def evaluate_all(results: list[common.ModelResult], splits: common.DataSplits) -> dict[str, dict]:
    """Evaluate every model on the validation and test splits.

    Args:
        results: Model results in run order.
        splits: Data splits providing the true labels.

    Returns:
        {key: {name, family, val, test, train_time_s, predict_time_s}}, in run order.
    """
    return {
        res.key: {
            "name": res.name,
            "family": res.family,
            "val": compute_metrics(splits.y_val, res.y_val_score),
            "test": compute_metrics(splits.y_test, res.y_test_score),
            "train_time_s": float(res.train_time_s),
            "predict_time_s": float(res.predict_time_s),
        }
        for res in results
    }
