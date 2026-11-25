"""Unit tests for script/bpf_ctl.py (subprocess.run monkeypatched; no root, no bpftool)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import bpf_ctl

PIN = "/sys/fs/bpf/lab4"


class Recorder:  # pylint: disable=too-few-public-methods  # callable fake, one method is enough
    """Fake subprocess.run recording argument lists and returning a canned result."""

    def __init__(self, stdout: str = "", returncode: int = 0, stderr: str = "") -> None:
        """Store the canned result."""
        self.calls: list[list[str]] = []
        self.kwargs: list[dict] = []
        self.result = subprocess.CompletedProcess([], returncode, stdout, stderr)

    def __call__(self, args: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        """Record the call and return the canned result."""
        self.calls.append(list(args))
        self.kwargs.append(kwargs)
        return self.result


@pytest.fixture(name="rec")
def rec_fixture(monkeypatch: pytest.MonkeyPatch) -> Recorder:
    """Install a Recorder as subprocess.run."""
    rec = Recorder()
    monkeypatch.setattr(bpf_ctl.subprocess, "run", rec)
    return rec


def test_run_no_shell_and_error(rec: Recorder) -> None:
    """Arguments pass as a list without shell=True; non-zero exit raises with stderr."""
    rec.result = subprocess.CompletedProcess([], 1, "", "boom")
    with pytest.raises(RuntimeError, match="boom") as err:
        bpf_ctl.run(["bpftool", "x"])
    assert "bpftool x" in str(err.value)
    assert not rec.kwargs[0].get("shell")


def test_load(rec: Recorder, tmp_path: Path) -> None:
    """Load uses loadall with pinmaps."""
    pin = str(tmp_path / "pin")
    bpf_ctl.load("a.o", pin)
    assert rec.calls == [["bpftool", "prog", "loadall", "a.o", f"{pin}/progs", "type", "xdp",
                          "pinmaps", f"{pin}/maps"]]


def test_batch(rec: Recorder, monkeypatch: pytest.MonkeyPatch) -> None:
    """Batch passes a temp file holding the lines."""
    seen: list[str] = []

    def fake(args: list[str], **_: object) -> subprocess.CompletedProcess:
        seen.append(Path(args[-1]).read_text(encoding="utf-8"))
        rec.calls.append(args)
        return rec.result

    monkeypatch.setattr(bpf_ctl.subprocess, "run", fake)
    bpf_ctl.batch(["map update a", "map update b"])
    assert rec.calls[0][:3] == ["bpftool", "batch", "file"]
    assert seen == ["map update a\nmap update b\n"]
    assert not Path(rec.calls[0][3]).exists()


def test_attach_modes(rec: Recorder) -> None:
    """Skb maps to xdpgeneric, native to xdpdrv, unknown raises."""
    bpf_ctl.attach("ext0", PIN)
    bpf_ctl.attach("ext0", PIN, "native")
    assert rec.calls[0] == ["bpftool", "net", "attach", "xdpgeneric", "pinned",
                            f"{PIN}/progs/xdp_ids", "dev", "ext0"]
    assert rec.calls[1][3] == "xdpdrv"
    with pytest.raises(ValueError):
        bpf_ctl.attach("ext0", PIN, "bogus")


def test_detach_ignores_errors(rec: Recorder) -> None:
    """Detach swallows a failing bpftool."""
    rec.result = subprocess.CompletedProcess([], 255, "", "no prog")
    bpf_ctl.detach("ext0")
    assert rec.calls == [["bpftool", "net", "detach", "xdpgeneric", "dev", "ext0"]]


def test_dump(rec: Recorder) -> None:
    """Dump returns the parsed JSON list and rejects other shapes."""
    rec.result = subprocess.CompletedProcess([], 0, json.dumps([{"key": 1}]), "")
    assert bpf_ctl.dump("flows", PIN) == [{"key": 1}]
    assert rec.calls[0] == ["bpftool", "-j", "map", "dump", "pinned", f"{PIN}/maps/flows"]
    rec.result = subprocess.CompletedProcess([], 0, "{}", "")
    with pytest.raises(RuntimeError):
        bpf_ctl.dump("flows", PIN)


@pytest.mark.parametrize("out", [{"retval": 2, "duration": 150},
                                 [{"retval": 2, "duration": 150}]])
def test_prog_run(rec: Recorder, out: object) -> None:
    """prog_run returns (retval, duration) from a dict or one-element list."""
    rec.result = subprocess.CompletedProcess([], 0, json.dumps(out), "")
    assert bpf_ctl.prog_run("xdp_ids", PIN, b"abc", repeat=5) == (2, 150)
    call = rec.calls[0]
    assert call[:6] == ["bpftool", "-j", "prog", "run", "pinned", f"{PIN}/progs/xdp_ids"]
    assert call[6] == "data_in" and call[8:] == ["repeat", "5"]


def test_prog_run_bad_keys(rec: Recorder) -> None:
    """Missing keys raise RuntimeError."""
    rec.result = subprocess.CompletedProcess([], 0, json.dumps({"ret": 1}), "")
    with pytest.raises(RuntimeError):
        bpf_ctl.prog_run("xdp_ids", PIN, b"abc")


def test_unpin(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unpin removes paths below bpffs and refuses everything else."""
    removed: list[str] = []
    monkeypatch.setattr(bpf_ctl.shutil, "rmtree", lambda p, **_: removed.append(p))
    bpf_ctl.unpin(PIN)
    assert removed == [PIN]
    for bad in ("/tmp/x", "/sys/fs/bpf", "/sys/fs/bpf/../../etc", "/sys/fs/bpfx/a"):
        with pytest.raises(ValueError):
            bpf_ctl.unpin(bad)
    assert removed == [PIN]
