"""Probe: can the existing detector be retuned to resolve the 9 µm
seed-magma population?

Background (see §7 manuscript retraction). At 2.18 µm/px the current
edge-based detector's area filter [80, 8000] px² bandpasses ≈ 20–200
µm features, an order of magnitude above the Mastersizer-confirmed
crystal population (Dv50 = 6.81 µm, Dv90 = 18.5 µm). This script
sweeps min_area down toward the 9 µm scale and reports whether the
detector still produces structured output or collapses into noise.

The sweep also shrinks the morphological-closing kernel proportionally,
since a 3-px+ closing kernel would merge adjacent few-pixel crystals
into one over-area blob before the area filter sees them.

Output: docs/optics/figures/probe_detector_at_9um.png and a stdout
summary table of counts + size statistics per (min_area, morph_base)
combination. Interpretation is intentionally left to the reader — the
script is a measurement, not a verdict.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np

from annotator.detection import process_frame
from annotator.types import LayerConfig
from optics.video_io import DEFAULT_CROP

LONG_VIDEO = "datasets/2026-02-04 11-08-51.mp4"
# Mid-batch frame — slurry filling the field, well past start.
FRAME_INDEX = 18_000  # t ≈ 600 s into the recording, batch 1 active
MM_PER_PX = 2.18e-3  # documented optical scale

# Mastersizer ground-truth percentiles (µm) — for the reference overlay.
MASTERSIZER_DV = {
    "Dv10": 1.56,
    "Dv50": 6.81,
    "Dv90": 18.5,
    "D[4;3]": 8.71,
    "D[3;2]": 3.95,
}

# (min_area_px², morph_base) pairs to sweep. Morph base shrinks with
# min_area so the closing kernel doesn't fuse adjacent few-pixel
# features into one.
SWEEP: list[tuple[float, int]] = [
    (80.0, 3),  # current default — baseline
    (40.0, 3),
    (20.0, 3),
    (20.0, 1),  # also try smaller morph kernel
    (10.0, 1),
    (5.0, 1),
]


def _detect_with_config(
    gray: np.ndarray,
    config: LayerConfig,
) -> list[tuple[float, float, float]]:
    """Return list of (cx_px, cy_px, sqrt_area_px) for detections."""
    result, _ = process_frame(gray, None, FRAME_INDEX, config)
    out: list[tuple[float, float, float]] = []
    for layer in result.layers:
        for c in layer.crystals:
            # Geometric-mean side length — same convention as
            # CrystalObservation.apparent_size_px.
            side = float(np.sqrt(c.width * c.height))
            out.append((c.x, c.y, side))
    return out


def _percentile_text(sizes_um: np.ndarray) -> str:
    if sizes_um.size == 0:
        return "no detections"
    qs = np.quantile(sizes_um, [0.1, 0.5, 0.9])
    return (
        f"n={sizes_um.size:5d}  "
        f"p10={qs[0]:6.2f}µm  "
        f"p50={qs[1]:6.2f}µm  "
        f"p90={qs[2]:6.2f}µm"
    )


def main() -> None:
    cap = cv2.VideoCapture(LONG_VIDEO)
    cap.set(cv2.CAP_PROP_POS_FRAMES, FRAME_INDEX)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise RuntimeError(
            f"could not read frame {FRAME_INDEX} from {LONG_VIDEO}"
        )
    frame = DEFAULT_CROP.apply(frame)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    base_config = LayerConfig(
        num_layers=3,
        sharpness_weight=0.7,
        flow_weight=0.3,
        blur_kernel=15,
        max_area=8000.0,
        max_aspect_ratio=3.0,
    )

    print(f"Frame: {LONG_VIDEO} idx={FRAME_INDEX}")
    print(
        f"Crop: {gray.shape[1]}x{gray.shape[0]} px at {MM_PER_PX * 1e3:.2f} µm/px"
    )
    print("Mastersizer reference (µm):")
    for k, v in MASTERSIZER_DV.items():
        print(f"  {k:>6} = {v:.2f}")
    print()
    print("Sweep results:")

    fig, axes = plt.subplots(len(SWEEP), 2, figsize=(14, 3.0 * len(SWEEP)))

    for row, (min_area, morph_base) in enumerate(SWEEP):
        config = replace(
            base_config,
            min_area=min_area,
            morph_base=morph_base,
        )
        dets = _detect_with_config(gray, config)
        sizes_px = np.array([d[2] for d in dets], dtype=np.float64)
        sizes_um = sizes_px * MM_PER_PX * 1e3

        label = (
            f"min_area={min_area:5.1f} px² "
            f"(≈{np.sqrt(min_area) * MM_PER_PX * 1e3:5.1f} µm linear), "
            f"morph_base={morph_base}"
        )
        print(f"  {label}: {_percentile_text(sizes_um)}")

        # Left: detection overlay (sub-sampled if too many).
        ax_img = axes[row, 0]
        ax_img.imshow(gray, cmap="gray", aspect="equal")
        if dets:
            xs = [d[0] for d in dets]
            ys = [d[1] for d in dets]
            ss = [max(0.3, d[2]) for d in dets]
            ax_img.scatter(
                xs,
                ys,
                s=ss,
                edgecolors="red",
                facecolors="none",
                linewidths=0.4,
            )
        ax_img.set_title(f"{label}\nn={len(dets)} detections", fontsize=8)
        ax_img.axis("off")

        # Right: size histogram with Mastersizer reference lines.
        ax_h = axes[row, 1]
        if sizes_um.size:
            bins_arr = np.logspace(0, 3, 60)
            ax_h.hist(
                sizes_um, bins=bins_arr.tolist(), color="steelblue", alpha=0.75
            )
        ax_h.set_xscale("log")
        ax_h.set_xlabel("apparent size (µm)")
        ax_h.set_ylabel("count")
        for k, v in MASTERSIZER_DV.items():
            ax_h.axvline(v, color="green", lw=0.8, ls="--")
            ax_h.text(
                v,
                ax_h.get_ylim()[1] * 0.9 if sizes_um.size else 1.0,
                k,
                color="green",
                fontsize=6,
                ha="left",
                va="top",
                rotation=90,
            )
        ax_h.axvspan(
            np.sqrt(min_area) * MM_PER_PX * 1e3,
            np.sqrt(8000.0) * MM_PER_PX * 1e3,
            color="orange",
            alpha=0.1,
            label="bandpass",
        )
        ax_h.set_xlim(1, 1000)
        ax_h.set_title("size histogram + Mastersizer (green)", fontsize=8)

    fig.suptitle(
        f"Detector probe at 9 µm scale — frame {FRAME_INDEX} of {LONG_VIDEO}",
        fontsize=10,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    out = Path("docs/optics/figures/probe_detector_at_9um.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=120)
    print(f"\nSaved {out}")


if __name__ == "__main__":
    main()
