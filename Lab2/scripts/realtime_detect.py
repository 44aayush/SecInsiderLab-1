"""Task F3 real-time: stream a CICFlowMeter V4 flow CSV through the trained pipeline."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from ddosids import config
from ddosids.realtime.detector import Detector, stream

RED, RESET = "\033[91m", "\033[0m"


class Tee:
    """Print to stdout and collect lines; colour only on a TTY (log stays plain)."""

    def __init__(self) -> None:
        self.lines: list[str] = []
        self.tty = sys.stdout.isatty()

    def __call__(self, text: str = "", red: bool = False) -> None:
        print(f"{RED}{text}{RESET}" if red and self.tty else text)
        self.lines.append(text)


def _line(r: pd.Series) -> str:
    def i(v):
        try:
            return str(int(float(v)))
        except (TypeError, ValueError):
            return str(v)
    return (f"{r.get('Timestamp', '?')}  {r.get('Src IP', '?')}:{i(r.get('Src Port'))} → "
            f"{r.get('Dst IP', '?')}:{i(r.get('Dst Port'))}/{i(r.get('Protocol'))}  "
            f"{r['pred']}  p={r['p_attack']:.2f}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("flows_csv", type=Path)
    p.add_argument("--rate", type=float, default=None, help="flows per second (default: unthrottled)")
    p.add_argument("--model", default=config.REALTIME_MODEL)
    p.add_argument("--models-dir", type=Path, default=config.ARTIFACTS_DIR / "models")
    p.add_argument("--outputs-dir", type=Path, default=config.OUTPUTS_DIR)
    a = p.parse_args(argv)

    out = a.outputs_dir / "realtime"
    out.mkdir(parents=True, exist_ok=True)
    say = Tee()
    det = Detector(a.model, a.models_dir)
    df = pd.read_csv(a.flows_csv, skipinitialspace=True)
    df.columns = df.columns.str.strip()
    say(f"Model: {a.model} | input: {a.flows_csv} | {len(df)} flows")

    parts, dropped, replaced = [], 0, 0
    for res in stream(df, det, batch_size=1, rate=a.rate):
        st = res.attrs["stats"]
        dropped += st["protocol0_dropped"]
        replaced += st["cells_replaced"]
        for _, r in res.iterrows():
            say(_line(r), red=bool(r["is_alert"]))
        parts.append(res)

    results = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    results.to_csv(out / "predictions.csv", index=False)
    n = len(results)
    n_alert = int(results["is_alert"].sum()) if n else 0
    lat = np.array(det.latencies_ms)
    bar = "=" * 72
    say(f"\n{bar}\nSummary\n{bar}")
    say(f"model                    : {a.model}")
    say(f"flows read               : {len(df)}")
    say(f"Protocol-0 rows dropped  : {dropped}")
    say(f"inf/NaN cells replaced   : {replaced}")
    say(f"flows classified         : {n}")
    say(f"BENIGN                   : {n - n_alert}")
    say(f"DDoS (alerts)            : {n_alert}")
    say(f"alert rate               : {100 * n_alert / n if n else 0:.2f} %")
    if len(lat):
        say(f"latency per flow (ms)    : mean {lat.mean():.3f} | median {np.median(lat):.3f}")
    if n_alert:
        say("Alert flows:")
        for _, r in results[results["is_alert"]].iterrows():
            say("  " + _line(r), red=True)
    else:
        say("Alert flows: none")
    (out / "run_log.txt").write_text("\n".join(say.lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
