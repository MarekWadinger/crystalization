"""Camera crystals traced by hand on raw PAL frames vs the microscope, 2026-10-30.

    uv run python scripts/traced_vs_lab.py

Reads ``datasets/camera_traced_chords.csv`` (max-Feret chords on raw PAL frames at
four lab sample times, endpoints in frame px; method ``chord`` = longest chord of
clearly bounded crystals, ``outline`` = max Feret of full-outline annotations of
every crystal, frame-edge crystals dropped; readers are blind AI annotators) and the microscope
chords in ``datasets/microscope_annotations.csv``. Converts traced chords to µm at
the modelled per-axis scale and prints, per sample and reader, the traced and lab
p50/p90 and their ratio k = lab / traced.

k constant over time  -> the camera sees the lab-size crystals; k is the scale
                         correction (or operator selection) and the detector
                         causes the drift of the Cellpose sizes.
k drifting with time  -> the camera sees a different population.
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

from optics.config import lens_from_config, load_camera, um_per_px_xy_at_focus

ROOT = Path(__file__).resolve().parents[1]
TRACED = ROOT / "datasets" / "camera_traced_chords.csv"
LAB = ROOT / "datasets" / "microscope_annotations.csv"
CLOCK = {
    "b1-s05": "12:07",
    "b1-s07": "12:30",
    "b1-s10": "13:32",
    "b1-s12": "14:20",
}


def _q(v: list[float], p: float) -> float:
    return float(np.percentile(v, p))


def main() -> None:
    cfg = load_camera()
    ux, uy = um_per_px_xy_at_focus(cfg, lens_from_config(cfg, 720, 576))
    traced: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in csv.DictReader(TRACED.open()):
        dx = (float(r["x2"]) - float(r["x1"])) * ux
        dy = (float(r["y2"]) - float(r["y1"])) * uy
        traced[(r["sample"], r["reader"])].append(math.hypot(dx, dy))
        traced[(r["sample"], r["method"] + "s")].append(math.hypot(dx, dy))
    lab: dict[str, list[float]] = defaultdict(list)
    for r in csv.DictReader(LAB.open()):
        if (
            r["kind"] == "crystal"
            and r["sample_id"] in CLOCK
            and r["value_mm"]
        ):
            lab[r["sample_id"]].append(1000.0 * float(r["value_mm"]))
    pooled = ["chords", "outlines"]
    readers = sorted({k[1] for k in traced} - set(pooled)) + pooled
    print(f"model scale {ux:.3f} x {uy:.3f} um/px (PAL)")
    print(
        f"{'sample':7} {'clock':5} {'reader':6} {'n':>3} {'cam p50':>8} {'cam p90':>8}"
        f" {'lab n':>5} {'lab p50':>8} {'lab p90':>8} {'k p50':>6} {'k p90':>6}"
    )
    for s, clock in CLOCK.items():
        lv = lab[s]
        for rd in readers:
            cv = traced.get((s, rd))
            if not cv:
                continue
            print(
                f"{s:7} {clock:5} {rd:6} {len(cv):3d} {_q(cv, 50):8.0f} {_q(cv, 90):8.0f}"
                f" {len(lv):5d} {_q(lv, 50):8.0f} {_q(lv, 90):8.0f}"
                f" {_q(lv, 50) / _q(cv, 50):6.2f} {_q(lv, 90) / _q(cv, 90):6.2f}"
            )
    # Growth: slope 1 = traced camera sizes grow with the lab; the Cellpose p90 gives 0.2-0.45.
    for m in pooled:
        lab90 = [math.log(_q(lab[s], 90)) for s in CLOCK]
        cam90 = [math.log(_q(traced[(s, m)], 90)) for s in CLOCK]
        print(
            f"log-log slope of {m} p90 vs lab p90: {np.polyfit(lab90, cam90, 1)[0]:.2f}"
        )


if __name__ == "__main__":
    main()
