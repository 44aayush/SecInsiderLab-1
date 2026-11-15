"""Tests for main.py: smoke run, logging and lazy imports (Task 3, T5.6)."""
from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path

import pytest

import main

SCRIPT = Path(main.__file__).resolve()
FIG_STEMS = (["metrics_bar_grouped", "metrics_small_multiples", "metrics_heatmap", "metrics_radar",
              "metrics_dot", "errors_bar", "time_bar", "comparison_table",
              "confusion_grid_counts", "confusion_grid_normalized",
              "confusion_gnb", "confusion_lr", "confusion_mlp",
              "roc_test", "roc_test_zoom", "roc_test_logx", "roc_grid", "roc_test_ml",
              "roc_test_dl",
              "dl_history_overlay", "dl_history_grid"])
METRIC_FILES = ["preprocess_summary.json", "metrics.json"] + [
    f"comparison_{s}.{e}" for s in ("test", "val") for e in ("csv", "md", "tex")]
SUBPROCESS_TIMEOUT_S = 120


def _run(fixture_csv: Path, out: Path, models: list[str]) -> int:
    """Call main with the smoke arguments.

    Args:
        fixture_csv: Sample CSV.
        out: Output root.
        models: Model keys.

    Returns:
        main's return value.
    """
    return main.main(["--csv", str(fixture_csv), "--models", *models, "--epochs", "1",
                      "--out", str(out)])


@pytest.fixture(name="smoke_out", scope="module")
def _smoke_out(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Run the gnb + lr + mlp smoke run once for the tests below.

    Args:
        tmp_path_factory: pytest temp directory factory.

    Returns:
        Output root of the run.
    """
    out = tmp_path_factory.mktemp("smoke")
    fixture = Path(__file__).resolve().parent / "fixtures" / "sample_ddos.csv"
    assert _run(fixture, out, ["gnb", "lr", "mlp"]) == 0
    return out


def test_smoke_run_metric_files(smoke_out: Path) -> None:
    """Log, json and table files of CLAUDE.md 6 exist and metrics.json is in run order."""
    assert (smoke_out / "run.log").exists()
    for name in METRIC_FILES:
        assert (smoke_out / "metrics" / name).exists(), name
    metrics = json.loads((smoke_out / "metrics" / "metrics.json").read_text())
    assert list(metrics) == ["gnb", "lr", "mlp"]


def test_smoke_run_figures_and_index(smoke_out: Path) -> None:
    """Every applicable stem exists as png and pdf; INDEX.md lists exactly those."""
    for stem in FIG_STEMS:
        assert (smoke_out / "figures" / f"{stem}.png").exists(), stem
        assert (smoke_out / "figures" / f"{stem}.pdf").exists(), stem
    index = (smoke_out / "figures" / "INDEX.md").read_text()
    listed = [line.split("`")[1] for line in index.splitlines() if line.startswith("| `")]
    assert sorted(listed) == sorted(FIG_STEMS)


def test_double_call_does_not_duplicate_log_lines(fixture_csv: Path, tmp_path: Path) -> None:
    """A second in-process call leaves exactly one handler pair and a fresh log."""
    _run(fixture_csv, tmp_path / "a", ["gnb"])
    _run(fixture_csv, tmp_path / "b", ["gnb"])
    assert len(logging.getLogger().handlers) == 2
    lines = (tmp_path / "b" / "run.log").read_text().splitlines()
    f1_lines = [line for line in lines if "gnb test F1" in line]
    assert len(f1_lines) == 1


def test_unknown_model_is_an_argparse_error(fixture_csv: Path, tmp_path: Path) -> None:
    """An unknown key exits with code 2."""
    with pytest.raises(SystemExit) as info:
        main.main(["--csv", str(fixture_csv), "--models", "svm", "--out", str(tmp_path)])
    assert info.value.code == 2


def test_ml_only_run_does_not_import_torch(fixture_csv: Path, tmp_path: Path) -> None:
    """--models gnb run as a fresh interpreter leaves torch out of sys.modules."""
    code = ("import sys; sys.path.insert(0, sys.argv[1]); import main; "
            "rc = main.main(['--csv', sys.argv[2], '--models', 'gnb', '--out', sys.argv[3]]); "
            "assert rc == 0; assert 'torch' not in sys.modules, 'torch was imported'")
    proc = subprocess.run([sys.executable, "-c", code, str(SCRIPT.parent), str(fixture_csv),
                           str(tmp_path)], capture_output=True, text=True, check=False,
                          timeout=SUBPROCESS_TIMEOUT_S)
    assert proc.returncode == 0, proc.stderr[-2000:]


def test_device_cpu_and_log_txt(fixture_csv: Path, tmp_path: Path) -> None:
    """--device cpu runs a DL model; --log-txt writes one ordered report and frees the handler."""
    report = tmp_path / "sub" / "run_report.txt"
    rc = main.main(["--csv", str(fixture_csv), "--models", "gnb", "mlp", "--epochs", "1",
                    "--device", "cpu", "--out", str(tmp_path / "out"), "--log-txt", str(report)])
    assert rc == 0
    assert len(logging.getLogger().handlers) == 2  # the text handler was removed again
    text = report.read_text(encoding="utf-8")
    titles = ["RUN HEADER", "CONFIGURATION", "RUN LOG", "PREPROCESS SUMMARY", "PER-MODEL DETAILS",
              "COMPARISON TABLE (VAL)", "COMPARISON TABLE (TEST)", "CONFUSION MATRICES",
              "FILES WRITTEN"]
    positions = [text.index(f"== {t}") for t in titles]
    assert positions == sorted(positions)
    assert "torch device: cpu" in text and "csv sha256:" in text and "<- best" in text
    assert "metrics/comparison_test.md" in text


def test_auto_device_resolves_to_cpu_here(monkeypatch: pytest.MonkeyPatch) -> None:
    """auto gives cpu without CUDA, and None (no torch) for an ML-only selection."""
    torch = pytest.importorskip("torch")
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert main.resolve_device(["mlp"], "auto") == "cpu"
    assert main.resolve_device(["gnb"], "auto") is None


def test_epoch_limits_per_model_and_override() -> None:
    """Without --epochs each model uses its own limit; --epochs overrides all."""
    pytest.importorskip("torch")
    assert main.epoch_limits(["gnb", "mlp", "cnn", "lstm"], None) == {
        "mlp": 30, "lstm": 40, "cnn": 30}
    assert main.epoch_limits(["mlp", "lstm"], 3) == {"mlp": 3, "lstm": 3}
    assert not main.epoch_limits(["gnb"], None)
