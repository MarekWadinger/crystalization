"""RQ4 follow-up — crystal sharpness with glass-rupture baseline removed.

Idea (operator-suggested): the static glass surface has cracks /
ruptures / etched marks that the detector picks up as high-sharpness
features. These contaminate every CSD because they live at fixed
pixels in every frame. If we image the tank when it's *empty*
(slurry drained, no crystals at all), every detection in that
window is by definition a glass artefact. We can then build a
per-pixel sharpness baseline from the empty footage and subtract it
from the in-batch sharpness of each detected crystal.

The output is the distribution of ``crystal_sharpness − rupture_baseline``
for the two batches' drying→discharge windows, fitted with Gaussians
and overlaid with vertical "mean lines" (analogous to the focus-line
in 01_mm_per_pixel.png).

Empty-tank window (from datasets/2026-02-04 11-08-51.json):
    t = 2270.5 s  (b1-e01 ``empty``)
        →
    t = 2532.5 s  (b2-e01b ``new_batch_vacuum_pull``)
    = 262 s of confirmed tank-empty state.

Reused batch windows from scripts/rq4_b1_vs_b2.py:
    b1 drying→discharge:  t = 1213.1 → 2270.5 s
    b2 drying→discharge:  t = 16340.5 → 17510.5 s
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TypedDict

import cv2
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

from annotator.types import LayerConfig
from optics.disambiguate import detect_observations
from optics.video_io import DEFAULT_CROP

LONG_VIDEO = "datasets/2026-02-04 11-08-51.mp4"
FPS = 30.0

# [2300, 2450] s — *inside* the b1 empty interval [b1-e01 @ 2270.5,
# discharge-segment-end @ 2453.5], with 30 s shaved off the front (residual
# draining) and 3 s off the back (cleaning starts). 150 s.
#
# IMPORTANT (verified by extracting frames at t=2300/2375/2450): this is
# NOT a clean dry sight glass — residual droplets and a wet film cling to
# the inside of the glass after draining. The "ruptures" we subtract are
# really "ruptures + residual droplet pattern at drain-stop". So the
# downstream metric is sharpness contributed by the slurry-filled batch
# frames OVER what a drained-wet-glass frame shows. Honest label, not
# "crystal-only sharpness".
EMPTY_WINDOW = (2300.0, 2450.0)
# Held-out window for noise-floor estimation — explicit b2-end empty segment,
# NOT overlapping with the reference-building window above. Closes the
# self-comparison-bias hole the red-team flagged.
EMPTY_WINDOW_ALT = (17900.5, 17934.5)
B1_WINDOW = (1213.1, 2270.5)
B2_WINDOW = (16340.5, 17510.5)


class _WindowResult(TypedDict, total=False):
    # set by _run_window
    label: str
    n_obs: int
    raw_sharpness: np.ndarray
    ref_sharpness_at_bbox: np.ndarray
    diff_sharpness: np.ndarray
    apparent_size_px: np.ndarray
    x_px: np.ndarray
    y_px: np.ndarray
    frame_idx: np.ndarray
    frame_range: tuple[int, int]
    frame_stride: int
    t_start: float
    t_end: float
    # added in main after _run_window
    bbox_noise: np.ndarray
    diff_median: float
    diff_iqr: float
    ci_lo: float
    ci_hi: float
    pearson_size: float


def _build_empty_reference(
    t0: float,
    t1: float,
    *,
    max_frames: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Build (a) the empty-tank reference IMAGE (gray, per-pixel median),
    and (b) the empty-tank sharpness map (Laplacian² smoothed).

    The reference image lets us SUBTRACT-AND-RECOMPUTE: rather than
    comparing absolute sharpness values (which conflates "the crystal
    is dimmer" with "the glass rupture got blocked"), we subtract the
    static glass appearance from each slurry frame and recompute
    sharpness on the residual. That isolates the *contributed* signal.

    Median across frames (not mean) so that any transient
    droplets / cavitation puffs / residual condensation drifting
    through during the "empty" window do NOT survive into the
    baseline — only what is genuinely persistent does.
    """
    start_frame = int(round(t0 * FPS))
    end_frame = int(round(t1 * FPS))
    span = end_frame - start_frame
    stride = max(1, span // max_frames)

    cap = cv2.VideoCapture(LONG_VIDEO)
    grays: list[np.ndarray] = []
    sharps: list[np.ndarray] = []
    idx = start_frame
    while idx < end_frame and len(grays) < max_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            break
        frame = DEFAULT_CROP.apply(frame)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float64)
        grays.append(gray)
        lap = cv2.Laplacian(gray, cv2.CV_64F)
        sharps.append(cv2.GaussianBlur(lap**2, (15, 15), 0))
        idx += stride
    cap.release()

    if not grays:
        raise RuntimeError("could not read any empty-window frames")
    print(
        f"[baseline] median over {len(grays)} empty-window frames "
        f"(t=[{t0:.1f}, {t1:.1f}], stride={stride})",
        file=sys.stderr,
    )
    ref_img = np.median(np.stack(grays, axis=0), axis=0)
    ref_sharp = np.median(np.stack(sharps, axis=0), axis=0)
    return ref_img, ref_sharp


def _run_window(
    label: str,
    t0: float,
    t1: float,
    *,
    max_frames: int,
    detector: str,
    ref_img: np.ndarray,
    ref_sharp: np.ndarray,
) -> _WindowResult:
    """Detect crystals; for each detection, compute three sharpness values:

    * ``raw_sharpness``   — Laplacian² of the slurry frame in the bbox
    * ``ref_sharpness``   — Laplacian² of the empty-tank reference in same bbox
    * ``diff_sharpness``  — Laplacian² of the *difference image*
      (|slurry − reference|) in the bbox — the "remaining signal" the user asked
      for. This isolates what's *new* in the slurry frame at that location and
      is the physically defensible "crystal − rupture" residual.

    Detection itself still runs on the raw slurry frame so we sample at the same
    candidate locations as the existing pipeline.
    """
    start_frame = int(round(t0 * FPS))
    end_frame = int(round(t1 * FPS))
    span = end_frame - start_frame
    stride = max(1, span // max_frames)

    config = LayerConfig(
        num_layers=3,
        sharpness_weight=0.7,
        flow_weight=0.3,
        blur_kernel=15,
        min_area=80.0,
        max_area=8000.0,
        max_aspect_ratio=3.0,
    )

    print(
        f"[{label}] window t=[{t0:.1f}, {t1:.1f}] frames=[{start_frame}, {end_frame}] "
        f"stride={stride} sampling={max_frames}",
        file=sys.stderr,
    )
    obs = detect_observations(
        LONG_VIDEO,
        config,
        frame_stride=stride,
        max_frames=max_frames,
        start_frame=start_frame,
        detector=detector,
    )
    print(
        f"[{label}] {len(obs)} detections (computing residual sharpness…)",
        file=sys.stderr,
    )

    # Group detections by frame_idx so we read each frame only once.
    H, W = ref_img.shape
    by_frame: dict[int, list[int]] = {}
    for i, o in enumerate(obs):
        by_frame.setdefault(o.frame_idx, []).append(i)

    raw_sharp = np.zeros(len(obs))
    ref_sharp_at_bbox = np.zeros(len(obs))
    diff_sharp = np.zeros(len(obs))

    cap = cv2.VideoCapture(LONG_VIDEO)
    for fidx, idxs in by_frame.items():
        cap.set(cv2.CAP_PROP_POS_FRAMES, fidx)
        ret, frame = cap.read()
        if not ret:
            continue
        frame = DEFAULT_CROP.apply(frame)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float64)
        # Difference image — what's NEW in this frame vs the empty-tank reference.
        diff = np.abs(gray - ref_img)
        # Raw and diff sharpness maps.
        raw_lap = cv2.Laplacian(gray, cv2.CV_64F)
        raw_map = cv2.GaussianBlur(raw_lap**2, (15, 15), 0)
        diff_lap = cv2.Laplacian(diff, cv2.CV_64F)
        diff_map = cv2.GaussianBlur(diff_lap**2, (15, 15), 0)

        for i in idxs:
            o = obs[i]
            side = max(1, int(round(o.apparent_size_px)))
            half = side // 2
            x = int(round(o.x_px))
            y = int(round(o.y_px))
            x0 = max(0, x - half)
            x1 = min(W, x + half + 1)
            y0 = max(0, y - half)
            y1 = min(H, y + half + 1)
            raw_sharp[i] = float(raw_map[y0:y1, x0:x1].mean())
            ref_sharp_at_bbox[i] = float(ref_sharp[y0:y1, x0:x1].mean())
            diff_sharp[i] = float(diff_map[y0:y1, x0:x1].mean())
    cap.release()

    frame_idx = np.array([o.frame_idx for o in obs], dtype=np.int64)
    sizes = np.array([o.apparent_size_px for o in obs], dtype=np.float64)
    xs = np.array([o.x_px for o in obs], dtype=np.float64)
    ys = np.array([o.y_px for o in obs], dtype=np.float64)
    return {
        "label": label,
        "n_obs": len(obs),
        "raw_sharpness": raw_sharp,
        "ref_sharpness_at_bbox": ref_sharp_at_bbox,
        "diff_sharpness": diff_sharp,
        "apparent_size_px": sizes,
        "x_px": xs,
        "y_px": ys,
        "frame_idx": frame_idx,
        "frame_range": (start_frame, end_frame),
        "frame_stride": stride,
        "t_start": t0,
        "t_end": t1,
    }


def _frame_cluster_bootstrap(
    x: np.ndarray, frame_idx: np.ndarray, n_boot: int = 500
) -> tuple[float, float]:
    """Bootstrap the mean of x, resampling by FRAME (cluster) not by detection.

    Within-frame detections are statistically correlated (they sample the
    same Lap² map). Resampling by frame gives an honest 95 % CI on μ. Returns
    (ci_lo, ci_hi).
    """
    rng = np.random.default_rng(0)
    frames = np.unique(frame_idx)
    bag = {f: x[frame_idx == f] for f in frames}
    boots = np.empty(n_boot)
    for b in range(n_boot):
        sel = rng.choice(frames, size=frames.size, replace=True)
        cat = np.concatenate([bag[f] for f in sel])
        boots[b] = cat.mean()
    return float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))


def _gauss_fit(x: np.ndarray) -> tuple[float, float]:
    if x.size < 2:
        return float("nan"), float("nan")
    mu, sigma = stats.norm.fit(x)
    return float(mu), float(sigma)


def _plot_gaussians(
    b1: _WindowResult,
    b2: _WindowResult,
    out_path: Path,
    *,
    noise_floor: float = 0.0,
    noise_dist: np.ndarray | None = None,
) -> None:
    """Four panels:
    (a) raw bbox sharpness (with mean lines + empty-tank reference at bbox)
    (b) difference-image sharpness (the rupture-subtracted crystal signal)
         with Gaussian fits and mean lines — the headline panel
    (c) same as (b) but FILTERED to detections above noise floor
         (the "remaining crystals" the user asked for)
    (d) per-time-bin evolution of mean diff_sharpness through each window —
         shows whether the signal grows over drying→discharge.
    """
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    ax_raw, ax_diff = axes[0]
    ax_filt, ax_time = axes[1]
    palette = {"b1": "C0", "b2": "C3"}

    # --- Panel A: raw + reference at bbox -----------------------------------
    raw_all = np.concatenate([b1["raw_sharpness"], b2["raw_sharpness"]])
    ref_all = np.concatenate(
        [b1["ref_sharpness_at_bbox"], b2["ref_sharpness_at_bbox"]]
    )
    hi_r = float(np.quantile(np.concatenate([raw_all, ref_all]), 0.99))
    bins_r = np.linspace(0, hi_r, 70)
    for d, col in ((b1, palette["b1"]), (b2, palette["b2"])):
        mu, sig = _gauss_fit(d["raw_sharpness"])
        ax_raw.hist(
            d["raw_sharpness"],
            bins=bins_r,
            density=True,
            alpha=0.45,
            color=col,
            label=f"{d['label']} slurry-frame  μ={mu:.1f} σ={sig:.1f}",
        )
        ax_raw.axvline(mu, color=col, linestyle="--", lw=1.5)
    ref_mu = float(ref_all.mean())
    ax_raw.axvline(
        ref_mu,
        color="0.3",
        lw=2.0,
        linestyle=":",
        label=f"empty-tank ref at same bboxes  μ={ref_mu:.1f}",
    )
    ax_raw.set_xlabel("Laplacian² sharpness in bbox")
    ax_raw.set_ylabel("density")
    ax_raw.set_title("Raw bbox sharpness vs empty-tank reference")
    ax_raw.legend(fontsize=8)
    ax_raw.grid(True, alpha=0.3)

    # --- Panel B: difference-image sharpness (the headline) -----------------
    diff_all = np.concatenate([b1["diff_sharpness"], b2["diff_sharpness"]])
    lo = float(np.quantile(diff_all, 0.005))
    hi = float(np.quantile(diff_all, 0.995))
    bins = np.linspace(lo, hi, 70)
    for d, col in ((b1, palette["b1"]), (b2, palette["b2"])):
        x = d["diff_sharpness"]
        mu, sig = _gauss_fit(x)
        ax_diff.hist(
            x,
            bins=bins,
            density=True,
            alpha=0.45,
            color=col,
            label=f"{d['label']} crystal-only  μ={mu:.2f} σ={sig:.2f} n={d['n_obs']}",
        )
        xs = np.linspace(lo, hi, 400)
        ax_diff.plot(xs, stats.norm.pdf(xs, mu, sig), color=col, lw=2)
        ax_diff.axvline(mu, color=col, linestyle="--", lw=1.8)
    if noise_floor > 0:
        ax_diff.axvline(
            noise_floor,
            color="0.2",
            lw=2,
            linestyle=":",
            label=f"same-bbox noise floor median  ={noise_floor:.1f}",
        )
    if noise_dist is not None and noise_dist.size:
        ax_diff.hist(
            noise_dist,
            bins=bins,
            density=True,
            alpha=0.20,
            color="0.4",
            label=f"held-out empty diff at same bboxes (n={noise_dist.size})",
            histtype="step",
            linewidth=1.8,
        )
    ax_diff.set_xlabel("Laplacian²(|slurry − empty_ref|) in bbox")
    ax_diff.set_ylabel("density")
    ax_diff.set_title(
        "Crystal-only sharpness (ruptures removed) — Gaussian fits"
    )
    ax_diff.legend(fontsize=8)
    ax_diff.grid(True, alpha=0.3)

    # --- Panel C: filtered to detections above noise floor ------------------
    # "Remaining crystals" = detections whose diff-image sharpness exceeds the
    # noise floor of empty-vs-ref. Below the floor it cannot be distinguished
    # from camera noise + median-shift jitter.
    threshold = noise_floor if noise_floor > 0 else 0.0
    bins_f = bins
    for d, col in ((b1, palette["b1"]), (b2, palette["b2"])):
        x = d["diff_sharpness"]
        kept = x[x > threshold]
        kept_frac = kept.size / x.size if x.size else 0.0
        mu, sig = _gauss_fit(kept)
        ax_filt.hist(
            kept,
            bins=bins_f,
            density=True,
            alpha=0.45,
            color=col,
            label=f"{d['label']}  kept={kept.size}/{x.size} ({kept_frac:.0%})"
            f"  μ={mu:.2f} σ={sig:.2f}",
        )
        xs = np.linspace(threshold, bins_f[-1], 400)
        ax_filt.plot(xs, stats.norm.pdf(xs, mu, sig), color=col, lw=2)
        ax_filt.axvline(mu, color=col, linestyle="--", lw=1.8)
    ax_filt.axvline(
        threshold,
        color="0.2",
        lw=2,
        linestyle=":",
        label=f"keep threshold = noise floor ({threshold:.1f})",
    )
    ax_filt.set_xlabel("Laplacian²(|slurry − empty_ref|) in bbox")
    ax_filt.set_ylabel("density")
    ax_filt.set_title("Remaining crystals (above-noise) — Gaussian fits")
    ax_filt.legend(fontsize=8)
    ax_filt.grid(True, alpha=0.3)

    # Show median + IQR + CI on the headline panel for honest summary stats.
    summary = []
    for d, col in ((b1, palette["b1"]), (b2, palette["b2"])):
        summary.append(
            f"{d['label']}: median={d['diff_median']:.1f}  IQR={d['diff_iqr']:.1f}  "
            f"95% CI(μ frame-cluster)=[{d['ci_lo']:.1f}, {d['ci_hi']:.1f}]  "
            f"r(diff, size)={d['pearson_size']:+.2f}"
        )
    ax_diff.text(
        0.02,
        0.98,
        "\n".join(summary),
        transform=ax_diff.transAxes,
        va="top",
        ha="left",
        fontsize=7,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.85),
    )

    # --- Panel D: time evolution within each window -------------------------
    for d, col in ((b1, palette["b1"]), (b2, palette["b2"])):
        x = d["diff_sharpness"]
        f = d["frame_idx"]
        if f.size == 0:
            continue
        t0, t1 = d["t_start"], d["t_end"]
        t = f / FPS  # absolute wallclock-style seconds
        # Normalise to phase progress in [0, 1] so b1 and b2 are comparable.
        progress = (t - t0) / (t1 - t0)
        # Bin into 12 quantile buckets.
        nbins = 12
        bin_edges = np.linspace(0, 1, nbins + 1)
        bin_centres = 0.5 * (bin_edges[1:] + bin_edges[:-1])
        means = np.zeros(nbins)
        stds = np.zeros(nbins)
        for k in range(nbins):
            mask = (progress >= bin_edges[k]) & (progress < bin_edges[k + 1])
            if mask.sum() > 5:
                means[k] = x[mask].mean()
                stds[k] = x[mask].std() / np.sqrt(mask.sum())
            else:
                means[k] = np.nan
                stds[k] = np.nan
        ax_time.errorbar(
            bin_centres,
            means,
            yerr=stds,
            marker="o",
            color=col,
            label=f"{d['label']}  μ_overall={x.mean():.1f}",
        )
    if noise_floor > 0:
        ax_time.axhline(
            noise_floor,
            color="0.2",
            lw=2,
            linestyle=":",
            label=f"noise floor = {noise_floor:.1f}",
        )
    ax_time.set_xlabel(
        "normalised phase progress  (0 = drying start,  1 = discharge)"
    )
    ax_time.set_ylabel("mean diff-image Lap² (per time bin)")
    ax_time.set_title("Time evolution within drying→discharge")
    ax_time.legend(fontsize=8)
    ax_time.grid(True, alpha=0.3)

    fig.suptitle(
        "RQ4 — drying→discharge slurry-frame sharpness with drained-wet-glass "
        "reference removed\n(reference is NOT a clean dry glass — residual film + "
        "droplets at drain-stop)",
        y=1.02,
        fontsize=11,
    )
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    # Reviewer recommendation #7: 80 frames over 1057 s → 1 / 13 s — too coarse
    # to see crystal growth in the time-evolution panel. 200 default.
    p.add_argument("--max-frames", type=int, default=200)
    p.add_argument("--baseline-frames", type=int, default=80)
    p.add_argument(
        "--detector", default="watershed", choices=["watershed", "edge"]
    )
    p.add_argument(
        "--out",
        type=Path,
        default=Path("docs/optics/figures/rq4_sharpness_minus_ruptures.png"),
    )
    p.add_argument(
        "--out-baseline-stats",
        type=Path,
        default=Path("docs/optics/figures/rq4_sharpness_baseline.png"),
    )
    args = p.parse_args(argv)

    ref_img, ref_sharp = _build_empty_reference(
        *EMPTY_WINDOW, max_frames=args.baseline_frames
    )
    print(
        f"[baseline] ref_img shape={ref_img.shape} "
        f"intensity μ={ref_img.mean():.1f} σ={ref_img.std():.1f}  "
        f"ref_sharp μ={ref_sharp.mean():.2f} σ={ref_sharp.std():.2f}",
        file=sys.stderr,
    )

    # ---- Noise floor: build a stack of diff-image maps from HELD-OUT
    # empty-window frames (b2-end empty segment, t=[17900.5, 17934.5]),
    # NOT overlapping with the reference window. We keep the maps so we
    # can later sample them at the SAME bboxes the signal was measured at —
    # apples-to-apples noise floor instead of whole-frame mean.
    held_diff_maps: list[np.ndarray] = []
    cap = cv2.VideoCapture(LONG_VIDEO)
    t0, t1 = EMPTY_WINDOW_ALT
    start_frame = int(round(t0 * FPS))
    end_frame = int(round(t1 * FPS))
    span = end_frame - start_frame
    stride_noise = max(1, span // 30)
    idx = start_frame
    while idx < end_frame and len(held_diff_maps) < 30:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            break
        frame = DEFAULT_CROP.apply(frame)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float64)
        diff = np.abs(gray - ref_img)
        diff_lap = cv2.Laplacian(diff, cv2.CV_64F)
        diff_map = cv2.GaussianBlur(diff_lap**2, (15, 15), 0)
        held_diff_maps.append(diff_map)
        idx += stride_noise
    cap.release()
    if not held_diff_maps:
        raise RuntimeError("could not build held-out noise frames")
    held_stack = np.stack(held_diff_maps, axis=0)  # (T, H, W)
    noise_floor_global_mu = float(held_stack.mean())
    noise_floor_global_sigma = float(held_stack.mean(axis=(1, 2)).std())
    print(
        f"[noise floor whole-frame] over {len(held_diff_maps)} held-out frames: "
        f"μ={noise_floor_global_mu:.2f} σ={noise_floor_global_sigma:.2f}",
        file=sys.stderr,
    )

    b1 = _run_window(
        "b1",
        *B1_WINDOW,
        max_frames=args.max_frames,
        detector=args.detector,
        ref_img=ref_img,
        ref_sharp=ref_sharp,
    )
    b2 = _run_window(
        "b2",
        *B2_WINDOW,
        max_frames=args.max_frames,
        detector=args.detector,
        ref_img=ref_img,
        ref_sharp=ref_sharp,
    )

    # ---- Per-detection noise floor at the SAME bbox locations the signal
    # was measured at. For each detection in b1/b2, draw the held-out
    # noise diff_sharpness from a randomly-chosen held-out frame at that
    # bbox. This gives a direct apples-to-apples noise distribution.
    H, W = ref_img.shape
    rng = np.random.default_rng(0)
    n_held = held_stack.shape[0]
    for d in (b1, b2):
        idxs = rng.integers(0, n_held, size=d["n_obs"])
        bb_noise = np.empty(d["n_obs"])
        for i in range(d["n_obs"]):
            side = max(1, int(round(d["apparent_size_px"][i])))
            half = side // 2
            xx = int(round(d["x_px"][i]))
            yy = int(round(d["y_px"][i]))
            x0 = max(0, xx - half)
            x1 = min(W, xx + half + 1)
            y0 = max(0, yy - half)
            y1 = min(H, yy + half + 1)
            tt = int(idxs[i])
            bb_noise[i] = float(held_stack[tt, y0:y1, x0:x1].mean())
        d["bbox_noise"] = bb_noise
        bb_med = float(np.median(bb_noise))
        print(
            f"[{d['label']}] SAME-bbox noise floor (held-out frame at same x,y): "
            f"μ={bb_noise.mean():.2f} σ={bb_noise.std():.2f} "
            f"med={bb_med:.2f}",
            file=sys.stderr,
        )

    for d in (b1, b2):
        raw_mu, raw_sig = _gauss_fit(d["raw_sharpness"])
        ref_mu = float(d["ref_sharpness_at_bbox"].mean())
        x = d["diff_sharpness"]
        diff_mu = float(x.mean())
        diff_med = float(np.median(x))
        diff_iqr = float(np.quantile(x, 0.75) - np.quantile(x, 0.25))
        ci_lo, ci_hi = _frame_cluster_bootstrap(x, d["frame_idx"])
        # Pearson correlation with bbox size — confounder check.
        r = float(np.corrcoef(x, d["apparent_size_px"])[0, 1])
        d["diff_median"] = diff_med
        d["diff_iqr"] = diff_iqr
        d["ci_lo"] = ci_lo
        d["ci_hi"] = ci_hi
        d["pearson_size"] = r
        print(
            f"[{d['label']}] n={d['n_obs']}  raw μ={raw_mu:.2f}  "
            f"ref-at-bbox μ={ref_mu:.2f}  diff μ={diff_mu:.2f} "
            f"med={diff_med:.2f} IQR={diff_iqr:.2f}  "
            f"95% CI(μ, cluster-by-frame)=[{ci_lo:.2f}, {ci_hi:.2f}]  "
            f"Pearson(diff,bbox)={r:+.3f}"
        )

    # Use the same-bbox noise floor — averaged over both batches' bbox-noise
    # distributions — as the honest threshold.
    same_bbox_noise = np.concatenate([b1["bbox_noise"], b2["bbox_noise"]])
    print(
        f"[noise floor SAME-bbox combined] μ={same_bbox_noise.mean():.2f} "
        f"σ={same_bbox_noise.std():.2f} med={np.median(same_bbox_noise):.2f}",
        file=sys.stderr,
    )
    _plot_gaussians(
        b1,
        b2,
        args.out,
        noise_floor=float(np.median(same_bbox_noise)),
        noise_dist=same_bbox_noise,
    )
    print(f"[rq4] wrote {args.out}", file=sys.stderr)

    # Diagnostic — the empty-tank reference IMAGE and sharpness map side-by-side.
    fig, (ax_img, ax_sh) = plt.subplots(1, 2, figsize=(11, 4))
    im_i = ax_img.imshow(ref_img, cmap="gray", aspect="auto")
    plt.colorbar(im_i, ax=ax_img, label="median intensity")
    ax_img.set_title(
        f"Empty-tank reference image\n({args.baseline_frames} frames, "
        f"t=[{EMPTY_WINDOW[0]:.0f}, {EMPTY_WINDOW[1]:.0f}] s)"
    )
    im_s = ax_sh.imshow(np.log1p(ref_sharp), cmap="magma", aspect="auto")
    plt.colorbar(im_s, ax=ax_sh, label="log(1 + Laplacian²)")
    ax_sh.set_title("Empty-tank sharpness map (glass ruptures)")
    fig.tight_layout()
    fig.savefig(args.out_baseline_stats, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"[rq4] wrote {args.out_baseline_stats}", file=sys.stderr)


if __name__ == "__main__":
    main()
