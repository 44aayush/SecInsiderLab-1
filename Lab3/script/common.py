"""Shared constants, result dataclasses, logging setup and figure saving for Lab 3.

Serves Tasks 1-3 (every module imports from here). It never imports torch or
``matplotlib.pyplot``: figures use the object-oriented ``Figure`` API only
(CLAUDE.md 4.12), so no GUI backend is ever loaded.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from matplotlib.figure import Figure

# common.py lives in Lab3/script/, so the Lab 3 root is one level up.
LAB3_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CSV = LAB3_DIR / "Friday-WorkingHours-Afternoon-DDos.csv"
DEFAULT_OUT = LAB3_DIR / "outputs"

SEED = 42
TRAIN_FRAC, VAL_FRAC, TEST_FRAC = 0.70, 0.15, 0.15
NEGATIVE_LABEL, POSITIVE_LABEL = "BENIGN", "DDoS"  # encoded 0 / 1
# Read at call time by preprocess.clean so tests can monkeypatch it (decision D1).
DROP_DUPLICATES = True
IDENTICAL_ATOL = 1e-6
# Shared DL defaults; each dl/*_dl.py module owns its MAX_EPOCHS (and may override lr/patience).
DL_BATCH_SIZE, DL_LR, DL_PATIENCE = 1024, 1e-3, 3
FIG_DPI = 200
# Okabe-Ito colour-blind-safe palette, yellow replaced by grey for contrast.
MODEL_COLORS = {
    "gnb": "#E69F00", "lr": "#56B4E9", "knn": "#009E73", "rf": "#0072B2",
    "xgb": "#D55E00", "mlp": "#CC79A7", "lstm": "#000000", "cnn": "#7F7F7F",
}

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
LOG_FILE_NAME = "run.log"


@dataclass(frozen=True)
class DataSplits:
    """Scaled train/validation/test arrays shared by all eight models.

    Attributes:
        x_train: Scaled float32 features, shape (n, f).
        x_val: Validation features.
        x_test: Test features.
        y_train: int64 labels, 1 = DDoS.
        y_val: Validation labels.
        y_test: Test labels.
        feature_names: Column names matching the feature axis.
    """

    x_train: np.ndarray
    x_val: np.ndarray
    x_test: np.ndarray
    y_train: np.ndarray
    y_val: np.ndarray
    y_test: np.ndarray
    feature_names: list[str]


@dataclass
class ModelResult:  # 8 fields: .pylintrc sets max-attributes=8 (CLAUDE.md 5)
    """Scores and timings of one trained model.

    Attributes:
        key: Registry key, e.g. "rf".
        name: Display name, e.g. "Random Forest".
        family: "ML" or "DL".
        y_val_score: P(DDoS) on the validation set, floats in [0, 1].
        y_test_score: P(DDoS) on the test set.
        train_time_s: Wall-clock fit time in seconds.
        predict_time_s: Wall-clock test-set prediction time in seconds.
        history: DL only, {"train_loss": [...], "val_loss": [...]}.
    """

    key: str
    name: str
    family: str
    y_val_score: np.ndarray
    y_test_score: np.ndarray
    train_time_s: float
    predict_time_s: float
    history: dict[str, list[float]] | None = None


def setup_logging(out_dir: Path) -> None:
    """Log to the console and to ``out_dir/run.log``; safe to call repeatedly.

    Args:
        out_dir: Output root; created if missing. run.log is overwritten (mode "w").
    """
    root = logging.getLogger()
    # Remove and close old handlers first, otherwise a second call (tests call
    # main() in-process) would duplicate every log line and leak file handles.
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
    out_dir.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(LOG_FORMAT)
    file_handler = logging.FileHandler(out_dir / LOG_FILE_NAME, mode="w", encoding="utf-8")
    for handler in (logging.StreamHandler(), file_handler):
        handler.setFormatter(formatter)
        root.addHandler(handler)
    root.setLevel(logging.INFO)


def add_text_log(path: Path) -> logging.Handler:
    """Attach a second file handler that appends every log line to ``path``.

    Used by ``--log-txt``; call ``remove_text_log`` when the run ends so repeated
    in-process calls do not leak the handle. The mode is "a" because
    ``run_report.start_report`` has already written the header into the file.

    Args:
        path: Text file to append to; parent directories are created.

    Returns:
        The handler, to be passed to ``remove_text_log``.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(path, mode="a", encoding="utf-8")
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logging.getLogger().addHandler(handler)
    return handler


def remove_text_log(handler: logging.Handler) -> None:
    """Detach and close a handler made by ``add_text_log``.

    Args:
        handler: Handler to remove.
    """
    logging.getLogger().removeHandler(handler)
    handler.close()


def save_figure(fig: Figure, stem: Path) -> None:
    """Write ``stem.png`` (FIG_DPI) and ``stem.pdf``, creating the parent directory.

    Args:
        fig: Figure built with the OO API (no pyplot).
        stem: Output path without suffix.
    """
    stem.parent.mkdir(parents=True, exist_ok=True)
    # Suffix is appended as a string: Path.with_suffix would clobber dots in names.
    fig.savefig(f"{stem}.png", dpi=FIG_DPI, bbox_inches="tight")
    fig.savefig(f"{stem}.pdf", bbox_inches="tight")
