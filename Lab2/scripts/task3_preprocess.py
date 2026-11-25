"""Task 3 CLI (Friday DDoS): load, clean, split, scale, select features."""
from __future__ import annotations

import argparse
import json
import contextlib
import io
import logging
import sys
from pathlib import Path

import pandas as pd

from ddosids import config
from ddosids.data import (
    clean, feature_columns, label_summary, load_raw, make_split, save_split, scale_train,
)
from ddosids.features import select_for_target

log = logging.getLogger("task3")


def _print_summary(raw_summary: pd.DataFrame, report: dict, df: pd.DataFrame,
                   train: pd.Series, test: pd.Series, tables: dict[str, pd.DataFrame]) -> None:
    bar = "=" * 72
    print(f"\n{bar}\nRaw label summary\n{bar}")
    print(raw_summary.to_string())
    print(f"\n{bar}\nCleaning steps\n{bar}")
    for s in report["steps"]:
        extra = {k: v for k, v in s.items()
                 if k not in ("step", "rows_before", "cols_before", "rows_after", "cols_after")}
        print(f"- {s['step']}: rows {s['rows_before']} -> {s['rows_after']}, "
              f"cols {s['cols_before']} -> {s['cols_after']}")
        for k, v in extra.items():
            print(f"    {k}: {v}")
    print(f"\nFinal: {df.shape[0]} rows x {report['n_features']} features "
          f"(+ {config.LABEL_COL}, {config.BINARY_COL})")
    print(f"\n{bar}\nFinal label summary\n{bar}")
    print(label_summary(df).to_string())
    print(f"\n{bar}\nSplit class counts (70/30, stratified on Label)\n{bar}")
    print(pd.DataFrame({"train": train, "test": test}).to_string())
    for target, table in tables.items():
        print(f"\n{bar}\nTop features by chi2: {target}\n{bar}")
        top = table.head(config.K)[["rank", "feature", "score", "p_value"]]
        print(top.to_string(index=False, float_format=lambda v: f"{v:.4g}"))


class Tee(io.StringIO):
    """Write to the real stdout and keep a copy for run_log.txt."""

    def __init__(self, stream) -> None:
        super().__init__()
        self._stream = stream

    def write(self, text: str) -> int:
        self._stream.write(text)
        return super().write(text)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data", type=Path, default=config.DATA_CSV)
    p.add_argument("--k", type=int, default=config.K)
    p.add_argument("--artifacts-dir", type=Path, default=config.ARTIFACTS_DIR)
    p.add_argument("--outputs-dir", type=Path, default=config.OUTPUTS_DIR)
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    out = a.outputs_dir / "task3"
    out.mkdir(parents=True, exist_ok=True)
    a.artifacts_dir.mkdir(parents=True, exist_ok=True)

    raw = load_raw(a.data)
    df, report = clean(raw)
    raw_summary = pd.DataFrame(report["raw_label_summary"]).set_index(config.LABEL_COL)
    raw_summary.to_csv(out / "label_summary_raw.csv")
    label_summary(df).to_csv(out / "label_summary_clean.csv")
    (out / "cleaning_report.json").write_text(json.dumps(report, indent=2))
    df.to_parquet(a.artifacts_dir / "clean.parquet")

    train_idx, test_idx = make_split(df)
    save_split(train_idx, test_idx, len(df), a.artifacts_dir / "split_indices.json")
    feats = feature_columns(df)
    _, x_scaled = scale_train(df.iloc[train_idx][feats], out)

    tables = {}
    for target, col in config.TARGETS.items():
        tables[target] = select_for_target(
            x_scaled, df.iloc[train_idx][col], target, a.k, a.artifacts_dir, out)

    tee = Tee(sys.stdout)
    with contextlib.redirect_stdout(tee):
        _print_summary(
            raw_summary, report, df,
            df.iloc[train_idx][config.LABEL_COL].value_counts(),
            df.iloc[test_idx][config.LABEL_COL].value_counts(), tables)
    (out / "run_log.txt").write_text(tee.getvalue())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
