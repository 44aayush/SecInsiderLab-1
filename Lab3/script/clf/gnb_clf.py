"""Gaussian Naive Bayes (defaults) classifier (Task 1).

Trains and scores Gaussian Naive Bayes on the shared scaled splits via
``clf.ml_common.run_sklearn`` (CLAUDE.md 4.9 and 5).
"""
from __future__ import annotations

from sklearn.naive_bayes import GaussianNB

import common
from clf.ml_common import run_sklearn

KEY = "gnb"
NAME = "Gaussian Naive Bayes"


def build_model() -> GaussianNB:
    """Create the unfitted model with the fixed hyper-parameters.

    Returns:
        A new GaussianNB.
    """
    return GaussianNB()


def run(splits: common.DataSplits) -> common.ModelResult:
    """Train on the train split and score the validation and test splits.

    Args:
        splits: Scaled data splits.

    Returns:
        ModelResult with P(DDoS) scores and timings.
    """
    return run_sklearn(build_model(), KEY, NAME, splits)
