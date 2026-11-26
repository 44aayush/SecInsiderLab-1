"""Replay CIC-IDS2017 test-split flows through the pinned xdp_ids program (CLAUDE.md D8).

Stdlib only. A flow is rebuilt from its six forward packet features as TCP packets from a random
10.99.x.y source; bpftool prog run feeds them to the real flowmeter, model and blocklist.
Inter-arrival times are not reproduced. A flow with more than 8 packets is also classified at its
8th packet by the kernel (CLAUDE.md O5), so its final verdict can come from that earlier point.
"""
from __future__ import annotations

import json
import math
import random
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import bpf_ctl
import pktbuild
from common import (EPHEMERAL_PORTS, NEGATIVE_LABEL, POSITIVE_LABEL, REPLAY_DST_IP,
                    REPLAY_DST_PORT, REPLAY_MAX_PAYLOAD, REPLAY_MAX_PKTS, REPLAY_PER_CLASS,
                    REPLAY_POOL_PATH, REPLAY_SRC_PREFIX, SEED)

PKTS, TOTAL, MAX, MIN, MEAN, ACT = ("Total Fwd Packets", "Total Length of Fwd Packets",
                                    "Fwd Packet Length Max", "Fwd Packet Length Min",
                                    "Fwd Packet Length Mean", "act_data_pkt_fwd")
MEAN_SCALE = 1000  # kernel unit of the mean (milli-bytes)
HOST_BITS = 16
SPREAD = 0.8  # flows are due within the first 80 % of the capture, so late ones still show
Flow = dict[str, Any]


def _whole(value: Any) -> int:
    """Convert an integral float or int to int.

    Args:
        value: A CSV cell.

    Returns:
        The integer value.

    Raises:
        ValueError: If the value is NaN, infinite or has a fraction.
    """
    number = float(value)
    if not number.is_integer():
        raise ValueError(f"not a whole number: {value!r}")
    return int(number)


def _build(n: int, total: int, hi: int, lo: int, act: int) -> list[int] | None:
    """Construct payload sizes with the given count, sum, max, min and non-empty count.

    Args:
        n: Packet count.
        total: Payload sum.
        hi: Largest payload.
        lo: Smallest payload.
        act: Packets with payload > 0.

    Returns:
        The sizes, or None when no list fits (the caller re-checks the result).
    """
    if n == 1 or hi == lo:
        return [hi] * n
    free, floor, zeros = n - 2, lo, 0  # free = slots between lo and hi that absorb the rest
    if lo == 0:
        zeros = n - act - 1  # one zero is the min itself
        free = n - 2 - zeros
        floor = 1
    rest = total - hi - lo
    if zeros < 0 or free < 0 or not free * floor <= rest <= free * hi:
        return None
    sizes = [floor] * free
    extra = rest - free * floor
    for i in range(free):
        add = min(extra, hi - floor)
        sizes[i] += add
        extra -= add
    return [hi, lo] + [0] * zeros + sizes


def payloads_from_row(row: dict[str, Any], max_pkts: int = REPLAY_MAX_PKTS) -> list[int] | None:
    """Rebuild forward payload sizes that reproduce the six packet features exactly.

    Args:
        row: Mapping with the kernel feature columns (CIC names).
        max_pkts: Largest packet count to accept.

    Returns:
        One payload size per packet, or None when the row is not exactly rebuildable (too many
        packets, payload above the MTU, infeasible counts, or a mean that does not match).
    """
    try:
        n, total, hi, lo, act = (_whole(row[c]) for c in (PKTS, TOTAL, MAX, MIN, ACT))
        mean = math.floor(float(row[MEAN]) * MEAN_SCALE)
    except (KeyError, TypeError, ValueError, OverflowError):
        return None
    if not (1 <= n <= max_pkts and 0 <= lo <= hi <= REPLAY_MAX_PAYLOAD and 0 <= act <= n):
        return None
    if total * MEAN_SCALE // n != mean:
        return None
    sizes = _build(n, total, hi, lo, act)
    ok = sizes is not None and (len(sizes), sum(sizes), max(sizes), min(sizes),
                                sum(s > 0 for s in sizes)) == (n, total, hi, lo, act)
    return sizes if ok else None


def build_pool(df: Any, y: Any, per_class: int = REPLAY_PER_CLASS,
               max_pkts: int = REPLAY_MAX_PKTS) -> list[Flow]:
    """Pick rebuildable rows of each class (a seeded shuffle, so the file is reproducible).

    Args:
        df: Frame with the kernel feature columns (anything with to_dict("records")).
        y: Labels aligned with df (0 = BENIGN, 1 = DDoS).
        per_class: Maximum entries per class.
        max_pkts: Largest packet count to accept.

    Returns:
        Entries {"label": "BENIGN" | "DDoS", "payloads": [...]}.
    """
    names = {0: NEGATIVE_LABEL, 1: POSITIVE_LABEL}
    items = list(zip(df.to_dict("records"), (int(v) for v in y)))
    random.Random(SEED).shuffle(items)
    pool: list[Flow] = []
    taken = dict.fromkeys(names, 0)
    for row, label in items:
        if taken[label] >= per_class:
            continue
        sizes = payloads_from_row(row, max_pkts)
        if sizes is not None:
            taken[label] += 1
            pool.append({"label": names[label], "payloads": sizes})
    return pool


def load_pool(path: Path = REPLAY_POOL_PATH) -> list[Flow]:
    """Read the pool written by train.py.

    Args:
        path: Pool JSON file.

    Returns:
        The entries.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def sample(pool: list[Flow], n: int, rng: random.Random) -> list[Flow]:
    """Draw n/2 flows of each class (an odd n adds one of a random class), shuffled.

    Args:
        pool: Entries of both classes.
        n: Number of flows.
        rng: Random source.

    Returns:
        Distinct pool entries; fewer when a class has too few.
    """
    want = {NEGATIVE_LABEL: n // 2, POSITIVE_LABEL: n // 2}
    if n % 2:
        want[rng.choice(sorted(want))] += 1
    picked = []
    for label, count in want.items():
        members = [f for f in pool if f["label"] == label]
        picked += rng.sample(members, min(count, len(members)))
    rng.shuffle(picked)
    return picked


def pick(n: int) -> list[Flow]:
    """Draw n flows from the stored pool with fresh randomness (no fixed seed).

    Args:
        n: Number of flows.

    Returns:
        The sampled flows.
    """
    return sample(load_pool(), n, random.Random())


def frames(flow: Flow, src_ip: str, sport: int) -> list[bytes]:
    """Build the frames of one flow; the last packet carries FIN|ACK.

    Args:
        flow: Pool entry.
        src_ip: Source address.
        sport: Source port.

    Returns:
        One Ethernet/IPv4/TCP frame per forward packet.
    """
    sizes, out = flow["payloads"], []
    for i, size in enumerate(sizes):
        if i == len(sizes) - 1:
            flags = pktbuild.FIN | pktbuild.ACK
        else:
            flags = pktbuild.ACK | (pktbuild.PSH if size else 0)
        out.append(pktbuild.tcp(src_ip, REPLAY_DST_IP, sport, REPLAY_DST_PORT, flags, size))
    return out


class Schedule:  # pylint: disable=too-few-public-methods  # one query method is the whole API
    """Random due times for flows, uniform in [0, SPREAD x timespan); rows interleave with live."""

    def __init__(self, flows: list[Flow], timespan: float, rng: random.Random,
                 clock: Callable[[], float] = time.monotonic) -> None:
        """Draw one due time per flow; the clock starts now.

        Args:
            flows: Flows to inject (random order comes from the random times).
            timespan: Capture length in seconds.
            rng: Random source.
            clock: Monotonic seconds (replaceable in tests).
        """
        self._clock, self._t0 = clock, clock()
        self.times = sorted(rng.uniform(0, SPREAD * timespan) for _ in flows)
        self._items = list(zip(self.times, rng.sample(flows, len(flows))))

    def due(self) -> list[Flow]:
        """Pop the flows whose time has come.

        Returns:
            Flows due now, each returned exactly once over the schedule's life.
        """
        elapsed = self._clock() - self._t0
        ready = [f for t, f in self._items if t <= elapsed]
        self._items = self._items[len(ready):]
        return ready


def run(pin: str, flows: list[Flow], rng: random.Random,
        used: set[int] | None = None) -> list[dict[str, Any]]:
    """Send every flow through the pinned xdp_ids from its own random 10.99.x.y source.

    Args:
        pin: Pin root of the loaded program.
        flows: Pool entries.
        rng: Random source for addresses and ports.
        used: Hosts already taken by earlier calls (updated), so sources stay unique.

    Returns:
        Ground truth {src_ip, sport, label, retvals} per flow (XDP action per packet).
    """
    used = set() if used is None else used
    hosts = rng.sample(sorted(set(range(1, (1 << HOST_BITS) - 1)) - used), len(flows))
    used.update(hosts)
    out = []
    for flow, host in zip(flows, hosts):
        ip = f"{REPLAY_SRC_PREFIX}.{host >> 8}.{host & 0xFF}"
        sport = rng.randint(*EPHEMERAL_PORTS)
        retvals = [bpf_ctl.prog_run("xdp_ids", pin, f)[0] for f in frames(flow, ip, sport)]
        out.append({"src_ip": ip, "sport": sport, "label": flow["label"], "retvals": retvals})
    return out
