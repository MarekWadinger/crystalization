"""Depth-disambiguation pipeline.

Inverts the front/back depth ambiguity of circular apertures using the
**focal-plane apparent-size distribution** as a Bayesian prior over
crystal physical sizes. The slurry is assumed homogeneous — the physical
size distribution does not depend on depth — which is realistic for a
well-stirred massecuite.

Pipeline
--------

1. Detect crystals across the video.
2. For each detection, score its mean local sharpness ``S_obs`` and read
   off its apparent size ``s_obs`` in pixels.
3. Build the **focal-plane apparent-size distribution** ``P_focus(s)``
   by selecting detections in the top sharpness quantile.
4. Convert ``P_focus(s)`` to a physical-size distribution
   ``P_w(w)`` by w = s · mm_per_px(d_focus).
5. For each non-focal-plane detection:
   - Recover the defocus circle-of-confusion from the sharpness model
     (Gaussian PSF: σ = c / 2, S ∝ (σ² + σ_floor²)⁻⁵ᐟ²).
   - Invert ``c(d_o)`` to get the two symmetric depths ``d_near``,
     ``d_far``.
   - Compute implied physical sizes ``w_near = s_obs · mm_per_px(d_near)``
     and ``w_far = s_obs · mm_per_px(d_far)``.
   - Pick the hypothesis with higher likelihood under ``P_w``.
6. Aggregate: estimated *physical* size of every crystal, fraction of
   detections on each side of focus at each defocus band, and how much
   the depth correction differs from the naive "use mm/px at d_focus
   for everything" baseline.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray

from annotator.detection import process_frame
from annotator.types import Crystal, LayerConfig
from optics.config import (
    detection_area_px,
    lens_from_config_and_video,
    load_camera,
)
from optics.model import (
    LensSetup,
    circle_of_confusion,
    mm_per_pixel_at,
)
from optics.video_io import CropBox, resolve_crop


@dataclass(frozen=True, slots=True)
class CrystalObservation:
    """A single detected crystal annotated with optics-derived quantities."""

    frame_idx: int
    x_px: float
    y_px: float
    apparent_size_px: float
    """Geometric-mean apparent size (sqrt of bounding-rect width × height)."""
    sharpness_score: float
    """Mean Laplacian-variance sharpness inside the bounding rect."""


def detect_observations(
    video_path: str,
    config: LayerConfig,
    *,
    frame_stride: int = 10,
    max_frames: int = 80,
    start_frame: int = 0,
    crop: CropBox | None = None,
    detector: str = "edge",
) -> list[CrystalObservation]:
    """Run the crystal detector on sampled frames.

    ``detector`` selects between:
    * ``"edge"`` — the inherited edge-based detector (legacy default).
    * ``"watershed"`` — the marker-controlled watershed segmentation
      (``optics.detect_watershed``) that handles dense in-focus
      clusters correctly. See manuscript §7.4.

    ``crop`` defaults to ``None`` → auto-detected per video via
    :func:`optics.video_io.resolve_crop`, so SD / HD / different DVR
    layouts all get a layout-correct crop instead of inheriting the
    HD-tuned ``DEFAULT_CROP``. Pass an explicit ``CropBox`` to override.

    Sharpness is *not* taken from the per-frame layer assignment — instead
    we recompute a per-pixel sharpness map and average it inside each
    crystal's bounding rectangle. This decouples the disambiguation from
    the existing layer segmentation and makes the per-crystal sharpness
    a continuous quantity rather than a discrete bin.
    """
    crop = resolve_crop(video_path, crop)
    process_fn = process_frame
    if detector == "watershed":
        from optics.detect_watershed import process_frame_watershed

        process_fn = process_frame_watershed
    elif detector != "edge":
        raise ValueError(
            f"detector must be 'edge' or 'watershed', got {detector!r}"
        )
    cap = cv2.VideoCapture(video_path)
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    stop = min(n_frames, start_frame + max_frames * frame_stride)
    indices = list(range(start_frame, stop, frame_stride))[:max_frames]
    blur_kernel = config.blur_kernel | 1
    obs: list[CrystalObservation] = []
    prev_gray: np.ndarray | None = None
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            break
        frame = crop.apply(frame)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        lap = cv2.Laplacian(gray, cv2.CV_64F)
        sharp_map: NDArray[np.float64] = cv2.GaussianBlur(
            lap**2, (blur_kernel, blur_kernel), 0
        )
        frame_result, _ = process_fn(gray, prev_gray, idx, config)
        for layer in frame_result.layers:
            for cry in layer.crystals:
                s = _mean_sharpness_in_rect(sharp_map, cry)
                obs.append(
                    CrystalObservation(
                        frame_idx=idx,
                        x_px=cry.x,
                        y_px=cry.y,
                        apparent_size_px=cry.size,
                        sharpness_score=float(s),
                    )
                )
        prev_gray = gray
    cap.release()
    return obs


def _mean_sharpness_in_rect(
    sharp_map: NDArray[np.float64], cry: Crystal
) -> float:
    """Average the smoothed Laplacian-variance map within the crystal rect."""
    h, w = sharp_map.shape
    half_w = max(1, int(cry.width / 2))
    half_h = max(1, int(cry.height / 2))
    cx = int(np.clip(cry.x, 0, w - 1))
    cy = int(np.clip(cry.y, 0, h - 1))
    x0 = max(0, cx - half_w)
    x1 = min(w, cx + half_w + 1)
    y0 = max(0, cy - half_h)
    y1 = min(h, cy + half_h + 1)
    roi = sharp_map[y0:y1, x0:x1]
    if roi.size == 0:
        return 0.0
    return float(roi.mean())


def _circle_of_confusion_to_object_distances(
    lens: LensSetup, d_focus: float, c_mm: float
) -> tuple[float, float] | None:
    """Invert c(d_o) at fixed lens settings — returns (d_near, d_far).

    c(d_o) = K · |d_o − d_focus| / d_o  with K = f² / (N (d_focus − f))

    Solve for d_o given c ≥ 0::

        d_o (1 − c/K)  = d_focus      →   d_far = d_focus / (1 − c/K)
        d_o (1 + c/K)  = d_focus      →   d_near = d_focus / (1 + c/K)

    Returns None for c values past the hyperfocal saturation point.
    """
    k = lens.focal_length**2 / (lens.f_number * (d_focus - lens.focal_length))
    ratio = c_mm / k
    if ratio >= 1.0:
        return None
    d_far = d_focus / (1.0 - ratio)
    d_near = d_focus / (1.0 + ratio)
    return d_near, d_far


def _sharpness_to_coc(
    s_norm: NDArray[np.float64],
    sigma_floor_mm: float,
) -> NDArray[np.float64]:
    """Invert the sharpness model to recover the CoC.

    From ``S = (σ² + σ_floor²)^(−5/2)`` normalised so peak = 1::

        (σ² + σ_floor²) = σ_floor² · S^(−2/5)
        σ²              = σ_floor² (S^(−2/5) − 1)

    Returns geometric blur c = 2σ (mm), zero where σ² < 0.
    """
    s = np.clip(s_norm, 1e-12, 1.0)
    sigma_sq = sigma_floor_mm**2 * (s ** (-2.0 / 5.0) - 1.0)
    sigma_sq = np.maximum(sigma_sq, 0.0)
    return 2.0 * np.sqrt(sigma_sq)


def _normalise_sharpness(
    raw: NDArray[np.float64], top_quantile: float = 0.995
) -> NDArray[np.float64]:
    """Map raw Laplacian-variance scores to [0, 1] using a robust top quantile."""
    cap = float(np.quantile(raw, top_quantile))
    if cap <= 0.0:
        return np.zeros_like(raw)
    return np.clip(raw / cap, 0.0, 1.0)


def _physical_size_prior(
    focal_apparent_sizes_px: NDArray[np.float64],
    lens: LensSetup,
    d_focus: float,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Empirical physical-size prior ``P_w(w)`` from focal-plane detections."""
    mm_per_px = float(mm_per_pixel_at(lens, d_focus, np.array([d_focus]))[0])
    sizes_mm = focal_apparent_sizes_px * mm_per_px
    edges = np.linspace(0.0, float(np.quantile(sizes_mm, 0.99) * 1.5), 60)
    hist, edges_out = np.histogram(sizes_mm, bins=edges, density=True)
    centres = 0.5 * (edges_out[1:] + edges_out[:-1])
    return centres, hist


def _likelihood(
    w_mm: float,
    centres: NDArray[np.float64],
    pdf: NDArray[np.float64],
) -> float:
    """Look up the prior density at ``w_mm`` (linear interp; floor below 1e-6)."""
    if w_mm <= 0.0:
        return 1e-6
    val = float(np.interp(w_mm, centres, pdf, left=1e-6, right=1e-6))
    return max(val, 1e-6)


@dataclass(frozen=True, slots=True)
class DisambiguationResult:
    """Per-crystal outcome of the depth-disambiguation step."""

    obs: CrystalObservation
    s_normalised: float
    coc_mm: float
    d_near: float
    d_far: float
    w_near_mm: float
    w_far_mm: float
    p_near: float
    side: str  # "near", "far", or "focus"
    physical_size_mm: float


def disambiguate(
    observations: list[CrystalObservation],
    lens: LensSetup,
    d_focus: float,
    *,
    focal_sharpness_quantile: float = 0.85,
    sigma_floor_mm: float | None = None,
) -> tuple[list[DisambiguationResult], dict[str, float]]:
    """Run the full per-crystal depth disambiguation.

    Parameters
    ----------
    observations:
        Output of :func:`detect_observations`.
    lens, d_focus:
        Optical setup.
    focal_sharpness_quantile:
        Detections above this normalised sharpness quantile are taken to
        sit at the focal plane and define the size prior.
    sigma_floor_mm:
        Sensor floor for the sharpness inversion (default = pitch / 2).

    Returns
    -------
    Per-crystal results plus a small dict of population-level statistics.
    """
    if sigma_floor_mm is None:
        sigma_floor_mm = (lens.pixel_pitch_um * 1e-3) / 2.0

    raw = np.array([o.sharpness_score for o in observations])
    s_norm = _normalise_sharpness(raw)

    sizes_px = np.array([o.apparent_size_px for o in observations])
    focal_mask = s_norm >= float(np.quantile(s_norm, focal_sharpness_quantile))
    centres_mm, pdf = _physical_size_prior(sizes_px[focal_mask], lens, d_focus)

    mm_per_px_focus = float(
        mm_per_pixel_at(lens, d_focus, np.array([d_focus]))[0]
    )

    results: list[DisambiguationResult] = []
    n_near = n_far = n_focus = 0
    for o, sn in zip(observations, s_norm):
        coc = float(_sharpness_to_coc(np.array([sn]), sigma_floor_mm)[0])
        if coc <= 0.0 or sn >= float(
            np.quantile(s_norm, focal_sharpness_quantile)
        ):
            results.append(
                DisambiguationResult(
                    obs=o,
                    s_normalised=float(sn),
                    coc_mm=coc,
                    d_near=d_focus,
                    d_far=d_focus,
                    w_near_mm=o.apparent_size_px * mm_per_px_focus,
                    w_far_mm=o.apparent_size_px * mm_per_px_focus,
                    p_near=0.5,
                    side="focus",
                    physical_size_mm=o.apparent_size_px * mm_per_px_focus,
                )
            )
            n_focus += 1
            continue

        pair = _circle_of_confusion_to_object_distances(lens, d_focus, coc)
        if pair is None:
            continue
        d_near, d_far = pair
        mm_near = float(mm_per_pixel_at(lens, d_focus, np.array([d_near]))[0])
        mm_far = float(mm_per_pixel_at(lens, d_focus, np.array([d_far]))[0])
        w_near = o.apparent_size_px * mm_near
        w_far = o.apparent_size_px * mm_far
        l_near = _likelihood(w_near, centres_mm, pdf)
        l_far = _likelihood(w_far, centres_mm, pdf)
        p_near = l_near / (l_near + l_far)
        side = "near" if p_near > 0.5 else "far"
        w = w_near if side == "near" else w_far
        results.append(
            DisambiguationResult(
                obs=o,
                s_normalised=float(sn),
                coc_mm=coc,
                d_near=d_near,
                d_far=d_far,
                w_near_mm=w_near,
                w_far_mm=w_far,
                p_near=p_near,
                side=side,
                physical_size_mm=w,
            )
        )
        if side == "near":
            n_near += 1
        else:
            n_far += 1

    stats = {
        "n_total": float(len(results)),
        "n_focus": float(n_focus),
        "n_near": float(n_near),
        "n_far": float(n_far),
        "frac_near": float(n_near / max(1, n_near + n_far)),
        "median_w_mm": float(np.median([r.physical_size_mm for r in results])),
        "mean_w_mm": float(np.mean([r.physical_size_mm for r in results])),
        "iqr_w_mm": float(
            np.quantile([r.physical_size_mm for r in results], 0.75)
            - np.quantile([r.physical_size_mm for r in results], 0.25)
        ),
    }
    return results, stats


def fig_discriminability(
    lens: LensSetup,
    d_focus: float,
    out_path: Path,
    *,
    deltas: tuple[float, ...] = (0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 40.0),
) -> None:
    """Show *how far from focus* a crystal must be for size to disambiguate it.

    For each near-side offset ``δ``, the same-blur far-side depth is the
    1/d_o-symmetric partner; the implied apparent-size ratio (near/far)
    is the y-axis. The right-hand x-axis marks the geometric blur c at
    the sensor — the detector cannot find crystals once c exceeds a few
    pixels, so the actually-usable region is a small subset of this
    curve.
    """
    deltas_arr = np.linspace(0.1, 50.0, 500)
    u_focus = 1.0 / d_focus
    d_near = d_focus - deltas_arr
    u_far = 2.0 * u_focus - 1.0 / d_near
    valid = u_far > 0
    d_far = np.where(valid, 1.0 / np.where(valid, u_far, 1.0), np.nan)
    ratio = d_far / d_near
    c = circle_of_confusion(lens, d_focus, d_near) * 1000.0

    fig, ax_l = plt.subplots(figsize=(8.5, 4.6))
    ax_l.plot(
        deltas_arr,
        ratio,
        color="C0",
        label="apparent-size ratio (near / far at same blur)",
    )
    ax_l.set_xlabel("near-side offset δ = d_focus − d_near (mm)")
    ax_l.set_ylabel("apparent-size ratio")
    ax_l.axhline(
        1.05, color="C3", linestyle=":", label="5 % discrimination threshold"
    )
    ax_l.grid(True, alpha=0.3)
    ax_r = ax_l.twinx()
    ax_r.plot(deltas_arr, c, color="C2", label="CoC at sensor (µm)")
    ax_r.set_ylabel("CoC at sensor (µm)")
    ax_r.axhline(
        lens.pixel_pitch_um,
        color="C2",
        linestyle=":",
        alpha=0.5,
        label=f"1-px blur ({lens.pixel_pitch_um:.1f} µm)",
    )
    ax_r.axhline(
        5 * lens.pixel_pitch_um,
        color="C2",
        linestyle="--",
        alpha=0.5,
        label="5-px blur — typical detection cutoff",
    )
    ax_l.legend(loc="upper left", fontsize=9)
    ax_r.legend(loc="upper right", fontsize=9)
    fig.suptitle(
        f"Discriminability: at f={lens.focal_length:.0f} mm, F/{lens.f_number:.1f},"
        f" focus={d_focus:.0f} mm",
        y=1.02,
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def save_observations_csv(
    results: list[DisambiguationResult],
    out_path: Path,
) -> None:
    """Dump per-crystal results to CSV for downstream inspection."""
    with out_path.open("w") as f:
        f.write(
            "frame_idx,x_px,y_px,apparent_size_px,sharpness_score,"
            "s_normalised,coc_mm,d_near,d_far,w_near_mm,w_far_mm,"
            "p_near,side,physical_size_mm\n"
        )
        for r in results:
            f.write(
                f"{r.obs.frame_idx},{r.obs.x_px:.2f},{r.obs.y_px:.2f},"
                f"{r.obs.apparent_size_px:.3f},{r.obs.sharpness_score:.3f},"
                f"{r.s_normalised:.4f},{r.coc_mm:.5f},"
                f"{r.d_near:.3f},{r.d_far:.3f},"
                f"{r.w_near_mm:.4f},{r.w_far_mm:.4f},"
                f"{r.p_near:.4f},{r.side},{r.physical_size_mm:.4f}\n"
            )


def fig_disambiguation(
    results: list[DisambiguationResult],
    out_path: Path,
    *,
    lens: LensSetup,
    d_focus: float,
) -> None:
    """Three-panel summary of the disambiguation outcome."""
    fig, (ax_size, ax_depth, ax_naive) = plt.subplots(
        1, 3, figsize=(15.5, 4.4)
    )

    sizes_focus = [r.physical_size_mm for r in results if r.side == "focus"]
    sizes_near = [r.physical_size_mm for r in results if r.side == "near"]
    sizes_far = [r.physical_size_mm for r in results if r.side == "far"]
    bins = np.linspace(0.0, 1.5, 40)
    ax_size.hist(
        sizes_focus, bins=bins, alpha=0.5, label="focal plane", color="C0"
    )
    ax_size.hist(
        sizes_near, bins=bins, alpha=0.5, label="near side", color="C3"
    )
    ax_size.hist(sizes_far, bins=bins, alpha=0.5, label="far side", color="C2")
    ax_size.set_xlabel("estimated physical size (mm)")
    ax_size.set_ylabel("crystal count")
    ax_size.set_title("Disambiguated physical-size distribution")
    ax_size.legend()
    ax_size.grid(True, alpha=0.3)

    depths_near = [r.d_near for r in results if r.side == "near"]
    depths_far = [r.d_far for r in results if r.side == "far"]
    n_near = len(depths_near)
    n_far = len(depths_far)
    n_focus = sum(1 for r in results if r.side == "focus")
    ax_depth.hist(
        depths_near, bins=40, alpha=0.6, color="C3", label=f"near (n={n_near})"
    )
    ax_depth.hist(
        depths_far, bins=40, alpha=0.6, color="C2", label=f"far (n={n_far})"
    )
    # Focal-plane detections all sit at d_focus by construction (no near/far
    # disambiguation needed) — show as a labelled marker, NOT a histogram
    # bar, to avoid drowning out the near/far distributions.
    ax_depth.axvline(
        d_focus,
        color="C0",
        linestyle="-",
        linewidth=2.2,
        alpha=0.8,
        label=f"focal plane @ d_focus={d_focus:.1f} mm  (n={n_focus})",
    )
    ax_depth.set_xlabel("estimated object distance (mm)")
    ax_depth.set_ylabel("crystal count")
    ax_depth.set_title(
        f"Per-crystal depth assignment (total n={n_near + n_far + n_focus})"
    )
    # Fewer tick locations to avoid overlap in the narrow x-range.
    ax_depth.xaxis.set_major_locator(plt.MaxNLocator(nbins=6))
    ax_depth.legend(fontsize=8, loc="upper right")
    ax_depth.grid(True, alpha=0.3)

    naive_mm_per_px = float(
        mm_per_pixel_at(lens, d_focus, np.array([d_focus]))[0]
    )
    naive_sizes = [r.obs.apparent_size_px * naive_mm_per_px for r in results]
    corrected_sizes = [r.physical_size_mm for r in results]
    ax_naive.hist(
        naive_sizes,
        bins=bins,
        alpha=0.5,
        label="naive (use mm/px at focus)",
        color="C0",
    )
    ax_naive.hist(
        corrected_sizes,
        bins=bins,
        alpha=0.5,
        label="depth-corrected",
        color="C1",
    )
    ax_naive.set_xlabel("physical size (mm)")
    ax_naive.set_ylabel("crystal count")
    ax_naive.set_title("Naive vs depth-corrected size estimate")
    ax_naive.legend()
    ax_naive.grid(True, alpha=0.3)

    fig.suptitle(
        "Front/back disambiguation via focal-plane size prior",
        y=1.02,
        fontsize=12,
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    """End-to-end run on the plant video."""
    cfg = load_camera()
    lens = lens_from_config_and_video(cfg, "datasets/2026-02-05 10-36-32.mp4")
    min_area, max_area = detection_area_px(cfg, lens)
    config = LayerConfig(
        num_layers=3,
        sharpness_weight=0.7,
        flow_weight=0.3,
        blur_kernel=15,
        min_area=min_area,
        max_area=max_area,
        max_aspect_ratio=3.0,
    )
    d_focus = cfg.focus_object_distance_mm

    print("Detecting crystals (watershed)…")
    obs = detect_observations(
        "datasets/2026-02-05 10-36-32.mp4",
        config,
        frame_stride=15,
        max_frames=60,
        detector="watershed",
    )
    print(f"  {len(obs)} crystal detections across sampled frames")

    print("Disambiguating depth…")
    results, stats = disambiguate(obs, lens, d_focus)

    print("\n=== Population statistics ===")
    for k, v in stats.items():
        print(f"  {k:20s}: {v:.4f}")

    out_dir = Path("docs/optics/figures")
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_disambiguation(
        results, out_dir / "09_disambiguation.png", lens=lens, d_focus=d_focus
    )
    fig_discriminability(lens, d_focus, out_dir / "10_discriminability.png")

    csv_path = Path("docs/optics/crystal_observations.csv")
    save_observations_csv(results, csv_path)
    print(
        f"\nFigures: {out_dir}/09_disambiguation.png, {out_dir}/10_discriminability.png"
    )
    print(f"Per-crystal CSV: {csv_path}")

    # Sanity-check the depth correction relative to naive scaling
    naive_mm_per_px = float(
        mm_per_pixel_at(lens, d_focus, np.array([d_focus]))[0]
    )
    naive_sizes = np.array(
        [r.obs.apparent_size_px * naive_mm_per_px for r in results]
    )
    corrected_sizes = np.array([r.physical_size_mm for r in results])
    diff = corrected_sizes - naive_sizes
    print("\n=== Depth-correction magnitude ===")
    print(f"  median naive size       : {np.median(naive_sizes):.4f} mm")
    print(f"  median corrected size   : {np.median(corrected_sizes):.4f} mm")
    print(f"  mean |correction|       : {float(np.mean(np.abs(diff))):.5f} mm")
    print(
        f"  mean |correction| / size: {float(np.mean(np.abs(diff)) / np.median(naive_sizes) * 100):.2f} %"
    )


if __name__ == "__main__":
    main()
