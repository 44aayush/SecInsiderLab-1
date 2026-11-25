"""Task 4 CLI (Friday DDoS): train, evaluate and persist LR / DT pipelines."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import platform
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn

from ddosids import config
from ddosids.evaluate import (
    class_spec, comparison_row, evaluate_model, plot_confusion, report_table,
)
from ddosids.models import fit_model, load_data, model_keys, selected_features

BAR = "=" * 72


class Tee:
    """Write to stdout and collect into a buffer."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def __call__(self, text: str = "") -> None:
        print(text)
        self.lines.append(text)


def _summary(say: Tee, key: str, m: dict) -> None:
    say(f"\n{BAR}\n{key}\n{BAR}")
    say(report_table(m).to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    say(f"accuracy = {m['accuracy']:.4f} | macro-F1 = {m['macro_f1']:.4f} "
        f"| weighted-F1 = {m['weighted_f1']:.4f}")
    cm = pd.DataFrame(m["confusion_matrix"], index=[f"true {c}" for c in m["classes"]],
                      columns=[f"pred {c}" for c in m["classes"]])
    say("Confusion matrix (rows = true, cols = predicted):")
    say(cm.to_string())
    say(f"fit = {m['fit_s']:.2f} s | inference = {m['infer_ms_per_1k']:.3f} ms per 1,000 flows")
    if "lr_converged" in m:
        say(f"LR converged: {m['lr_converged']} (n_iter={m['lr_n_iter']}/{m['lr_max_iter']})")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--artifacts-dir", type=Path, default=config.ARTIFACTS_DIR)
    p.add_argument("--outputs-dir", type=Path, default=config.OUTPUTS_DIR)
    a = p.parse_args(argv)

    out = a.outputs_dir / "task4"
    fig_dir = out / "figures"
    models_dir = a.artifacts_dir / "models"
    fig_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)
    say = Tee()

    df, x, split = load_data(a.artifacts_dir)
    tr, te = np.asarray(split["train_idx"]), np.asarray(split["test_idx"])
    x_train, x_test = x.iloc[tr], x.iloc[te]
    say(f"Data: {len(df)} rows, {x.shape[1]} features; train {len(tr)} / test {len(te)}")

    all_metrics: dict[str, dict] = {}
    rows, meta_models = [], {}
    for key, target, model in model_keys():
        col = config.TARGETS[target]
        pipe, info = fit_model(model, x_train, df[col].iloc[tr])
        m = evaluate_model(pipe, x_test, df[col].iloc[te], target)
        m.update(info)
        sel = selected_features(pipe)
        want = json.loads((a.artifacts_dir / f"selected_features_{target}.json").read_text())
        if set(sel) != set(want["features"]):
            raise RuntimeError(f"{key}: selected features differ from Task 3 JSON")
        m["selected_features"] = sel
        all_metrics[key] = m
        plot_confusion(m["confusion_matrix"], class_spec(target)[2], key, fig_dir)
        report_table(m).to_csv(out / f"report_{key}.csv", index=False)
        joblib.dump(pipe, models_dir / f"{key}.joblib")
        rows.append(comparison_row(key, target, model, m))
        meta_models[key] = {
            "target": target, "model": model, "selected_features": sel,
            "classes": [int(c) for c in pipe.classes_],
            "metrics": {"accuracy": m["accuracy"], "macro_f1": m["macro_f1"],
                        "weighted_f1": m["weighted_f1"],
                        "per_class_f1": {n: v["f1"] for n, v in m["per_class"].items()}},
        }
        _summary(say, key, m)

    comp = pd.DataFrame(rows)
    comp.to_csv(out / "comparison.csv", index=False)
    (out / "metrics.json").write_text(json.dumps(all_metrics, indent=2))
    meta = {
        "input_features": x.columns.tolist(),
        "random_state": config.RANDOM_STATE,
        "split": {"test_size": config.TEST_SIZE, "n_train": len(tr), "n_test": len(te),
                  "n_rows": len(df), "stratify": split.get("stratify")},
        "trained_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "versions": {"python": platform.python_version(), "sklearn": sklearn.__version__,
                     "pandas": pd.__version__, "numpy": np.__version__},
        "models": meta_models,
    }
    (models_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    say(f"\n{BAR}\nComparison table\n{BAR}")
    say(comp.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    (out / "run_log.txt").write_text("\n".join(say.lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
