"""Visualise the diff-image at the heart of the rupture-subtraction pipeline,
and compare image-level subtraction (what the pipeline does) against
sharpness-level subtraction (the obvious-looking alternative that's wrong).

Outputs a 2x3 panel:

  | raw slurry frame |  empty reference IMG  | |slurry − ref|        |
  | Lap²(slurry)     |  Lap²(empty_ref)      | Lap²(|slurry−ref|)    |
                                              ↑  image-level (PIPELINE)
  Plus a 1x2 comparison panel:
    | Lap²(slurry) − Lap²(empty_ref)  |  Lap²(|slurry−ref|) − Lap²(slurry)−Lap²(empty_ref) |
       ↑ sharpness-level (NAIVE)         ↑ difference between methods
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

# Empty-window for the median reference (same as the main pipeline uses).
EMPTY_WINDOW = (2300.0, 2450.0)
# Representative slurry frame inside the b1 drying→discharge window
# (b1 window is [1213.1, 2270.5] s). Default is mid-window.
DEFAULT_SAMPLE_T = 1750.0


def _build_ref(t0: float, t1: float, n: int) -> np.ndarray:
    start = int(round(t0 * FPS))
    end = int(round(t1 * FPS))
    stride = max(1, (end - start) // n)
    cap = cv2.VideoCapture(LONG_VIDEO)
    grays: list[np.ndarray] = []
    idx = start
    while idx < end and len(grays) < n:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            break
        frame = DEFAULT_CROP.apply(frame)
        grays.append(
            cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float64)
        )
        idx += stride
    cap.release()
    if not grays:
        raise RuntimeError("could not build reference")
    print(
        f"[ref] built from {len(grays)} frames in [{t0:.0f}, {t1:.0f}] s",
        file=sys.stderr,
    )
    return np.median(np.stack(grays, axis=0), axis=0)


def _grab_frame(t: float) -> np.ndarray:
    cap = cv2.VideoCapture(LONG_VIDEO)
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(t * FPS)))
    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise RuntimeError(f"could not read frame at t={t}")
    frame = DEFAULT_CROP.apply(frame)
    return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float64)


def _sharp(gray: np.ndarray) -> np.ndarray:
    """Gaussian-smoothed Laplacian² — matches the pipeline exactly."""
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    return cv2.GaussianBlur(lap**2, (15, 15), 0)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--t",
        type=float,
        default=DEFAULT_SAMPLE_T,
        help="seconds into the video for the sample slurry frame",
    )
    p.add_argument("--ref-frames", type=int, default=60)
    p.add_argument(
        "--out",
        type=Path,
        default=Path("docs/optics/figures/rq4_diff_image_inspect.png"),
    )
    args = p.parse_args(argv)

    ref_img = _build_ref(*EMPTY_WINDOW, n=args.ref_frames)
    slurry = _grab_frame(args.t)

    # IMAGE-LEVEL subtraction (the pipeline approach).
    diff = np.abs(slurry - ref_img)
    sharp_of_diff = _sharp(diff)

    # SHARPNESS-LEVEL subtraction (the naive alternative).
    sharp_slurry = _sharp(slurry)
    sharp_ref = _sharp(ref_img)
    sharp_minus_sharp = sharp_slurry - sharp_ref  # can be negative

    # Difference between the two approaches.
    method_diff = sharp_of_diff - sharp_minus_sharp

    # -------- 2x4 panel: the actual images --------
    fig, axes = plt.subplots(2, 4, figsize=(20, 8))
    (a, b, c_gray, c_magma), (d, e, f_blank, f) = axes
    f_blank.axis("off")  # spare cell

    im_a = a.imshow(slurry, cmap="gray", vmin=0, vmax=255)
    a.set_title(
        f"(A) raw slurry frame @ t = {args.t:.0f} s\n(grayscale 0–255)"
    )
    plt.colorbar(im_a, ax=a, fraction=0.046)

    im_b = b.imshow(ref_img, cmap="gray", vmin=0, vmax=255)
    b.set_title(
        f"(B) empty-tank reference\n(grayscale 0–255, median of {args.ref_frames} drained-glass frames)"
    )
    plt.colorbar(im_b, ax=b, fraction=0.046)

    diff_max = float(diff.max())
    im_cg = c_gray.imshow(diff, cmap="gray", vmin=0, vmax=diff_max)
    c_gray.set_title(
        f"(C₁) |slurry − reference| — GRAYSCALE\n"
        f"same colormap as A & B, 0–{diff_max:.0f}"
    )
    plt.colorbar(im_cg, ax=c_gray, fraction=0.046)

    im_cm = c_magma.imshow(diff, cmap="magma", vmin=0, vmax=diff_max)
    c_magma.set_title(
        "(C₂) |slurry − reference| — MAGMA\n(same data as C₁, colourised for contrast)"
    )
    plt.colorbar(im_cm, ax=c_magma, fraction=0.046)

    im_d = d.imshow(np.log1p(sharp_slurry), cmap="viridis")
    d.set_title("(D) log(1 + Lap²(slurry))\nedge map of slurry frame")
    plt.colorbar(im_d, ax=d, fraction=0.046)

    im_e = e.imshow(np.log1p(sharp_ref), cmap="viridis")
    e.set_title("(E) log(1 + Lap²(empty reference))\nedge map of empty glass")
    plt.colorbar(im_e, ax=e, fraction=0.046)

    im_f = f.imshow(np.log1p(sharp_of_diff), cmap="viridis")
    f.set_title("(F) log(1 + Lap²(diff))  ←  PIPELINE\nedge map of (C₁/C₂)")
    plt.colorbar(im_f, ax=f, fraction=0.046)

    fig.suptitle(
        f"Diff-image inspection — slurry @ t={args.t:.0f} s vs empty-tank reference "
        f"({args.ref_frames} frames in [{EMPTY_WINDOW[0]:.0f}, {EMPTY_WINDOW[1]:.0f}] s)",
        y=1.00,
        fontsize=12,
    )
    fig.tight_layout()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"[out] {args.out}", file=sys.stderr)

    # -------- 1x3 comparison: the two methods + their difference --------
    out2 = args.out.with_name(args.out.stem + "_methods.png")
    fig2, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(16, 5))

    # Method 1: image-level subtraction (pipeline).
    im1 = ax1.imshow(
        sharp_of_diff,
        cmap="viridis",
        vmin=0,
        vmax=float(np.quantile(sharp_of_diff, 0.99)),
    )
    ax1.set_title(
        "Method A (pipeline): Lap²(|slurry − ref|)\nsubtract IMAGES first, then sharpen"
    )
    plt.colorbar(im1, ax=ax1, fraction=0.046)

    # Method 2: sharpness-level subtraction (naive).
    lo = float(np.quantile(sharp_minus_sharp, 0.01))
    hi = float(np.quantile(sharp_minus_sharp, 0.99))
    lim = max(abs(lo), abs(hi))
    im2 = ax2.imshow(sharp_minus_sharp, cmap="RdBu_r", vmin=-lim, vmax=lim)
    ax2.set_title(
        "Method B (naive): Lap²(slurry) − Lap²(ref)\n"
        "sharpen first, then subtract  →  signed values!"
    )
    plt.colorbar(im2, ax=ax2, fraction=0.046)

    # Difference between methods.
    lo = float(np.quantile(method_diff, 0.01))
    hi = float(np.quantile(method_diff, 0.99))
    lim = max(abs(lo), abs(hi))
    im3 = ax3.imshow(method_diff, cmap="RdBu_r", vmin=-lim, vmax=lim)
    ax3.set_title("(Method A) − (Method B)\nwhere the two approaches disagree")
    plt.colorbar(im3, ax=ax3, fraction=0.046)

    fig2.suptitle(
        "Image-level vs sharpness-level subtraction — same frame, two pipelines",
        y=1.02,
        fontsize=12,
    )
    fig2.tight_layout()
    fig2.savefig(out2, dpi=160, bbox_inches="tight")
    plt.close(fig2)
    print(f"[out] {out2}", file=sys.stderr)

    # -------- Histograms of per-pixel sharpness, both methods --------
    out3 = args.out.with_name(args.out.stem + "_hist.png")
    fig3, ax = plt.subplots(figsize=(9, 5))
    sd = np.asarray(sharp_of_diff.ravel(), dtype=np.float64)
    ss = np.asarray(sharp_minus_sharp.ravel(), dtype=np.float64)
    lo = min(float(np.quantile(sd, 0.005)), float(np.quantile(ss, 0.005)))
    hi = max(float(np.quantile(sd, 0.995)), float(np.quantile(ss, 0.995)))
    bins_arr = np.linspace(lo, hi, 120)
    bins_list = bins_arr.tolist()
    ax.hist(
        sd,
        bins=bins_list,
        density=True,
        alpha=0.5,
        color="C2",
        label=f"Method A (pipeline)  μ={sd.mean():.1f} σ={sd.std():.1f} "
        f"median={np.median(sd):.1f}",
    )
    ax.hist(
        ss,
        bins=bins_list,
        density=True,
        alpha=0.5,
        color="C3",
        label=f"Method B (naive)     μ={ss.mean():+.1f} σ={ss.std():.1f} "
        f"median={np.median(ss):+.1f}",
    )
    ax.axvline(0, color="k", lw=1, alpha=0.5)
    ax.set_xlabel("per-pixel sharpness after rupture subtraction")
    ax.set_ylabel("density")
    ax.set_title(
        "Per-pixel sharpness distributions — image-level (A) vs sharpness-level (B)"
    )
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    fig3.tight_layout()
    fig3.savefig(out3, dpi=160, bbox_inches="tight")
    plt.close(fig3)
    print(f"[out] {out3}", file=sys.stderr)

    # -------- Printed stats --------
    print()
    print(
        f"diff image           μ={diff.mean():.2f}  σ={diff.std():.2f}  "
        f"max={diff.max():.1f}"
    )
    print(
        f"Lap²(slurry)         μ={sharp_slurry.mean():.2f}  σ={sharp_slurry.std():.2f}"
    )
    print(
        f"Lap²(ref)            μ={sharp_ref.mean():.2f}  σ={sharp_ref.std():.2f}"
    )
    print(
        f"Lap²(diff)   (A)     μ={sharp_of_diff.mean():.2f}  σ={sharp_of_diff.std():.2f}"
    )
    print(
        f"Lap²(s)−Lap²(r) (B)  μ={sharp_minus_sharp.mean():+.2f}  "
        f"σ={sharp_minus_sharp.std():.2f}  "
        f"neg-fraction={(sharp_minus_sharp < 0).mean():.2%}"
    )
    print(
        f"A − B difference     μ={method_diff.mean():.2f}  σ={method_diff.std():.2f}"
    )


if __name__ == "__main__":
    main()
