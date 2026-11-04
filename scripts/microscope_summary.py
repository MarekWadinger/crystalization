"""Crystal sizes vs time since seeding, ZRA lab run 2026-10-30.

Reads the AI transcription of the burned-in microscope measurements
(``datasets/microscope_annotations.csv``, one row per green line) and the
run sidecar (``datasets/2026-10-30 08-45-33.json``: sample times and the
two seeding events). Prints one row per sample: batch, sample time,
minutes since that batch's seeding, number of measured crystals, and
min / median / max length in µm. ``kind == "scale"`` rows (reference
lines, field width) and unreadable values are excluded.

The lengths are operator-chosen single chords, not a size distribution.

    uv run python scripts/microscope_summary.py [--csv]
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "datasets" / "microscope_annotations.csv"
SIDECAR = ROOT / "datasets" / "2026-10-30 08-45-33.json"


def summary_rows() -> list[list[object]]:
    """One row per sample: batch, HH:MM, min since seeding, id, n, min/median/max µm."""
    side = json.loads(SIDECAR.read_text())
    seed = {
        e["id"].split("-")[0]: datetime.fromisoformat(e["wallclock"])
        for e in side["events"]
        if e.get("is_seeding")
    }
    vals: dict[str, list[float]] = defaultdict(list)
    when: dict[str, str] = {}
    for r in csv.DictReader(CSV.open(newline="")):
        if r["kind"] != "crystal" or not r["value_mm"]:
            continue
        key = r["sample_id"] or r["photo"]
        vals[key].append(float(r["value_mm"]) * 1000.0)
        when[key] = r["sample_wallclock"]

    rows: list[list[object]] = []
    for key, v in vals.items():
        wc = when[key]
        batch = key.split("-")[0] if wc else ""
        dt_min = (
            round(
                (datetime.fromisoformat(wc) - seed[batch]).total_seconds() / 60
            )
            if wc and batch in seed
            else ""
        )
        rows.append(
            [batch or "-", wc[11:16] if wc else "-", dt_min, key, len(v),
             round(min(v)), round(statistics.median(v)), round(max(v))]
        )  # fmt: skip
    rows.sort(key=lambda r: (str(r[0]), str(r[1])))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--csv", action="store_true", help="CSV output")
    a = ap.parse_args()

    side = json.loads(SIDECAR.read_text())
    seed = {
        e["id"].split("-")[0]: datetime.fromisoformat(e["wallclock"])
        for e in side["events"]
        if e.get("is_seeding")
    }
    rows = summary_rows()
    head = ["batch", "sample", "min_since_seeding", "id", "n",
            "min_um", "median_um", "max_um"]  # fmt: skip
    if a.csv:
        w = csv.writer(__import__("sys").stdout, lineterminator="\n")
        w.writerow(head)
        w.writerows(rows)
        return
    print("seeding:", {k: v.strftime("%H:%M:%S") for k, v in seed.items()})
    print("{:>5} {:>6} {:>5} {:<10} {:>3} {:>6} {:>6} {:>6}".format(*head[:8]))
    for r in rows:
        print("{:>5} {:>6} {:>5} {:<10} {:>3} {:>6} {:>6} {:>6}".format(*r))


if __name__ == "__main__":
    main()
