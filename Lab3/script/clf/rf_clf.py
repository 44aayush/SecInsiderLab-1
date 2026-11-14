"""Random Forest classifier (Task 1).

Trains and scores Random Forest on the shared scaled splits via
``clf.ml_common.run_sklearn`` (CLAUDE.md 4.9 and 5).
"""
from __future__ import annotations

from sklearn.ensemble import RandomForestClassifier

import common
from clf.ml_common import run_sklearn

KEY = "rf"
NAME = "Random Forest"
N_ESTIMATORS = 100
N_JOBS = -1  # use all cores


def build_model() -> RandomForestClassifier:
    """Create the unfitted model with the fixed hyper-parameters.

    Returns:
        A new RandomForestClassifier.
    """
    return RandomForestClassifier(
        n_estimators=N_ESTIMATORS, n_jobs=N_JOBS, random_state=common.SEED)


def run(splits: common.DataSplits) -> common.ModelResult:
    """Train on the train split and score the validation and test splits.

    Args:
        splits: Scaled data splits.

    Returns:
        ModelResult with P(DDoS) scores and timings.
    """
    return run_sklearn(build_model(), KEY, NAME, splits)
