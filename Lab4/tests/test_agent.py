"""Session, CLI and output contract of agent.py with a fake bpf_ctl (no kernel needed)."""
from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path
from typing import Any

import pytest

import agent
import flowview
from conftest import FIXTURES

IFACE = "veth0"
EXPECTED_SUMMARY = {"iface", "model", "timespan_s", "started", "ended", "stats", "flows_classified",
                    "flows_malicious"}


class FakeCtl:  # pylint: disable=too-few-public-methods  # test double, __getattr__ only
    """Records bpf_ctl calls and serves canned dumps."""

    def __init__(self) -> None:
        """Start with no calls."""
        self.calls: list[str] = []

    def __getattr__(self, name: str) -> Any:
        """Return a recorder for any bpf_ctl function.

        Args:
            name: Function name.

        Returns:
            A callable that records its name.
        """
        def record(*_a: Any, **_k: Any) -> list[Any]:
            self.calls.append(name)
            return []
        return record


@pytest.fixture(name="env")
def _env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FakeCtl:
    """Patch bpf_ctl, the lock dir and the interface list; create interface IFACE.

    Args:
        monkeypatch: pytest fixture.
        tmp_path: pytest fixture.

    Returns:
        The fake bpf_ctl.
    """
    fake = FakeCtl()
    (tmp_path / "net" / IFACE).mkdir(parents=True)
    monkeypatch.setattr(agent, "bpf_ctl", fake)
    monkeypatch.setattr(agent, "LOCK_DIR", tmp_path)
    monkeypatch.setattr(agent, "SYS_NET", tmp_path / "net")
    return fake


def _session() -> agent.Session:
    """Build a session on IFACE with the always-Malicious stub model.

    Returns:
        The session.
    """
    return agent.Session(IFACE, "dt", FIXTURES / "always_malicious.json")


def test_session_call_order(env: FakeCtl) -> None:
    """Start: unpin, load, two batches, detach, attach; stop: detach, unpin."""
    with _session():
        pass
    assert env.calls == ["unpin", "load", "batch", "batch", "detach", "attach", "detach", "unpin"]


def test_session_cleans_up_on_error(env: FakeCtl) -> None:
    """An error inside the session still detaches, unpins and frees the lock."""
    with pytest.raises(KeyError):
        with _session():
            raise KeyError("poll failed")
    assert env.calls[-2:] == ["detach", "unpin"]
    with _session():  # lock is free again
        pass


def test_second_session_same_iface_fails(env: FakeCtl) -> None:
    """While one session holds the lock, a second start raises RuntimeError."""
    with _session():
        with pytest.raises(RuntimeError, match="already running"):
            _session().start()
    assert env.calls.count("load") == 1


@pytest.mark.usefixtures("env")
@pytest.mark.parametrize("name", ["mgmt0", "nope0", "../x", "a b", "a;b", "", "x" * 16])
def test_validate_iface_rejects(name: str) -> None:
    """Bad, management or unknown names are rejected."""
    with pytest.raises(ValueError):
        agent.validate_iface(name)


@pytest.mark.usefixtures("env")
def test_validate_iface_accepts() -> None:
    """An existing name passes."""
    assert agent.validate_iface(IFACE) == IFACE


def test_cli_model_case_insensitive() -> None:
    """--model xgb becomes XGB."""
    assert agent.parse_args(["--model", "xgb"]).model == "XGB"
    assert agent.parse_args([]).model == "ALL"


@pytest.mark.parametrize("flag,value", [("--timespan", "0"), ("--timespan", "3601"),
                                        ("--block-seconds", "0"), ("--block-seconds", "3601"),
                                        ("--model", "RF"), ("--replay", "-1"), ("--replay", "101"),
                                        ("--replay", "x")])
def test_cli_bounds(flag: str, value: str) -> None:
    """Out-of-range numbers and unknown models exit with the argparse error code."""
    with pytest.raises(SystemExit) as exc:
        agent.parse_args([flag, value])
    assert exc.value.code == 2


def _row(result: str = "Normal", sport: int = 1) -> flowview.FlowRow:
    """Build a FlowRow.

    Args:
        result: Normal or Malicious.
        sport: Source port.

    Returns:
        The row.
    """
    return flowview.FlowRow("10.0.0.2", sport, "10.0.0.1", 80, "TCP", "t", result, "DT: x", 4)


def test_jsonl_one_line_per_new_or_changed_flow(tmp_path: Path, capsys: pytest.CaptureFixture[str]
                                                ) -> None:
    """Repeated identical rows are silent; a new flow or a changed result prints a line."""
    seen: dict[Any, Any] = {}
    with open(tmp_path / "o.jsonl", "w", encoding="utf-8") as sink:
        agent.emit_changes([_row(), _row(sport=2)], seen, sink)
        agent.emit_changes([_row(), _row(sport=2)], seen, sink)
        agent.emit_changes([_row("Malicious")], seen, sink)
    lines = (tmp_path / "o.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3 == len(capsys.readouterr().out.splitlines())
    assert json.loads(lines[2])["result"] == "Malicious"


def test_jsonl_keeps_middle_dot(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The ALL-mode separator is written as the character, not a backslash-u escape."""
    row = dataclasses.replace(_row(), models="DT: x \xb7 XGB: y")
    with open(tmp_path / "o.jsonl", "w", encoding="utf-8") as sink:
        agent.emit_changes([row], {}, sink)
    for text in (capsys.readouterr().out, (tmp_path / "o.jsonl").read_text(encoding="utf-8")):
        assert "\xb7" in text and "\\u" not in text


class FakeSession:
    """Session stand-in whose poll returns one Malicious flow."""

    def __init__(self, *_a: Any) -> None:
        """Accept and ignore the Session arguments."""

    def __enter__(self) -> "FakeSession":
        """Return self."""
        return self

    def __exit__(self, *_exc: object) -> None:
        """Do nothing."""

    def replay(self, flows: list[Any]) -> list[dict[str, Any]]:
        """Return one ground-truth entry per flow.

        Args:
            flows: Flows to replay.

        Returns:
            Fake ground truth.
        """
        return [{"src_ip": "10.99.0.1", "sport": 1, "label": f, "retvals": [2]} for f in flows]

    def poll(self) -> tuple[list[flowview.FlowRow], dict[str, int]]:
        """Return one Malicious row and fixed stats.

        Returns:
            (rows, stats).
        """
        return [_row("Malicious")], {"ST_PKTS": 9}


def test_summary_keys_and_chown(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """main writes the summary with the contract keys and chowns when LAB4_UID/GID are set."""
    chowned: list[tuple[Any, int, int]] = []
    monkeypatch.setattr(agent, "Session", FakeSession)
    monkeypatch.setattr(agent, "POLL_INTERVAL_S", 0.01)
    monkeypatch.setattr(agent, "setup_logging", lambda _out: None)
    monkeypatch.setattr(os, "chown", lambda p, u, g: chowned.append((p, u, g)))
    monkeypatch.setenv("LAB4_UID", "1234")
    monkeypatch.setenv("LAB4_GID", "5678")
    assert agent.main(["--timespan", "1", "--out", str(tmp_path), "--iface", IFACE]) == 0
    (summary,) = tmp_path.glob("*_summary.json")
    data = json.loads(summary.read_text(encoding="utf-8"))
    assert set(data) == EXPECTED_SUMMARY
    assert (data["flows_classified"], data["flows_malicious"], data["stats"]) == (1, 1,
                                                                                {"ST_PKTS": 9})
    assert len(list(tmp_path.glob("*.jsonl"))) == 1
    assert chowned and all(c[1:] == (1234, 5678) for c in chowned)


def test_replay_flag_writes_ground_truth(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """--replay N draws N flows, replays them and writes <stamp>_replay.json."""
    monkeypatch.setattr(agent, "Session", FakeSession)
    monkeypatch.setattr(agent, "POLL_INTERVAL_S", 0.01)
    monkeypatch.setattr(agent, "setup_logging", lambda _out: None)
    monkeypatch.setattr(agent.replay, "pick", lambda n: ["DDoS"] * n)
    monkeypatch.setattr(agent.replay, "SPREAD", 0.1)
    assert agent.main(["--timespan", "1", "--out", str(tmp_path), "--iface", IFACE,
                       "--replay", "3"]) == 0
    (truth,) = tmp_path.glob("*_replay.json")
    assert [e["label"] for e in json.loads(truth.read_text(encoding="utf-8"))] == ["DDoS"] * 3


def test_no_replay_file_by_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Without --replay nothing is replayed or written."""
    monkeypatch.setattr(agent, "Session", FakeSession)
    monkeypatch.setattr(agent, "POLL_INTERVAL_S", 0.01)
    monkeypatch.setattr(agent, "setup_logging", lambda _out: None)
    assert agent.main(["--timespan", "1", "--out", str(tmp_path), "--iface", IFACE]) == 0
    assert not list(tmp_path.glob("*_replay.json"))


def test_chown_skipped_without_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Without LAB4_UID/LAB4_GID nothing is chowned."""
    monkeypatch.delenv("LAB4_UID", raising=False)
    monkeypatch.setattr(os, "chown", lambda *_a: pytest.fail("chown called"))
    agent._chown([tmp_path])  # pylint: disable=protected-access


@pytest.mark.usefixtures("env")
def test_main_reports_lock_conflict(tmp_path: Path) -> None:
    """main returns 1 when the interface is already captured."""
    with _session():
        argv = ["--iface", IFACE, "--out", str(tmp_path / "o"), "--model-file",
                str(FIXTURES / "always_malicious.json")]
        assert agent.main(argv) == 1
