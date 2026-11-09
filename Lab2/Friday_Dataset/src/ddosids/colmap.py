"""Column mapping between CICFlowMeter V4 output and the ISCX training names."""
from __future__ import annotations

import re

import pandas as pd

ISCX_FEATURES: list[str] = [
    "Destination Port",
    "Flow Duration",
    "Total Fwd Packets",
    "Total Backward Packets",
    "Total Length of Fwd Packets",
    "Total Length of Bwd Packets",
    "Fwd Packet Length Max",
    "Fwd Packet Length Min",
    "Fwd Packet Length Mean",
    "Fwd Packet Length Std",
    "Bwd Packet Length Max",
    "Bwd Packet Length Min",
    "Bwd Packet Length Mean",
    "Bwd Packet Length Std",
    "Flow Bytes/s",
    "Flow Packets/s",
    "Flow IAT Mean",
    "Flow IAT Std",
    "Flow IAT Max",
    "Flow IAT Min",
    "Fwd IAT Total",
    "Fwd IAT Mean",
    "Fwd IAT Std",
    "Fwd IAT Max",
    "Fwd IAT Min",
    "Bwd IAT Total",
    "Bwd IAT Mean",
    "Bwd IAT Std",
    "Bwd IAT Max",
    "Bwd IAT Min",
    "Fwd PSH Flags",
    "Bwd PSH Flags",
    "Fwd URG Flags",
    "Bwd URG Flags",
    "Fwd Header Length",
    "Bwd Header Length",
    "Fwd Packets/s",
    "Bwd Packets/s",
    "Min Packet Length",
    "Max Packet Length",
    "Packet Length Mean",
    "Packet Length Std",
    "Packet Length Variance",
    "FIN Flag Count",
    "SYN Flag Count",
    "RST Flag Count",
    "PSH Flag Count",
    "ACK Flag Count",
    "URG Flag Count",
    "CWE Flag Count",
    "ECE Flag Count",
    "Down/Up Ratio",
    "Average Packet Size",
    "Avg Fwd Segment Size",
    "Avg Bwd Segment Size",
    "Fwd Avg Bytes/Bulk",
    "Fwd Avg Packets/Bulk",
    "Fwd Avg Bulk Rate",
    "Bwd Avg Bytes/Bulk",
    "Bwd Avg Packets/Bulk",
    "Bwd Avg Bulk Rate",
    "Subflow Fwd Packets",
    "Subflow Fwd Bytes",
    "Subflow Bwd Packets",
    "Subflow Bwd Bytes",
    "Init_Win_bytes_forward",
    "Init_Win_bytes_backward",
    "act_data_pkt_fwd",
    "min_seg_size_forward",
    "Active Mean",
    "Active Std",
    "Active Max",
    "Active Min",
    "Idle Mean",
    "Idle Std",
    "Idle Max",
    "Idle Min",
]

META_COLS: list[str] = ["Flow ID", "Src IP", "Src Port", "Dst IP", "Protocol", "Timestamp"]

# ISCX name -> CICFlowMeter V4 name (names that differ after normalization)
OVERRIDES: dict[str, str] = {
    "Destination Port": "Dst Port",
    "Total Fwd Packets": "Total Fwd Packet",
    "Total Backward Packets": "Total Bwd packets",
    "Total Length of Fwd Packets": "Total Length of Fwd Packet",
    "Total Length of Bwd Packets": "Total Length of Bwd Packet",
    "Min Packet Length": "Packet Length Min",
    "Max Packet Length": "Packet Length Max",
    "CWE Flag Count": "CWR Flag Count",
    "Avg Fwd Segment Size": "Fwd Segment Size Avg",
    "Avg Bwd Segment Size": "Bwd Segment Size Avg",
    "Fwd Avg Bytes/Bulk": "Fwd Bytes/Bulk Avg",
    "Fwd Avg Packets/Bulk": "Fwd Packet/Bulk Avg",
    "Fwd Avg Bulk Rate": "Fwd Bulk Rate Avg",
    "Bwd Avg Bytes/Bulk": "Bwd Bytes/Bulk Avg",
    "Bwd Avg Packets/Bulk": "Bwd Packet/Bulk Avg",
    "Bwd Avg Bulk Rate": "Bwd Bulk Rate Avg",
    "Init_Win_bytes_forward": "FWD Init Win Bytes",
    "Init_Win_bytes_backward": "Bwd Init Win Bytes",
    "act_data_pkt_fwd": "Fwd Act Data Pkts",
    "min_seg_size_forward": "Fwd Seg Size Min",
}

def normalize(name: str) -> str:
    """Lowercase and strip everything except [a-z0-9]."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


# ISCX name -> V4 name: explicit override, else the same name (verified against the V4 header in tests).
ISCX_TO_V4: dict[str, str] = {f: OVERRIDES.get(f, f) for f in ISCX_FEATURES}
V4_TO_ISCX: dict[str, str] = {v: k for k, v in ISCX_TO_V4.items()}
assert len(V4_TO_ISCX) == len(ISCX_TO_V4) == len(ISCX_FEATURES) == 77, "mapping is not one-to-one"
_NORM_TO_ISCX: dict[str, str] = {normalize(k): k for k in ISCX_TO_V4}
assert len(_NORM_TO_ISCX) == 77, "normalized ISCX names collide"


def map_v4_to_iscx(df: pd.DataFrame) -> pd.DataFrame:
    """Rename V4 feature columns to ISCX names (explicit table, then normalized match).

    Meta columns and any unknown columns are kept unchanged.
    """
    ren: dict[str, str] = {}
    for c in df.columns:
        if c in META_COLS:
            continue
        tgt = V4_TO_ISCX.get(c) or _NORM_TO_ISCX.get(normalize(c))
        if tgt is not None and tgt not in ren.values():
            ren[c] = tgt
    return df.rename(columns=ren)
