"""Three ways to remove static glass artefacts ("ruptures") from a slurry frame.

Compared on the same target frame in batch 1 drying→discharge so the methods
are directly comparable. Each method addresses a different failure mode of
plain image-level subtraction (which mostly captured the illumination shift,
not the ruptures).

METHOD 1 — Temporal median subtraction
  Build a "static background" not from an empty interval, but from a short
  time window AROUND the target frame (e.g. ±5 s). The per-pixel median over
  that window is "everything that didn't move in 10 s" — ruptures, LED gradient,
  slowly-drifting slurry texture. Subtracting it leaves only motion: crystals,
  bubbles, density swirls. NO reference image needed.

METHOD 2 — Divisive normalisation against the empty reference
  slurry / (empty_ref + ε). The LED gradient is *multiplicative* (it scales
  everything by some factor at each pixel), so dividing cancels it cleanly.
  Look for deviations from 1.

METHOD 3 — Spatial high-pass filter
  Subtract a heavily blurred version of the slurry frame from the slurry frame
  itself. Removes everything that varies slowly across the image — LED gradient,
  big bright zones — and keeps fine-grained edges. Needs no reference at all.

OUTPUT FILES (self-documenting):
  rq4_rupture_removal_all_methods.png
    8 panels — raw frame on the left, then each method's processed image
    next to its edge map.

  rq4_rupture_removal_hist.png
    Per-pixel sharpness distributions for each method overlaid on one axes,
    so you can read off mean, spread, where each one sits.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np

from optics.video_io import DEFAULT_CROP

LONG_VIDEO = "datasets/2026-02-04 11-08-51.mp4"
FPS = 30.0

# Same windows as the rest of the RQ4 work.
EMPTY_WINDOW = (2300.0, 2450.0)  # for method 2 (divisive normalisation)
DEFAULT_SAMPLE_T = 1750.0  # representative b1 drying→discharge frame

# Method 1: temporal window radius around the target frame (seconds).
TEMPORAL_RADIUS_S = 5.0
TEMPORAL_N_FRAMES = 21  # ~2 Hz sampling across 10 s window


def _grab_frame(t: float) -> np.ndarray:
    cap = cv2.VideoCapture(LONG_VIDEO)
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(t * FPS)))
    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise RuntimeError(f"could not read frame at t={t}")
    return cv2.cvtColor(DEFAULT_CROP.apply(frame), cv2.COLOR_BGR2GRAY).astype(
        np.float64
    )


def _median_window(t_centre: float, radius_s: float, n: int) -> np.ndarray:
    """Per-pixel median of n frames evenly sampled in [t-radius, t+radius]."""
    times = np.linspace(t_centre - radius_s, t_centre + radius_s, n)
    grays = [_grab_frame(t) for t in times]
    return np.median(np.stack(grays, axis=0), axis=0)


def _empty_ref(t0: float, t1: float, n: int) -> np.ndarray:
    times = np.linspace(t0, t1, n)
    grays = [_grab_frame(t) for t in times]
    return np.median(np.stack(grays, axis=0), axis=0)


def _sharp(gray: np.ndarray) -> np.ndarray:
    """Gaussian-smoothed Laplacian² — the pipeline's sharpness measure."""
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    return cv2.GaussianBlur(lap**2, (15, 15), 0)


def method_1_temporal(
    target: np.ndarray, t_centre: float
) -> tuple[np.ndarray, np.ndarray, str]:
    """Subtract a ±5 s temporal median. Returns (processed, sharpness, label)."""
    bg = _median_window(t_centre, TEMPORAL_RADIUS_S, TEMPORAL_N_FRAMES)
    processed = np.abs(target - bg)
    return (
        processed,
        _sharp(processed),
        (
            f"Method 1 — temporal median subtraction\n"
            f"|frame@{t_centre:.0f}s − median(frame@{t_centre - TEMPORAL_RADIUS_S:.0f}..{t_centre + TEMPORAL_RADIUS_S:.0f}s)|\n"
            f"static-content cancellation, no empty reference needed"
        ),
    )


def method_2_divisive(
    target: np.ndarray, ref_img: np.ndarray
) -> tuple[np.ndarray, np.ndarray, str]:
    """Divide by the empty reference. Multiplicative LED-gradient cancels.

    Output is "deviation from 1" rescaled to 0–255 for visualisation; the
    raw ratio is unitless.
    """
    eps = 1.0
    ratio = target / (ref_img + eps)
    # Express as |ratio − 1| × 128 so a uniform image would be black, and
    # scenes that differ from the empty ref show up as bright.
    deviation = np.abs(ratio - 1.0) * 128.0
    # Clip to a sensible visualisation range (raw deviation has a heavy tail).
    deviation = np.clip(deviation, 0, 255)
    return (
        deviation,
        _sharp(deviation),
        (
            "Method 2 — divisive normalisation\n"
            "|slurry / (empty_ref + 1) − 1| × 128, clipped 0–255\n"
            "cancels multiplicative LED gradient cleanly"
        ),
    )


def method_3_highpass(
    target: np.ndarray, sigma_px: float = 25.0
) -> tuple[np.ndarray, np.ndarray, str]:
    """Subtract a heavily-blurred copy of the frame from itself.

    Removes anything varying slower than ~sigma pixels (LED gradient, bulk
    brightness shifts). Keeps fine-grained edges. No reference image used.
    """
    k = int(sigma_px) * 6 + 1
    lowpass = cv2.GaussianBlur(target, (k, k), sigma_px)
    processed = np.abs(target - lowpass)
    return (
        processed,
        _sharp(processed),
        (
            f"Method 3 — spatial high-pass filter\n"
            f"|frame − GaussianBlur(frame, σ={sigma_px:.0f} px)|\n"
            f"no reference needed, no temporal data needed"
        ),
    )


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--t",
        type=float,
        default=DEFAULT_SAMPLE_T,
        help="seconds into the long video for the target slurry frame",
    )
    p.add_argument("--empty-frames", type=int, default=40)
    p.add_argument(
        "--out-images",
        type=Path,
        default=Path(
            "docs/optics/figures/rq4_rupture_removal_all_methods.png"
        ),
    )
    p.add_argument(
        "--out-hist",
        type=Path,
        default=Path("docs/optics/figures/rq4_rupture_removal_hist.png"),
    )
    args = p.parse_args(argv)

    target = _grab_frame(args.t)
    print(
        f"[target] frame at t={args.t:.0f} s loaded ({target.shape})",
        file=sys.stderr,
    )

    ref_img = _empty_ref(*EMPTY_WINDOW, n=args.empty_frames)
    print(
        f"[ref] empty median from [{EMPTY_WINDOW[0]:.0f},{EMPTY_WINDOW[1]:.0f}] s",
        file=sys.stderr,
    )

    m1_img, m1_sharp, m1_label = method_1_temporal(target, args.t)
    print("[m1] temporal-median done", file=sys.stderr)
    m2_img, m2_sharp, m2_label = method_2_divisive(target, ref_img)
    print("[m2] divisive done", file=sys.stderr)
    m3_img, m3_sharp, m3_label = method_3_highpass(target)
    print("[m3] high-pass done", file=sys.stderr)

    # -------- 8-panel comparison: raw + each method's processed + sharpness --------
    fig, axes = plt.subplots(2, 4, figsize=(20, 9))
    (a0, a1, a2, a3), (b0, b1, b2, b3) = axes

    im = a0.imshow(target, cmap="gray", vmin=0, vmax=255)
    a0.set_title(
        f"raw slurry frame  t={args.t:.0f} s\n(b1 drying→discharge)\nFOR REFERENCE"
    )
    plt.colorbar(im, ax=a0, fraction=0.046)

    for ax, img, label in (
        (a1, m1_img, m1_label),
        (a2, m2_img, m2_label),
        (a3, m3_img, m3_label),
    ):
        vmax = float(np.quantile(img, 0.995))
        im = ax.imshow(img, cmap="gray", vmin=0, vmax=vmax)
        ax.set_title(label + f"\n(grayscale 0–{vmax:.0f})", fontsize=9)
        plt.colorbar(im, ax=ax, fraction=0.046)

    # Sharpness of raw frame for reference.
    raw_sharp = _sharp(target)
    im = b0.imshow(np.log1p(raw_sharp), cmap="viridis")
    b0.set_title(
        "Lap²(raw slurry) — log1p\nNO rupture removal\n(what the original pipeline used)",
        fontsize=9,
    )
    plt.colorbar(im, ax=b0, fraction=0.046)

    for ax, sh, label_short in (
        (b1, m1_sharp, "Method 1"),
        (b2, m2_sharp, "Method 2"),
        (b3, m3_sharp, "Method 3"),
    ):
        im = ax.imshow(np.log1p(sh), cmap="viridis")
        ax.set_title(
            f"Lap² of {label_short}'s processed image — log1p\n"
            f"μ={sh.mean():.1f} σ={sh.std():.1f}",
            fontsize=9,
        )
        plt.colorbar(im, ax=ax, fraction=0.046)

    fig.suptitle(
        f"Rupture-removal method comparison — same target frame, three approaches\n"
        f"target: b1 drying→discharge slurry frame at t={args.t:.0f} s of "
        f"datasets/2026-02-04 11-08-51.mp4",
        y=1.00,
        fontsize=12,
    )
    fig.tight_layout()
    args.out_images.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out_images, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"[out] {args.out_images}", file=sys.stderr)

    # -------- Per-pixel sharpness histograms (overlaid) --------
    fig2, ax = plt.subplots(figsize=(11, 6))
    series = (
        ("raw slurry (no rupture removal)", raw_sharp, "0.5"),
        ("Method 1 — temporal median subtraction", m1_sharp, "C2"),
        ("Method 2 — divisive normalisation", m2_sharp, "C0"),
        ("Method 3 — spatial high-pass filter", m3_sharp, "C3"),
    )
    lo = 0.0
    hi = max(float(np.quantile(s, 0.99)) for _, s, _ in series)
    bins = np.linspace(lo, hi, 120).tolist()
    for name, sh, col in series:
        flat = sh.ravel()
        ax.hist(
            flat,
            bins=bins,
            density=True,
            alpha=0.45,
            color=col,
            label=f"{name}\nμ={flat.mean():.1f}  median={np.median(flat):.1f}  σ={flat.std():.1f}",
        )
    ax.set_xlabel("per-pixel Lap² sharpness")
    ax.set_ylabel("density")
    ax.set_title(
        "Per-pixel sharpness distributions of the processed image — "
        "lower means more rupture/lighting is removed,\n"
        "real-crystal sharpness should survive in the right tail"
    )
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig2.tight_layout()
    fig2.savefig(args.out_hist, dpi=160, bbox_inches="tight")
    plt.close(fig2)
    print(f"[out] {args.out_hist}", file=sys.stderr)

    # -------- Numbers --------
    print()
    print(
        f"target frame                      μ={target.mean():.2f}  σ={target.std():.2f}"
    )
    print(
        f"Lap²(raw slurry)                  μ={raw_sharp.mean():.2f}  σ={raw_sharp.std():.2f}"
    )
    print(
        f"Method 1 sharpness (temporal)     μ={m1_sharp.mean():.2f}  σ={m1_sharp.std():.2f}"
    )
    print(
        f"Method 2 sharpness (divisive)     μ={m2_sharp.mean():.2f}  σ={m2_sharp.std():.2f}"
    )
    print(
        f"Method 3 sharpness (high-pass)    μ={m3_sharp.mean():.2f}  σ={m3_sharp.std():.2f}"
    )


if __name__ == "__main__":
    main()
