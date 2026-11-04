"""2026-10-30 sampled run: microscope sizes and traced camera chords per strike.

Times are minutes since that strike's seeding, from the run sidecar's video
seconds ``t`` (sample ``t`` − seeding event ``t``), so b1 is seeded at
11:29:33 and b2 at 15:22:00.
"""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from optics.config import lens_from_config, load_camera, um_per_px_xy_at_focus

ROOT = Path(__file__).resolve().parents[2]
SIDECAR = ROOT / "datasets" / "2026-10-30 08-45-33.json"
MICROSCOPE = ROOT / "datasets" / "microscope_annotations.csv"
TRACED = ROOT / "datasets" / "camera_traced_chords.csv"
PRE_SEED = frozenset({"b1-s02"})
"""Samples taken before seeding (sidecar comment 'pred očkom')."""


@dataclass(frozen=True, slots=True)
class Sample:
    """One microscope sample: time since seeding and its crystal chords."""

    sample_id: str
    t_min: float
    sizes_um: np.ndarray

    @property
    def median_um(self) -> float:
        return float(np.median(self.sizes_um))


def seeding_t_s() -> dict[str, float]:
    """Video seconds of each strike's seeding event (sidecar)."""
    side = json.loads(SIDECAR.read_text())
    return {
        e["id"].split("-")[0]: float(e["t"])
        for e in side["events"]
        if e.get("is_seeding")
    }


def microscope_samples() -> dict[str, list[Sample]]:
    """Post-seeding microscope samples per strike, sorted by time."""
    side = json.loads(SIDECAR.read_text())
    t_s = {s["id"]: float(s["t"]) for s in side["samples"]}
    seed = seeding_t_s()
    vals: dict[str, list[float]] = defaultdict(list)
    for r in csv.DictReader(MICROSCOPE.open(newline="")):
        sid = r["sample_id"]
        if r["kind"] == "crystal" and r["value_mm"] and sid in t_s:
            vals[sid].append(1000.0 * float(r["value_mm"]))
    out: dict[str, list[Sample]] = defaultdict(list)
    for sid, v in vals.items():
        if sid in PRE_SEED:
            continue
        b = sid.split("-")[0]
        t = (t_s[sid] - seed[b]) / 60.0
        out[b].append(Sample(sid, t, np.array(v)))
    return {b: sorted(s, key=lambda x: x.t_min) for b, s in out.items()}


@dataclass(frozen=True, slots=True)
class TracedFrame:
    """Median traced chord of one reader on one raw PAL frame."""

    reader: str
    frame: str
    t_min: float
    n: int
    median_um: float


def traced_frames(
    method: str = "chord", strike: str = "b1"
) -> list[TracedFrame]:
    """Per (frame, reader) medians of the blind AI traces, in µm.

    Chords are converted per axis at the modelled PAL scale from
    ``configs/camera_100.toml`` (as ``scripts/traced_vs_lab.py``). The frame
    time is the raw frame's video second (its file name) since seeding.
    """
    cfg = load_camera()
    ux, uy = um_per_px_xy_at_focus(cfg, lens_from_config(cfg, 720, 576))
    seed = seeding_t_s()[strike]
    chords: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in csv.DictReader(TRACED.open(newline="")):
        if r["method"] != method or not r["sample"].startswith(strike):
            continue
        dx = (float(r["x2"]) - float(r["x1"])) * ux
        dy = (float(r["y2"]) - float(r["y1"])) * uy
        chords[(r["reader"], r["raw_frame"])].append(math.hypot(dx, dy))
    out = [
        TracedFrame(
            reader=rd,
            frame=fr,
            t_min=(float(fr.removeprefix("raw_").removesuffix(".png")) - seed)
            / 60.0,
            n=len(v),
            median_um=float(np.median(v)),
        )
        for (rd, fr), v in chords.items()
    ]
    return sorted(out, key=lambda f: (f.t_min, f.reader))
