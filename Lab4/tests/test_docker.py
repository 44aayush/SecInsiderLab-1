"""Docker-stack tests (marker ``docker``): skipped unless the compose stack is running.

Run the stack first: ``docker compose up -d``. Stdlib only.
"""
from __future__ import annotations

import json
import subprocess
import urllib.request
from pathlib import Path

import pytest

LAB_DIR = Path(__file__).resolve().parent.parent
UI_URL = "http://172.28.0.2:8080/api/interfaces"
CMD_TIMEOUT_S = 120
HTTP_TIMEOUT_S = 5
SHORT_RUN_S = 10
NORMAL_RUN_S = 20
SERVERS = ("172.28.2.10", "172.28.2.11")
CLIENT_IP = "172.28.1.20"
IDS_ADDRS = {"mgmt0": "172.28.0.2", "ext0": "172.28.1.2", "int0": "172.28.2.2"}

pytestmark = pytest.mark.docker


def compose(*args: str, check: bool = False) -> subprocess.CompletedProcess:
    """Run ``docker compose`` in the lab directory.

    Args:
        *args: Arguments after ``docker compose``.
        check: Raise on a non-zero exit code.

    Returns:
        The completed process with text stdout (stderr merged).
    """
    return subprocess.run(["docker", "compose", *args], cwd=LAB_DIR, capture_output=True,
                          text=True, timeout=CMD_TIMEOUT_S, check=check)


def running_services() -> set[str]:
    """Return the names of the running compose services (empty when docker is unavailable).

    Returns:
        Set of service names.
    """
    try:
        res = compose("ps", "--status", "running", "--services")
    except (OSError, subprocess.TimeoutExpired):
        return set()
    return set(res.stdout.split()) if res.returncode == 0 else set()


def require(*services: str) -> None:
    """Skip the calling test unless every named service is running.

    Args:
        *services: Compose service names.
    """
    missing = set(services) - running_services()
    if missing:
        pytest.skip(f"compose stack not running: {sorted(missing)}")


def run_agent(timespan: int, model: str = "ALL") -> tuple[int, list[dict]]:
    """Run the agent in the ids container and parse its JSON flow lines.

    Args:
        timespan: Capture length in seconds.
        model: ``--model`` value.

    Returns:
        Tuple of (exit code, flow rows: parsed stdout JSON lines that carry ``src_ip``).
    """
    res = compose("exec", "-T", "ids", "python3", "script/agent.py", "--iface", "ext0",
                  "--model", model, "--timespan", str(timespan))
    rows = []
    for line in res.stdout.splitlines():
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict) and "src_ip" in obj:
            rows.append(obj)
    return res.returncode, rows


def test_task4_check() -> None:
    """Task 4: docker/task4_check.sh exits 0 (ping and HTTP from the pinger)."""
    require("nginx", "apache", "pinger")
    res = subprocess.run(["bash", "docker/task4_check.sh"], cwd=LAB_DIR, capture_output=True,
                         text=True, timeout=CMD_TIMEOUT_S, check=False)
    assert res.returncode == 0, res.stdout + res.stderr


def test_ids_interfaces() -> None:
    """The ids container has mgmt0, ext0 and int0 with the CLAUDE.md 5.6 addresses."""
    require("ids")
    out = compose("exec", "-T", "ids", "ip", "-br", "addr").stdout
    for name, addr in IDS_ADDRS.items():
        line = next((ln for ln in out.splitlines() if ln.startswith(name)), "")
        assert f"{addr}/24" in line, f"{name} should have {addr}: {out}"


def test_client_routes_via_ids() -> None:
    """The client reaches the back network through the ids ext0 address."""
    require("client")
    out = compose("exec", "-T", "client", "ip", "route", "show").stdout
    assert "via 172.28.1.2" in out, out


def test_ui_only_on_mgmt() -> None:
    """The UI answers on mgmt0 (without listing mgmt0) and is unreachable from the front network."""
    require("ids", "client")
    with urllib.request.urlopen(UI_URL, timeout=HTTP_TIMEOUT_S) as resp:
        assert resp.status == 200
        assert "mgmt0" not in json.load(resp)["interfaces"]
    res = compose("exec", "-T", "client", "wget", "-q", "-T", "3", "-O", "/dev/null",
                  "http://172.28.1.2:8080")
    assert res.returncode != 0, "UI must not be reachable from the front network"


def test_agent_short_run() -> None:
    """A 10 s ALL run exits 0, sees the client's flows to both servers and leaves no XDP on ext0."""
    require("ids", "client")
    code, rows = run_agent(SHORT_RUN_S)
    assert code == 0
    for server in SERVERS:
        flows = [r for r in rows if r["src_ip"] == CLIENT_IP and r["dst_ip"] == server]
        assert flows, f"no flow to {server}"
    net = compose("exec", "-T", "ids", "bpftool", "-j", "net", "show", "dev", "ext0").stdout
    assert json.loads(net)[0]["xdp"] == [], net


def test_agent_normal_traffic_not_blocked() -> None:
    """Review focus 1: normal client traffic stays Normal and the client logs no FAIL line."""
    require("ids", "client")
    since = compose("exec", "-T", "client", "date", "-u", "+%Y-%m-%dT%H:%M:%SZ"
                    ).stdout.strip()
    code, rows = run_agent(NORMAL_RUN_S)
    assert code == 0
    bad = [r for r in rows if r.get("result") == "Malicious"]
    log = compose("logs", "client", "--since", since).stdout
    fails = [ln for ln in log.splitlines() if ln.endswith("FAIL")]
    assert not bad and not fails, (
        f"Malicious flows (with features): {json.dumps(bad, indent=1)}; client FAILs: {fails}")
