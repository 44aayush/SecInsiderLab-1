"""Logistic Regression classifier (Task 1).

Trains and scores Logistic Regression on the shared scaled splits via
``clf.ml_common.run_sklearn`` (CLAUDE.md 4.9 and 5).
"""
from __future__ import annotations

from sklearn.linear_model import LogisticRegression

import common
from clf.ml_common import run_sklearn

KEY = "lr"
NAME = "Logistic Regression"
MAX_ITER = 2000


def build_model() -> LogisticRegression:
    """Create the unfitted model with the fixed hyper-parameters.

    Returns:
        A new LogisticRegression.
    """
    return LogisticRegression(max_iter=MAX_ITER, random_state=common.SEED)


def run(splits: common.DataSplits) -> common.ModelResult:
    """Train on the train split and score the validation and test splits.

    Args:
        splits: Scaled data splits.

    Returns:
        ModelResult with P(DDoS) scores and timings.
    """
    return run_sklearn(build_model(), KEY, NAME, splits)
