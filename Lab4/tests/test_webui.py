"""Tests for script/webui.py (fake Session; server on port 0 in a thread)."""
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

import agent
import flowview
import webui

HEADERS = ["Src IP", "Src Port", "Dst IP", "Dst Port", "Timestamp", "Result", "Models"]
IDS = ["iface", "timespan", "model", "start", "stop", "status", "flows"]


class FakeSession:
    """Records constructor args; poll returns one flow."""

    instances: list["FakeSession"] = []

    def __init__(self, iface: str, model: str = "ALL") -> None:
        self.args = (iface, model)
        self.stopped = False
        FakeSession.instances.append(self)

    def start(self) -> None:
        """No-op start."""

    def poll(self):
        """Return one malicious flow and stats."""
        row = flowview.FlowRow("10.0.0.2", 1234, "10.0.0.3", 80, "TCP", "t", "Malicious",
                               "DT: Malicious", 9)
        return [row], {"ST_PKTS": 5}

    def stop(self) -> None:
        """Mark stopped."""
        self.stopped = True


@pytest.fixture(name="srv")
def srv_fixture(monkeypatch, tmp_path: Path):
    """Server on a free port with a fake /sys/class/net and Session."""
    for name in ("ext0", "mgmt0", "lo"):
        (tmp_path / name).mkdir()
    monkeypatch.setattr(agent, "SYS_NET", tmp_path)
    monkeypatch.setattr(agent, "Session", FakeSession)
    FakeSession.instances = []
    server = webui.UiServer(("127.0.0.1", 0), "XGB")
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server
    server.capture.stop()
    server.shutdown()
    server.server_close()


def call(srv, path: str, body=None, raw: bytes | None = None):
    """Do a request; return (status, parsed body or text)."""
    data = raw if raw is not None else (None if body is None else json.dumps(body).encode())
    req = urllib.request.Request(f"http://127.0.0.1:{srv.server_address[1]}{path}", data=data)
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            text = res.read().decode()
            is_json = res.headers["Content-Type"] == "application/json"
            return res.status, (json.loads(text) if is_json else text)
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read() or b"{}")


def test_index_has_controls_and_columns(srv):
    """Page carries the element ids and the header order."""
    status, html = call(srv, "/")
    assert status == 200
    assert all(f'id="{i}"' in html for i in IDS)
    positions = [html.index(f">{h}</th>") for h in HEADERS]
    assert positions == sorted(positions)
    assert "Available Local Interfaces" in html and "Start Packet Capture" in html


def test_interfaces_excludes_mgmt(srv):
    """mgmt0 is never offered."""
    _, data = call(srv, "/api/interfaces")
    assert data["interfaces"] == ["ext0", "lo"] and data["default"] == "ext0"


@pytest.mark.parametrize("body", [
    {"iface": "../x", "timespan": 5, "model": "DT"},
    {"iface": "eth0;rm", "timespan": 5, "model": "DT"},
    {"iface": "mgmt0", "timespan": 5, "model": "DT"},
    {"iface": "ext0", "timespan": 0, "model": "DT"},
    {"iface": "ext0", "timespan": 3601, "model": "DT"},
    {"iface": "ext0", "timespan": "abc", "model": "DT"},
    {"iface": "ext0", "timespan": 5, "model": "RF"}, {"timespan": 5}, {"iface": "ext0"}, {}])
def test_start_rejects_bad_input(srv, body):
    """Bad input gives 400 and never creates a session."""
    assert call(srv, "/api/start", body)[0] == 400
    assert not FakeSession.instances


def test_start_rejects_garbage_and_oversize(srv):
    """Non-JSON is 400; a body over 4 KB is 413."""
    assert call(srv, "/api/start", raw=b"not json")[0] == 400
    assert call(srv, "/api/start", raw=b"x" * 5000)[0] == 413
    assert not FakeSession.instances


def test_start_accepts_and_passes_args(srv):
    """A valid start is 202 and the session gets the exact values."""
    assert call(srv, "/api/start", {"iface": "ext0", "timespan": 30, "model": "dt"})[0] == 202
    assert FakeSession.instances[0].args == ("ext0", "DT")


def test_second_start_conflicts(srv):
    """Only one capture at a time."""
    body = {"iface": "ext0", "timespan": 30, "model": "ALL"}
    assert call(srv, "/api/start", body)[0] == 202
    assert call(srv, "/api/start", body)[0] == 409


def test_flows_shape(srv):
    """Snapshot has the contract keys and the polled row."""
    assert call(srv, "/api/flows")[1]["running"] is False
    call(srv, "/api/start", {"iface": "ext0", "timespan": 30, "model": "ALL"})
    for _ in range(50):
        data = call(srv, "/api/flows")[1]
        if data["rows"]:
            break
        time.sleep(0.05)
    assert set(data) == {"running", "remaining_s", "iface", "model", "stats", "rows"}
    assert data["running"] and data["rows"][0]["src_ip"] == "10.0.0.2"
    assert data["stats"] == {"ST_PKTS": 5}


def test_stop(srv):
    """Stop ends the capture and stops the session."""
    call(srv, "/api/start", {"iface": "ext0", "timespan": 30, "model": "ALL"})
    assert call(srv, "/api/stop", {})[0] == 200
    assert call(srv, "/api/flows")[1]["running"] is False
    assert FakeSession.instances[0].stopped


def test_binds_given_host_only():
    """The server binds exactly the host it was given."""
    server = webui.UiServer(("127.0.0.1", 0), "ALL")
    try:
        assert server.server_address[0] == "127.0.0.1"
    finally:
        server.server_close()
