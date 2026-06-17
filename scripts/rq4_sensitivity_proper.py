"""Proper sensitivity analysis of Methods 1 and 3 — dense parameter sweeps.

What "proper" means here:
  * Dense sweep (≥7 levels) along each axis instead of 3-point min/mid/max.
  * 2D heatmap with contour lines, so the response surface is visible.
  * Marginal one-at-a-time (OAT) line plots — each shows outcome vs one
    parameter with the other held at its mid-grid value.
  * Tornado bar chart ranking the *magnitude* of each parameter's effect
    (range of outcome over its sweep) — the bigger the bar, the more
    sensitive the method is to that parameter.

Outcome metric: median per-pixel Lap² of the processed image — same metric
that drives the downstream Gaussian-fit pipeline. Lower means more bulk
lighting/rupture is removed.

For Method 1, frame loads are cached and reused: a single 161-frame
superset (±80 s around the target) covers every (radius, n) combination.

OUTPUTS:
  rq4_sensitivity_method1_proper.png   — heatmap + 2 marginals + tornado
  rq4_sensitivity_method3_proper.png   — heatmap + 2 marginals + tornado
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

# Method 1: temporal median subtraction — radius (s) × n_frames
M1_RADIUS_LEVELS = np.array([0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 40.0, 80.0])  # s
M1_NFRAMES_LEVELS = np.array([3, 5, 11, 21, 41, 81, 161])

# Method 3: spatial high-pass — sigma_lp (px) × sharp_kernel (px)
M3_SIGMA_LEVELS = np.array([2.0, 5.0, 10.0, 25.0, 50.0, 100.0, 200.0])  # px
M3_SHARPK_LEVELS = np.array([3, 5, 9, 15, 25, 45, 75])


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


def _sharp(gray: np.ndarray, ksize: int = 15) -> np.ndarray:
    k = max(1, int(ksize)) | 1
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    return cv2.GaussianBlur(lap**2, (k, k), 0)


def _load_superset(
    t_centre: float, max_radius_s: float, max_n: int
) -> dict[float, np.ndarray]:
    """Load enough frames to satisfy every (radius, n) combination in the sweep.

    Returns a {time_seconds: frame} dict so each evaluation can index by time.
    """
    times = np.unique(
        np.concatenate(
            [
                np.linspace(t_centre - r, t_centre + r, max_n)
                for r in M1_RADIUS_LEVELS
            ]
        )
    )
    print(
        f"[m1 cache] preloading {len(times)} unique frame times…",
        file=sys.stderr,
    )
    cache: dict[float, np.ndarray] = {}
    for t in times:
        cache[float(t)] = _grab(float(t))
    return cache


def method_1_eval(
    target: np.ndarray,
    t_centre: float,
    radius: float,
    n: int,
    cache: dict[float, np.ndarray],
) -> float:
    times = np.linspace(t_centre - radius, t_centre + radius, n)
    grays = np.stack([cache[float(t)] for t in times], axis=0)
    bg = np.median(grays, axis=0)
    processed = np.abs(target - bg)
    return float(np.median(_sharp(processed, 15)))


def method_3_eval(target: np.ndarray, sigma: float, sharp_k: int) -> float:
    k_lp = int(sigma) * 6 + 1
    lowpass = cv2.GaussianBlur(target, (k_lp, k_lp), sigma)
    processed = np.abs(target - lowpass)
    return float(np.median(_sharp(processed, sharp_k)))


def _plot_sensitivity(
    matrix: np.ndarray,
    row_values: np.ndarray,
    col_values: np.ndarray,
    row_label: str,
    col_label: str,
    method_title: str,
    out_path: Path,
) -> None:
    """4-panel sensitivity figure: heatmap + 2 marginals + tornado."""
    fig = plt.figure(figsize=(14, 9))
    gs = fig.add_gridspec(
        2, 3, height_ratios=[2.5, 1.6], width_ratios=[2.0, 1.4, 1.4]
    )

    # ---- (A) 2D heatmap with contour lines ----------------------------------
    ax_h = fig.add_subplot(gs[0, 0])
    im = ax_h.imshow(
        matrix,
        cmap="viridis",
        aspect="auto",
        origin="lower",
        extent=(0, len(col_values), 0, len(row_values)),
    )
    cs = ax_h.contour(
        np.arange(len(col_values)) + 0.5,
        np.arange(len(row_values)) + 0.5,
        matrix,
        colors="white",
        linewidths=0.8,
        alpha=0.7,
    )
    ax_h.clabel(cs, inline=True, fontsize=8)
    ax_h.set_xticks(np.arange(len(col_values)) + 0.5)
    ax_h.set_xticklabels([f"{v:g}" for v in col_values])
    ax_h.set_yticks(np.arange(len(row_values)) + 0.5)
    ax_h.set_yticklabels([f"{v:g}" for v in row_values])
    ax_h.set_xlabel(col_label)
    ax_h.set_ylabel(row_label)
    ax_h.set_title("(A) response surface — median Lap² over the 2D grid")
    plt.colorbar(im, ax=ax_h, label="median per-pixel Lap²")

    # ---- (B) marginal sweep along columns (col axis), row at mid -------------
    ax_c = fig.add_subplot(gs[0, 1])
    mid_row = len(row_values) // 2
    ax_c.plot(col_values, matrix[mid_row, :], "o-", color="C0", lw=2)
    ax_c.set_xlabel(col_label)
    ax_c.set_ylabel("median Lap²")
    ax_c.set_title(
        f"(B) OAT sweep along {col_label}\n({row_label} held at "
        f"{row_values[mid_row]:g})"
    )
    if col_values.max() / max(col_values.min(), 1e-9) > 30:
        ax_c.set_xscale("log")
    ax_c.grid(True, alpha=0.3)

    # ---- (C) marginal sweep along rows (row axis), col at mid ----------------
    ax_r = fig.add_subplot(gs[0, 2])
    mid_col = len(col_values) // 2
    ax_r.plot(row_values, matrix[:, mid_col], "o-", color="C3", lw=2)
    ax_r.set_xlabel(row_label)
    ax_r.set_ylabel("median Lap²")
    ax_r.set_title(
        f"(C) OAT sweep along {row_label}\n({col_label} held at "
        f"{col_values[mid_col]:g})"
    )
    if row_values.max() / max(row_values.min(), 1e-9) > 30:
        ax_r.set_xscale("log")
    ax_r.grid(True, alpha=0.3)

    # ---- (D) Tornado: range of outcome along each axis ----------------------
    # For each row of the matrix compute outcome range; aggregate over rows
    # to get the typical range when varying the COLUMN parameter, and similarly
    # for the other axis. This is a simple global-sensitivity measure (each
    # axis's range averaged over the other axis's levels).
    col_ranges = matrix.max(axis=1) - matrix.min(
        axis=1
    )  # per-row variation by col
    row_ranges = matrix.max(axis=0) - matrix.min(
        axis=0
    )  # per-col variation by row
    col_param_effect = float(col_ranges.mean())
    row_param_effect = float(row_ranges.mean())

    # Also compute % effect relative to overall mean for a normalised reading.
    overall_mean = float(matrix.mean())
    col_pct = 100.0 * col_param_effect / overall_mean if overall_mean else 0.0
    row_pct = 100.0 * row_param_effect / overall_mean if overall_mean else 0.0

    ax_t = fig.add_subplot(gs[1, :])
    bars = [col_param_effect, row_param_effect]
    labels = [col_label, row_label]
    pcts = [col_pct, row_pct]
    order = np.argsort(bars)[::-1]
    bars = [bars[i] for i in order]
    labels = [labels[i] for i in order]
    pcts = [pcts[i] for i in order]
    y = np.arange(len(bars))
    ax_t.barh(y, bars, color=["C0", "C3"][: len(bars)])
    ax_t.set_yticks(y)
    ax_t.set_yticklabels(labels)
    ax_t.invert_yaxis()
    for i, (b, p) in enumerate(zip(bars, pcts, strict=False)):
        ax_t.text(
            b,
            i,
            f"  Δ={b:.1f}   ({p:.1f} % of mean)",
            va="center",
            fontsize=10,
        )
    ax_t.set_xlabel("mean range of median Lap² over the parameter's sweep")
    ax_t.set_title("(D) Tornado — which parameter moves the outcome more")
    ax_t.grid(True, axis="x", alpha=0.3)
    ax_t.set_xlim(0, max(bars) * 1.35 if max(bars) > 0 else 1.0)

    fig.suptitle(method_title, y=1.00, fontsize=12)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
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

    # ----- Method 1 sweep -----
    cache = _load_superset(
        args.t, M1_RADIUS_LEVELS.max(), int(M1_NFRAMES_LEVELS.max())
    )
    m1 = np.zeros((len(M1_RADIUS_LEVELS), len(M1_NFRAMES_LEVELS)))
    print("[m1] sweeping…", file=sys.stderr)
    for i, r in enumerate(M1_RADIUS_LEVELS):
        for j, n in enumerate(M1_NFRAMES_LEVELS):
            m1[i, j] = method_1_eval(target, args.t, float(r), int(n), cache)
        print(
            f"  row r={r:.1f}s done  ({np.round(m1[i], 1)})", file=sys.stderr
        )
    _plot_sensitivity(
        m1,
        row_values=M1_RADIUS_LEVELS,
        col_values=M1_NFRAMES_LEVELS.astype(float),
        row_label="temporal radius (s)",
        col_label="N frames sampled in window",
        method_title=(
            "Method 1 — temporal median subtraction:  proper sensitivity analysis\n"
            f"target frame: b1 drying→discharge @ t={args.t:.0f} s\n"
            f"sweep: {len(M1_RADIUS_LEVELS)} × {len(M1_NFRAMES_LEVELS)} = "
            f"{m1.size} evaluations; outcome = median per-pixel Lap²"
        ),
        out_path=args.out_dir / "rq4_sensitivity_method1_proper.png",
    )

    # ----- Method 3 sweep -----
    m3 = np.zeros((len(M3_SIGMA_LEVELS), len(M3_SHARPK_LEVELS)))
    print("[m3] sweeping…", file=sys.stderr)
    for i, s in enumerate(M3_SIGMA_LEVELS):
        for j, k in enumerate(M3_SHARPK_LEVELS):
            m3[i, j] = method_3_eval(target, float(s), int(k))
        print(
            f"  row σ={s:.1f}px done  ({np.round(m3[i], 1)})", file=sys.stderr
        )
    _plot_sensitivity(
        m3,
        row_values=M3_SIGMA_LEVELS,
        col_values=M3_SHARPK_LEVELS.astype(float),
        row_label="low-pass σ (px)",
        col_label="post-Lap² smoothing kernel sharp_k (px)",
        method_title=(
            "Method 3 — spatial high-pass filter:  proper sensitivity analysis\n"
            f"target frame: b1 drying→discharge @ t={args.t:.0f} s\n"
            f"sweep: {len(M3_SIGMA_LEVELS)} × {len(M3_SHARPK_LEVELS)} = "
            f"{m3.size} evaluations; outcome = median per-pixel Lap²"
        ),
        out_path=args.out_dir / "rq4_sensitivity_method3_proper.png",
    )


if __name__ == "__main__":
    main()
