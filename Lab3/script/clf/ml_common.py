"""Shared training and scoring helper for the scikit-learn style classifiers (Task 1).

Every ``*_clf.py`` module delegates to ``run_sklearn`` so that timing and score
extraction are identical for all five models (CLAUDE.md 5).
"""
from __future__ import annotations

import logging
import time
from typing import Any

import common

log = logging.getLogger(__name__)

FAMILY = "ML"


def run_sklearn(model: Any, key: str, name: str, splits: common.DataSplits,
                fit_kwargs: dict[str, Any] | None = None) -> common.ModelResult:
    """Fit a model, then score the validation and test sets.

    Args:
        model: Unfitted estimator with ``fit`` and ``predict_proba``.
        key: Registry key, e.g. "rf".
        name: Display name.
        splits: Scaled data splits.
        fit_kwargs: Extra keyword arguments for ``fit`` (e.g. XGBoost eval_set).

    Returns:
        ModelResult with P(DDoS) for val and test and the two timings.
    """
    # repr(model) lists every hyper-parameter, so the run log is self-describing.
    log.info("%s hyper-parameters: %r", name, model)
    start = time.perf_counter()
    model.fit(splits.x_train, splits.y_train, **(fit_kwargs or {}))
    train_time = time.perf_counter() - start
    # Validation scoring is not timed: only the test prediction is reported (CLAUDE.md 4.11).
    val_score = model.predict_proba(splits.x_val)[:, 1]
    start = time.perf_counter()
    test_score = model.predict_proba(splits.x_test)[:, 1]
    predict_time = time.perf_counter() - start
    log.info("%s: fit %.2f s, test predict %.2f s", name, train_time, predict_time)
    return common.ModelResult(key, name, FAMILY, val_score, test_score, train_time, predict_time)
