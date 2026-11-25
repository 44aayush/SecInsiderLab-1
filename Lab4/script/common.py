"""Shared constants and logging setup for Lab 4 (stdlib only; host and IDS image).

Mirrors the C contract of ``xdp/lab4_common.h`` (CLAUDE.md 5.3); ``tests/test_consistency.py``
compares the two. Constants and logging follow ``../Lab3/script/common.py`` (copied and adapted).
"""
from __future__ import annotations

import logging
from pathlib import Path

# common.py lives in Lab4/script/, so the Lab 4 root is one level up.
LAB4_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CSV = LAB4_DIR / "Friday-WorkingHours-Afternoon-DDos.csv"
DEFAULT_OUT = LAB4_DIR / "outputs"
MODELS_DIR = LAB4_DIR / "models"
KERNEL_MODEL_PATH = MODELS_DIR / "kernel_model.json"
TEST_VECTORS_PATH = MODELS_DIR / "test_vectors.json"
BPF_OBJ = LAB4_DIR / "xdp" / "lab4_xdp.bpf.o"

SEED = 42
TRAIN_FRAC, VAL_FRAC, TEST_FRAC = 0.70, 0.15, 0.15
NEGATIVE_LABEL, POSITIVE_LABEL = "BENIGN", "DDoS"  # encoded 0 / 1
# Read at call time by preprocess.clean so tests can monkeypatch it.
DROP_DUPLICATES = True
IDENTICAL_ATOL = 1e-6

# Kernel features: (CIC column, scale s); index order is the contract (CLAUDE.md 5.1).
KERNEL_FEATURES: tuple[tuple[str, int], ...] = (
    ("Total Fwd Packets", 1),
    ("Total Length of Fwd Packets", 1),
    ("Fwd Packet Length Max", 1),
    ("Fwd Packet Length Min", 1),
    ("Fwd Packet Length Mean", 1000),
    ("Fwd IAT Total", 1000),
    ("Fwd IAT Mean", 1000),
    ("Fwd IAT Max", 1000),
    ("Fwd IAT Min", 1000),
    ("act_data_pkt_fwd", 1),
)

# Mirrors of xdp/lab4_common.h (CLAUDE.md 5.3).
N_FEATURES = 10
MAX_NODES = 8192
MAX_TREES = 64  # roots[0] = DT, roots[1..n] = XGB trees
MAX_TREE_DEPTH = 10  # walk bound = MAX_TREE_DEPTH + 1 steps
LEAF_SHIFT = 16
CLASSIFY_MIN_PKTS = 8
MAX_FLOWS = 65536
MAX_BLOCKED = 65536
N_TEST_VECS = 1024
MODE_OFF, MODE_DT, MODE_XGB, MODE_ALL = 0, 1, 2, 3
V_NORMAL, V_MALICIOUS, V_NONE = 0, 1, 255
STAT_NAMES: tuple[str, ...] = ("ST_PKTS", "ST_PASS", "ST_DROP", "ST_FLOWS_CLASSIFIED",
                               "ST_FLOWS_MALICIOUS", "ST_BLOCKS_ADDED", "ST_NOT_TRACKED")
N_STATS = len(STAT_NAMES)
MODEL_MODES = {"DT": MODE_DT, "XGB": MODE_XGB, "ALL": MODE_ALL}

# Model selection (CLAUDE.md 4.4, O4, D6).
DT_DEPTHS = (6, 8, 10)
XGB_TREES = 20
XGB_DEPTHS = (4, 5, 6)
XGB_LR = 0.1
DEPTH_F1_TOL = 0.0005

# Runtime.
PIN_DIR = "/sys/fs/bpf/lab4"
MGMT_IFACE = "mgmt0"
DEFAULT_IFACE = "ext0"
DEFAULT_TIMESPAN_S = 30
MAX_TIMESPAN_S = 3600
DEFAULT_BLOCK_S = 60
POLL_INTERVAL_S = 1.0
TIMESTAMP_FMT = "%d-%m-%Y %I:%M:%S %p"

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
LOG_FILE_NAME = "run.log"


def setup_logging(out_dir: Path) -> None:
    """Log to the console and to ``out_dir/run.log``; safe to call repeatedly.

    Args:
        out_dir: Output root; created if missing. run.log is overwritten (mode "w").
    """
    root = logging.getLogger()
    # Close old handlers first, otherwise a second call would duplicate every line.
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
