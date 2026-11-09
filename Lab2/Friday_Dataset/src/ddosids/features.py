"""T3.4: chi2 SelectKBest per target."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.feature_selection import SelectKBest, chi2  # noqa: E402

from ddosids.config import K  # noqa: E402


def score_features(x_scaled: pd.DataFrame, y: pd.Series, k: int = K) -> pd.DataFrame:
    """Scores table sorted by rank: feature, score, p_value, rank, selected."""
    sel = SelectKBest(chi2, k=k).fit(x_scaled, y)
    table = pd.DataFrame(
        {"feature": x_scaled.columns, "score": sel.scores_, "p_value": sel.pvalues_}
    )
    table["score"] = table["score"].fillna(-np.inf)
    table = table.sort_values("score", ascending=False, kind="stable").reset_index(drop=True)
    table["rank"] = np.arange(1, len(table) + 1)
    support = pd.Series(sel.get_support(), index=x_scaled.columns)
    table["selected"] = table["feature"].map(support).to_numpy()
    return table


def plot_top(table: pd.DataFrame, target: str, out_dir: Path, k: int = K) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    top = table.head(k).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(top["feature"], top["score"], color="#3b6ea5")
    ax.set_xlabel("chi2 score (MinMax-scaled train set)")
    ax.set_title(f"Top-{k} features by chi2 ({target})")
    fig.tight_layout()
    fig.savefig(out_dir / f"feature_scores_{target}.png", dpi=200)
    fig.savefig(out_dir / f"feature_scores_{target}.pdf")
    plt.close(fig)


def select_for_target(
    x_scaled: pd.DataFrame, y: pd.Series, target: str, k: int,
    artifacts_dir: Path, outputs_dir: Path,
) -> pd.DataFrame:
    """Run selection, write CSV, figures and the selected-features JSON. Returns the table."""
    table = score_features(x_scaled, y, k)
    outputs_dir.mkdir(parents=True, exist_ok=True)
    table.to_csv(outputs_dir / f"feature_scores_{target}.csv", index=False)
    plot_top(table, target, outputs_dir / "figures", k)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "target": target, "score_func": "chi2", "k": k,
        "features": table.loc[table["selected"], "feature"].tolist(),
    }
    (artifacts_dir / f"selected_features_{target}.json").write_text(json.dumps(payload, indent=2))
    return table
