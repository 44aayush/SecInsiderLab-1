"""Decode bpftool map dumps of the XDP program into display rows (stdlib only; CLAUDE.md 5.5).

Input is the "formatted" (BTF-decoded) dict of each element of `bpftool -j map dump`; the parsers
are tested against real dumps in tests/fixtures/. `saddr`/`daddr` are a little-endian read of the
network-order bytes, so they are turned back into bytes with "little".
"""
from __future__ import annotations

import socket
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from common import MODE_ALL, MODE_DT, MODE_XGB, STAT_NAMES, TIMESTAMP_FMT, V_MALICIOUS, V_NORMAL

NS_PER_S = 1e9
PROTOS = {6: "TCP", 17: "UDP"}
VERDICT_NAMES = {V_NORMAL: "Normal", V_MALICIOUS: "Malicious"}
NO_VERDICT = "n/a"
MODEL_SEP = " · "


@dataclass(frozen=True)
class FlowRow:  # pylint: disable=too-many-instance-attributes  # 9 fields fixed by CLAUDE.md 5.5
    """One classified flow as shown to the user."""

    src_ip: str
    src_port: int
    dst_ip: str
    dst_port: int
    proto: str
    timestamp: str
    result: str
    models: str
    pkts: int


def _ip(value: int) -> str:
    """Convert a bpftool-decoded u32 address to dotted-quad text.

    Args:
        value: Little-endian read of the network-order address bytes.

    Returns:
        Dotted-quad string.
    """
    return socket.inet_ntoa(value.to_bytes(4, "little"))


def _models(mode: int, dt: int, xgb: int) -> str:
    """Describe the per-model verdicts that the active mode produced.

    Args:
        mode: MODE_DT, MODE_XGB or MODE_ALL.
        dt: Decision Tree verdict.
        xgb: XGBoost verdict.

    Returns:
        E.g. "DT: Normal", "XGB: Malicious" or "DT: Normal · XGB: Normal".
    """
    parts = []
    if mode in (MODE_DT, MODE_ALL):
        parts.append(f"DT: {VERDICT_NAMES.get(dt, NO_VERDICT)}")
    if mode in (MODE_XGB, MODE_ALL):
        parts.append(f"XGB: {VERDICT_NAMES.get(xgb, NO_VERDICT)}")
    return MODEL_SEP.join(parts)


def parse_flows(dump: list[dict[str, Any]], mode: int, now_wall: float,
                now_mono_ns: int) -> list[FlowRow]:
    """Turn a `flows` map dump into rows, skipping flows that were never classified.

    Args:
        dump: Parsed `bpftool -j map dump` list.
        mode: Active model mode (MODE_DT, MODE_XGB or MODE_ALL).
        now_wall: Current wall-clock time (time.time()).
        now_mono_ns: Current CLOCK_MONOTONIC in ns (time.monotonic_ns()).

    Returns:
        One FlowRow per classified flow, in dump order.
    """
    rows = []
    for entry in dump:
        key, val = entry["formatted"]["key"], entry["formatted"]["value"]
        if not val["classified_ns"]:
            continue
        wall = now_wall - (now_mono_ns - val["classified_ns"]) / NS_PER_S
        verdict = VERDICT_NAMES.get(val["verdict"], VERDICT_NAMES[V_NORMAL])
        rows.append(FlowRow(
            _ip(key["saddr"]), key["sport"], _ip(key["daddr"]), key["dport"],
            PROTOS.get(key["proto"], str(key["proto"])),
            datetime.fromtimestamp(wall).strftime(TIMESTAMP_FMT), verdict,
            _models(mode, val["dt_verdict"], val["xgb_verdict"]), val["pkts"]))
    return rows


def parse_stats(dump: list[dict[str, Any]]) -> dict[str, int]:
    """Sum the per-CPU values of the `stats` map by counter name.

    Args:
        dump: Parsed `bpftool -j map dump` list.

    Returns:
        Counter name (common.STAT_NAMES) to total over all CPUs.
    """
    out = dict.fromkeys(STAT_NAMES, 0)
    for entry in dump:
        fmt = entry["formatted"]
        out[STAT_NAMES[fmt["key"]]] = sum(v["value"] for v in fmt["values"])
    return out
