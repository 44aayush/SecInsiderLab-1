"""Build tests/fixtures/sample_ddos.csv from the full Friday CSV at raw line level (seed fixed)."""
from __future__ import annotations

import random
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "Friday-WorkingHours-Afternoon-DDos.csv"
DST = Path(__file__).with_name("sample_ddos.csv")
SEED = 42


def label_of(line: bytes) -> bytes:
    return line.rstrip(b"\r\n").rsplit(b",", 1)[1]


def main() -> None:
    rng = random.Random(SEED)
    lines = SRC.read_bytes().splitlines(keepends=True)
    header, rows = lines[0], lines[1:]
    counts = Counter(rows)
    benign: list[int] = []
    ddos: list[int] = []
    special: list[int] = []
    dup_idx: dict[bytes, list[int]] = {}
    for i, ln in enumerate(rows):
        (benign if label_of(ln) == b"BENIGN" else ddos).append(i)
        if b"Infinity" in ln or b"NaN" in ln:
            special.append(i)
        if counts[ln] > 1:
            dup_idx.setdefault(ln, []).append(i)
    assert len(special) == 34, len(special)  # all inf/NaN rows

    chosen: set[int] = set(special)
    chosen.update(rng.sample(ddos, 1500))
    chosen.update(rng.sample(benign, 1300))
    dups = sorted(dup_idx, key=lambda b: (label_of(b), b))
    benign_dups = [d for d in dups if label_of(d) == b"BENIGN"]
    other_dups = [d for d in dups if label_of(d) != b"BENIGN"]
    for d in rng.sample(benign_dups, 120) + rng.sample(other_dups, min(10, len(other_dups))):
        chosen.update(dup_idx[d])  # all copies
    out = [rows[i] for i in sorted(chosen)]
    DST.write_bytes(header + b"".join(out))
    print(f"wrote {len(out)} rows to {DST}")


if __name__ == "__main__":
    main()
