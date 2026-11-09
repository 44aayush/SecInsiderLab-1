"""Project-wide constants for Lab 2."""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_CSV = PROJECT_ROOT / "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

RANDOM_STATE = 42
TEST_SIZE = 0.3
K = 20

BENIGN = "BENIGN"
LABELS = [
    "BENIGN",
    "Web Attack - Brute Force",
    "Web Attack - XSS",
    "Web Attack - Sql Injection",
]
LABEL_COL = "Label"
BINARY_COL = "binary_label"
TARGETS = {"binary": BINARY_COL, "multiclass": LABEL_COL}

# chosen in T4.5: highest attack-F1 (0.986), no missed attacks on the test split (recall 1.0), FPR 0.037 %
REALTIME_MODEL = "binary_dt_default"
