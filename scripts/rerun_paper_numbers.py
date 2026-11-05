"""Recompute every computed number of the CEP paper from the current config.

Each row prints: the paper's current value (``old``, with its place in
``papers/cep``), the value recomputed now from ``configs/camera_100.toml`` and
the case-study video (``new``), whether the old value is reproduced, which
pixel axis it depends on, the weakest source class among its inputs, and the
function that computes it.

    uv run --frozen python scripts/rerun_paper_numbers.py            # all
    uv run --frozen python scripts/rerun_paper_numbers.py --no-video # optics only
    uv run --frozen python scripts/rerun_paper_numbers.py --json out.json
    uv run --frozen python scripts/rerun_paper_numbers.py --fig07    # redraw fig 07

Scale columns: ``x`` / ``y`` = a length along a row / a column, ``area`` =
area-equivalent (geometric-mean pixel), ``free`` = no pixel scale enters.
The detector CSD rows are detector artefacts, not crystal sizes: the edge CSD
follows the area window and the watershed CSD its own seed spacing
(``_PEAK_MIN_DISTANCE``); both are printed for the current window
(``detection_area_px``) and the legacy ``[80, 8000]`` px² window.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)  # the optics modules read datasets/ relative to the repo

from annotator.types import LayerConfig  # noqa: E402
from optics.config import (  # noqa: E402
    SOURCE_RANK,
    detection_area_px,
    lens_from_config,
    load_camera,
    source_classes,
    um_per_px_xy_at_focus,
)
from optics.model import LensSetup, circle_of_confusion  # noqa: E402
from optics.psf import sharpness_diffraction, working_f_number  # noqa: E402
from optics.scale_chain import nominal_scales, sample_budget  # noqa: E402

VIDEO = "datasets/2026-02-05 10-36-32.mp4"
LEGACY_WINDOW = (80.0, 8000.0)
FRAME = 750
STRIDE, N_FRAMES = 15, 60  # optics.csd.main / optics.kpi.run_pipeline

CFG = load_camera()
CLS = source_classes(CFG.source_path)


@dataclass
class Row:
    name: str
    where: str
    old: str
    new: str
    scale: str
    cls: str
    source: str
    reproduced: str = ""


ROWS: list[Row] = []


def weakest(*keys: str) -> str:
    """Weakest source class among config keys (or literal class names)."""
    classes = [CLS.get(k, k) for k in keys]
    return max(classes, key=lambda c: SOURCE_RANK.index(c))


def _matches(old: str, new: str) -> str:
    """``yes`` when the leading numbers of ``new`` match ``old`` to ±1 in its last digit."""
    num = r"[-+]?\d[\d ,]*\.?\d*"
    o = [s.replace(" ", "").replace(",", "") for s in re.findall(num, old)]
    n = [s.replace(" ", "").replace(",", "") for s in re.findall(num, new)]
    if not o or old.startswith("—") or "UNSOURCED" in old:
        return "n/a"
    if len(n) < len(o):
        return "no"
    for a, b in zip(o, n[: len(o)], strict=True):  # leading numbers only
        dec = len(a.split(".")[1]) if "." in a else 0
        if (
            abs(float(b) - float(a)) > 1.01 * 10.0**-dec
        ):  # ±1 in the last digit
            return "no"
    return "yes"


def add(
    name: str,
    where: str,
    old: str,
    new: str,
    scale: str,
    cls: str,
    source: str,
) -> None:
    ROWS.append(
        Row(name, where, old, new, scale, cls, source, _matches(old, new))
    )


# ── optics: config only ───────────────────────────────────────────────────


def _lens(pitch_um: float, n: float | None = None) -> LensSetup:
    return LensSetup(
        focal_length=CFG.focal_length_mm,
        f_number=CFG.f_number if n is None else n,
        extension_tube=CFG.extension_tube_mm,
        pixel_pitch_um=pitch_um,
        sensor_width=CFG.sensor_width_mm,
        sensor_height=CFG.sensor_height_mm,
    )


def _dof_half_um(
    k_mm: float, d: float, pitch_um: float
) -> tuple[float, float]:
    """Near and far half-widths (µm) where the CoC reaches ``pitch_um``."""
    r = pitch_um * 1e-3 / k_mm
    return 1e3 * (d - d / (1 + r)), 1e3 * (d / (1 - r) - d)


def _fwhm_um(lens: LensSetup, d: float) -> float:
    """FWHM of the sharpness cusp, as in ``optics.plots.fig_sharpness_vs_distance``."""
    do = np.linspace(d - 5.0, d + 5.0, 20000)
    c = circle_of_confusion(lens, d, do)
    s = sharpness_diffraction(
        c,
        lens.f_number,
        sensor_floor_mm=lens.pixel_pitch_um * 1e-3 / 2,
        magnification=lens.focal_length / (d - lens.focal_length),
    )
    above = do[s >= 0.5]
    return 1e3 * float(above[-1] - above[0])


def _ratio_at(d: float, delta_mm: float) -> float:
    """Near/far apparent-size ratio for the 1/d-symmetric pair (fig 10)."""
    dn = d - delta_mm
    df = 1.0 / (2.0 / d - 1.0 / dn)
    return df / dn


def optics_rows() -> dict[str, float]:
    f, e, x, n = (
        CFG.focal_length_mm,
        CFG.extension_tube_mm,
        CFG.focus_travel_mm,
        CFG.f_number,
    )
    i = f + e + x
    d = f * i / (i - f)
    d_cfg = CFG.focus_object_distance_mm
    k = f**2 / (n * (d - f))
    geo = "lens.focal_length_mm lens.extension_tube_mm lens.focus_travel_mm".split()
    pitch = "camera.cell_width_um camera.pixel_clock_mhz dvr.sampling_rate_mhz".split()
    disp = ["display_1080p.stretch_x", "display_1080p.stretch_y"]

    add(
        "image distance i = f + e + x",
        "optics.tex fig 18 caption",
        "95 mm",
        f"{i:.0f} mm",
        "free",
        weakest(*geo),
        "f + e + focus_travel",
    )
    add(
        "focused object distance d_focus",
        "hardware.tex, optics.tex, figs 01/02/06/09",
        "55.4 mm",
        f"{d:.1f} mm (exact {d:.3f}; config [focus] {d_cfg})",
        "free",
        weakest(*geo),
        "f·i/(i−f); configs [focus].object_distance_mm",
    )

    sc = nominal_scales(CFG)
    (px_x, px_y), (cx, cy) = sc["PAL 720×576"], sc["1080p clip"]
    lens_clip = lens_from_config(
        CFG, CFG.display_width_px, CFG.display_height_px
    )
    lens_pal = lens_from_config(CFG)
    ux, uy = um_per_px_xy_at_focus(CFG, lens_clip)
    mc = sample_budget(CFG, 100_000)
    q = {k2: np.percentile(v, [2.5, 97.5]) for k2, v in mc.items()}
    add(
        "µm/px at focus, 1080p clip, x",
        "abstract, hardware, optics, csd, highlights",
        "1.66 µm/px",
        f"{cx:.3f} µm/px [95 % {q['1080p clip x'][0]:.3f}–{q['1080p clip x'][1]:.3f}]",
        "x",
        weakest(*geo, *pitch, *disp),
        "optics.scale_chain.nominal_scales / sample_budget",
    )
    add(
        "µm/px at focus, 1080p clip, y",
        "(paper has one isotropic 1.66)",
        "1.66 µm/px",
        f"{cy:.3f} µm/px [95 % {q['1080p clip y'][0]:.3f}–{q['1080p clip y'][1]:.3f}]",
        "y",
        weakest(*geo, "camera.cell_height_um", *disp),
        "optics.scale_chain.nominal_scales",
    )
    add(
        "µm/px at focus, 1080p clip, geometric mean (areas)",
        "—",
        "1.66 µm/px",
        f"{math.sqrt(cx * cy):.3f} µm/px (config d_focus 55.1: {ux:.4f} × {uy:.4f})",
        "area",
        weakest(*geo, *pitch, *disp),
        "optics.config.um_per_px_xy_at_focus",
    )
    add(
        "µm/px at focus, PAL sample, x × y",
        "— (paper reports no PAL scale)",
        "—",
        f"{px_x:.3f} × {px_y:.3f} µm/px [95 % x {q['PAL 720×576 x'][0]:.3f}–{q['PAL 720×576 x'][1]:.3f}]",
        "x, y",
        weakest(*geo, *pitch),
        "optics.scale_chain.nominal_scales",
    )
    add(
        "sensor pitch",
        "hardware.tex (Hanwha 2.9 µm)",
        "2.9 µm",
        f"PAL sample {CFG.sample_pitch_um[0]:.3f} × {CFG.sample_pitch_um[1]:.3f} µm; "
        f"1080p px {lens_clip.pixel_pitch_x_um:.3f} × {lens_clip.pixel_pitch_y_um:.3f} µm",
        "x, y",
        weakest(*pitch),
        "CameraConfig.sample_pitch_um, optics.config.sensor_pitch_xy",
    )
    add(
        "sensor active area",
        "hardware.tex",
        "5.57 × 3.13 mm",
        f"{CFG.sensor_width_mm:.2f} × {CFG.sensor_height_mm:.2f} mm (cells × cell size)",
        "x, y",
        weakest("camera.cells_h", "camera.cell_width_um"),
        "CameraConfig.sensor_width_mm",
    )
    add(
        "transverse magnification M at focus",
        "—",
        "—",
        f"{f / (d - f):.3f}",
        "free",
        weakest(*geo),
        "optics.model.magnification",
    )

    delta = CFG.sight_glass_thickness_mm * (1 - 1 / CFG.sight_glass_index)
    glass = ["sight_glass.thickness_mm", "sight_glass.refractive_index"]
    add(
        "sight-glass shift Δ = t(1 − 1/n)",
        "optics.tex, fig 05/18",
        "6.84 mm",
        f"{delta:.2f} mm (n = 1.47 borosilicate: "
        f"{CFG.sight_glass_thickness_mm * (1 - 1 / 1.47):.2f})",
        "free",
        weakest(*glass),
        "optics.model.SightGlass.apparent_shift",
    )
    add(
        "apparent glass thickness t − Δ",
        "optics.tex fig 18, §face",
        "13.61 mm",
        f"{CFG.sight_glass_thickness_mm - delta:.2f} mm",
        "free",
        weakest(*glass),
        "t − Δ",
    )

    e10 = 10.0
    add(
        "µm/px ratio e = 10 vs installed e (with focus travel)",
        "optics.tex §tube, fig 06, discussion",
        "factor of 6 / 4.5×",
        f"{(e + x) / (e10 + x):.2f}× ((e+x)/(10+x)); e ratio {e / e10:.1f}×",
        "free",
        weakest(*geo),
        "object_scale ∝ 1/(e + x)",
    )
    add(
        "µm/px at e = 10 mm, 1080p clip",
        "optics.tex §tube",
        "10.4 µm/px",
        f"x {lens_clip.pixel_pitch_x_um * f / (e10 + x):.2f}, y {lens_clip.pixel_pitch_y_um * f / (e10 + x):.2f}, "
        f"geo {lens_clip.pixel_pitch_um * f / (e10 + x):.2f} µm/px",
        "x, y",
        weakest(*geo, *pitch, *disp),
        "optics.scale_chain.object_scale",
    )
    add(
        "scale change per ±1 mm focus travel",
        "optics.tex §stackup",
        "∓1.7 %",
        f"∓{100 / (e + x):.2f} %",
        "free",
        weakest(*geo),
        "1/(e + x)",
    )
    add(
        "CoC saturation K = c_∞ = f²/(N(d − f))",
        "optics.tex §dent (K), fig 02",
        "37.50 mm",
        f"{k:.2f} mm",
        "free",
        weakest(*geo, "lens.f_number"),
        "optics.disambiguate._circle_of_confusion_to_object_distances",
    )

    for label, pitch_um, src in (
        (
            "1 PAL sample (geo mean; fig 04 threshold)",
            lens_pal.pixel_pitch_um,
            "optics.plots.fig_dof_envelope",
        ),
        (
            "1 1080p clip px (geo mean)",
            lens_clip.pixel_pitch_um,
            "same formula, clip pixel",
        ),
    ):
        near, far = _dof_half_um(k, d, pitch_um)
        add(
            f"in-focus half-slice at F/{n:g}, CoC ≤ {label}",
            "defocus.tex fig 04, sizing, csd, discussion",
            "±4.2 µm",
            f"±{0.5 * (near + far):.1f} µm (near {near:.2f}, far {far:.2f}; pitch {pitch_um:.3f} µm)",
            "area",
            weakest(*geo, *pitch, "lens.f_number"),
            src,
        )
        k16 = f**2 / (16.0 * (d - f))
        near16, far16 = _dof_half_um(k16, d, pitch_um)
        add(
            f"in-focus half-slice at F/16, CoC ≤ {label}",
            "defocus.tex fig 04, discussion",
            "±42 µm",
            f"±{0.5 * (near16 + far16):.0f} µm",
            "area",
            weakest(*geo, *pitch, "lens.iris_stops"),
            src,
        )
        add(
            f"sharpness FWHM at F/{n:g}, floor = ({label})/2",
            "defocus.tex fig 03, optics §slabops",
            "4.9 µm",
            f"{_fwhm_um(_lens(pitch_um), d):.1f} µm",
            "area",
            weakest(*geo, *pitch, "lens.f_number"),
            "optics.plots.fig_sharpness_vs_distance",
        )
        n5, f5 = _dof_half_um(k, d, 5 * pitch_um)
        d5 = 0.5 * (n5 + f5)
        add(
            f"δ where CoC = 5 × ({label})",
            "detection.tex §selectivity, fig 10, optics §slabops",
            "±21 µm",
            f"±{d5:.0f} µm",
            "area",
            weakest(*geo, *pitch, "lens.f_number"),
            "optics.disambiguate.fig_discriminability",
        )
        add(
            f"near/far size discrimination at δ = 5 × ({label})",
            "detection.tex §selectivity, fig 10",
            "0.08 %",
            f"{100 * (_ratio_at(d, d5 * 1e-3) - 1):.2f} %",
            "free",
            weakest(*geo, *pitch, "lens.f_number"),
            "optics.disambiguate.fig_discriminability",
        )
    deltas = np.linspace(0.001, 5.0, 50000)
    r = np.array([_ratio_at(d, dd) for dd in deltas])
    add(
        "δ at 5 % near/far discrimination",
        "detection.tex fig 10",
        "1.3 mm",
        f"{deltas[np.argmax(r >= 1.05)]:.1f} mm",
        "free",
        weakest(*geo),
        "optics.disambiguate.fig_discriminability",
    )

    for lab, dd in (
        ("near", d_cfg - 0.2),
        ("at focus", d_cfg),
        ("far", d_cfg + 0.2),
    ):
        s = dd / d_cfg
        add(
            f"fig 07 µm/px at d_o = {dd:.1f} mm ({lab}), 1080p",
            "sizing.tex fig 07 captions",
            {"near": "1.659", "at focus": "1.665", "far": "1.671"}[lab]
            + " µm/px",
            f"x {ux * s:.3f} × y {uy * s:.3f} µm/px",
            "x, y",
            weakest(*geo, *pitch, *disp),
            "optics.config.um_per_px_xy_at_focus × d_o/d_focus",
        )
    near_pal, far_pal = _dof_half_um(k, d, lens_pal.pixel_pitch_um)
    add(
        "fig 07 scale change over ±0.2 mm",
        "sizing.tex fig 07",
        "±0.36 %",
        f"±{100 * 0.2 / d_cfg:.2f} %",
        "free",
        weakest(*geo),
        "0.2 / d_focus",
    )
    add(
        "fig 07 window ±0.2 mm vs F/1.6 half-slice",
        "sizing.tex fig 07",
        "48×",
        f"{200 / (0.5 * (near_pal + far_pal)):.0f}× (PAL-sample slice); "
        f"{200 / _dof_half_um(k, d, lens_clip.pixel_pitch_um)[0]:.0f}× (clip-px slice)",
        "area",
        weakest(*geo, *pitch),
        "0.2 mm / half-slice",
    )

    for win, lab in (
        (LEGACY_WINDOW, "legacy [80, 8000] px²"),
        (detection_area_px(CFG, lens_clip), "current detection_area_px"),
    ):
        lo, hi = (math.sqrt(a) for a in win)
        add(
            f"size window of {lab} on 1080p (side of a square)",
            "abstract, detection fig 11, csd preface, discussion, conclusions",
            "15–150 µm (also 20–200)" if "legacy" in lab else "—",
            f"x {lo * ux:.1f}–{hi * ux:.0f}, y {lo * uy:.1f}–{hi * uy:.0f}, "
            f"area-eq {lo * math.sqrt(ux * uy):.1f}–{hi * math.sqrt(ux * uy):.0f} µm "
            f"({win[0]:.0f}–{win[1]:.0f} px²)",
            "x, y",
            weakest(*geo, *pitch, *disp, "detection.min_side_px"),
            "optics.config.detection_area_px",
        )
    add(
        "watershed _PEAK_MIN_DISTANCE 12 px in µm (1080p)",
        "csd.tex tab ws-constants",
        "12 px ≈ ½ crystal at 1.66 µm/px",
        f"x {12 * ux:.1f}, y {12 * uy:.1f} µm",
        "x, y",
        weakest(*geo, *pitch, *disp),
        "optics.detect_watershed._PEAK_MIN_DISTANCE",
    )
    add(
        "autocorrelation first-decorrelation offset",
        "optics.tex §anchoring",
        "42.5 px (UNSOURCED: no script)",
        "not recomputed",
        "x",
        "UNSOURCED",
        "none",
    )
    add(
        "autocorrelation period 2 × 42.5 px along a row, 1080p",
        "optics.tex §anchoring",
        "0.14 mm",
        f"{85 * ux / 1000:.3f} mm (x axis)",
        "x",
        "UNSOURCED",
        "42.5 px × 2 × µm_x",
    )

    # Dent analysis: the generator is not in the repo; the c = 5.8 µm input is
    # UNSOURCED, so only the algebra that follows from it is recomputed.
    c_dent = 5.8e-3
    d_dent = k * d / (k + c_dent)
    add(
        "dent CoC c (Laplacian² medians 11 664 / 12 996)",
        "optics.tex §dent, fig 17",
        "5.8 µm (UNSOURCED)",
        "not recomputed",
        "area",
        "UNSOURCED",
        "none in repo",
    )
    add(
        "dent apparent distance K·d/(K + c), c = 5.8 µm",
        "optics.tex eq dent",
        "55.074 mm",
        f"{d_dent:.3f} mm (δ = {1e3 * (d - d_dent):.1f} µm)",
        "free",
        "UNSOURCED",
        "algebra on UNSOURCED c",
    )
    add(
        "face table: outer-face hypothesis inner-face apparent d_o",
        "optics.tex tab face",
        "68.679 mm",
        f"{d_dent + CFG.sight_glass_thickness_mm - delta:.3f} mm",
        "free",
        weakest("UNSOURCED", *glass),
        "d_dent + (t − Δ)",
    )
    add(
        "face table: inner-face hypothesis outer-face apparent d_o",
        "optics.tex tab face",
        "41.469 mm",
        f"{d_dent - (CFG.sight_glass_thickness_mm - delta):.3f} mm",
        "free",
        weakest("UNSOURCED", *glass),
        "d_dent − (t − Δ)",
    )
    h_inner = d_dent + delta
    add(
        "real H → inner glass face",
        "optics.tex eq hreal",
        "— (removed 2026-11-05)",
        f"{h_inner:.2f} mm",
        "free",
        weakest("UNSOURCED", *glass),
        "d_dent + Δ",
    )
    add(
        "H behind front element",
        "optics.tex eq hfront",
        "— (removed 2026-11-05)",
        f"{h_inner - CFG.sight_glass_thickness_mm - CFG.air_gap_mm:.1f} mm "
        f"(with d_focus instead of d_dent: {d + delta - CFG.sight_glass_thickness_mm - CFG.air_gap_mm:.1f})",
        "free",
        weakest("UNSOURCED", *glass, "lens.air_gap_mm"),
        "optics.error_budget.derived",
    )
    h2 = CFG.flange_distance_mm + e + CFG.lens_body_length_mm + x - i
    add(
        "H′ behind (extended) front element",
        "optics.tex §stackup",
        "12.0 mm",
        f"{h2:.1f} mm",
        "free",
        weakest(*geo, "camera.flange_distance_mm", "lens.body_length_mm"),
        "optics.error_budget.derived H2_behind_front_mm",
    )
    tests = (
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "--collect-only",
                "-q",
                "tests/test_optics.py",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        .stdout.strip()
        .splitlines()
    )
    add(
        "tests in tests/test_optics.py",
        "appendix_reproduction.tex",
        "10 tests",
        tests[-1].split(" in ")[0] if tests else "?",
        "free",
        "CHOICE",
        "pytest --collect-only",
    )
    return {"ux": ux, "uy": uy, "d": d, "k": k}


def diffraction_rows() -> None:
    """Diffraction at the image-side working F-number ``N_w = N (1 + M)``.

    Printed after all other rows so that the row numbers cited in the paper
    for the earlier rows do not move.
    """
    f, e, x, n = (
        CFG.focal_length_mm,
        CFG.extension_tube_mm,
        CFG.focus_travel_mm,
        CFG.f_number,
    )
    i = f + e + x
    d = f * i / (i - f)
    geo = "lens.focal_length_mm lens.extension_tube_mm lens.focus_travel_mm".split()
    pitch = "camera.cell_width_um camera.pixel_clock_mhz dvr.sampling_rate_mhz".split()
    lens_pal = lens_from_config(CFG)
    m = f / (d - f)
    lam_um = 0.55
    pal_um = lens_pal.pixel_pitch_um
    for stop in (n, 8.0, 16.0):
        nw = working_f_number(stop, m)
        fwhm_d = 2.3548 * 0.42 * lam_um * nw
        add(
            f"diffraction FWHM at the sensor, F/{stop:g} (N_w = N(1+M) = {nw:.1f})",
            "defocus.tex §psf, §dof, discussion",
            "—",
            f"{fwhm_d:.1f} µm = {fwhm_d / pal_um:.2f} PAL samples (σ {0.42 * lam_um * nw:.2f} µm)",
            "area",
            weakest(*geo, *pitch, "lens.f_number"),
            "optics.psf.sharpness_diffraction (σ = 0.42 λ N_w, λ = 550 nm)",
        )
    n_lim = pal_um / (2.3548 * 0.42 * lam_um * (1 + m))
    add(
        "nominal F-number at which the diffraction FWHM reaches one PAL sample",
        "defocus.tex §dof, discussion",
        "—",
        f"F/{n_lim:.1f}",
        "free",
        weakest(*geo, *pitch),
        "pitch / (2.3548 · 0.42 λ (1 + M))",
    )


# ── video: case-study clip ────────────────────────────────────────────────


def _layer_config(window: tuple[float, float]) -> LayerConfig:
    return LayerConfig(
        num_layers=3,
        sharpness_weight=0.7,
        flow_weight=0.3,
        blur_kernel=15,
        min_area=window[0],
        max_area=window[1],
        max_aspect_ratio=3.0,
    )


def video_rows(out: dict[str, object]) -> None:
    import cv2

    from annotator.detection import process_frame
    from optics.csd import aggregate_csd
    from optics.detect_watershed import process_frame_watershed
    from optics.disambiguate import detect_observations, disambiguate
    from optics.measure import collect_sharpness_histogram, fit_power_law_tail
    from optics.model import mm_per_pixel_at
    from optics.video_io import DEFAULT_CROP, CropBox, resolve_crop

    cap = cv2.VideoCapture(VIDEO)
    nf, fps = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), cap.get(cv2.CAP_PROP_FPS)
    w, h = (
        int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    )
    cap.set(cv2.CAP_PROP_POS_FRAMES, FRAME)
    _, frame750 = cap.read()
    cap.release()
    add(
        "case-study clip frames, fps, size",
        "hardware.tex §recording",
        "1568 frames, 30 fps, 1920 × 1080",
        f"{nf} frames, {fps:.0f} fps, {w} × {h}",
        "free",
        "MEASURED",
        "cv2.VideoCapture",
    )

    auto = resolve_crop(VIDEO, None)
    for lab, cb in (
        ("DEFAULT_CROP (figs 07, 11, 12, 17)", DEFAULT_CROP),
        ("auto crop (figs 08, 09, 14; resolve_crop)", auto),
    ):
        cw, ch = w - cb.left - cb.right, h - cb.top - cb.bottom
        add(
            f"cropped frame, {lab}",
            "hardware.tex §recording, fig 00",
            "1800 × 905 px ≈ 78 %",
            f"{cw} × {ch} px ≈ {100 * cw * ch / (w * h):.0f} % (t{cb.top} b{cb.bottom} l{cb.left} r{cb.right})",
            "free",
            "CHOICE",
            "optics.video_io.CropBox / resolve_crop",
        )

    alphas = {}
    for lab, old, cb in (
        ("v0.1 no crop", "5.36", CropBox(0, 0, 0, 0)),
        ("v0.2 top 55 + bottom 120", "4.57", CropBox(55, 120, 0, 0)),
        ("v0.3 DEFAULT_CROP", "4.88", DEFAULT_CROP),
        ("auto crop (what optics.measure runs)", "4.88", auto),
    ):
        a, _ = fit_power_law_tail(*collect_sharpness_histogram(VIDEO, crop=cb))
        alphas[lab] = a
        add(
            f"sharpness tail exponent α, {lab}",
            "defocus.tex tab crop, fig 08, highlights, discussion",
            old,
            f"{a:.2f} ({100 * (a - 5) / 5:+.1f} % vs 5)",
            "free",
            "MEASURED",
            "optics.measure.collect_sharpness_histogram + fit_power_law_tail",
        )
    out["alpha"] = alphas

    lens = lens_from_config(CFG, w, h)
    d = CFG.focus_object_distance_mm
    cur = detection_area_px(CFG, lens)
    gray = cv2.cvtColor(DEFAULT_CROP.apply(frame750), cv2.COLOR_BGR2GRAY)
    counts = {}
    for wlab, cfg_l in (
        ("current", _layer_config(cur)),
        ("legacy", _layer_config(LEGACY_WINDOW)),
        ("LayerConfig()", LayerConfig()),
    ):
        for dlab, fn in (
            ("edge", process_frame),
            ("watershed", process_frame_watershed),
        ):
            res, _ = fn(gray, None, FRAME, cfg_l)
            counts[f"{dlab} {wlab}"] = sum(layer.count for layer in res.layers)
    out["frame750"] = counts
    add(
        "frame 750, edge detector, current window (fig 11 = optics.qualitative)",
        "detection.tex fig 11, csd §failure",
        "55",
        str(counts["edge current"]),
        "area",
        "CHOICE",
        "optics.qualitative.fig_detection_overlay",
    )
    add(
        "frame 750, edge detector, legacy window",
        "detection.tex fig 11",
        "55",
        str(counts["edge legacy"]),
        "area",
        "CHOICE",
        "annotator.detection.process_frame",
    )
    add(
        "frame 750, edge / watershed, LayerConfig() (fig 17 = optics.detect_watershed)",
        "csd.tex fig 17, §watershed",
        "102 / 740",
        f"{counts['edge LayerConfig()']} / {counts['watershed LayerConfig()']}",
        "area",
        "CHOICE",
        "optics.detect_watershed._build_comparison_figure",
    )
    add(
        "frame 750, edge / watershed, current window",
        "—",
        "—",
        f"{counts['edge current']} / {counts['watershed current']}",
        "area",
        "CHOICE",
        "process_frame / process_frame_watershed",
    )
    add(
        "frame 750, edge / watershed, legacy window",
        "—",
        "—",
        f"{counts['edge legacy']} / {counts['watershed legacy']}",
        "area",
        "CHOICE",
        "process_frame / process_frame_watershed",
    )
    add(
        "frame 750, edge share of watershed (fig 17)",
        "csd.tex fig 17",
        "14 %",
        f"{100 * counts['edge LayerConfig()'] / counts['watershed LayerConfig()']:.0f} %",
        "area",
        "CHOICE",
        "ratio of the two counts",
    )

    old_csd = {
        "edge legacy": dict(
            n="18 823",
            median="0.037",
            mean="0.051",
            std="0.042",
            cv="0.83",
            pct="0.021 / 0.027 / 0.055 / 0.134",
            s="0.57",
            scale="0.042",
            nf="70 / 30",
        ),
        "watershed legacy": dict(
            n="52 302",
            median="0.074",
            mean="0.080",
            std="0.032",
            cv="0.40",
            pct="0.039 / 0.056 / 0.098 / 0.144",
            s="0.40",
            scale="0.074",
            nf="72 / 28",
        ),
    }
    mm_focus = float(mm_per_pixel_at(lens, d, np.array([d]))[0])
    csd_out = {}
    for det in ("edge", "watershed"):
        for wlab, win in (("current", cur), ("legacy", LEGACY_WINDOW)):
            key = f"{det} {wlab}"
            print(f"[rerun] CSD {key} …", file=sys.stderr, flush=True)
            obs = detect_observations(
                VIDEO,
                _layer_config(win),
                frame_stride=STRIDE,
                max_frames=N_FRAMES,
                detector=det,
            )
            results, st = disambiguate(obs, lens, d)
            c = aggregate_csd(results, lens, d)
            pn = np.array([r.p_near for r in results if r.side != "focus"])
            corr = np.array(
                [
                    r.physical_size_mm - r.obs.apparent_size_px * mm_focus
                    for r in results
                ]
            )
            dn = np.array([r.d_near for r in results if r.side == "near"])
            dfar = np.array([r.d_far for r in results if r.side == "far"])
            spread = np.abs(np.concatenate([dn, dfar]) - d)
            row = {
                "n": int(c["n_total"]),
                "frames": len({o.frame_idx for o in obs}),
                **{
                    k2: float(c[k2])
                    for k2 in (
                        "median",
                        "mean",
                        "std",
                        "cv",
                        "p05",
                        "p25",
                        "p75",
                        "p95",
                        "lognorm_s",
                        "lognorm_scale",
                    )
                },
                "frac_near": st["frac_near"],
                "n_focus": int(st["n_focus"]),
                "n_near": int(st["n_near"]),
                "n_far": int(st["n_far"]),
                "p_near_within_0.002": float(
                    np.mean(np.abs(pn - 0.5) <= 0.002)
                )
                if pn.size
                else float("nan"),
                "p_near_q": [
                    float(v)
                    for v in np.quantile(pn, [0.001, 0.01, 0.5, 0.99, 0.999])
                ]
                if pn.size
                else [],
                "mean_abs_corr_pct": float(
                    100 * np.mean(np.abs(corr)) / c["median"]
                ),
                "depth_offset_um_p50_p99": [
                    float(1e3 * v) for v in np.quantile(spread, [0.5, 0.99])
                ]
                if spread.size
                else [],
                "window_px2": list(win),
            }
            csd_out[key] = row
            o = old_csd.get(key, {})
            tag = f"{det} CSD, {wlab} window [{win[0]:.0f}, {win[1]:.0f}] px² (detector artefact)"
            where = (
                "csd.tex tab csd-edge"
                if det == "edge"
                else "csd.tex tab ws-compare, fig 14, abstract"
            )
            cls = weakest(
                "lens.extension_tube_mm", "camera.cell_width_um", "CHOICE"
            )
            add(
                f"{tag}: detections / {N_FRAMES} frames",
                where,
                o.get("n", "—"),
                f"{row['n']}",
                "free",
                "CHOICE",
                "optics.disambiguate.detect_observations",
            )
            for k2, lab in (
                ("median", "median"),
                ("mean", "mean"),
                ("std", "std"),
            ):
                add(
                    f"{tag}: {lab} size (mm)",
                    where,
                    o.get(k2, "—"),
                    f"{row[k2]:.3f}",
                    "area",
                    cls,
                    "optics.csd.aggregate_csd",
                )
            add(
                f"{tag}: CV",
                where,
                o.get("cv", "—"),
                f"{row['cv']:.2f}",
                "free",
                "CHOICE",
                "optics.csd.aggregate_csd",
            )
            add(
                f"{tag}: p5 / p25 / p75 / p95 (mm)",
                where,
                o.get("pct", "—"),
                " / ".join(
                    f"{row[p]:.3f}" for p in ("p05", "p25", "p75", "p95")
                ),
                "area",
                cls,
                "optics.csd.aggregate_csd",
            )
            add(
                f"{tag}: log-normal s",
                where + ", discussion, conclusions (0.39)",
                o.get("s", "—"),
                f"{row['lognorm_s']:.2f}",
                "free",
                "CHOICE",
                "optics.csd.aggregate_csd",
            )
            add(
                f"{tag}: log-normal scale (mm)",
                where,
                o.get("scale", "—"),
                f"{row['lognorm_scale']:.3f}",
                "area",
                cls,
                "optics.csd.aggregate_csd",
            )
            add(
                f"{tag}: Bayes near / far split (tie-break artefact)",
                where + ", fig 09 (79/21), growth",
                o.get("nf", "—"),
                f"{100 * row['frac_near']:.0f} / {100 - 100 * row['frac_near']:.0f}",
                "free",
                "CHOICE",
                "optics.disambiguate.disambiguate",
            )
            add(
                f"{tag}: share of p_near within 0.500 ± 0.002",
                "— (fact 5 of the audit)",
                "—",
                f"{100 * row['p_near_within_0.002']:.1f} %",
                "free",
                "CHOICE",
                "optics.disambiguate.disambiguate",
            )
            add(
                f"{tag}: mean |depth correction| / median",
                "csd.tex §depthsmall, fig 09",
                "0.01 %",
                f"{row['mean_abs_corr_pct']:.3f} %",
                "free",
                cls,
                "optics.kpi.run_pipeline (same formula)",
            )
            if row["depth_offset_um_p50_p99"]:
                add(
                    f"{tag}: |d − d_focus| of near/far assignments, p50 / p99",
                    "sizing.tex fig 09",
                    "±0.005 mm",
                    " / ".join(
                        f"{v:.1f} µm" for v in row["depth_offset_um_p50_p99"]
                    ),
                    "area",
                    cls,
                    "optics.disambiguate.disambiguate",
                )
    out["csd"] = csd_out


def render_fig07() -> None:
    """Redraw ``07_overlay_{near,at_focus,far}.png`` at the per-axis 1080p scale.

    ``scale_overlay.render_demos`` builds its lens without a frame size (a PAL
    sample, 3.75 µm/px) and draws a square-pixel grid, but ``frame_0.png`` is a
    1080p clip frame whose pixel is 1.465 × 1.914 µm. Here the cropped frame is
    first resampled down the columns by µm_y/µm_x, so every displayed pixel is
    µm_x wide and µm_x tall in the slurry; the square grid of ``render_pair`` is
    then metrically true on both axes.
    """
    import cv2

    from annotator.sharpness import compute_sharpness_map
    from annotator.viz import colorize_map
    from optics.model import mm_per_pixel_at
    from optics.video_io import DEFAULT_CROP
    from scale_overlay.render_demos import render_pair

    lens_clip = lens_from_config(
        CFG, CFG.display_width_px, CFG.display_height_px
    )
    ux, uy = um_per_px_xy_at_focus(CFG, lens_clip)
    square = LensSetup(
        focal_length=CFG.focal_length_mm,
        f_number=CFG.f_number,
        extension_tube=CFG.extension_tube_mm,
        pixel_pitch_um=lens_clip.pixel_pitch_x_um,
        sensor_width=CFG.sensor_width_mm,
        sensor_height=CFG.sensor_height_mm,
    )
    frame = cv2.imread("docs/optics/frame_0.png")
    if frame is None or frame.shape[1] != CFG.display_width_px:
        raise FileNotFoundError(
            "docs/optics/frame_0.png (a 1920 × 1080 clip frame) missing"
        )
    crop = DEFAULT_CROP.apply(frame)
    sharp = colorize_map(
        compute_sharpness_map(
            cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), kernel=15
        ),
        cv2.COLORMAP_INFERNO,
    )
    h, w = crop.shape[:2]
    size = (w, round(h * uy / ux))
    crop_sq = np.asarray(
        cv2.resize(crop, size, interpolation=cv2.INTER_CUBIC), dtype=np.uint8
    )
    sharp_sq = np.asarray(
        cv2.resize(sharp, size, interpolation=cv2.INTER_CUBIC), dtype=np.uint8
    )
    d = CFG.focus_object_distance_mm
    for label, d_o in (("near", d - 0.2), ("at_focus", d), ("far", d + 0.2)):
        out = render_pair(crop_sq, square, d, d_o, sharp_sq)
        path = Path("docs/optics/figures") / f"07_overlay_{label}.png"
        cv2.imwrite(str(path), out)
        s = float(mm_per_pixel_at(square, d, np.array([d_o]))[0]) * 1000.0
        print(
            f"{path.name}: d_o = {d_o:.1f} mm, {s:.3f} µm per displayed px "
            f"(frame px {ux * d_o / d:.3f} × {uy * d_o / d:.3f}), rows ×{uy / ux:.3f}"
        )


def main() -> None:
    p = argparse.ArgumentParser(
        description="Recompute every computed number of the CEP paper."
    )
    p.add_argument("--no-video", action="store_true", help="optics rows only")
    p.add_argument(
        "--json", type=Path, help="also write rows and raw results here"
    )
    p.add_argument(
        "--fig07",
        action="store_true",
        help="only redraw the 07_overlay_* figures at the per-axis 1080p scale",
    )
    args = p.parse_args()
    if args.fig07:
        render_fig07()
        return
    out: dict[str, object] = {"config": str(CFG.source_path.relative_to(ROOT))}
    out["optics"] = optics_rows()
    if not args.no_video:
        video_rows(out)
    diffraction_rows()
    print(
        "| # | Number | Paper (where) | Old | New | Reproduced | Scale | Weakest class | Source |"
    )
    print("|---:|---|---|---|---|---|---|---|---|")
    for j, r in enumerate(ROWS, 1):
        print(
            f"| {j} | {r.name} | {r.where} | {r.old} | {r.new} | {r.reproduced} | {r.scale} | "
            f"{r.cls} | `{r.source}` |"
        )
    if args.json:
        out["rows"] = [asdict(r) for r in ROWS]
        args.json.write_text(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
