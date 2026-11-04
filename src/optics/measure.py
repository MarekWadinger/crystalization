"""Measure the observed sharpness distribution on a real video.

We sample many frames, compute a per-pixel Laplacian-variance map, and
build the empirical distribution of pixel sharpness scores. If the depth
across the crystal slurry is approximately uniform, this distribution is a
weighted average of the theoretical s(d_o) curve over the depth axis — so
its *shape* tells us whether the geometric Gaussian-PSF + diffraction
model is sufficient.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray

from optics.config import lens_from_config_and_video, load_camera
from optics.model import LensSetup, circle_of_confusion, magnification
from optics.psf import sharpness_diffraction
from optics.video_io import CropBox, resolve_crop


def collect_sharpness_histogram(
    video_path: str,
    *,
    frame_stride: int = 5,
    max_frames: int = 120,
    start_frame: int = 0,
    blur_kernel: int = 15,
    n_bins: int = 200,
    crop: CropBox | None = None,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Aggregate per-pixel Laplacian-variance sharpness over many frames.

    Returns ``(bin_centres, density)``: a normalised histogram of pixel
    sharpness scores accumulated across ``max_frames`` frames sampled
    every ``frame_stride``.

    ``crop`` defaults to auto-detected per video via
    :func:`optics.video_io.resolve_crop` so SD / HD / different DVR
    layouts all get a layout-correct crop.
    """
    crop = resolve_crop(video_path, crop)
    cap = cv2.VideoCapture(video_path)
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    stop = min(n_frames, start_frame + max_frames * frame_stride)
    indices = list(range(start_frame, stop, frame_stride))[:max_frames]
    k = blur_kernel | 1
    values: list[NDArray[np.float64]] = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            break
        frame = crop.apply(frame)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        lap = cv2.Laplacian(gray, cv2.CV_64F)
        squared = lap**2
        smoothed = cv2.GaussianBlur(squared, (k, k), 0)
        sharp = np.log1p(smoothed).ravel().astype(np.float64)
        values.append(sharp[::32])  # subsample within each frame
    cap.release()

    flat = np.concatenate(values)
    hist, edges = np.histogram(flat, bins=n_bins, density=True)
    centres = 0.5 * (edges[1:] + edges[:-1])
    return centres, hist


def fit_band(
    density: NDArray[np.float64],
    *,
    quantile_lo: float = 0.5,
    quantile_hi: float = 0.95,
) -> tuple[int, int]:
    """Bin indices ``[lo, hi)`` between two quantiles of the cumulative histogram."""
    cdf = np.cumsum(density) / density.sum()
    return (
        int(np.searchsorted(cdf, quantile_lo)),
        int(np.searchsorted(cdf, quantile_hi)),
    )


def fit_power_law_tail(
    centres: NDArray[np.float64],
    density: NDArray[np.float64],
    *,
    quantile_lo: float = 0.5,
    quantile_hi: float = 0.95,
) -> tuple[float, float]:
    """Fit a power law ``density ∝ centres^(-alpha)`` over a quantile band.

    Returns ``(alpha, intercept)`` of ``log density = intercept − alpha · log x``
    over the bins between the ``quantile_lo`` and ``quantile_hi`` points of the
    cumulative histogram (:func:`fit_band`).
    """
    lo_idx, hi_idx = fit_band(
        density, quantile_lo=quantile_lo, quantile_hi=quantile_hi
    )
    x = centres[lo_idx:hi_idx]
    y = density[lo_idx:hi_idx]
    mask = (x > 0) & (y > 0)
    x, y = x[mask], y[mask]
    if len(x) < 5:
        return float("nan"), float("nan")
    slope, intercept = np.polyfit(np.log(x), np.log(y), 1)
    return float(-slope), float(intercept)


def predicted_sharpness_marginal(
    lens: LensSetup,
    d_focus: float,
    d_min: float,
    d_max: float,
    *,
    n: int = 2000,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Predicted sharpness histogram for uniform depth distribution.

    Assumes the crystals are uniformly distributed in depth over
    ``[d_min, d_max]``. Returns ``(s_values, density)``.
    """
    d = np.linspace(d_min, d_max, n)
    c = circle_of_confusion(lens, d_focus, d)
    s = sharpness_diffraction(
        c, lens.f_number, magnification=magnification(lens, d_focus)
    )
    # depth is uniform → density of s is the inverse |ds/dd|
    ds_dd = np.gradient(s, d)
    density = 1.0 / np.maximum(np.abs(ds_dd), 1e-12)
    density /= density.sum() * (s.max() - s.min()) / len(s)
    order = np.argsort(s)
    return s[order], density[order]


def fig_measured_vs_theory(
    video_path: str,
    out_path: Path,
    lens: LensSetup,
    d_focus: float,
) -> dict[str, float]:
    """Render the measured sharpness density with its fitted slope.

    The fit line is drawn only over the 50–95 % band it was fitted on, which
    is shaded. No model curve is drawn: a population spread uniformly over a
    depth range much wider than the in-focus slice gives a density that is not
    comparable with this pixel statistic (papers/cep §4.4).
    """
    del lens, d_focus  # kept for call compatibility; no model panel
    centres, density = collect_sharpness_histogram(video_path)
    alpha, intercept = fit_power_law_tail(centres, density)
    lo_idx, hi_idx = fit_band(density)
    x_lo, x_hi = float(centres[lo_idx]), float(centres[hi_idx - 1])

    mask = density > 0
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    ax.axvspan(x_lo, x_hi, color="0.85", label="fit band (50–95 % of pixels)")
    ax.semilogy(
        centres[mask], density[mask], color="C0", label="measured density"
    )
    if not np.isnan(alpha):
        x_fit = np.linspace(max(x_lo, 1e-6), x_hi, 50)
        y_fit = np.exp(intercept) * x_fit ** (-alpha)
        ax.semilogy(
            x_fit,
            y_fit,
            color="C3",
            linestyle="--",
            linewidth=2.0,
            label=f"log–log fit over the band: α = {alpha:.2f}",
        )
    ax.set_xlabel("per-pixel sharpness log(1 + G * (∇²I)²)")
    ax.set_ylabel("density (log)")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return {
        "alpha_measured": alpha,
        "intercept_measured": intercept,
        "band_lo": x_lo,
        "band_hi": x_hi,
    }


def main() -> None:
    """Run the measurement on the plant video and print stats."""
    cfg = load_camera()
    lens = lens_from_config_and_video(cfg, "datasets/2026-02-05 10-36-32.mp4")
    d_focus = cfg.focus_object_distance_mm
    out_dir = Path("docs/optics/figures")
    out_dir.mkdir(parents=True, exist_ok=True)
    stats = fig_measured_vs_theory(
        "datasets/2026-02-05 10-36-32.mp4",
        out_dir / "08_measured_vs_theory.png",
        lens,
        d_focus=d_focus,
    )
    print(stats)


if __name__ == "__main__":
    main()
