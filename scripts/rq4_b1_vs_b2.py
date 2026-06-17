"""RQ4 cross-batch self-validation — b1 vs b2 drying→discharge.

Runs the existing pipeline (`detect_observations` → `disambiguate` →
`aggregate_csd` + α from `collect_sharpness_histogram`) twice on the
SAME long recording ``datasets/2026-02-04 11-08-51.mp4`` — once on the
*batch-1 drying→discharge* window captured at the start of the file,
once on the *batch-2 drying→discharge* window at the end. Same camera,
same lens, same focus, same recording session: only the batch differs.

Windows (from the sidecar of the long recording, see
``datasets/2026-02-04 11-08-51.json``):

* **b1 drying→discharge** — t = 1213.1 s (predicted b1-e08 ``drying``)
  through t = 2270.5 s (observed b1-e01 ``empty``). Length 1057.4 s.
* **b2 drying→discharge** — t = 16340.5 s (observed b2-e08 ``drying``)
  through t = 17510.5 s (observed eb2-10b ``empty``). Length 1170.0 s.

Caveat: b1's drying/aeration start are predicted via the 0.9021 scale
(b1 anchor: discharge @ 11:46:10), so the b1 window is *bracketed by*
prediction at the leading edge and by direct observation at the
trailing edge; b2's window is fully observed. Crystal-size kinetics
across the two windows should still be comparable because both end
just before the discharge release and both span the same phase pair.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TypedDict

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

from annotator.types import LayerConfig
from optics.csd import aggregate_csd, fig_csd_final
from optics.disambiguate import (
    DisambiguationResult,
    detect_observations,
    disambiguate,
)
from optics.measure import collect_sharpness_histogram, fit_power_law_tail
from optics.model import LensSetup, mm_per_pixel_at

LONG_VIDEO = "datasets/2026-02-04 11-08-51.mp4"
FPS = 30.0

# (t_start_s, t_end_s) per batch, in the long recording's timeline.
B1_WINDOW = (1213.1, 2270.5)  # b1-e08_pred drying → b1-e01 empty
B2_WINDOW = (16340.5, 17510.5)  # b2-e08 drying → eb2-10b empty

THEORETICAL_ALPHA = 5.0


class _WindowResult(TypedDict):
    label: str
    window_s: tuple[float, float]
    frame_range: tuple[int, int]
    frame_stride: int
    sampled_frames: int
    n_detections: int
    per_frame_mean: float
    per_frame_std: float
    csd: dict[str, float]
    sizes_mm: np.ndarray
    alpha: float
    alpha_deviation_pct: float
    dstats: dict[str, int | float]
    mean_correction_mm: float
    mean_correction_pct: float
    results: list[DisambiguationResult]
    lens: LensSetup
    d_focus: float


def _run_window(
    label: str,
    t0: float,
    t1: float,
    *,
    max_frames: int,
    detector: str,
) -> _WindowResult:
    start_frame = int(round(t0 * FPS))
    end_frame = int(round(t1 * FPS))
    span_frames = end_frame - start_frame
    frame_stride = max(1, span_frames // max_frames)

    config = LayerConfig(
        num_layers=3,
        sharpness_weight=0.7,
        flow_weight=0.3,
        blur_kernel=15,
        min_area=80.0,
        max_area=8000.0,
        max_aspect_ratio=3.0,
    )
    lens = LensSetup(
        focal_length=35.0,
        f_number=1.6,
        extension_tube=45.0,
        pixel_pitch_um=2.8,
    )
    d_focus = 62.2

    print(
        f"[rq4][{label}] window t={t0:.1f}→{t1:.1f}s "
        f"(frames {start_frame}→{end_frame}, stride={frame_stride}, "
        f"sampling {max_frames}) — detecting…",
        file=sys.stderr,
    )
    obs = detect_observations(
        LONG_VIDEO,
        config,
        frame_stride=frame_stride,
        max_frames=max_frames,
        start_frame=start_frame,
        detector=detector,
    )
    print(f"[rq4][{label}] {len(obs)} detections", file=sys.stderr)

    print(f"[rq4][{label}] disambiguating…", file=sys.stderr)
    results, dstats = disambiguate(obs, lens, d_focus)

    mm_per_px_focus = float(
        mm_per_pixel_at(lens, d_focus, np.array([d_focus]))[0]
    )
    corr = np.array(
        [
            r.physical_size_mm - r.obs.apparent_size_px * mm_per_px_focus
            for r in results
        ],
        dtype=np.float64,
    )
    median_size = (
        float(np.median([r.physical_size_mm for r in results]))
        if results
        else 0.0
    )
    mean_abs_corr = float(np.mean(np.abs(corr))) if corr.size else 0.0
    mean_abs_corr_pct = (
        100.0 * mean_abs_corr / median_size if median_size > 0.0 else 0.0
    )

    print(f"[rq4][{label}] aggregating CSD…", file=sys.stderr)
    csd = aggregate_csd(results, lens, d_focus)

    print(f"[rq4][{label}] α fit…", file=sys.stderr)
    centres, density = collect_sharpness_histogram(
        LONG_VIDEO,
        frame_stride=frame_stride,
        max_frames=max_frames,
        start_frame=start_frame,
    )
    alpha, _ = fit_power_law_tail(centres, density)

    counts: dict[int, int] = {}
    for o in obs:
        counts[o.frame_idx] = counts.get(o.frame_idx, 0) + 1
    per_frame = np.array(list(counts.values()), dtype=np.float64)

    return {
        "label": label,
        "window_s": (t0, t1),
        "frame_range": (start_frame, end_frame),
        "frame_stride": frame_stride,
        "sampled_frames": len(counts),
        "n_detections": len(obs),
        "per_frame_mean": float(per_frame.mean()) if per_frame.size else 0.0,
        "per_frame_std": float(per_frame.std()) if per_frame.size else 0.0,
        "csd": {k: float(v) for k, v in csd.items() if k != "sizes_mm"},
        "sizes_mm": np.asarray(csd["sizes_mm"], dtype=np.float64),
        "alpha": float(alpha),
        "alpha_deviation_pct": (alpha - THEORETICAL_ALPHA)
        / THEORETICAL_ALPHA
        * 100.0,
        "dstats": {
            k: (int(v) if isinstance(v, (int, np.integer)) else float(v))
            for k, v in dstats.items()
        },
        "mean_correction_mm": mean_abs_corr,
        "mean_correction_pct": mean_abs_corr_pct,
        "results": results,
        "lens": lens,
        "d_focus": d_focus,
    }


def _fmt_row(name: str, b1: object, b2: object, unit: str = "") -> str:
    def _f(x: object) -> str:
        if isinstance(x, float):
            if abs(x) >= 100 or (x != 0 and abs(x) < 1e-3):
                return f"{x:.3e}"
            return f"{x:.4f}"
        return str(x)

    return f"| {name:38s} | {_f(b1):>14s} | {_f(b2):>14s} | {unit} |"


def _print_comparison(b1: _WindowResult, b2: _WindowResult) -> None:
    print()
    print("# RQ4 — batch-1 vs batch-2: drying→discharge (same recording)")
    print()
    print(f"Video: `{LONG_VIDEO}`")
    print(
        f"b1 window: t={b1['window_s'][0]:.1f}→{b1['window_s'][1]:.1f}s, frames {b1['frame_range']}"
    )
    print(
        f"b2 window: t={b2['window_s'][0]:.1f}→{b2['window_s'][1]:.1f}s, frames {b2['frame_range']}"
    )
    print()
    print(f"| {'metric':38s} | {'b1':>14s} | {'b2':>14s} | unit |")
    print(f"| {'-' * 38} | {'-' * 14}:| {'-' * 14}:| --- |")
    print(
        _fmt_row("sampled frames", b1["sampled_frames"], b2["sampled_frames"])
    )
    print(_fmt_row("frame stride", b1["frame_stride"], b2["frame_stride"]))
    print(_fmt_row("total detections", b1["n_detections"], b2["n_detections"]))
    print(
        _fmt_row(
            "detections / frame (mean)",
            b1["per_frame_mean"],
            b2["per_frame_mean"],
        )
    )
    print(
        _fmt_row(
            "detections / frame (std)",
            b1["per_frame_std"],
            b2["per_frame_std"],
        )
    )
    for k in ("median", "mean", "std", "cv", "p05", "p25", "p75", "p95"):
        unit = "" if k == "cv" else "mm"
        print(_fmt_row(f"CSD {k}", b1["csd"][k], b2["csd"][k], unit))
    print(
        _fmt_row(
            "CSD lognorm s", b1["csd"]["lognorm_s"], b2["csd"]["lognorm_s"]
        )
    )
    print(
        _fmt_row(
            "CSD lognorm scale",
            b1["csd"]["lognorm_scale"],
            b2["csd"]["lognorm_scale"],
        )
    )
    print(_fmt_row("α (sharpness power-law)", b1["alpha"], b2["alpha"]))
    print(
        _fmt_row(
            "α deviation vs theory (5.0)",
            b1["alpha_deviation_pct"],
            b2["alpha_deviation_pct"],
            "%",
        )
    )
    print(
        _fmt_row("n_focus", b1["dstats"]["n_focus"], b2["dstats"]["n_focus"])
    )
    print(_fmt_row("n_near", b1["dstats"]["n_near"], b2["dstats"]["n_near"]))
    print(_fmt_row("n_far", b1["dstats"]["n_far"], b2["dstats"]["n_far"]))
    print(
        _fmt_row(
            "fraction near",
            b1["dstats"]["frac_near"],
            b2["dstats"]["frac_near"],
        )
    )
    print(
        _fmt_row(
            "mean depth correction",
            b1["mean_correction_mm"],
            b2["mean_correction_mm"],
            "mm",
        )
    )
    print(
        _fmt_row(
            "mean depth correction (%)",
            b1["mean_correction_pct"],
            b2["mean_correction_pct"],
            "%",
        )
    )
    print()
    b1_med_um = b1["csd"]["median"] * 1000.0
    b2_med_um = b2["csd"]["median"] * 1000.0
    delta_um = b2_med_um - b1_med_um
    print(
        f"**Median crystal size at focal point:** b1 = {b1_med_um:.1f} µm, "
        f"b2 = {b2_med_um:.1f} µm (Δ = {delta_um:+.1f} µm, "
        f"{100 * delta_um / b1_med_um:+.1f} % of b1)."
    )


def _fig_overlay(b1: _WindowResult, b2: _WindowResult, out_path: Path) -> None:
    """Side-by-side b1 vs b2 CSD: histogram + ECDF + log-normal fits."""
    s1 = b1["sizes_mm"]
    s2 = b2["sizes_mm"]
    upper = float(np.quantile(np.concatenate([s1, s2]), 0.99) * 1.4)
    bins = np.linspace(0.0, upper, 50)

    fig, (ax_hist, ax_ecdf, ax_fit) = plt.subplots(1, 3, figsize=(15.5, 4.6))

    for sizes, color, label, csd in (
        (s1, "C0", "b1 drying→discharge", b1["csd"]),
        (s2, "C3", "b2 drying→discharge", b2["csd"]),
    ):
        med = csd["median"]
        ax_hist.hist(
            sizes,
            bins=bins,
            density=True,
            histtype="stepfilled",
            alpha=0.45,
            color=color,
            edgecolor=color,
            linewidth=1.5,
            label=f"{label} (n={sizes.size}, med={med * 1000:.1f} µm)",
        )
        ax_hist.axvline(med, color=color, linestyle="--", linewidth=1.2)

        srt = np.sort(sizes)
        ecdf = np.arange(1, srt.size + 1) / srt.size
        ax_ecdf.plot(srt, ecdf, color=color, linewidth=2, label=label)

        x = np.linspace(max(bins[0], 1e-6), bins[-1], 400)
        pdf = stats.lognorm.pdf(
            x, csd["lognorm_s"], loc=0.0, scale=csd["lognorm_scale"]
        )
        ax_fit.plot(
            x,
            pdf,
            color=color,
            linewidth=2,
            label=f"{label}: s={csd['lognorm_s']:.3f}, scale={csd['lognorm_scale']:.4f} mm",
        )

    ax_hist.set_xlabel("depth-corrected physical size (mm)")
    ax_hist.set_ylabel("density")
    ax_hist.set_title("CSD overlay (normalised)")
    ax_hist.legend(fontsize=8)
    ax_hist.grid(True, alpha=0.3)

    ax_ecdf.set_xlabel("size (mm)")
    ax_ecdf.set_ylabel("ECDF")
    ax_ecdf.set_title("Empirical CDFs — Δ_KS quantifies divergence")
    ks_stat, ks_p = stats.ks_2samp(s1, s2)
    ax_ecdf.text(
        0.05,
        0.95,
        f"KS = {ks_stat:.4f}\np = {ks_p:.2e}",
        transform=ax_ecdf.transAxes,
        va="top",
        fontsize=9,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.85),
    )
    ax_ecdf.legend(fontsize=8, loc="lower right")
    ax_ecdf.grid(True, alpha=0.3)

    ax_fit.set_xlabel("size (mm)")
    ax_fit.set_ylabel("log-normal pdf")
    ax_fit.set_title("Single-component log-normal fits")
    ax_fit.legend(fontsize=8)
    ax_fit.grid(True, alpha=0.3)

    fig.suptitle(
        "RQ4 — batch-1 vs batch-2 CSD at drying→discharge (same recording, same optics)",
        y=1.02,
        fontsize=12,
    )
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--max-frames", type=int, default=60)
    p.add_argument(
        "--detector", default="watershed", choices=["watershed", "edge"]
    )
    p.add_argument("--json", action="store_true")
    p.add_argument(
        "--out-dir",
        type=Path,
        default=Path("docs/optics/figures"),
        help="where to write the three RQ4 figures",
    )
    args = p.parse_args(argv)

    b1 = _run_window(
        "b1", *B1_WINDOW, max_frames=args.max_frames, detector=args.detector
    )
    b2 = _run_window(
        "b2", *B2_WINDOW, max_frames=args.max_frames, detector=args.detector
    )

    out = args.out_dir
    print(f"[rq4] writing figures to {out.resolve()}", file=sys.stderr)
    fig_csd_final(
        b1["results"], b1["lens"], b1["d_focus"], out / "rq4_csd_b1.png"
    )
    fig_csd_final(
        b2["results"], b2["lens"], b2["d_focus"], out / "rq4_csd_b2.png"
    )
    _fig_overlay(b1, b2, out / "rq4_csd_overlay.png")
    print(f"  - {out / 'rq4_csd_b1.png'}")
    print(f"  - {out / 'rq4_csd_b2.png'}")
    print(f"  - {out / 'rq4_csd_overlay.png'}")

    if args.json:
        import json

        slim = {
            k: {
                kk: vv
                for kk, vv in d.items()
                if kk not in ("results", "lens", "sizes_mm")
            }
            for k, d in (("b1", b1), ("b2", b2))
        }
        print(json.dumps(slim, indent=2, default=str))
    else:
        _print_comparison(b1, b2)


if __name__ == "__main__":
    main()
