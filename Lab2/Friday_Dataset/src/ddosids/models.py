"""T4.1: pipelines (MinMax -> chi2 top-k -> classifier) for the binary DDoS target."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.feature_selection import SelectKBest, chi2
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler
from sklearn.tree import DecisionTreeClassifier

from ddosids.config import K, RANDOM_STATE, TARGETS

LR_MAX_ITER = 5000
MODEL_NAMES = ["lr_default", "lr_balanced", "dt_default", "dt_balanced"]


def build_pipeline(clf: Any, k: int = K) -> Pipeline:
    return Pipeline([
        ("scale", MinMaxScaler(clip=True)),
        ("select", SelectKBest(chi2, k=k)),
        ("clf", clf),
    ])


def make_classifier(model: str) -> Any:
    makers = {
        "lr_default": lambda: LogisticRegression(max_iter=LR_MAX_ITER),
        "lr_balanced": lambda: LogisticRegression(max_iter=LR_MAX_ITER, class_weight="balanced"),
        "dt_default": lambda: DecisionTreeClassifier(random_state=RANDOM_STATE),
        "dt_balanced": lambda: DecisionTreeClassifier(
            random_state=RANDOM_STATE, class_weight="balanced"),
    }
    return makers[model]()


def model_keys(targets: list[str] | None = None) -> list[tuple[str, str, str]]:
    """(key, target, model) for each requested target (default: all in config.TARGETS)."""
    targets = list(TARGETS) if targets is None else targets
    return [(f"{t}_{m}", t, m) for t in targets for m in MODEL_NAMES]


def load_data(artifacts_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Return (df, features-in-parquet-order df, split dict)."""
    df = pd.read_parquet(artifacts_dir / "clean.parquet")
    split = json.loads((artifacts_dir / "split_indices.json").read_text())
    non_feat = set(TARGETS.values())
    feats = [c for c in df.columns if c not in non_feat and c != "Label"]
    return df, df[feats], split


def fit_model(model: str, x_train: pd.DataFrame, y_train: pd.Series,
              k: int = K) -> tuple[Pipeline, dict[str, Any]]:
    """Fit one pipeline; returns it and info (fit_s, lr convergence)."""
    pipe = build_pipeline(make_classifier(model), k)
    t0 = time.perf_counter()
    pipe.fit(x_train, y_train)
    info: dict[str, Any] = {"fit_s": time.perf_counter() - t0}
    clf = pipe.named_steps["clf"]
    if model.startswith("lr"):
        n_iter = int(clf.n_iter_.max())
        info["lr_n_iter"] = n_iter
        info["lr_max_iter"] = LR_MAX_ITER
        info["lr_converged"] = n_iter < LR_MAX_ITER
    return pipe, info


def selected_features(pipe: Pipeline) -> list[str]:
    return pipe[:-1].get_feature_names_out().tolist()
