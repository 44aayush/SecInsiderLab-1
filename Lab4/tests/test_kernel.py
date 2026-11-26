"""Kernel tests: load the BPF object and drive it with BPF_PROG_TEST_RUN (stdlib only, root).

Run inside the IDS image (CLAUDE.md 7): `python3 -m pytest tests/test_kernel.py -m kernel`.
bpftool JSON: every map element carries a "formatted" dict with the BTF-decoded key and value.
"""
from __future__ import annotations

import json
import random
import socket
import struct
import time
import uuid
from typing import Any, Iterator

import pytest

import bpf_ctl
import kmodel
import pktbuild
import replay
from common import (BPF_OBJ, KERNEL_MODEL_PATH, LAB4_DIR, MODE_ALL, MODE_DT, MODE_XGB, N_FEATURES,
                    N_TEST_VECS, REPLAY_POOL_PATH, STAT_NAMES, TEST_VECTORS_PATH)
from conftest import FIXTURES

pytestmark = pytest.mark.kernel

PASS, DROP = 2, 1  # XDP_PASS, XDP_DROP
SRC, SRC2, DST = "10.0.0.2", "10.0.0.3", "10.0.0.1"
SPORT, DPORT = 40000, 80
BLOCK_NS = 60 * 10**9
VECTORS_PATH = TEST_VECTORS_PATH
EVIDENCE_DIR = LAB4_DIR / "outputs" / "kernel"
TIMING_REPEAT = 100_000
NS_PER_MS = 1_000_000
EXPIRY_SLEEP_S = 0.05
UDP_PKTS_BELOW, UDP_PAYLOAD = 7, 10
MID_PAYLOAD, FIN_FLAGS = 100, pktbuild.FIN | pktbuild.ACK
LEAF_ONE = 1 << 16
SHORT_FRAME, DUMMY_FRAME = 20, bytes(64)
NORMAL = {"nodes": [[-1, 0, 0, 0, 0]], "dt_root": 0, "xgb_roots": [0], "xgb_base_margin": 0}
# DT says Malicious, XGB margin is negative: ALL must not drop.
SPLIT = {"nodes": [[-1, 0, 0, 0, 1], [-1, 0, 0, 0, -LEAF_ONE]], "dt_root": 0, "xgb_roots": [1],
         "xgb_base_margin": 0}


def _ip_key(ip: str) -> int:
    """Return an address as bpftool prints the u32 key (network-order bytes read little-endian)."""
    return int.from_bytes(socket.inet_aton(ip), "little")


def _send(pin: str, frame: bytes, repeat: int = 1) -> int:
    """Run xdp_ids on one frame and return its XDP action."""
    return bpf_ctl.prog_run("xdp_ids", pin, frame, repeat)[0]


def _configure(pin: str, model: dict[str, Any], mode: int, block_ns: int = BLOCK_NS) -> None:
    """Write the model into the maps and set the mode (config is a single batch)."""
    bpf_ctl.batch(kmodel.batch_lines(model, pin) + [kmodel.config_line(mode, model, block_ns, pin)])


def _stats(pin: str) -> dict[str, int]:
    """Return the per-CPU stats summed over CPUs, by name."""
    out = dict.fromkeys(STAT_NAMES, 0)
    for entry in bpf_ctl.dump("stats", pin):
        fmt = entry["formatted"]
        out[STAT_NAMES[fmt["key"]]] = sum(v["value"] for v in fmt["values"])
    return out


def _flows(pin: str) -> list[dict[str, Any]]:
    """Return the decoded values of the flow map."""
    return [e["formatted"]["value"] for e in bpf_ctl.dump("flows", pin)]


def _blocked(pin: str) -> list[int]:
    """Return the blocked source keys."""
    return [e["formatted"]["key"] for e in bpf_ctl.dump("blocklist", pin)]


def _fin_flow(pin: str, src: str = SRC) -> list[int]:
    """Send SYN, PSH/ACK (100 B), ACK (50 B), FIN/ACK and return the four actions."""
    steps = [(pktbuild.SYN, 0), (pktbuild.PSH | pktbuild.ACK, MID_PAYLOAD), (pktbuild.ACK, 50),
             (FIN_FLAGS, 0)]
    return [_send(pin, pktbuild.tcp(src, DST, SPORT, DPORT, f, n)) for f, n in steps]


@pytest.fixture(name="pin")
def _pin() -> Iterator[str]:
    """Load the BPF object into a fresh pin dir and unpin it afterwards."""
    path = f"/sys/fs/bpf/lab4_test_{uuid.uuid4().hex[:8]}"
    bpf_ctl.load(BPF_OBJ, path)
    yield path
    bpf_ctl.unpin(path)


def test_flowmeter_tcp_fin(pin: str) -> None:
    """A SYN, data, ACK, FIN flow yields the right counters and one Normal verdict."""
    _configure(pin, NORMAL, MODE_DT)
    assert _fin_flow(pin) == [PASS] * 4
    (flow,) = _flows(pin)
    assert (flow["pkts"], flow["bytes"], flow["len_max"], flow["len_min"]) == (4, 150, 100, 0)
    assert flow["act_data_pkts"] == 2
    assert 0 <= flow["iat_min_ns"] <= flow["iat_max_ns"] <= flow["last_ns"] - flow["first_ns"]
    assert flow["classified_ns"] > 0 and flow["verdict"] == 0


def test_classify_trigger(pin: str) -> None:
    """A UDP flow without FIN is classified at its 8th packet, not before."""
    _configure(pin, NORMAL, MODE_DT)
    frame = pktbuild.udp(SRC, DST, SPORT, DPORT, UDP_PAYLOAD)
    for _ in range(UDP_PKTS_BELOW):
        _send(pin, frame)
    assert _flows(pin)[0]["classified_ns"] == 0
    _send(pin, frame)
    assert _flows(pin)[0]["classified_ns"] > 0


def test_filter_blocks_after_malicious(pin: str) -> None:
    """A Malicious verdict drops the classifying packet and blocks the source only."""
    _configure(pin, kmodel.load(FIXTURES / "always_malicious.json"), MODE_DT)
    assert _fin_flow(pin)[-1] == DROP
    assert _blocked(pin) == [_ip_key(SRC)]
    assert _send(pin, pktbuild.tcp(SRC, DST, SPORT, DPORT, pktbuild.ACK)) == DROP
    assert _send(pin, pktbuild.tcp(SRC2, DST, SPORT, DPORT, pktbuild.ACK)) == PASS
    stats = _stats(pin)
    assert (stats["ST_DROP"], stats["ST_BLOCKS_ADDED"]) == (2, 1)


def test_block_expiry(pin: str) -> None:
    """After the block time the source passes again and its entry is removed."""
    _configure(pin, kmodel.load(FIXTURES / "always_malicious.json"), MODE_DT, NS_PER_MS)
    assert _fin_flow(pin)[-1] == DROP
    time.sleep(EXPIRY_SLEEP_S)
    assert _send(pin, pktbuild.tcp(SRC, DST, SPORT, DPORT, pktbuild.ACK)) == PASS
    assert not _blocked(pin)


def test_mode_all_requires_both(pin: str) -> None:
    """ALL needs both models to agree; DT alone blocks on the same model."""
    _configure(pin, SPLIT, MODE_ALL)
    assert _fin_flow(pin)[-1] == PASS
    (flow,) = _flows(pin)
    assert (flow["dt_verdict"], flow["xgb_verdict"], flow["verdict"]) == (1, 0, 0)
    assert not _blocked(pin)
    _configure(pin, SPLIT, MODE_DT)
    assert _fin_flow(pin, SRC2)[-1] == DROP
    assert _blocked(pin) == [_ip_key(SRC2)]


def test_mode_off(pin: str) -> None:
    """With the all-zero config nothing is classified."""
    assert _fin_flow(pin)[-1] == PASS
    assert _flows(pin)[0]["classified_ns"] == 0


NOT_TRACKED = {
    "arp": pktbuild.arp(),
    "ipv6": pktbuild.ipv6(),
    "icmp": pktbuild.icmp(SRC, DST),
    "fragment": pktbuild.tcp(SRC, DST, SPORT, DPORT, pktbuild.ACK, frag=pktbuild.MF),
    "short": pktbuild.truncated(pktbuild.tcp(SRC, DST, SPORT, DPORT, pktbuild.ACK), SHORT_FRAME),
    "ihl4": pktbuild.tcp(SRC, DST, SPORT, DPORT, pktbuild.ACK, ihl=4),
    "doff4": pktbuild.tcp(SRC, DST, SPORT, DPORT, pktbuild.ACK, doff=4),
    "vlan": pktbuild.vlan(pktbuild.ipv4(SRC, DST, pktbuild.PROTO_TCP,
                                    pktbuild.tcp_segment(SPORT, DPORT, pktbuild.ACK))),
}


@pytest.mark.parametrize("frame", NOT_TRACKED.values(), ids=NOT_TRACKED.keys())
def test_not_tracked_pass(pin: str, frame: bytes) -> None:
    """Unsupported or malformed frames pass, create no flow and are counted."""
    _configure(pin, kmodel.load(FIXTURES / "always_malicious.json"), MODE_ALL)
    assert _send(pin, frame) == PASS
    assert not _flows(pin)
    assert _stats(pin)["ST_NOT_TRACKED"] == 1


@pytest.mark.skipif(not VECTORS_PATH.exists(), reason="test vectors file not built")
def test_kernel_parity(pin: str) -> None:
    """Kernel verdicts and margins equal the Python integer model on the test vectors."""
    model = kmodel.load(KERNEL_MODEL_PATH)
    vecs = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))
    count = len(vecs["x"])
    assert 1 <= count <= N_TEST_VECS
    lines = [f"map update pinned {pin}/maps/test_vecs key hex {struct.pack('<I', i).hex(' ')} "
             f"value hex {struct.pack(f'<{N_FEATURES}q', *x).hex(' ')}"
             for i, x in enumerate(vecs["x"])]
    bpf_ctl.batch(kmodel.batch_lines(model, pin) + [kmodel.config_line(MODE_ALL, model, 0, pin)]
                  + lines)
    bpf_ctl.prog_run("classify_test", pin, DUMMY_FRAME, count)
    got = [e["formatted"]["value"] for e in bpf_ctl.dump("test_results", pin)][:count]
    assert [g["dt_verdict"] for g in got] == vecs["dt"]
    assert [g["xgb_margin"] for g in got] == vecs["xgb_margin"]


def _replay_flows(pin: str, count: int) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Replay count pool flows with the real model; return the ground truth and flows by source."""
    _configure(pin, kmodel.load(KERNEL_MODEL_PATH), MODE_ALL)
    truth = replay.run(pin, replay.sample(replay.load_pool(), count, random.Random(7)),
                       random.Random(8))
    by_src = {}
    for entry in bpf_ctl.dump("flows", pin):
        key, value = entry["formatted"]["key"], entry["formatted"]["value"]
        by_src[socket.inet_ntoa(key["saddr"].to_bytes(4, "little"))] = value
    return truth, by_src


@pytest.mark.skipif(not (REPLAY_POOL_PATH.exists() and KERNEL_MODEL_PATH.exists()),
                    reason="replay pool or kernel model not built")
def test_replay_through_xdp_ids(pin: str) -> None:
    """4 replayed flows (2 per class) give 4 classified flows from 10.99.x.y; blocks stay there."""
    truth, by_src = _replay_flows(pin, 4)
    assert sorted(by_src) == sorted(t["src_ip"] for t in truth)
    assert all(ip.startswith("10.99.") and v["classified_ns"] > 0 for ip, v in by_src.items())
    blocked = [socket.inet_ntoa(k.to_bytes(4, "little")) for k in _blocked(pin)]
    assert all(ip.startswith("10.99.") for ip in blocked)


@pytest.mark.skipif(not (REPLAY_POOL_PATH.exists() and KERNEL_MODEL_PATH.exists()),
                    reason="replay pool or kernel model not built")
def test_replay_evidence(pin: str) -> None:
    """Replay 100 flows and record how many of each label the kernel called Malicious."""
    truth, by_src = _replay_flows(pin, 100)
    counts: dict[str, dict[str, int]] = {}
    for entry in truth:
        stat = counts.setdefault(entry["label"], {"flows": 0, "malicious": 0})
        stat["flows"] += 1
        stat["malicious"] += by_src[entry["src_ip"]]["verdict"] == 1
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    text = json.dumps(counts, indent=1)
    (EVIDENCE_DIR / "replay_summary.json").write_text(text, encoding="utf-8")
    assert sum(c["flows"] for c in counts.values()) == 100


def _avg_ns(pin: str, frame: bytes) -> int:
    """Average ns per run of xdp_ids on one frame (TIMING_REPEAT runs)."""
    return bpf_ctl.prog_run("xdp_ids", pin, frame, TIMING_REPEAT)[1]


def _timing(pin: str, model: dict[str, Any]) -> dict[str, int]:
    """Time mid-flow, classifying-FIN and not-tracked packets, each on a fresh source.

    A reused source would already be blocked by the earlier stub run and the packet would be
    dropped before the flowmeter (the 46 ns bug), so every measurement gets its own source.
    """
    timing: dict[str, int] = {}
    for i, (mode_name, mode) in enumerate((("DT", MODE_DT), ("XGB", MODE_XGB), ("ALL", MODE_ALL))):
        _configure(pin, model, mode)
        src_mid, src_fin = f"10.1.{i}.1", f"10.1.{i}.2"
        timing[f"mid_flow_{mode_name}"] = _avg_ns(
            pin, pktbuild.tcp(src_mid, DST, SPORT, DPORT, pktbuild.PSH | pktbuild.ACK, MID_PAYLOAD))
        timing[f"classify_fin_{mode_name}"] = _avg_ns(
            pin, pktbuild.tcp(src_fin, DST, SPORT, DPORT, FIN_FLAGS))
        # The FIN path must have classified (Normal), otherwise the number measures something else.
        fin_flow = [e["formatted"]["value"] for e in bpf_ctl.dump("flows", pin)
                    if e["formatted"]["key"]["saddr"] == _ip_key(src_fin)]
        assert len(fin_flow) == 1
        assert fin_flow[0]["classified_ns"] > 0 and fin_flow[0]["verdict"] == 0
        assert not {_ip_key(src_mid), _ip_key(src_fin)} & set(_blocked(pin))
    timing["not_tracked"] = _avg_ns(pin, pktbuild.arp())
    return timing


def test_record_evidence(pin: str) -> None:
    """Write timing, program sizes and raw map dumps to outputs/kernel/."""
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    _configure(pin, NORMAL, MODE_DT)
    _fin_flow(pin)
    for name in ("flows", "stats"):
        text = json.dumps(bpf_ctl.dump(name, pin), indent=1)
        (EVIDENCE_DIR / f"{name}_dump.json").write_text(text, encoding="utf-8")
    # Malicious flow fixture for flowview tests: SRC2 is classified by the always-Malicious stub.
    _configure(pin, kmodel.load(FIXTURES / "always_malicious.json"), MODE_ALL)
    _fin_flow(pin, SRC2)
    text = json.dumps(bpf_ctl.dump("flows", pin), indent=1)
    (EVIDENCE_DIR / "flows_dump_malicious.json").write_text(text, encoding="utf-8")
    show = ["bpftool", "-j", "prog", "show", "pinned", f"{pin}/progs/xdp_ids"]
    size = json.loads(bpf_ctl.run(show))
    sizes = {k: size[k] for k in ("bytes_xlated", "bytes_jited")}
    (EVIDENCE_DIR / "prog_sizes.json").write_text(json.dumps(sizes, indent=1), encoding="utf-8")
    model = kmodel.load(KERNEL_MODEL_PATH) if KERNEL_MODEL_PATH.exists() else NORMAL
    timing = _timing(pin, model)
    (EVIDENCE_DIR / "timing.json").write_text(json.dumps(timing, indent=1), encoding="utf-8")
    assert all(v > 0 for v in timing.values())
