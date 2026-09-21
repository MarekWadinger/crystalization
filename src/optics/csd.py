"""Crystal Size Distribution (CSD) aggregation.

This module consumes the per-crystal :class:`DisambiguationResult` records
produced by :mod:`optics.disambiguate` and reduces them to the population-
level Crystal Size Distribution at Camera 100.

Under the homogeneous-slurry assumption used by the disambiguation step
(see ``docs/optics/disambiguation_results.md``), the *physical* size
distribution does not depend on depth: every depth slice should sample
from the same underlying CSD. The CSD is therefore fitted as a single
component (log-normal and Gaussian), not as a mixture.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray
from scipy import stats

from annotator.types import LayerConfig
from optics.config import lens_from_config_and_video, load_camera
from optics.disambiguate import (
    DisambiguationResult,
    detect_observations,
    disambiguate,
)
from optics.model import LensSetup, mm_per_pixel_at

FloatArray = NDArray[np.float64]


def aggregate_csd(
    results: list[DisambiguationResult],
    lens: LensSetup,
    d_focus: float,
) -> dict[str, FloatArray | float]:
    """Aggregate per-crystal depth-corrected sizes into population CSD stats.

    Computes summary statistics (median, mean, std, CV, quantiles) on the
    depth-corrected ``physical_size_mm`` field, then fits a log-normal and
    a Gaussian to the same sample. Single-component fits — the homogeneous-
    slurry assumption says there should only be one physical mode.

    Returns
    -------
    dict with keys
        ``sizes_mm`` (FloatArray), ``median``, ``mean``, ``std``, ``cv``,
        ``p05``, ``p25``, ``p75``, ``p95``,
        ``lognorm_s``, ``lognorm_loc``, ``lognorm_scale``,
        ``norm_loc``, ``norm_scale``, ``n_total``.
    """
    sizes_mm: FloatArray = np.asarray(
        [r.physical_size_mm for r in results], dtype=np.float64
    )
    if sizes_mm.size == 0:
        raise ValueError("aggregate_csd: no results to aggregate")

    mean = float(np.mean(sizes_mm))
    std = float(np.std(sizes_mm, ddof=1)) if sizes_mm.size > 1 else 0.0
    cv = std / mean if mean > 0.0 else float("nan")

    # Lognorm fit requires strictly positive samples.
    positive = sizes_mm[sizes_mm > 0.0]
    if positive.size < 2:
        raise ValueError("aggregate_csd: need >=2 positive sizes for fitting")
    ln_s, ln_loc, ln_scale = stats.lognorm.fit(positive, floc=0.0)
    n_loc, n_scale = stats.norm.fit(sizes_mm)

    _ = d_focus, lens  # kept in signature for symmetry / future depth-binning
    return {
        "sizes_mm": sizes_mm,
        "median": float(np.median(sizes_mm)),
        "mean": mean,
        "std": std,
        "cv": cv,
        "p05": float(np.quantile(sizes_mm, 0.05)),
        "p25": float(np.quantile(sizes_mm, 0.25)),
        "p75": float(np.quantile(sizes_mm, 0.75)),
        "p95": float(np.quantile(sizes_mm, 0.95)),
        "lognorm_s": float(ln_s),
        "lognorm_loc": float(ln_loc),
        "lognorm_scale": float(ln_scale),
        "norm_loc": float(n_loc),
        "norm_scale": float(n_scale),
        "n_total": float(sizes_mm.size),
    }


def _naive_sizes_mm(
    results: list[DisambiguationResult], lens: LensSetup, d_focus: float
) -> FloatArray:
    """Apparent-size-at-focus baseline: every detection scaled by mm/px(d_focus)."""
    mm_per_px = float(mm_per_pixel_at(lens, d_focus, np.array([d_focus]))[0])
    return np.asarray(
        [r.obs.apparent_size_px * mm_per_px for r in results], dtype=np.float64
    )


def fig_csd_final(
    results: list[DisambiguationResult],
    lens: LensSetup,
    d_focus: float,
    out_path: Path,
) -> None:
    """Render the three-panel final CSD figure to ``out_path``."""
    stats_dict = aggregate_csd(results, lens, d_focus)
    sizes_mm = np.asarray(stats_dict["sizes_mm"], dtype=np.float64)
    naive_mm = _naive_sizes_mm(results, lens, d_focus)

    median = float(stats_dict["median"])
    mean = float(stats_dict["mean"])
    cv = float(stats_dict["cv"])
    p25 = float(stats_dict["p25"])
    p75 = float(stats_dict["p75"])
    ln_s = float(stats_dict["lognorm_s"])
    ln_loc = float(stats_dict["lognorm_loc"])
    ln_scale = float(stats_dict["lognorm_scale"])
    n_loc = float(stats_dict["norm_loc"])
    n_scale = float(stats_dict["norm_scale"])

    upper = float(np.quantile(sizes_mm, 0.99) * 1.4)
    bins = np.linspace(0.0, upper, 50)
    bin_width = float(bins[1] - bins[0])

    fig, (ax_naive, ax_corr, ax_assump) = plt.subplots(
        1, 3, figsize=(15.5, 4.8)
    )

    # Panel 1: naive apparent-size-at-focus
    ax_naive.hist(
        naive_mm, bins=bins, color="C0", alpha=0.85, edgecolor="white"
    )
    ax_naive.axvline(
        float(np.quantile(naive_mm, 0.25)),
        color="C3",
        linestyle=":",
        label=f"p25 = {np.quantile(naive_mm, 0.25):.3f} mm",
    )
    ax_naive.axvline(
        float(np.median(naive_mm)),
        color="k",
        linestyle="--",
        label=f"median = {np.median(naive_mm):.3f} mm",
    )
    ax_naive.axvline(
        float(np.quantile(naive_mm, 0.75)),
        color="C3",
        linestyle=":",
        label=f"p75 = {np.quantile(naive_mm, 0.75):.3f} mm",
    )
    ax_naive.set_xlabel("apparent size (mm) @ mm/px(d_focus)")
    ax_naive.set_ylabel("crystal count")
    ax_naive.set_title("Naive: apparent size at focus")
    ax_naive.legend(fontsize=8)
    ax_naive.grid(True, alpha=0.3)

    # Panel 2: depth-corrected + fits
    counts, edges, _ = ax_corr.hist(
        sizes_mm,
        bins=bins,
        color="C1",
        alpha=0.7,
        edgecolor="white",
        label="depth-corrected",
    )
    centres = 0.5 * (edges[1:] + edges[:-1])
    n_total = float(sizes_mm.size)
    x_curve = np.linspace(max(bins[0], 1e-6), bins[-1], 400)
    ln_pdf = stats.lognorm.pdf(x_curve, ln_s, loc=ln_loc, scale=ln_scale)
    n_pdf = stats.norm.pdf(x_curve, loc=n_loc, scale=n_scale)
    ax_corr.plot(
        x_curve,
        ln_pdf * n_total * bin_width,
        color="C3",
        lw=2,
        label=f"lognorm (s={ln_s:.2f}, scale={ln_scale:.3f})",
    )
    ax_corr.plot(
        x_curve,
        n_pdf * n_total * bin_width,
        color="C2",
        lw=2,
        linestyle="--",
        label=f"gaussian (μ={n_loc:.3f}, σ={n_scale:.3f})",
    )
    ax_corr.axvline(
        median, color="k", linestyle="--", label=f"median = {median:.3f} mm"
    )
    ax_corr.axvline(
        mean,
        color="C4",
        linestyle=":",
        label=f"mean = {mean:.3f} mm | CV = {cv:.2f}",
    )
    ax_corr.set_xlabel("depth-corrected physical size (mm)")
    ax_corr.set_ylabel("crystal count")
    ax_corr.set_title("Depth-corrected CSD with single-component fits")
    ax_corr.legend(fontsize=8)
    ax_corr.grid(True, alpha=0.3)
    _ = counts, centres, p25, p75  # silence unused

    # Panel 3: homogeneous-slurry sanity check (focus / near / far overlay)
    focus_sizes = np.asarray(
        [r.physical_size_mm for r in results if r.side == "focus"],
        dtype=np.float64,
    )
    near_sizes = np.asarray(
        [r.physical_size_mm for r in results if r.side == "near"],
        dtype=np.float64,
    )
    far_sizes = np.asarray(
        [r.physical_size_mm for r in results if r.side == "far"],
        dtype=np.float64,
    )
    for sample, color, label in (
        (focus_sizes, "C0", f"focal-plane prior (n={focus_sizes.size})"),
        (near_sizes, "C3", f"near side (n={near_sizes.size})"),
        (far_sizes, "C2", f"far side (n={far_sizes.size})"),
    ):
        if sample.size == 0:
            continue
        ax_assump.hist(
            sample,
            bins=bins,
            density=True,
            histtype="step",
            alpha=0.7,
            color=color,
            linewidth=1.8,
            label=label,
        )
    ax_assump.set_xlabel("depth-corrected physical size (mm)")
    ax_assump.set_ylabel("density")
    ax_assump.set_title("Homogeneous-slurry check: same shape across depths?")
    ax_assump.legend(fontsize=8)
    ax_assump.grid(True, alpha=0.3)

    fig.suptitle(
        "Final depth-corrected crystal-size distribution at Camera 100",
        y=1.02,
        fontsize=12,
    )
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    """End-to-end CSD aggregation run on the plant video."""
    config = LayerConfig(
        num_layers=3,
        sharpness_weight=0.7,
        flow_weight=0.3,
        blur_kernel=15,
        min_area=80.0,
        max_area=8000.0,
        max_aspect_ratio=3.0,
    )
    cfg = load_camera()
    lens = lens_from_config_and_video(cfg, "datasets/2026-02-05 10-36-32.mp4")
    d_focus = cfg.focus_object_distance_mm

    print("Detecting crystals (watershed)…")
    obs = detect_observations(
        "datasets/2026-02-05 10-36-32.mp4",
        config,
        frame_stride=15,
        max_frames=60,
        detector="watershed",
    )
    print(f"  {len(obs)} detections")

    print("Disambiguating depth…")
    results, _ = disambiguate(obs, lens, d_focus)
    print(f"  {len(results)} per-crystal results")

    print("Aggregating CSD…")
    csd = aggregate_csd(results, lens, d_focus)

    print("\n=== CSD summary statistics ===")
    for key in (
        "n_total",
        "median",
        "mean",
        "std",
        "cv",
        "p05",
        "p25",
        "p75",
        "p95",
    ):
        print(f"  {key:10s}: {float(csd[key]):.4f}")

    print("\n=== Single-component fits ===")
    print(
        f"  lognorm: s={float(csd['lognorm_s']):.4f}, "
        f"loc={float(csd['lognorm_loc']):.4f}, "
        f"scale={float(csd['lognorm_scale']):.4f}"
    )
    print(
        f"  gaussian: loc={float(csd['norm_loc']):.4f}, "
        f"scale={float(csd['norm_scale']):.4f}"
    )

    out_path = Path("docs/optics/figures/14_csd_final.png")
    fig_csd_final(results, lens, d_focus, out_path)
    print(f"\nFigure: {out_path}")

    print("\n=== Headline ===")
    print(f"  median   = {float(csd['median']):.4f} mm")
    print(f"  mean     = {float(csd['mean']):.4f} mm")
    print(f"  std      = {float(csd['std']):.4f} mm")
    print(f"  CV       = {float(csd['cv']):.4f}")
    print(
        f"  lognorm  = (s={float(csd['lognorm_s']):.4f}, "
        f"loc={float(csd['lognorm_loc']):.4f}, "
        f"scale={float(csd['lognorm_scale']):.4f})"
    )


if __name__ == "__main__":
    main()
