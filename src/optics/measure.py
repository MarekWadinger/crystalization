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

from optics.model import LensSetup, circle_of_confusion
from optics.psf import sharpness_diffraction
from optics.video_io import DEFAULT_CROP, CropBox


def collect_sharpness_histogram(
    video_path: str,
    *,
    frame_stride: int = 5,
    max_frames: int = 120,
    start_frame: int = 0,
    blur_kernel: int = 15,
    n_bins: int = 200,
    crop: CropBox = DEFAULT_CROP,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Aggregate per-pixel Laplacian-variance sharpness over many frames.

    Returns ``(bin_centres, density)``: a normalised histogram of pixel
    sharpness scores accumulated across ``max_frames`` frames sampled
    every ``frame_stride``.
    """
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


def fit_power_law_tail(
    centres: NDArray[np.float64],
    density: NDArray[np.float64],
    *,
    quantile_lo: float = 0.5,
    quantile_hi: float = 0.95,
) -> tuple[float, float]:
    """Fit a power law ``density ∝ centres^(-alpha)`` to the right tail.

    Returns ``(alpha, intercept)``. We use the upper half of the histogram
    (sharp-ish pixels) so the fit is dominated by the focused-slice tail.
    """
    cdf = np.cumsum(density) / density.sum()
    lo_idx = int(np.searchsorted(cdf, quantile_lo))
    hi_idx = int(np.searchsorted(cdf, quantile_hi))
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
    s = sharpness_diffraction(c, lens.f_number)
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
    depth_range_mm: float = 5.0,
) -> dict[str, float]:
    """Render the measured-vs-theoretical sharpness comparison."""
    centres, density = collect_sharpness_histogram(video_path)
    alpha, intercept = fit_power_law_tail(centres, density)

    # Drop the leftmost mode (background log1p(0)=0 baseline)
    mask = density > 0
    centres = centres[mask]
    density = density[mask]

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11.5, 4.4))
    axL.semilogy(
        centres, density, color="C0", label="measured (Laplacian-var)"
    )
    if not np.isnan(alpha):
        x_fit = np.linspace(centres[len(centres) // 2], centres[-1], 50)
        y_fit = np.exp(intercept) * x_fit ** (-alpha)
        axL.semilogy(
            x_fit,
            y_fit,
            color="C3",
            linestyle="--",
            label=f"power-law fit: α = {alpha:.2f}",
        )
    axL.set_xlabel("log1p(Laplacian²) — sharpness")
    axL.set_ylabel("density (log)")
    axL.set_title(
        f"Measured pixel-sharpness distribution\n({Path(video_path).name})"
    )
    axL.legend(loc="upper right")
    axL.grid(True, alpha=0.3)

    s_pred, density_pred = predicted_sharpness_marginal(
        lens, d_focus, d_focus - depth_range_mm, d_focus + depth_range_mm
    )
    axR.semilogy(
        s_pred, density_pred, color="C1", label="theory (uniform depth)"
    )
    axR.set_xlabel("predicted normalised sharpness")
    axR.set_ylabel("density (log)")
    axR.set_title(
        "Theoretical density under uniform depth in\n"
        f"[{d_focus - depth_range_mm:.0f}, {d_focus + depth_range_mm:.0f}] mm"
    )
    axR.legend(loc="upper right")
    axR.grid(True, alpha=0.3)
    fig.suptitle(
        "Measured distribution has a heavy tail consistent with a power-law cusp",
        y=1.02,
        fontsize=11,
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return {
        "alpha_measured": alpha,
        "intercept_measured": intercept,
        "n_centres": float(len(centres)),
    }


def main() -> None:
    """Run the measurement on the plant video and print stats."""
    lens = LensSetup(
        focal_length=35.0,
        f_number=1.6,
        extension_tube=45.0,
        pixel_pitch_um=2.8,
    )
    out_dir = Path("docs/optics/figures")
    out_dir.mkdir(parents=True, exist_ok=True)
    stats = fig_measured_vs_theory(
        "datasets/2026-02-05 10-36-32.mp4",
        out_dir / "08_measured_vs_theory.png",
        lens,
        d_focus=62.2,
    )
    print(stats)


if __name__ == "__main__":
    main()
