"""Pipeline KPI snapshot + CHANGELOG.md updater.

Runs the full Camera 100 pipeline end-to-end (measure → disambiguate
→ aggregate CSD), collects standardised KPIs, and writes a single
``## KPIs — vX.Y.Z`` section to the top of ``CHANGELOG.md`` for the
*next* release.

The companion git post-commit hook (``scripts/optics-release.sh``,
installed via ``pre-commit install --hook-type post-commit``) detects
when ``src/optics/`` changes have been committed, runs this module,
then runs ``cz bump --increment minor`` to cut the release. Each
pipeline run becomes a tagged 0.x.0 release with a frozen KPI report.

Manual usage:

* ``uv run python -m optics.kpi`` — print KPI table to stdout.
* ``uv run python -m optics.kpi --update-changelog`` — also rewrite
  the ``Unreleased KPIs`` block at the top of ``CHANGELOG.md``.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from annotator.types import LayerConfig
from optics.config import (
    detection_area_px,
    lens_from_config_and_video,
    load_camera,
)
from optics.csd import aggregate_csd
from optics.disambiguate import detect_observations, disambiguate
from optics.measure import collect_sharpness_histogram, fit_power_law_tail

CHANGELOG_PATH = Path("CHANGELOG.md")
DEFAULT_VIDEO = "datasets/2026-02-05 10-36-32.mp4"
THEORETICAL_ALPHA = 5.0


@dataclass
class Detection:
    n_total: int
    detections_per_frame_mean: float
    detections_per_frame_std: float
    detector: str
    min_area_px: float
    max_area_px: float


@dataclass
class Csd:
    median_mm: float
    mean_mm: float
    std_mm: float
    cv: float
    p05_mm: float
    p25_mm: float
    p75_mm: float
    p95_mm: float
    lognorm_s: float
    lognorm_scale: float


@dataclass
class Optics:
    alpha_measured: float
    alpha_theoretical: float
    alpha_deviation_pct: float


@dataclass
class Disambiguation:
    n_focus: int
    n_near: int
    n_far: int
    frac_near: float
    mean_correction_mm: float
    mean_correction_pct: float


@dataclass
class Setup:
    focal_length_mm: float
    f_number: float
    extension_tube_mm: float
    d_focus_mm: float
    pixel_pitch_um: float
    detector: str
    video_path: str
    sampled_frames: int


@dataclass
class KpiReport:
    timestamp_utc: str
    setup: Setup
    detection: Detection
    csd: Csd
    optics: Optics
    disambiguation: Disambiguation
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_pipeline(
    *,
    video: str = DEFAULT_VIDEO,
    detector: str = "watershed",
    frame_stride: int = 15,
    max_frames: int = 60,
) -> KpiReport:
    """Run the full pipeline once and capture KPIs."""
    cfg = load_camera()
    lens = lens_from_config_and_video(cfg, video)
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

    print("[kpi] detecting crystals…", file=sys.stderr)
    obs = detect_observations(
        video,
        config,
        frame_stride=frame_stride,
        max_frames=max_frames,
        detector=detector,
    )

    print("[kpi] disambiguating depth…", file=sys.stderr)
    results, dstats = disambiguate(obs, lens, d_focus)

    # Compute depth-correction magnitudes (naive-at-focus vs depth-corrected).
    from optics.model import mm_per_pixel_at as _mm

    mm_per_px_focus = float(_mm(lens, d_focus, np.array([d_focus]))[0])
    corr = np.array(
        [
            r.physical_size_mm - r.obs.apparent_size_px * mm_per_px_focus
            for r in results
        ],
        dtype=np.float64,
    )
    median_size = float(np.median([r.physical_size_mm for r in results]))
    mean_abs_corr = float(np.mean(np.abs(corr))) if corr.size else 0.0
    mean_abs_corr_pct = (
        100.0 * mean_abs_corr / median_size if median_size > 0.0 else 0.0
    )

    print("[kpi] aggregating CSD…", file=sys.stderr)
    csd = aggregate_csd(results, lens, d_focus)

    print("[kpi] measuring sharpness α…", file=sys.stderr)
    centres, density = collect_sharpness_histogram(
        video, frame_stride=frame_stride, max_frames=max_frames
    )
    alpha, _ = fit_power_law_tail(centres, density)
    alpha_dev = (alpha - THEORETICAL_ALPHA) / THEORETICAL_ALPHA * 100.0

    counts: dict[int, int] = {}
    for o in obs:
        counts[o.frame_idx] = counts.get(o.frame_idx, 0) + 1
    per_frame = np.array(list(counts.values()), dtype=np.float64)

    return KpiReport(
        timestamp_utc=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        setup=Setup(
            focal_length_mm=lens.focal_length,
            f_number=lens.f_number,
            extension_tube_mm=lens.extension_tube,
            d_focus_mm=d_focus,
            pixel_pitch_um=lens.pixel_pitch_um,
            detector=detector,
            video_path=video,
            sampled_frames=len(counts),
        ),
        detection=Detection(
            n_total=len(obs),
            detections_per_frame_mean=float(per_frame.mean())
            if per_frame.size
            else 0.0,
            detections_per_frame_std=float(per_frame.std())
            if per_frame.size
            else 0.0,
            detector=detector,
            min_area_px=config.min_area,
            max_area_px=config.max_area,
        ),
        csd=Csd(
            median_mm=float(csd["median"]),
            mean_mm=float(csd["mean"]),
            std_mm=float(csd["std"]),
            cv=float(csd["cv"]),
            p05_mm=float(csd["p05"]),
            p25_mm=float(csd["p25"]),
            p75_mm=float(csd["p75"]),
            p95_mm=float(csd["p95"]),
            lognorm_s=float(csd["lognorm_s"]),
            lognorm_scale=float(csd["lognorm_scale"]),
        ),
        optics=Optics(
            alpha_measured=alpha,
            alpha_theoretical=THEORETICAL_ALPHA,
            alpha_deviation_pct=alpha_dev,
        ),
        disambiguation=Disambiguation(
            n_focus=int(dstats["n_focus"]),
            n_near=int(dstats["n_near"]),
            n_far=int(dstats["n_far"]),
            frac_near=float(dstats["frac_near"]),
            mean_correction_mm=mean_abs_corr,
            mean_correction_pct=mean_abs_corr_pct,
        ),
    )


def format_markdown(report: KpiReport, version: str | None = None) -> str:
    """Render a KPI block suitable for CHANGELOG.md."""
    s = report.setup
    d = report.detection
    c = report.csd
    o = report.optics
    db = report.disambiguation
    header = (
        f"### KPIs — v{version} ({report.timestamp_utc})"
        if version
        else f"### KPIs (unreleased, {report.timestamp_utc})"
    )
    lines = [
        header,
        "",
        f"**Setup:** f={s.focal_length_mm:.0f} mm, F/{s.f_number:.1f}, "
        f"e={s.extension_tube_mm:.0f} mm, d_focus={s.d_focus_mm:.1f} mm, "
        f"pitch={s.pixel_pitch_um:.1f} µm, detector=`{s.detector}`, "
        f"video=`{Path(s.video_path).name}` ({s.sampled_frames} frames sampled).",
        "",
        "| Category | Metric | Value |",
        "|---|---|---:|",
        f"| Detection | total detections | **{d.n_total}** |",
        f"| Detection | per-frame mean ± std | {d.detections_per_frame_mean:.1f} ± {d.detections_per_frame_std:.1f} |",
        f"| Detection | area filter (px²) | [{d.min_area_px:.0f}, {d.max_area_px:.0f}] |",
        f"| CSD | median (mm) | **{c.median_mm:.4f}** |",
        f"| CSD | mean (mm) | {c.mean_mm:.4f} |",
        f"| CSD | std (mm) | {c.std_mm:.4f} |",
        f"| CSD | CV | **{c.cv:.3f}** |",
        f"| CSD | p05 / p25 / p75 / p95 (mm) | {c.p05_mm:.3f} / {c.p25_mm:.3f} / {c.p75_mm:.3f} / {c.p95_mm:.3f} |",
        f"| CSD | log-normal s, scale | {c.lognorm_s:.3f}, {c.lognorm_scale:.4f} |",
        f"| Optics | α measured | **{o.alpha_measured:.3f}** (theory={o.alpha_theoretical:.1f}, Δ={o.alpha_deviation_pct:+.1f} %) |",
        f"| Disambiguation | focal / near / far counts | {db.n_focus} / {db.n_near} / {db.n_far} |",
        f"| Disambiguation | fraction near (excluding focal) | {db.frac_near:.3f} |",
        f"| Disambiguation | mean depth correction (mm, %) | {db.mean_correction_mm:.5f}, {db.mean_correction_pct:.3f} % |",
        "",
    ]
    return "\n".join(lines)


def update_changelog(report: KpiReport, path: Path = CHANGELOG_PATH) -> None:
    """Replace any 'Unreleased' KPI block at the top of CHANGELOG.md.

    Commitizen owns the rest of the file (version headers, conventional-
    commit list); we only touch the leading ``## Unreleased`` section.
    """
    new_block = format_markdown(report, version=None)
    sentinel = "<!-- kpi:unreleased -->"
    end_sentinel = "<!-- /kpi:unreleased -->"
    section = f"{sentinel}\n\n{new_block}\n{end_sentinel}\n"
    if not path.exists():
        path.write_text("# Changelog\n\n" + section)
        return
    text = path.read_text()
    if sentinel in text and end_sentinel in text:
        start = text.index(sentinel)
        end = text.index(end_sentinel) + len(end_sentinel) + 1
        text = text[:start] + section + text[end:]
    else:
        text = (
            text.replace(
                "# Changelog\n",
                "# Changelog\n\n" + section,
                1,
            )
            if "# Changelog" in text
            else "# Changelog\n\n" + section + text
        )
    path.write_text(text)


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", default=DEFAULT_VIDEO)
    parser.add_argument(
        "--detector", default="watershed", choices=["watershed", "edge"]
    )
    parser.add_argument("--update-changelog", action="store_true")
    parser.add_argument(
        "--json", action="store_true", help="emit JSON instead of markdown"
    )
    args = parser.parse_args(argv)

    report = run_pipeline(video=args.video, detector=args.detector)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(format_markdown(report))

    if args.update_changelog:
        update_changelog(report)
        print(f"[kpi] wrote KPI block to {CHANGELOG_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
