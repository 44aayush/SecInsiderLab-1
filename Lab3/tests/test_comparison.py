"""Tests for the comparison tables and the figure index (Task 3)."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

import common
import comparison
import figure_index

EXPECTED_COLUMNS = ["Model", "Family", "Accuracy", "Precision", "Recall", "F1", "Macro-F1",
                    "ROC-AUC", "TP", "TN", "FP", "FN", "Train time (s)", "Predict time (s)"]
FULL_RUN_STEMS = 26


def test_build_table_columns_and_sort(fake_metrics: dict) -> None:
    """Columns follow CLAUDE.md 5, rows are sorted by F1 descending."""
    for split in ("test", "val"):
        df = comparison.build_table(fake_metrics, split)
        assert list(df.columns) == EXPECTED_COLUMNS
        assert len(df) == len(fake_metrics)
        assert df["F1"].is_monotonic_decreasing


def test_build_table_rounds_to_four_decimals(fake_metrics: dict) -> None:
    """Scores are decimals with at most 4 places, and match the metrics."""
    df = comparison.build_table(fake_metrics, "test")
    for col in ("Accuracy", "F1", "ROC-AUC"):
        assert ((df[col] * 10_000).round(6) % 1 == 0).all()
    row = df.iloc[0]
    key = next(k for k, v in fake_metrics.items() if v["name"] == row["Model"])
    assert row["F1"] == round(fake_metrics[key]["test"]["f1"], 4)
    for col in ("TP", "TN", "FP", "FN"):
        assert row[col] == fake_metrics[key]["test"][col.lower()]


def test_save_table_writes_three_files(fake_metrics: dict, tmp_path: Path) -> None:
    """csv, md and tex exist, and the csv round-trips."""
    df = comparison.build_table(fake_metrics, "test")
    comparison.save_table(df, tmp_path / "metrics", "comparison_test")
    for suffix in ("csv", "md", "tex"):
        assert (tmp_path / "metrics" / f"comparison_test.{suffix}").stat().st_size > 0
    csv = pd.read_csv(tmp_path / "metrics" / "comparison_test.csv")
    assert list(csv.columns) == EXPECTED_COLUMNS
    assert "0." in (tmp_path / "metrics" / "comparison_test.md").read_text()


def test_plot_table_image(fake_metrics: dict, tmp_path: Path) -> None:
    """The table image is written as png and pdf."""
    comparison.plot_table_image(comparison.build_table(fake_metrics, "test"), tmp_path)
    assert (tmp_path / "comparison_table.png").exists()
    assert (tmp_path / "comparison_table.pdf").exists()


def test_figure_index_lists_only_existing(tmp_path: Path) -> None:
    """INDEX.md names the PNGs that exist and nothing else."""
    fig_dir = tmp_path / "figures"
    fig_dir.mkdir()
    for stem in ("roc_test", "confusion_rf", "metrics_radar"):
        (fig_dir / f"{stem}.png").write_bytes(b"")
    comparison.write_figure_index(tmp_path)
    text = (fig_dir / "INDEX.md").read_text()
    for stem in ("roc_test", "confusion_rf", "metrics_radar"):
        assert f"[{stem}]({stem}.png)" in text
    assert "roc_grid" not in text and "confusion_gnb" not in text
    assert "Total: 3 figures listed." in text


def test_catalog_expands_to_26_stems() -> None:
    """The catalog has 18 fixed stems plus the confusion pattern (8 keys)."""
    assert len(comparison.FIGURE_CATALOG) - 1 + len(common.MODEL_COLORS) == FULL_RUN_STEMS


def _full_index_text(tmp_path: Path) -> tuple[list[str], str]:
    """Create every catalog PNG for 8 models, write INDEX.md and return (stems, text).

    Args:
        tmp_path: Output root.

    Returns:
        The stems created and the INDEX.md text.
    """
    fig_dir = tmp_path / "figures"
    fig_dir.mkdir()
    stems = [s for s in comparison.FIGURE_CATALOG if s != figure_index.CONFUSION_PATTERN]
    stems += [f"confusion_{k}" for k in common.MODEL_COLORS]
    for stem in stems:
        (fig_dir / f"{stem}.png").write_bytes(b"")
    comparison.write_figure_index(tmp_path)
    return stems, (fig_dir / "INDEX.md").read_text()


def test_full_index_has_four_tier_headings(tmp_path: Path) -> None:
    """A full 8-model index has the 4 tier headings and the right total."""
    _, text = _full_index_text(tmp_path)
    for title, _ in figure_index.TIERS.values():
        assert f"## {title}" in text
    assert f"Total: {FULL_RUN_STEMS} figures listed." in text


def test_each_stem_appears_in_exactly_one_tier(tmp_path: Path) -> None:
    """Every stem is linked once, and the tiers hold 7 / 5 / 6 / 8 figures."""
    stems, text = _full_index_text(tmp_path)
    assert all(text.count(f"[{s}]({s}.png)") == 1 for s in stems)
    sizes = [sum(1 for v in comparison.FIGURE_CATALOG.values() if v[0] == t) for t in (1, 2, 3)]
    assert sizes == [7, 5, 6]


def test_build_table_sorts_on_unrounded_f1(fake_metrics: dict) -> None:
    """Two models equal at 4 decimals are ordered by their raw F1."""
    low, high = 0.99991, 0.99993   # both round to 0.9999
    metrics = {}
    for key, f1 in (("gnb", low), ("rf", high)):  # run order puts the worse model first
        entry = {**fake_metrics["rf"], "name": key,
                 "test": {**fake_metrics["rf"]["test"], "f1": f1}}
        metrics[key] = entry
    df = comparison.build_table(metrics, "test")
    assert list(df["Model"]) == ["rf", "gnb"]
    assert df["F1"].nunique() == 1


def test_table_markdown_four_decimals(fake_metrics: dict) -> None:
    """The shared markdown renderer prints scores with 4 and times with 3 decimals."""
    text = comparison.table_markdown(comparison.build_table(fake_metrics, "test"))
    assert re.search(r"\| +\d\.\d{4} +\|", text)
    assert not re.search(r"\d\.\d{5,}", text)


def test_tex_has_resizebox_note(fake_metrics: dict, tmp_path: Path) -> None:
    """The tex export carries the resizebox hint and a booktabs rule."""
    comparison.save_table(comparison.build_table(fake_metrics, "test"), tmp_path, "t")
    text = (tmp_path / "t.tex").read_text()
    assert "resizebox" in text and "\\toprule" in text
