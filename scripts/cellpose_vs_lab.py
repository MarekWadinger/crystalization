"""Untuned Cellpose sizes vs the microscope at matched times, 2026-10-30.

    uv run python scripts/cellpose_vs_lab.py VIDEO

VIDEO is the LQ H.264 encoding of ``2026-10-30 08-45-33`` (location in
``datasets/README.md``). For every 4×-objective lab sample after 11:46, three
frames (sample ``t`` from the sidecar, ±60 s) are cut with ffmpeg and run
through the shipped ``crystal_detector`` pipeline (crop, flat-field + CLAHE,
current checkpoint, analyze.py thresholds) at several ``diameter`` settings.
Per sample it compares the camera 90th percentile of max Feret (µm at the
modelled per-axis scale) with the microscope 90th percentile from
``datasets/microscope_annotations.csv`` and prints, per batch and diameter,
the log-log slope of camera p90 on lab p90. Slope 1 = constant scale error;
slope < 1 = camera sizes level off.

Samples up to 11:46 are left out: there the outlines follow texture
(crystals span 3–9 px) and the microscope used the 10× objective.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

from crystal_detector.analyze import (
    CELLPROB_THRESHOLD,
    FLOW_THRESHOLD,
    crop,
    flat_field_correction,
    resolve_model,
)
from optics.config import lens_from_config, load_camera, um_per_px_xy_at_focus

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "datasets" / "microscope_annotations.csv"
SIDECAR = ROOT / "datasets" / "2026-10-30 08-45-33.json"
SAMPLES = [  # 4× objective, crystals resolved on PAL
    *("b1-s05 b1-s06 b1-s07 b1-s08 b1-s09 b1-s10 b1-s11 b1-s12".split()),
    *("b2-s04 b2-s05 b2-s06 b2-s07 b2-s08 b2-s09".split()),
]
OFFSETS_S = (-60, 0, 60)
DIAMETERS = (None, 45, 60, 90)
MIN_AREA_PX = 15


def _frame(video: str, t: float, tmp: Path) -> np.ndarray:
    png = tmp / f"{t:.0f}.png"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-ss",
            f"{t}",
            "-i",
            video,
            "-frames:v",
            "1",
            str(png),
        ],
        check=True,
    )
    bgr = cv2.imread(str(png))
    if bgr is None or bgr.shape[:2] != (576, 720):
        raise SystemExit(
            f"bad frame at t={t}: {None if bgr is None else bgr.shape}"
        )
    return bgr


def _ferets_um(masks: np.ndarray, ux: float, uy: float) -> list[float]:
    out = []
    for i in range(1, int(masks.max()) + 1):
        ys, xs = np.nonzero(masks == i)
        if len(xs) < MIN_AREA_PX:
            continue
        pts = np.c_[xs, ys].astype(np.float32)
        h = cv2.convexHull(pts).reshape(-1, 2) * (ux, uy)
        out.append(float(np.sqrt(((h[:, None] - h[None]) ** 2).sum(-1)).max()))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument("video")
    a = ap.parse_args()

    from cellpose import models

    t_of = {
        s["id"]: float(s["t"])
        for s in json.loads(SIDECAR.read_text())["samples"]
    }
    lab: dict[str, list[float]] = defaultdict(list)
    for r in csv.DictReader(LAB.open()):
        if (
            r["kind"] == "crystal"
            and r["sample_id"] in SAMPLES
            and r["value_mm"]
        ):
            lab[r["sample_id"]].append(1000 * float(r["value_mm"]))

    cfg = load_camera()
    ux, uy = um_per_px_xy_at_focus(cfg, lens_from_config(cfg, 720, 576))
    model = models.CellposeModel(
        gpu=True, pretrained_model=str(resolve_model())
    )
    cam: dict[tuple[str, object], list[float]] = defaultdict(list)
    count: dict[tuple[str, object], list[int]] = defaultdict(list)
    with tempfile.TemporaryDirectory() as d:
        for s in SAMPLES:
            for dt in OFFSETS_S:
                img = flat_field_correction(
                    crop(_frame(a.video, t_of[s] + dt, Path(d)))
                )
                for dia in DIAMETERS:
                    masks = model.eval(
                        img,
                        diameter=dia,
                        flow_threshold=FLOW_THRESHOLD,
                        cellprob_threshold=CELLPROB_THRESHOLD,
                    )[0]
                    f = _ferets_um(masks, ux, uy)
                    cam[(s, dia)] += f
                    count[(s, dia)].append(len(f))

    print(f"scale {ux:.2f} × {uy:.2f} µm/px; p90 in µm")
    print(
        f"{'sample':8} {'lab p90':>8} "
        + " ".join(f"{'d=' + str(x):>9}" for x in DIAMETERS)
    )
    for s in SAMPLES:
        row = " ".join(
            f"{np.percentile(cam[(s, x)], 90):9.0f}" for x in DIAMETERS
        )
        print(f"{s:8} {np.percentile(lab[s], 90):8.0f} {row}")
    print(
        "crystals per frame (d=None):",
        f"{min(min(count[(s, None)]) for s in SAMPLES)}–{max(max(count[(s, None)]) for s in SAMPLES)}",
    )
    slopes = []
    for b in ("b1", "b2"):
        mine = [s for s in SAMPLES if s.startswith(b)]
        x = np.log([np.percentile(lab[s], 90) for s in mine])
        for dia in DIAMETERS:
            y = np.log([np.percentile(cam[(s, dia)], 90) for s in mine])
            k = float(np.polyfit(x, y, 1)[0])
            slopes.append(k)
            print(f"slope {b} d={dia}: {k:.2f}")
    print(f"slope range: {min(slopes):.2f}–{max(slopes):.2f}")


if __name__ == "__main__":
    main()
