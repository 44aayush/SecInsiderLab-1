"""Web UI for the real-time cycle (Task 3; stdlib only; CLAUDE.md 5.5).

One page (web/index.html) plus a small JSON API. One capture runs at a time, in a daemon thread
that polls an agent.Session; the kernel does all classification and filtering.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import random
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import agent
import flowview
import replay
from common import (DEFAULT_IFACE, DEFAULT_REPLAY_UI, LAB4_DIR, MAX_REPLAY, MAX_TIMESPAN_S,
                    MGMT_IFACE, MODEL_MODES, POLL_INTERVAL_S, setup_logging, DEFAULT_OUT)

LOG = logging.getLogger(__name__)
INDEX_HTML = LAB4_DIR / "web" / "index.html"
MAX_BODY = 4096
MAX_ROWS = 500
DEFAULT_PORT = 8080
FlowKey = tuple[str, int, str, int, str]


class BadRequest(ValueError):
    """Invalid client input (HTTP 400)."""


class Capture:
    """State of the single capture (thread-safe)."""

    def __init__(self, default_model: str) -> None:
        """Create an idle state.

        Args:
            default_model: Model preselected in the UI.
        """
        self.default_model = default_model
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._flows: dict[FlowKey, flowview.FlowRow] = {}
        self._stats: dict[str, int] = {}
        self._info: dict[str, Any] = {"iface": "", "model": "", "deadline": 0.0, "replay": []}

    def running(self) -> bool:
        """Report whether a capture thread is alive.

        Returns:
            True while a capture runs.
        """
        return self._thread is not None and self._thread.is_alive()

    def start(self, iface: str, timespan: int, model: str, n_replay: int = 0) -> None:
        """Start a capture; the session is started here so failures reach the client.

        Args:
            iface: Validated interface.
            timespan: Seconds to run.
            model: "DT", "XGB" or "ALL".
            n_replay: Dataset flows to replay through the kernel program (0 = none).

        Raises:
            RuntimeError: If a capture is already running (here or on another process).
        """
        with self._lock:
            if self.running():
                raise RuntimeError("capture already running")
            session = agent.Session(iface, model)
            session.start()
            try:
                pool = replay.pick(n_replay) if n_replay else []
                sched = replay.Schedule(pool, timespan, random.Random())
            except (RuntimeError, ValueError, OSError):
                session.stop()
                raise
            self._flows, self._stats = {}, {}
            self._info = {"iface": iface, "model": model, "replay": [],
                          "deadline": time.monotonic() + timespan}
            self._stop = threading.Event()
            self._thread = threading.Thread(target=self._run, args=(session, self._stop, sched),
                                            daemon=True)
            self._thread.start()

    def _run(self, session: Any, stop: threading.Event, sched: replay.Schedule) -> None:
        """Poll the session until the deadline or stop, then always stop it.

        Args:
            session: A started agent.Session.
            stop: Set by Capture.stop.
            sched: Replay schedule; its due flows are injected on each tick.
        """
        try:
            while not stop.is_set() and time.monotonic() < self._info["deadline"]:
                flows = sched.due()
                truth = session.replay(flows) if flows else []
                rows, stats = session.poll()
                with self._lock:
                    self._info["replay"] += truth
                    for row in rows:
                        self._flows[(row.src_ip, row.src_port, row.dst_ip, row.dst_port,
                                     row.proto)] = row
                    self._stats = stats
                stop.wait(POLL_INTERVAL_S)
        except (RuntimeError, ValueError, OSError) as exc:
            LOG.error("capture failed: %s", exc)
        finally:
            session.stop()

    def stop(self) -> None:
        """Stop the running capture and wait for its cleanup."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join()

    def snapshot(self) -> dict[str, Any]:
        """Build the /api/flows payload.

        Returns:
            running, remaining_s, iface, model, stats, rows (newest first, capped) and replay
            (ground truth of the replayed flows).
        """
        with self._lock:
            rows = [dataclasses.asdict(r) for r in reversed(list(self._flows.values()))]
            remaining = max(0, round(self._info["deadline"] - time.monotonic()))
            return {"running": self.running(), "remaining_s": remaining if self.running() else 0,
                    "iface": self._info["iface"], "model": self._info["model"],
                    "stats": dict(self._stats), "rows": rows[:MAX_ROWS],
                    "replay": list(self._info["replay"])}


def _to_int(value: Any, name: str) -> int:
    """Convert a JSON int or digit string.

    Args:
        value: Parsed JSON value.
        name: Field name for the error message.

    Returns:
        The integer.

    Raises:
        BadRequest: If the value is a bool or neither int nor str.
        ValueError: If a string is not an integer.
    """
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise BadRequest(f"{name} must be an integer")
    return int(value)


def parse_start(body: bytes, default_model: str) -> tuple[str, int, str, int]:
    """Validate a /api/start body (trust boundary).

    Args:
        body: Raw JSON bytes.
        default_model: Used when "model" is absent.

    Returns:
        (iface, timespan, model, replay).

    Raises:
        BadRequest: On any invalid value.
    """
    try:
        data = json.loads(body)
        iface, span = data["iface"], data["timespan"]
        model = str(data.get("model", default_model)).upper()
        span = _to_int(span, "timespan")
        n_replay = _to_int(data.get("replay", DEFAULT_REPLAY_UI), "replay")
        agent.validate_iface(str(iface))
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise BadRequest(str(exc)) from exc
    if not 1 <= span <= MAX_TIMESPAN_S:
        raise BadRequest(f"timespan must be 1..{MAX_TIMESPAN_S}")
    if model not in MODEL_MODES:
        raise BadRequest(f"model must be one of {sorted(MODEL_MODES)}")
    if not 0 <= n_replay <= MAX_REPLAY:
        raise BadRequest(f"replay must be 0..{MAX_REPLAY}")
    return str(iface), span, model, n_replay


class Handler(BaseHTTPRequestHandler):
    """HTTP routes of CLAUDE.md 5.5."""

    server: "UiServer"

    # pylint: disable-next=redefined-builtin  # signature fixed by BaseHTTPRequestHandler
    def log_message(self, format: str, *args: Any) -> None:
        """Route access logs to logging.

        Args:
            format: printf-style format.
            *args: Format arguments.
        """
        LOG.debug(format, *args)

    def _send(self, code: int, payload: Any = None, ctype: str = "application/json") -> None:
        """Write a response.

        Args:
            code: HTTP status.
            payload: Bytes for HTML, otherwise a JSON-serialisable object.
            ctype: Content type.
        """
        data = payload if isinstance(payload, bytes) else json.dumps(payload or {}).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # pylint: disable=invalid-name  # http.server naming
        """Serve the page, the interface list and the flow snapshot."""
        cap = self.server.capture
        if self.path == "/":
            self._send(HTTPStatus.OK, INDEX_HTML.read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/interfaces":
            names = sorted(p.name for p in agent.SYS_NET.iterdir() if p.name != MGMT_IFACE)
            self._send(HTTPStatus.OK, {"interfaces": names, "default": DEFAULT_IFACE,
                                       "model": cap.default_model})
        elif self.path == "/api/flows":
            self._send(HTTPStatus.OK, cap.snapshot())
        else:
            self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:  # pylint: disable=invalid-name  # http.server naming
        """Handle start and stop."""
        cap = self.server.capture
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if length < 0 or length > MAX_BODY:
            self._send(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "body too large"})
        elif self.path == "/api/stop":
            self.rfile.read(length)
            cap.stop()
            self._send(HTTPStatus.OK, {"stopped": True})
        elif self.path == "/api/start":
            self._start(cap, self.rfile.read(length))
        else:
            self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def _start(self, cap: Capture, body: bytes) -> None:
        """Validate and start a capture, mapping failures to status codes.

        Args:
            cap: The capture state.
            body: Raw request body.
        """
        try:
            cap.start(*parse_start(body, cap.default_model))
        except BadRequest as exc:
            self._send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except RuntimeError as exc:
            self._send(HTTPStatus.CONFLICT, {"error": str(exc)})
        except (ValueError, OSError) as exc:
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
        else:
            self._send(HTTPStatus.ACCEPTED, {"started": True})


class UiServer(ThreadingHTTPServer):
    """HTTP server that carries the capture state."""

    daemon_threads = True

    def __init__(self, addr: tuple[str, int], default_model: str) -> None:
        """Bind the socket.

        Args:
            addr: (host, port); port 0 picks a free port.
            default_model: Model preselected in the UI.
        """
        super().__init__(addr, Handler)
        self.capture = Capture(default_model)


def main(argv: list[str] | None = None) -> int:
    """Serve the UI until interrupted.

    Args:
        argv: Arguments without the program name.

    Returns:
        0 on a clean exit.
    """
    p = argparse.ArgumentParser(description="Lab 4 web UI")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--model", type=str.upper, choices=sorted(MODEL_MODES), default="ALL")
    args = p.parse_args(argv)
    setup_logging(DEFAULT_OUT / "webui")
    server = UiServer((args.host, args.port), args.model)
    LOG.info("serving on http://%s:%d", *server.server_address)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.capture.stop()
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
