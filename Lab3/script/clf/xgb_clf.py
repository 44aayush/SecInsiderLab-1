"""XGBoost gradient-boosted trees classifier (Task 1).

Trains and scores XGBoost on the shared scaled splits via
``clf.ml_common.run_sklearn`` (CLAUDE.md 4.9 and 5).
"""
from __future__ import annotations

from xgboost import XGBClassifier

import common
from clf.ml_common import run_sklearn

KEY = "xgb"
NAME = "XGBoost"
N_ESTIMATORS = 500
MAX_DEPTH = 6
LEARNING_RATE = 0.1
TREE_METHOD = "hist"
EVAL_METRIC = "logloss"
EARLY_STOPPING_ROUNDS = 20
N_JOBS = -1  # use all cores


def build_model() -> XGBClassifier:
    """Create the unfitted model with the fixed hyper-parameters.

    Returns:
        A new XGBClassifier.
    """
    return XGBClassifier(
        n_estimators=N_ESTIMATORS, max_depth=MAX_DEPTH, learning_rate=LEARNING_RATE,
        tree_method=TREE_METHOD, eval_metric=EVAL_METRIC,
        early_stopping_rounds=EARLY_STOPPING_ROUNDS, n_jobs=N_JOBS, random_state=common.SEED)


def run(splits: common.DataSplits) -> common.ModelResult:
    """Train on the train split and score the validation and test splits.

    Args:
        splits: Scaled data splits.

    Returns:
        ModelResult with P(DDoS) scores and timings.
    """
    # The validation set drives early stopping; verbose=False silences per-round output.
    fit_kwargs = {"eval_set": [(splits.x_val, splits.y_val)], "verbose": False}
    return run_sklearn(build_model(), KEY, NAME, splits, fit_kwargs=fit_kwargs)
