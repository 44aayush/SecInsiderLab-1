"""K-Nearest Neighbors classifier (Task 1).

Trains and scores K-Nearest Neighbors on the shared scaled splits via
``clf.ml_common.run_sklearn`` (CLAUDE.md 4.9 and 5).
"""
from __future__ import annotations

from sklearn.neighbors import KNeighborsClassifier

import common
from clf.ml_common import run_sklearn

KEY = "knn"
NAME = "K-Nearest Neighbors"
N_NEIGHBORS = 5
N_JOBS = -1  # use all cores


def build_model() -> KNeighborsClassifier:
    """Create the unfitted model with the fixed hyper-parameters.

    Returns:
        A new KNeighborsClassifier.
    """
    return KNeighborsClassifier(n_neighbors=N_NEIGHBORS, n_jobs=N_JOBS)


def run(splits: common.DataSplits) -> common.ModelResult:
    """Train on the train split and score the validation and test splits.

    Args:
        splits: Scaled data splits.

    Returns:
        ModelResult with P(DDoS) scores and timings.
    """
    return run_sklearn(build_model(), KEY, NAME, splits)
