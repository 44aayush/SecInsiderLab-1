"""Real-time agent: loads the XDP program, polls its maps and reports classified flows.

Stdlib only (CLAUDE.md 4.4, 5.5, O8). The kernel does capture, classification and filtering; this
module only configures it through bpftool and displays results. One capture per interface is
enforced with a non-blocking flock that the kernel drops when the process dies.
"""
from __future__ import annotations

import argparse
import dataclasses
import fcntl
import json
import logging
import os
import re
import signal
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, TextIO

import bpf_ctl
import flowview
import kmodel
from common import (BPF_OBJ, DEFAULT_BLOCK_S, DEFAULT_IFACE, DEFAULT_OUT, DEFAULT_TIMESPAN_S,
                    KERNEL_MODEL_PATH, MAX_TIMESPAN_S, MGMT_IFACE, MODEL_MODES, PIN_DIR,
                    POLL_INTERVAL_S, V_MALICIOUS, setup_logging)

LOG = logging.getLogger(__name__)
LOCK_DIR = Path("/run")
SYS_NET = Path("/sys/class/net")
IFACE_RE = re.compile(r"[A-Za-z0-9_.-]{1,15}")  # IFNAMSIZ - 1
LOCK_MODE = 0o600
NS_PER_S = 10**9
MAX_BLOCK_S = 3600
FILE_STAMP = "%Y%m%d-%H%M%S"
FlowKey = tuple[str, int, str, int, str]


def validate_iface(name: str) -> str:
    """Check an interface name at the trust boundary.

    Args:
        name: Candidate interface name.

    Returns:
        The same name.

    Raises:
        ValueError: If the name is malformed, is the management interface or does not exist.
    """
    if not IFACE_RE.fullmatch(name) or name in (".", "..") or name == MGMT_IFACE:
        raise ValueError(f"invalid interface: {name!r}")
    if not (SYS_NET / name).exists():
        raise ValueError(f"unknown interface: {name!r}")
    return name


class Session:
    """One XDP capture on one interface (context manager; always detaches and unpins)."""

    def __init__(self, iface: str, model: str = "ALL", model_file: Path = KERNEL_MODEL_PATH,
                 block_s: int = DEFAULT_BLOCK_S, xdp_mode: str = "skb") -> None:
        """Validate the arguments; nothing touches the kernel until `start`.

        Args:
            iface: Interface to attach to.
            model: "DT", "XGB" or "ALL".
            model_file: Kernel model JSON.
            block_s: Block duration in seconds.
            xdp_mode: "skb" or "native".
        """
        self.iface = validate_iface(iface)
        self.model = model.upper()
        self.model_file, self.block_s, self.xdp_mode = model_file, block_s, xdp_mode
        self.pin = f"{PIN_DIR}/{self.iface}"
        self._lock_fd: int | None = None

    def _acquire(self) -> None:
        """Take the per-interface lock.

        Raises:
            RuntimeError: If another capture holds it.
        """
        fd = os.open(LOCK_DIR / f"lab4-{self.iface}.lock", os.O_CREAT | os.O_RDWR, LOCK_MODE)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            os.close(fd)
            raise RuntimeError(f"capture already running on {self.iface}") from exc
        self._lock_fd = fd

    def start(self) -> None:
        """Lock, remove stale state, load, configure, then attach (attach is always last)."""
        self._acquire()
        try:
            model = kmodel.load(self.model_file)
            bpf_ctl.unpin(self.pin)
            bpf_ctl.load(BPF_OBJ, self.pin)
            bpf_ctl.batch(kmodel.batch_lines(model, self.pin))
            mode = MODEL_MODES[self.model]
            bpf_ctl.batch([kmodel.config_line(mode, model, self.block_s * NS_PER_S, self.pin)])
            bpf_ctl.detach(self.iface)
            bpf_ctl.attach(self.iface, self.pin, self.xdp_mode)
        except Exception:
            self.stop()
            raise

    def poll(self) -> tuple[list[flowview.FlowRow], dict[str, int]]:
        """Read the maps once.

        Returns:
            (classified flow rows, summed stats).
        """
        rows = flowview.parse_flows(bpf_ctl.dump("flows", self.pin), MODEL_MODES[self.model],
                                    time.time(), time.monotonic_ns())
        return rows, flowview.parse_stats(bpf_ctl.dump("stats", self.pin))

    def stop(self) -> None:
        """Detach, unpin and release the lock; safe to call twice."""
        try:
            bpf_ctl.detach(self.iface)
            bpf_ctl.unpin(self.pin)
        finally:
            if self._lock_fd is not None:
                os.close(self._lock_fd)
                self._lock_fd = None

    def __enter__(self) -> "Session":
        """Start the session.

        Returns:
            self.
        """
        self.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        """Stop the session, also after an error."""
        self.stop()


def _chown(paths: list[Path]) -> None:
    """Give files written as root to LAB4_UID/LAB4_GID when both are set.

    Args:
        paths: Files and directories to chown.
    """
    uid, gid = os.environ.get("LAB4_UID"), os.environ.get("LAB4_GID")
    if uid and gid:
        for path in paths:
            os.chown(path, int(uid), int(gid))


def emit_changes(rows: list[flowview.FlowRow], seen: dict[FlowKey, tuple[str, str]],
                 sink: TextIO) -> None:
    """Write one JSON line per new or changed flow to stdout and `sink`.

    Args:
        rows: Classified flows of this poll.
        seen: Flow key to (result, models) already reported; updated in place.
        sink: Open text file for the JSONL copy.
    """
    for row in rows:
        key = (row.src_ip, row.src_port, row.dst_ip, row.dst_port, row.proto)
        if seen.get(key) != (row.result, row.models):
            seen[key] = (row.result, row.models)
            line = json.dumps(dataclasses.asdict(row)) + "\n"
            sys.stdout.write(line)
            sys.stdout.flush()
            sink.write(line)


def _bounded(low: int, high: int) -> Callable[[str], int]:
    """Build an argparse type for an int in [low, high].

    Args:
        low: Smallest allowed value.
        high: Largest allowed value.

    Returns:
        The converter.
    """
    def convert(text: str) -> int:
        value = int(text)
        if not low <= value <= high:
            raise argparse.ArgumentTypeError(f"must be {low}..{high}")
        return value
    return convert


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse the command line (CLAUDE.md 5.5).

    Args:
        argv: Arguments without the program name.

    Returns:
        The namespace.
    """
    p = argparse.ArgumentParser(description="Real-time in-kernel DDoS detection (XDP)")
    p.add_argument("--iface", default=DEFAULT_IFACE)
    p.add_argument("--model", type=str.upper, choices=sorted(MODEL_MODES), default="ALL")
    p.add_argument("--timespan", type=_bounded(1, MAX_TIMESPAN_S), default=DEFAULT_TIMESPAN_S)
    p.add_argument("--block-seconds", type=_bounded(1, MAX_BLOCK_S), default=DEFAULT_BLOCK_S)
    p.add_argument("--model-file", type=Path, default=KERNEL_MODEL_PATH)
    p.add_argument("--xdp-mode", choices=["skb", "native"], default="skb")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT / "realtime")
    return p.parse_args(argv)


def _capture(args: argparse.Namespace, base: Path, stop: threading.Event,
             seen: dict[FlowKey, tuple[str, str]]) -> dict[str, int]:
    """Run the session and poll loop, writing the JSONL file.

    Args:
        args: Parsed command line.
        base: Output path prefix.
        stop: Set by SIGINT/SIGTERM.
        seen: Reported flows; updated in place.

    Returns:
        The last stats read.
    """
    stats: dict[str, int] = {}
    session = Session(args.iface, args.model, args.model_file, args.block_seconds, args.xdp_mode)
    with session, open(f"{base}.jsonl", "w", encoding="utf-8") as sink:
        deadline = time.monotonic() + args.timespan
        while not stop.is_set() and time.monotonic() < deadline:
            rows, stats = session.poll()
            emit_changes(rows, seen, sink)
            sink.flush()
            stop.wait(POLL_INTERVAL_S)
    return stats


def main(argv: list[str] | None = None) -> int:
    """Run one capture for `--timespan` seconds (or until SIGINT/SIGTERM).

    Args:
        argv: Arguments without the program name (default sys.argv).

    Returns:
        0 on success, 1 if the capture could not start or failed.
    """
    args = parse_args(argv)
    stop = threading.Event()
    old = {s: signal.signal(s, lambda _n, _f: stop.set()) for s in (signal.SIGINT, signal.SIGTERM)}
    started = datetime.now()
    base = args.out / f"{started.strftime(FILE_STAMP)}_{args.iface}_{args.model}"
    seen: dict[FlowKey, tuple[str, str]] = {}
    try:
        args.out.mkdir(parents=True, exist_ok=True)
        setup_logging(args.out)
        stats = _capture(args, base, stop, seen)
    except (RuntimeError, ValueError, OSError) as exc:
        LOG.error("capture failed: %s", exc)
        return 1
    finally:
        for sig, handler in old.items():
            signal.signal(sig, handler)
    bad = flowview.VERDICT_NAMES[V_MALICIOUS]
    summary = {"iface": args.iface, "model": args.model, "timespan_s": args.timespan,
               "started": started.isoformat(timespec="seconds"),
               "ended": datetime.now().isoformat(timespec="seconds"), "stats": stats,
               "flows_classified": len(seen),
               "flows_malicious": sum(res == bad for res, _ in seen.values())}
    Path(f"{base}_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    _chown([args.out, Path(f"{base}.jsonl"), Path(f"{base}_summary.json")])
    return 0


if __name__ == "__main__":
    sys.exit(main())
