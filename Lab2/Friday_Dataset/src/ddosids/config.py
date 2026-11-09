"""Project-wide constants for the Friday DDoS sub-project."""
from __future__ import annotations

from pathlib import Path

FRIDAY_ROOT = Path(__file__).resolve().parents[2]
DATA_CSV = FRIDAY_ROOT / "Friday-WorkingHours-Afternoon-DDos.csv"
ARTIFACTS_DIR = FRIDAY_ROOT / "artifacts"
OUTPUTS_DIR = FRIDAY_ROOT / "outputs"

RANDOM_STATE = 42
TEST_SIZE = 0.3
K = 20

BENIGN = "BENIGN"
ATTACK_NAME = "DDoS"
LABELS = [BENIGN, ATTACK_NAME]
LABEL_COL = "Label"
BINARY_COL = "binary_label"
TARGETS = {"binary": BINARY_COL}

# chosen in F2.V: DDoS-F1 0.9996 (ties dt_balanced), recall 0.9993, 7 FP of 28,521 BENIGN test flows (FPR 0.025 %); LR has ~2,000 FP
REALTIME_MODEL = "binary_dt_default"
