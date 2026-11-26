"""Tests for script/replay.py (no kernel: bpf_ctl.prog_run is replaced)."""
from __future__ import annotations

import random
from typing import Any

import pytest

import replay
from common import NEGATIVE_LABEL, POSITIVE_LABEL

HAND = {"Total Fwd Packets": 4, "Total Length of Fwd Packets": 150, "Fwd Packet Length Max": 100,
        "Fwd Packet Length Min": 0, "Fwd Packet Length Mean": 37.5, "act_data_pkt_fwd": 2}
FIN_ACK_FLAGS = 0x11
ETH_IP_TCP = 14 + 20 + 20


def _features(sizes: list[int]) -> dict[str, float]:
    """Compute the six packet features of a payload list.

    Args:
        sizes: Payload sizes.

    Returns:
        A row in the CIC column names.
    """
    return {"Total Fwd Packets": len(sizes), "Total Length of Fwd Packets": sum(sizes),
            "Fwd Packet Length Max": max(sizes), "Fwd Packet Length Min": min(sizes),
            "Fwd Packet Length Mean": sum(sizes) / len(sizes),
            "act_data_pkt_fwd": sum(s > 0 for s in sizes)}


def test_hand_row_is_reproduced_exactly() -> None:
    """The rebuilt payloads give back all six features."""
    sizes = replay.payloads_from_row(HAND)
    assert sizes is not None and _features(sizes) == HAND


@pytest.mark.parametrize("sizes", [[0], [60], [0, 0, 5], [7, 7, 7], [1, 1460, 3, 0, 0, 22, 900],
                                   [0] * 7 + [500], [3, 90, 5, 5, 5, 5, 5, 5, 5]])
def test_roundtrip(sizes: list[int]) -> None:
    """Rows computed from a payload list are rebuilt to the same six features."""
    row = _features(sizes)
    rebuilt = replay.payloads_from_row(row)
    assert rebuilt is not None and _features(rebuilt) == row


@pytest.mark.parametrize("change", [
    {"act_data_pkt_fwd": 4},                                 # min 0 needs an empty packet
    {"Total Length of Fwd Packets": 400},                    # above n * max
    {"Total Length of Fwd Packets": 151},                    # mean no longer matches
    {"Fwd Packet Length Max": 2000, "Total Length of Fwd Packets": 2000},   # above the MTU
    {"Total Fwd Packets": 40}, {"Fwd Packet Length Mean": float("nan")},
    {"Fwd Packet Length Min": 5, "act_data_pkt_fwd": 3}])    # no empty packet allowed
def test_infeasible_rows_return_none(change: dict[str, Any]) -> None:
    """Rows that cannot be rebuilt exactly give None."""
    assert replay.payloads_from_row({**HAND, **change}) is None


def test_missing_column_returns_none() -> None:
    """A row without a feature column gives None."""
    assert replay.payloads_from_row({"Total Fwd Packets": 3}) is None


class Frame:  # pylint: disable=too-few-public-methods  # stands in for a DataFrame
    """Minimal to_dict("records") provider."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        """Keep the rows."""
        self.rows = rows

    def to_dict(self, _orient: str) -> list[dict[str, Any]]:
        """Return the rows."""
        return self.rows


def test_build_pool_caps_and_skips() -> None:
    """At most per_class entries per label, infeasible rows skipped."""
    rows = [_features([i, 0, i]) for i in range(1, 30)] + [{**HAND, "act_data_pkt_fwd": 4}]
    pool = replay.build_pool(Frame(rows * 2), [0] * 30 + [1] * 30, per_class=5)
    labels = [f["label"] for f in pool]
    assert labels.count(NEGATIVE_LABEL) == 5 == labels.count(POSITIVE_LABEL)
    assert all(_features(f["payloads"])["Total Fwd Packets"] == len(f["payloads"]) for f in pool)


def _pool(per_class: int = 30) -> list[dict[str, Any]]:
    """Build a pool of distinct flows.

    Args:
        per_class: Entries per label.

    Returns:
        The pool.
    """
    return [{"label": lab, "payloads": [i, 0, i + 1]}
            for lab in (NEGATIVE_LABEL, POSITIVE_LABEL) for i in range(per_class)]


@pytest.mark.parametrize("n", [0, 1, 4, 20, 21, 100])
def test_sample_balanced_and_distinct(n: int) -> None:
    """Half of each class (odd n: one extra), no entry twice."""
    out = replay.sample(_pool(60), n, random.Random(1))
    counts = [sum(f["label"] == lab for f in out) for lab in (NEGATIVE_LABEL, POSITIVE_LABEL)]
    assert len(out) == n and abs(counts[0] - counts[1]) == n % 2
    assert len({id(f) for f in out}) == n


def test_sample_is_random_and_mixed() -> None:
    """Two seeds give different orders; the output is not sorted by class."""
    a, b = (replay.sample(_pool(), 20, random.Random(s)) for s in (1, 2))
    assert a != b
    assert [f["label"] for f in a] != sorted(f["label"] for f in a)


def test_sample_short_class() -> None:
    """A class with too few entries gives what it has."""
    pool = _pool(3)
    assert len(replay.sample(pool, 20, random.Random(0))) == 6


def test_schedule_times_in_window_and_each_flow_once() -> None:
    """Times lie in [0, 0.8 x timespan); every flow comes out exactly once, in time order."""
    now, flows = [100.0], _pool(10)
    sched = replay.Schedule(flows, 50, random.Random(5), lambda: now[0])
    assert len(sched.times) == len(flows) and sched.times == sorted(sched.times)
    assert all(0 <= t < 0.8 * 50 for t in sched.times)
    got: list[Any] = []
    for step in range(0, 61, 5):
        now[0] = 100.0 + step
        got += sched.due()
    assert sorted(map(id, got)) == sorted(map(id, flows))
    assert sched.due() == []


def test_schedule_due_per_tick() -> None:
    """Each tick returns exactly the flows with time <= elapsed that were not yet returned."""
    now = [100.0]
    sched = replay.Schedule(_pool(10), 100, random.Random(6), lambda: now[0])
    done = 0
    for elapsed in (0, 10, 40, 79.9, 200):
        now[0] = 100.0 + elapsed
        due = sched.due()
        assert len(due) == sum(t <= elapsed for t in sched.times) - done
        done += len(due)
    assert done == 20


def test_run_keeps_sources_unique_across_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """A shared `used` set keeps sources unique over several calls."""
    monkeypatch.setattr(replay.bpf_ctl, "prog_run", lambda *_a: [2])
    used: set[int] = set()
    rng = random.Random(1)
    out = [e["src_ip"] for _ in range(5) for e in replay.run("/p", _pool(2)[:4], rng, used)]
    assert len(set(out)) == len(out) == 20


def test_frames_flags_and_sizes() -> None:
    """One frame per packet, payload sizes kept, FIN|ACK only on the last."""
    out = replay.frames({"label": "DDoS", "payloads": [0, 100, 5]}, "10.99.1.2", 4000)
    assert [len(f) - ETH_IP_TCP for f in out] == [0, 100, 5]
    assert [f[ETH_IP_TCP - 20 + 13] for f in out][-1] == FIN_ACK_FLAGS
    assert all(f[ETH_IP_TCP - 20 + 13] != FIN_ACK_FLAGS for f in out[:-1])


def test_run_unique_sources_in_10_99(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every flow gets its own 10.99.x.y source; all frames go to xdp_ids."""
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(replay.bpf_ctl, "prog_run",
                        lambda prog, pin, _data, repeat=1: calls.append((prog, pin)) or (2, 1))
    flows = replay.sample(_pool(), 40, random.Random(3))
    out = replay.run("/pin", flows, random.Random(4))
    assert len({r["src_ip"] for r in out}) == 40
    assert all(r["src_ip"].startswith("10.99.") for r in out)
    assert all(len(r["retvals"]) == 3 for r in out)
    assert set(calls) == {("xdp_ids", "/pin")} and len(calls) == 120
