"""Label-free checks of the two classical detectors (CEP paper §7).

No hand-labelled crystals are used. Two checks:

``sweep``  Watershed seed constants on the case-study clip
           (``datasets/2026-02-05 10-36-32.mp4``). ``_PEAK_MIN_DISTANCE`` and
           ``_PEAK_THRESHOLD_ABS`` of ``optics.detect_watershed`` are varied one
           at a time (and jointly); for each setting the script prints the
           detections per frame, the median and 5th percentile of the
           area-equivalent size at the focal-plane clip scale, and the share of
           the cropped frame covered by the kept basins (direct evidence of
           tiling). Single frames, no optical flow, configured area window.

``time``   Both detectors against time since seeding on the full strike b2 of
           the 2026-02-04 PAL recording (``datasets/2026-02-04 11-08-51.mp4``;
           seeding = sidecar event ``b2-e06``, 12:30, operator log, SCADA steam
           cut 12:31:30). At each time 10 frames 1 s apart are run through
           ``optics.disambiguate.detect_observations`` with the configured PAL
           window and the automatic crop; sizes are area-equivalent at the
           focal-plane PAL scale. The microscope medians of 2026-10-30 (another
           day, operator-picked chords, ``scripts/microscope_summary.py``) are
           drawn for reference in ``docs/optics/figures/19_detector_vs_time.png``.

    uv run --frozen python scripts/detector_checks.py sweep
    uv run --frozen python scripts/detector_checks.py time [--no-fig]
    uv run --frozen python scripts/detector_checks.py all --json out.json

Neither check is a crystal-size measurement.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)  # the optics modules read datasets/ relative to the repo
sys.path.insert(0, str(ROOT / "scripts"))

import optics.detect_watershed as ws  # noqa: E402
from annotator.types import Crystal, LayerConfig  # noqa: E402
from optics.config import (  # noqa: E402
    detection_area_px,
    lens_from_config,
    load_camera,
)
from optics.model import mm_per_pixel_at  # noqa: E402

CLIP = "datasets/2026-02-05 10-36-32.mp4"
PAL = "datasets/2026-02-04 11-08-51.mp4"
PAL_SIDECAR = "datasets/2026-02-04 11-08-51.json"
SWEEP_FRAMES = (150, 400, 650, 900, 1150, 1400)
# (min distance px, threshold px); the configured constants are (12, 6).
SWEEP = (
    (6, 6.0),
    (8, 6.0),
    (12, 6.0),
    (16, 6.0),
    (24, 6.0),
    (12, 3.0),
    (12, 9.0),
    (6, 3.0),
    (24, 12.0),
)
TIMES_MIN = (-40, -20, 0, 10, 20, 30, 45, 60, 90, 120, 150, 180, 200)
N_PER_TIME, STRIDE_S = 10, 1.0

CFG = load_camera()


def _layer_config(window: tuple[float, float]) -> LayerConfig:
    return LayerConfig(
        num_layers=3,
        sharpness_weight=0.7,
        flow_weight=0.3,
        blur_kernel=15,
        min_area=window[0],
        max_area=window[1],
        max_aspect_ratio=3.0,
    )


def sweep() -> list[dict[str, float]]:
    """Watershed output on the clip for each seed-constant setting."""
    import cv2

    from optics.video_io import resolve_crop

    lens = lens_from_config(CFG, CFG.display_width_px, CFG.display_height_px)
    d = CFG.focus_object_distance_mm
    um_px = 1e3 * float(mm_per_pixel_at(lens, d, np.array([d]))[0])
    cfg_l = _layer_config(detection_area_px(CFG, lens))
    crop = resolve_crop(CLIP, None)
    cap = cv2.VideoCapture(CLIP)
    grays = []
    for idx in SWEEP_FRAMES:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f"cannot read frame {idx} of {CLIP}")
        grays.append(cv2.cvtColor(crop.apply(frame), cv2.COLOR_BGR2GRAY))
    cap.release()

    orig = (
        ws._PEAK_MIN_DISTANCE,
        ws._PEAK_THRESHOLD_ABS,
        ws._crystal_from_region,
    )
    kept: list[int] = []

    def recording(
        region: NDArray[np.uint8], config: LayerConfig
    ) -> Crystal | None:
        cry = orig[2](region, config)
        if cry is not None:
            kept.append(int(cv2.countNonZero(region)))
        return cry

    rows = []
    try:
        setattr(ws, "_crystal_from_region", recording)  # noqa: B010
        for md, thr in SWEEP:
            setattr(ws, "_PEAK_MIN_DISTANCE", md)  # noqa: B010
            setattr(ws, "_PEAK_THRESHOLD_ABS", thr)  # noqa: B010
            sizes: list[float] = []
            cover: list[float] = []
            for idx, g in zip(SWEEP_FRAMES, grays, strict=True):
                kept.clear()
                res, _ = ws.process_frame_watershed(g, None, idx, cfg_l)
                sizes += [
                    c.size for layer in res.layers for c in layer.crystals
                ]
                cover.append(sum(kept) / g.size)
            s = np.asarray(sizes) * um_px
            rows.append(
                {
                    "min_distance_px": md,
                    "threshold_px": thr,
                    "per_frame": len(sizes) / len(SWEEP_FRAMES),
                    "median_um": float(np.median(s)),
                    "p05_um": float(np.percentile(s, 5)),
                    "coverage": float(np.mean(cover)),
                }
            )
    finally:
        for name, value in zip(
            (
                "_PEAK_MIN_DISTANCE",
                "_PEAK_THRESHOLD_ABS",
                "_crystal_from_region",
            ),
            orig,
            strict=True,
        ):
            setattr(ws, name, value)
    return rows


def detector_vs_time() -> list[dict[str, float | str]]:
    """Edge and watershed medians against time since seeding, PAL strike b2."""
    import cv2

    from optics.disambiguate import detect_observations
    from optics.video_io import resolve_crop

    side = json.loads(Path(PAL_SIDECAR).read_text())
    seed_id = side["kpi_pairing_hint"]["seeding_event_id"]
    t_seed = next(e["t"] for e in side["events"] if e["id"] == seed_id)
    lens = lens_from_config(CFG)  # PAL raster
    cfg_l = _layer_config(detection_area_px(CFG, lens))
    crop = resolve_crop(PAL, None)
    cap = cv2.VideoCapture(PAL)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    rows: list[dict[str, float | str]] = []
    for tm in TIMES_MIN:
        start = round((t_seed + 60.0 * tm) * fps)
        for det in ("edge", "watershed"):
            print(f"[time] {tm:+d} min {det}", file=sys.stderr, flush=True)
            obs = detect_observations(
                PAL,
                cfg_l,
                frame_stride=round(STRIDE_S * fps),
                max_frames=N_PER_TIME,
                start_frame=start,
                crop=crop,
                detector=det,
            )
            # PAL samples, not µm: the scale is not validated in the image
            s = np.array([o.apparent_size_px for o in obs])
            rows.append(
                {
                    "t_min": tm,
                    "detector": det,
                    "per_frame": len(s) / N_PER_TIME,
                    "median_px": float(np.median(s))
                    if s.size
                    else float("nan"),
                    "p25_px": float(np.percentile(s, 25))
                    if s.size
                    else float("nan"),
                    "p75_px": float(np.percentile(s, 75))
                    if s.size
                    else float("nan"),
                }
            )
    return rows


def fig_detector_vs_time(
    rows: list[dict[str, float | str]], out: Path
) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.8, 4.0))
    for det, col, mk in (("edge", "C0", "o"), ("watershed", "C1", "s")):
        r = [x for x in rows if x["detector"] == det]
        t = np.array([x["t_min"] for x in r], dtype=float)
        med = np.array([x["median_px"] for x in r], dtype=float)
        lo = np.array([x["p25_px"] for x in r], dtype=float)
        hi = np.array([x["p75_px"] for x in r], dtype=float)
        ax.fill_between(t, lo, hi, color=col, alpha=0.15, linewidth=0)
        ax.plot(
            t, med, color=col, marker=mk, label=f"{det} detector, median (IQR)"
        )
    ax.axvline(0.0, color="0.5", linestyle="--", linewidth=1.0)
    ax.set_yscale("log")
    ax.set_xlabel("time since seeding (min)")
    ax.set_ylabel("area-equivalent size (PAL samples, log)")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=8, loc="center right")
    fig.tight_layout()
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)


def _print_sweep(rows: list[dict[str, float]]) -> None:
    print(
        "| min distance (px) | threshold (px) | detections / frame | median (µm) | p5 (µm) | basin coverage |"
    )
    print("|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        print(
            f"| {r['min_distance_px']:.0f} | {r['threshold_px']:.0f} | {r['per_frame']:.0f} | "
            f"{r['median_um']:.0f} | {r['p05_um']:.0f} | {100 * r['coverage']:.0f} % |"
        )


def _print_time(rows: list[dict[str, float | str]]) -> None:
    print(
        "| t since seeding (min) | detector | detections / frame | median (PAL samples) | IQR (PAL samples) |"
    )
    print("|---:|---|---:|---:|---|")
    for r in rows:
        print(
            f"| {r['t_min']} | {r['detector']} | {r['per_frame']:.0f} | {r['median_px']:.1f} | "
            f"{r['p25_px']:.1f}–{r['p75_px']:.1f} |"
        )


def main() -> None:
    p = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    p.add_argument("check", choices=("sweep", "time", "all"))
    p.add_argument("--json", type=Path, help="also write the rows here")
    p.add_argument("--no-fig", action="store_true", help="skip figure 19")
    a = p.parse_args()
    out: dict[str, object] = {}
    if a.check in ("sweep", "all"):
        sw = sweep()
        out["sweep"] = sw
        _print_sweep(sw)
    if a.check in ("time", "all"):
        rows = detector_vs_time()
        out["time"] = rows
        _print_time(rows)
        if not a.no_fig:
            fig_detector_vs_time(
                rows, Path("docs/optics/figures/19_detector_vs_time.png")
            )
    if a.json:
        a.json.write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
