"""Parameter sensitivity grids for the two promising rupture-removal methods.

Two output figures, each 3x3 = 9 cells. Each cell shows the edge map
(log(1 + Lap²)) of the processed image at one combination of parameter levels
(min / mid / max on each axis). Outer row/column labels mark the parameter
values. Per-cell title shows median Lap² as a summary statistic.

METHOD 1 axes:
  rows = TEMPORAL_RADIUS_S (half-width of the median window) ∈ {1, 5, 20} s
  cols = TEMPORAL_N_FRAMES (samples in that window)         ∈ {5, 21, 81}

METHOD 3 axes:
  rows = sigma_px (low-pass kernel scale)        ∈ {5, 25, 100} px
  cols = sharp_kernel (post-Lap² smoothing size) ∈ {5, 15, 45}  px

OUTPUTS (self-documenting filenames):
  rq4_sensitivity_method1_temporal_grid.png   — 3x3 grid for Method 1
  rq4_sensitivity_method3_highpass_grid.png   — 3x3 grid for Method 3
  rq4_sensitivity_summary.png                 — median Lap² heatmaps for both
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
DEFAULT_SAMPLE_T = 1750.0

M1_RADIUS_LEVELS = [1.0, 5.0, 20.0]  # seconds
M1_NFRAMES_LEVELS = [5, 21, 81]

M3_SIGMA_LEVELS = [5.0, 25.0, 100.0]  # px
M3_SHARPK_LEVELS = [5, 15, 45]  # px


def _grab(t: float) -> np.ndarray:
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
    times = np.linspace(t_centre - radius_s, t_centre + radius_s, n)
    grays = [_grab(t) for t in times]
    return np.median(np.stack(grays, axis=0), axis=0)


def _sharp(gray: np.ndarray, ksize: int = 15) -> np.ndarray:
    k = max(1, ksize) | 1
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    return cv2.GaussianBlur(lap**2, (k, k), 0)


def _grid_plot(
    cells: list[list[tuple[np.ndarray, str]]],
    row_label: str,
    col_label: str,
    row_values: list,
    col_values: list,
    title: str,
    out_path: Path,
) -> None:
    n_rows = len(cells)
    n_cols = len(cells[0])
    fig, axes = plt.subplots(
        n_rows, n_cols, figsize=(4.2 * n_cols, 3.8 * n_rows)
    )
    # find common colour scale across all cells (use 99th pct of log(1+x) so
    # outliers don't blow out the scale)
    all_log = np.concatenate(
        [np.log1p(cell[0]).ravel() for row in cells for cell in row]
    )
    vmin = float(np.quantile(all_log, 0.01))
    vmax = float(np.quantile(all_log, 0.99))

    for i, row in enumerate(cells):
        for j, (sh, summary) in enumerate(row):
            ax = axes[i, j]
            im = ax.imshow(np.log1p(sh), cmap="viridis", vmin=vmin, vmax=vmax)
            ax.set_title(summary, fontsize=9)
            ax.set_xticks([])
            ax.set_yticks([])
            if j == 0:
                ax.set_ylabel(f"{row_label}\n= {row_values[i]}", fontsize=10)
            if i == n_rows - 1:
                ax.set_xlabel(f"{col_label} = {col_values[j]}", fontsize=10)
    fig.suptitle(title, y=1.00, fontsize=12)
    fig.tight_layout()
    cax = fig.add_axes((0.92, 0.15, 0.015, 0.7))
    fig.colorbar(im, cax=cax, label="log(1 + Lap²)")
    fig.subplots_adjust(right=0.90)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"[out] {out_path}", file=sys.stderr)


def method_1_sweep(target: np.ndarray, t_centre: float, sharp_k: int = 15):
    """Return a 3x3 grid of (sharpness_map, summary_str) tuples."""
    rows = []
    medians = np.zeros((len(M1_RADIUS_LEVELS), len(M1_NFRAMES_LEVELS)))
    for i, radius in enumerate(M1_RADIUS_LEVELS):
        row = []
        for j, n in enumerate(M1_NFRAMES_LEVELS):
            bg = _median_window(t_centre, radius, n)
            processed = np.abs(target - bg)
            sh = _sharp(processed, sharp_k)
            med = float(np.median(sh))
            mu = float(sh.mean())
            medians[i, j] = med
            row.append(
                (
                    sh,
                    f"radius={radius:.0f}s, n={n}\nmedian={med:.1f}  μ={mu:.1f}",
                )
            )
            print(
                f"  M1 radius={radius:>5.1f}s n={n:>3d}  median={med:6.2f}  μ={mu:6.2f}",
                file=sys.stderr,
            )
        rows.append(row)
    return rows, medians


def method_3_sweep(target: np.ndarray):
    """Return a 3x3 grid of (sharpness_map, summary_str) tuples."""
    rows = []
    medians = np.zeros((len(M3_SIGMA_LEVELS), len(M3_SHARPK_LEVELS)))
    for i, sigma in enumerate(M3_SIGMA_LEVELS):
        k_lp = int(sigma) * 6 + 1
        lowpass = cv2.GaussianBlur(target, (k_lp, k_lp), sigma)
        processed = np.abs(target - lowpass)
        row = []
        for j, sharp_k in enumerate(M3_SHARPK_LEVELS):
            sh = _sharp(processed, sharp_k)
            med = float(np.median(sh))
            mu = float(sh.mean())
            medians[i, j] = med
            row.append(
                (
                    sh,
                    f"σ_lp={sigma:.0f}px, sharp_k={sharp_k}\nmedian={med:.1f}  μ={mu:.1f}",
                )
            )
            print(
                f"  M3 σ_lp={sigma:>5.1f} sharp_k={sharp_k:>2d}  median={med:6.2f}  μ={mu:6.2f}",
                file=sys.stderr,
            )
        rows.append(row)
    return rows, medians


def _summary_plot(
    m1_medians: np.ndarray, m3_medians: np.ndarray, out_path: Path
) -> None:
    fig, (ax1, ax3) = plt.subplots(1, 2, figsize=(13, 5))

    im1 = ax1.imshow(m1_medians, cmap="viridis", aspect="auto")
    ax1.set_xticks(range(len(M1_NFRAMES_LEVELS)))
    ax1.set_xticklabels([f"n={n}" for n in M1_NFRAMES_LEVELS])
    ax1.set_yticks(range(len(M1_RADIUS_LEVELS)))
    ax1.set_yticklabels([f"{r:.0f}s" for r in M1_RADIUS_LEVELS])
    ax1.set_xlabel("number of samples in window")
    ax1.set_ylabel("temporal half-radius")
    ax1.set_title("Method 1 — median Lap²  (heatmap across 3×3 grid)")
    for i in range(m1_medians.shape[0]):
        for j in range(m1_medians.shape[1]):
            ax1.text(
                j,
                i,
                f"{m1_medians[i, j]:.0f}",
                ha="center",
                va="center",
                color="white"
                if m1_medians[i, j] < m1_medians.mean()
                else "black",
            )
    plt.colorbar(im1, ax=ax1, label="median per-pixel Lap²")

    im3 = ax3.imshow(m3_medians, cmap="viridis", aspect="auto")
    ax3.set_xticks(range(len(M3_SHARPK_LEVELS)))
    ax3.set_xticklabels([f"k={k}" for k in M3_SHARPK_LEVELS])
    ax3.set_yticks(range(len(M3_SIGMA_LEVELS)))
    ax3.set_yticklabels([f"σ={s:.0f}px" for s in M3_SIGMA_LEVELS])
    ax3.set_xlabel("Lap² smoothing kernel (sharp_k)")
    ax3.set_ylabel("low-pass blur σ")
    ax3.set_title("Method 3 — median Lap²  (heatmap across 3×3 grid)")
    for i in range(m3_medians.shape[0]):
        for j in range(m3_medians.shape[1]):
            ax3.text(
                j,
                i,
                f"{m3_medians[i, j]:.0f}",
                ha="center",
                va="center",
                color="white"
                if m3_medians[i, j] < m3_medians.mean()
                else "black",
            )
    plt.colorbar(im3, ax=ax3, label="median per-pixel Lap²")

    fig.suptitle(
        "Sensitivity summary — median Lap² across each method's 3×3 grid\n"
        "(lower = more bulk lighting/rupture removed; reads the same as the histograms)",
        y=1.02,
        fontsize=12,
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"[out] {out_path}", file=sys.stderr)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--t", type=float, default=DEFAULT_SAMPLE_T)
    p.add_argument(
        "--out-dir",
        type=Path,
        default=Path("docs/optics/figures"),
    )
    args = p.parse_args(argv)

    target = _grab(args.t)
    print(f"[target] frame at t={args.t:.0f} s", file=sys.stderr)

    print("[M1] sweeping temporal-median parameters…", file=sys.stderr)
    m1_cells, m1_medians = method_1_sweep(target, args.t)
    _grid_plot(
        m1_cells,
        row_label="temporal radius",
        col_label="N frames",
        row_values=[f"{r:.0f}s" for r in M1_RADIUS_LEVELS],
        col_values=M1_NFRAMES_LEVELS,
        title=(
            "Method 1 — temporal median subtraction, parameter sensitivity grid\n"
            f"target frame: b1 drying→discharge @ t={args.t:.0f} s\n"
            "each cell = log(1 + Lap²(|target − temporal_median|))"
        ),
        out_path=args.out_dir / "rq4_sensitivity_method1_temporal_grid.png",
    )

    print("[M3] sweeping high-pass parameters…", file=sys.stderr)
    m3_cells, m3_medians = method_3_sweep(target)
    _grid_plot(
        m3_cells,
        row_label="low-pass σ",
        col_label="sharp kernel",
        row_values=[f"{s:.0f}px" for s in M3_SIGMA_LEVELS],
        col_values=M3_SHARPK_LEVELS,
        title=(
            "Method 3 — spatial high-pass filter, parameter sensitivity grid\n"
            f"target frame: b1 drying→discharge @ t={args.t:.0f} s\n"
            "each cell = log(1 + Lap²(|target − GaussianBlur(target, σ)|)) "
            "with post-Lap² smoothing kernel sharp_k"
        ),
        out_path=args.out_dir / "rq4_sensitivity_method3_highpass_grid.png",
    )

    _summary_plot(
        m1_medians,
        m3_medians,
        args.out_dir / "rq4_sensitivity_summary.png",
    )


if __name__ == "__main__":
    main()
