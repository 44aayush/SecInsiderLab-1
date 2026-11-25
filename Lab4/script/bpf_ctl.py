"""Thin bpftool wrapper for Lab 4 user space (stdlib only; CLAUDE.md 5.5, O8).

Every call is an argument list handed to ``subprocess.run`` (never a shell). A failing command
raises ``RuntimeError`` carrying the command and its stderr.

Caveat: the JSON key names of ``bpftool -j prog run`` are not yet verified against real output
(T4.4). `prog_run` therefore parses defensively: it accepts a dict or a one-element list and
expects the keys "retval" and "duration" (average ns); anything else raises ``RuntimeError``.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

BPFTOOL = "bpftool"
BPFFS_ROOT = "/sys/fs/bpf"
ATTACH_MODES = {"skb": "xdpgeneric", "native": "xdpdrv"}
PROG_NAME = "xdp_ids"
LOG = logging.getLogger(__name__)


def run(args: list[str]) -> str:
    """Run a command without a shell.

    Args:
        args: Full argument list, program first.

    Returns:
        The command's stdout.

    Raises:
        RuntimeError: If the exit code is non-zero (message holds command and stderr).
    """
    proc = subprocess.run(args, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        cmd = " ".join(args)
        raise RuntimeError(f"command failed ({proc.returncode}): {cmd}: {proc.stderr.strip()}")
    return proc.stdout


def load(obj: str | Path, pin_dir: str) -> None:
    """Load all programs of a BPF object and pin programs and maps under `pin_dir`.

    Args:
        obj: Path of the compiled BPF object.
        pin_dir: Pin root; programs go to `progs/`, maps to `maps/`.
    """
    # bpftool creates progs/ itself but not necessarily the parent.
    Path(pin_dir).mkdir(parents=True, exist_ok=True)
    run([BPFTOOL, "prog", "loadall", str(obj), f"{pin_dir}/progs", "type", "xdp",
         "pinmaps", f"{pin_dir}/maps"])


def batch(lines: list[str]) -> None:
    """Execute bpftool batch commands (one call for many map updates).

    Args:
        lines: One bpftool command per entry, without the leading "bpftool".
    """
    with tempfile.NamedTemporaryFile("w", suffix=".batch", delete=False) as tmp:
        tmp.write("\n".join(lines) + "\n")
    try:
        run([BPFTOOL, "batch", "file", tmp.name])
    finally:
        os.unlink(tmp.name)


def detach(iface: str) -> None:
    """Detach any generic-mode XDP program from `iface`; errors are ignored.

    Args:
        iface: Interface name.
    """
    try:
        run([BPFTOOL, "net", "detach", "xdpgeneric", "dev", iface])
    except RuntimeError as exc:
        LOG.debug("detach ignored: %s", exc)


def attach(iface: str, pin_dir: str, mode: str = "skb") -> None:
    """Attach the pinned `xdp_ids` program to `iface`.

    Args:
        iface: Interface name.
        pin_dir: Pin root used by `load`.
        mode: "skb" (xdpgeneric) or "native" (xdpdrv).

    Raises:
        ValueError: If `mode` is unknown.
    """
    if mode not in ATTACH_MODES:
        raise ValueError(f"unknown xdp mode: {mode!r}")
    run([BPFTOOL, "net", "attach", ATTACH_MODES[mode], "pinned",
         f"{pin_dir}/progs/{PROG_NAME}", "dev", iface])


def dump(map_name: str, pin_dir: str) -> list[dict[str, Any]]:
    """Dump a pinned map as parsed JSON.

    Args:
        map_name: Pin name of the map (e.g. "flows").
        pin_dir: Pin root used by `load`.

    Returns:
        The parsed JSON list of map elements.

    Raises:
        RuntimeError: If the output is not a JSON list.
    """
    data = json.loads(run([BPFTOOL, "-j", "map", "dump", "pinned", f"{pin_dir}/maps/{map_name}"]))
    if not isinstance(data, list):
        raise RuntimeError(f"unexpected map dump for {map_name}: {type(data).__name__}")
    return data


def prog_run(prog: str, pin_dir: str, data: bytes, repeat: int = 1) -> tuple[int, int]:
    """Run a pinned program with BPF_PROG_TEST_RUN on one packet.

    Args:
        prog: Program pin name (e.g. "xdp_ids").
        pin_dir: Pin root used by `load`.
        data: Packet bytes (data_in).
        repeat: Number of repetitions.

    Returns:
        (retval, average duration in ns).

    Raises:
        RuntimeError: If the JSON lacks "retval" or "duration" (keys unverified, see module doc).
    """
    with tempfile.NamedTemporaryFile(suffix=".pkt", delete=False) as tmp:
        tmp.write(data)
    try:
        out = run([BPFTOOL, "-j", "prog", "run", "pinned", f"{pin_dir}/progs/{prog}",
                   "data_in", tmp.name, "repeat", str(repeat)])
    finally:
        os.unlink(tmp.name)
    parsed = json.loads(out)
    if isinstance(parsed, list) and len(parsed) == 1:
        parsed = parsed[0]
    if not isinstance(parsed, dict) or "retval" not in parsed or "duration" not in parsed:
        raise RuntimeError(f"unexpected prog run output: {out.strip()[:200]}")
    return int(parsed["retval"]), int(parsed["duration"])


def unpin(pin_dir: str) -> None:
    """Remove a pin directory (rm -rf), refusing anything outside bpffs.

    Args:
        pin_dir: Directory below /sys/fs/bpf/.

    Raises:
        ValueError: If the normalised path is not strictly below /sys/fs/bpf/.
    """
    norm = os.path.normpath(pin_dir)
    if not norm.startswith(BPFFS_ROOT + "/"):
        raise ValueError(f"refusing to unpin outside {BPFFS_ROOT}/: {pin_dir}")
    shutil.rmtree(norm, ignore_errors=True)
