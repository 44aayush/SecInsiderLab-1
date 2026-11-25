"""flowview parsers against real bpftool dumps captured by test_kernel.py (stdlib only)."""
from __future__ import annotations

import copy
import json
from datetime import datetime
from typing import Any

import flowview
from common import MODE_ALL, MODE_DT, MODE_XGB, STAT_NAMES, TIMESTAMP_FMT
from conftest import FIXTURES

NOW_WALL, AGE_S = 1_700_000_000.0, 5


def _load(name: str) -> list[dict[str, Any]]:
    """Read a captured dump from tests/fixtures.

    Args:
        name: File name.

    Returns:
        The parsed JSON list.
    """
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _rows(name: str, mode: int) -> list[flowview.FlowRow]:
    """Parse a fixture dump taken AGE_S seconds after its flows were classified.

    Args:
        name: Fixture file name.
        mode: Model mode.

    Returns:
        The rows.
    """
    dump = _load(name)
    mono = max(e["formatted"]["value"]["classified_ns"] for e in dump) + AGE_S * 10**9
    return flowview.parse_flows(dump, mode, NOW_WALL, mono)


def test_normal_flow_fields() -> None:
    """The real Normal dump gives dotted IPs, ports, protocol and Normal."""
    row = _rows("flows_dump.json", MODE_DT)[0]
    assert (row.src_ip, row.src_port) == ("10.0.0.2", 40000)
    assert (row.dst_ip, row.dst_port) == ("10.0.0.1", 80)
    assert (row.proto, row.result, row.pkts) == ("TCP", "Normal", 4)


def test_timestamp_format_and_age() -> None:
    """The timestamp matches TIMESTAMP_FMT and is AGE_S before 'now'."""
    row = _rows("flows_dump.json", MODE_DT)[0]
    parsed = datetime.strptime(row.timestamp, TIMESTAMP_FMT)
    assert parsed == datetime.fromtimestamp(NOW_WALL - AGE_S).replace(microsecond=0)


def test_models_strings_per_mode() -> None:
    """Each mode names only the models it ran."""
    assert _rows("flows_dump.json", MODE_DT)[0].models == "DT: Normal"
    mal = {r.src_ip: r for r in _rows("flows_dump_malicious.json", MODE_ALL)}["10.0.0.3"]
    assert (mal.result, mal.models) == ("Malicious", "DT: Malicious · XGB: Malicious")
    xgb = {r.src_ip: r for r in _rows("flows_dump_malicious.json", MODE_XGB)}["10.0.0.3"]
    assert xgb.models == "XGB: Malicious"
    assert _rows("flows_dump.json", MODE_ALL)[0].models == "DT: Normal · XGB: n/a"


def test_normal_all_mode_string() -> None:
    """An ALL flow with both Normal verdicts reads 'DT: Normal · XGB: Normal'."""
    dump = copy.deepcopy(_load("flows_dump.json"))
    dump[0]["formatted"]["value"]["xgb_verdict"] = 0
    row = flowview.parse_flows(dump, MODE_ALL, NOW_WALL, 10**13)[0]
    assert row.models == "DT: Normal · XGB: Normal"


def test_unclassified_flows_excluded() -> None:
    """A flow with classified_ns == 0 yields no row."""
    dump = copy.deepcopy(_load("flows_dump.json"))
    dump[0]["formatted"]["value"]["classified_ns"] = 0
    assert not flowview.parse_flows(dump, MODE_DT, NOW_WALL, 10**13)


def test_parse_stats_sums_cpus() -> None:
    """Per-CPU values are summed and named; the fixture has 2 packets on cpu 0 and 2 on cpu 3."""
    stats = flowview.parse_stats(_load("stats_dump.json"))
    assert list(stats) == list(STAT_NAMES)
    assert (stats["ST_PKTS"], stats["ST_PASS"], stats["ST_DROP"]) == (4, 4, 0)
    assert stats["ST_FLOWS_CLASSIFIED"] == 1
