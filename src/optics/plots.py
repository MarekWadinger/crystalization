"""Publication-quality plots for the optics chapter.

Run as a module to regenerate every figure into ``docs/optics/figures/``::

    uv run python -m optics.plots
"""

from __future__ import annotations

from pathlib import Path

import tomllib

import matplotlib.pyplot as plt
import numpy as np

from optics.config import (
    lens_from_config,
    load_camera,
    sight_glass_from_config,
)
from optics.model import (
    LensSetup,
    circle_of_confusion,
    mm_per_pixel_at,
)
from optics.psf import sharpness_diffraction, sharpness_gaussian

_CFG = load_camera()
_FIG = tomllib.loads(_CFG.source_path.read_text())["figures"]

CAMERA_100 = lens_from_config(_CFG)
"""Camera 100 install loaded from ``configs/camera_100.toml`` (sensor-native pitch)."""

SIGHT_GLASS = sight_glass_from_config(_CFG)
"""Sight glass geometry loaded from ``configs/camera_100.toml``."""

D_FOCUS = _CFG.focus_object_distance_mm
"""Focused object distance from config; derived from i_fixed = f + e."""

PLT_STYLE: dict[str, object] = {
    "figure.dpi": 140,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
    "font.size": 11,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "lines.linewidth": 1.8,
}


def _setup_style() -> None:
    plt.rcParams.update(PLT_STYLE)


def _annotate_focus(
    ax: plt.Axes, d_focus: float, *, label: str = "focused plane"
) -> None:
    """Mark the focused object distance — use axes-coordinates so reorder-safe."""
    ax.axvline(d_focus, color="k", linestyle="--", linewidth=1.0, alpha=0.6)
    ax.annotate(
        f"{label}\nd_focus = {d_focus:.0f} mm",
        xy=(d_focus, 1.0),
        xycoords=("data", "axes fraction"),
        xytext=(4, -4),
        textcoords="offset points",
        va="top",
        ha="left",
        fontsize=9,
    )


def fig_mm_per_pixel(out_path: Path) -> None:
    """mm/px vs object distance — linear, depth-of-field-independent."""
    d_o = np.linspace(max(40.0, D_FOCUS - 30.0), D_FOCUS * 6.0, 400)
    px = mm_per_pixel_at(CAMERA_100, D_FOCUS, d_o) * 1000.0  # µm/px

    fig, ax = plt.subplots(figsize=(6.5, 4.0))
    ax.plot(d_o, px, label="µm/px at object plane")
    ax.set_xlabel("object distance d_o (mm)")
    ax.set_ylabel("object-plane pixel size (µm/px)")
    ax.set_title(
        "Object-plane pixel size is LINEAR in d_o\n"
        f"f={CAMERA_100.focal_length:.0f} mm, e={CAMERA_100.extension_tube:.0f} mm, "
        f"focus={D_FOCUS:.0f} mm, pitch={CAMERA_100.pixel_pitch_um:.1f} µm"
    )
    _annotate_focus(ax, D_FOCUS)
    px_focus = float(mm_per_pixel_at(CAMERA_100, D_FOCUS, D_FOCUS) * 1000.0)
    ax.scatter(
        [D_FOCUS],
        [px_focus],
        zorder=5,
        s=40,
        color="C3",
        label=f"focus point: {px_focus:.2f} µm/px",
    )
    ax.legend(loc="lower right")
    fig.savefig(out_path)
    plt.close(fig)


def fig_coc_vs_distance(out_path: Path) -> None:
    """Geometric CoC vs object distance — asymmetric near/far.

    Zoomed to ±20 % of focus where DoF live; beyond that the lens is
    saturated at its hyperfocal blur limit and the model becomes
    uninteresting.
    """
    half = max(2.0, D_FOCUS * 0.2)
    d_o = np.linspace(D_FOCUS - half, D_FOCUS + half, 600)
    c = circle_of_confusion(CAMERA_100, D_FOCUS, d_o) * 1000.0  # µm

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11.5, 4.2))
    axL.plot(d_o, c)
    axL.set_xlabel("object distance d_o (mm)")
    axL.set_ylabel("circle of confusion c (µm at sensor)")
    axL.set_title(
        f"CoC vs d_o (geometric)\n"
        f"f={CAMERA_100.focal_length:.0f} mm, "
        f"F/{CAMERA_100.f_number:.1f}, focus={D_FOCUS:.0f} mm"
    )
    _annotate_focus(axL, D_FOCUS)
    c_inf = (
        CAMERA_100.aperture_diameter
        * CAMERA_100.focal_length
        / (D_FOCUS - CAMERA_100.focal_length)
        * 1000.0
    )
    axL.axhline(
        CAMERA_100.pixel_pitch_um,
        color="C3",
        linestyle=":",
        linewidth=1.0,
        label=f"1-pixel blur ({CAMERA_100.pixel_pitch_um:.1f} µm)",
    )
    axL.set_ylim(0, c.max() * 1.05)
    axL.legend()
    # context note for the saturation limit (rendered in title only —
    # within this ±15 mm window the curve is not yet saturated)
    axL.text(
        0.02,
        0.95,
        f"hyperfocal limit (d_o → ∞): c_∞ = {c_inf:.0f} µm",
        transform=axL.transAxes,
        fontsize=8,
        alpha=0.7,
    )

    # Reciprocal-distance view: symmetric and linear.
    u = 1.0 / d_o
    axR.plot(u * 1000.0, c)  # u in 1/m for legibility
    axR.set_xlabel("reciprocal object distance 1/d_o (1/m)")
    axR.set_ylabel("circle of confusion c (µm)")
    axR.set_title(
        "Reciprocal-distance view\n(SYMMETRIC and LINEAR around focus)"
    )
    axR.axvline(
        1000.0 / D_FOCUS,
        color="k",
        linestyle="--",
        linewidth=1.0,
        alpha=0.6,
        label=f"u_focus = 1/{D_FOCUS:.0f} mm",
    )
    axR.legend()

    fig.savefig(out_path)
    plt.close(fig)


def fig_sharpness_vs_distance(out_path: Path) -> None:
    """Sharpness measure vs **defocus** δ = d_o − d_focus.

    The natural x-axis is the *defocus* relative to the focused plane,
    in micrometres — the geometric c is linear in δ, the FWHM of the
    sharpness cusp lives at a few × the sensor pixel pitch, and the
    near/far asymmetry is visible as the difference between negative
    and positive δ. We auto-fit the range to ~50× the FWHM so the
    cusp occupies a few % of the plot (visible but not the whole
    figure).

    Three panels:
      * linear-y, against δ — shows the cusp and the (small) asymmetry
      * log-y, against δ — exposes the c⁻⁵ tail
      * linear-y, against c (CoC at sensor) — the underlying model axis
    """
    pitch_mm = CAMERA_100.pixel_pitch_um * 1e-3
    sensor_floor = pitch_mm / 2.0

    # Fit the x-range adaptively. First a coarse pass to find the FWHM
    # in defocus units, then a properly-zoomed window at ~50× FWHM.
    coarse = np.linspace(D_FOCUS - 5.0, D_FOCUS + 5.0, 20000)
    c_coarse = circle_of_confusion(CAMERA_100, D_FOCUS, coarse)
    s_coarse = sharpness_diffraction(
        c_coarse, CAMERA_100.f_number, sensor_floor_mm=sensor_floor
    )
    above_half = s_coarse >= 0.5
    fwhm_mm = (
        float(coarse[above_half][-1] - coarse[above_half][0])
        if above_half.any()
        else 0.01
    )
    # Cusp at ~7 % of visible width — readable peak + visible tails.
    window_mm = max(0.005, 15.0 * fwhm_mm)

    d_o = np.linspace(D_FOCUS - window_mm, D_FOCUS + window_mm, 8000)
    delta_um = (d_o - D_FOCUS) * 1000.0
    c = circle_of_confusion(CAMERA_100, D_FOCUS, d_o)
    s_geom = sharpness_gaussian(c, sigma_floor=sensor_floor)
    s_diff = sharpness_diffraction(
        c, CAMERA_100.f_number, sensor_floor_mm=sensor_floor
    )

    # FWHM-matched Gaussian for visual reference (NOT the model).
    s_diff_arr = np.asarray(s_diff)
    half_mask = s_diff_arr >= 0.5
    if half_mask.any():
        fwhm = d_o[half_mask][-1] - d_o[half_mask][0]
        sigma_gauss = float(fwhm / 2.3548)
        s_gauss = np.exp(-0.5 * ((d_o - D_FOCUS) / sigma_gauss) ** 2)
    else:
        s_gauss = np.zeros_like(d_o)

    fig, (axL, axM, axR) = plt.subplots(1, 3, figsize=(15.5, 4.4))
    axL.plot(delta_um, s_geom, label="Gaussian PSF (c⁻⁵)", color="C0")
    axL.plot(
        delta_um, s_diff, label="+ diffraction & sensor floor", color="C1"
    )
    axL.plot(
        delta_um,
        s_gauss,
        label="Gaussian (FWHM-matched reference)",
        color="C3",
        linestyle="--",
    )
    axL.set_xlabel(
        f"defocus δ = d_o − d_focus (µm)  [d_focus = {D_FOCUS:.1f} mm]"
    )
    axL.axvline(0.0, color="k", linestyle="--", alpha=0.5, linewidth=1)
    axL.set_ylabel("normalised sharpness")
    axL.set_title(
        f"Sharpness vs defocus, linear (FWHM = {fwhm_mm * 1000:.1f} µm)"
    )
    axL.legend(loc="upper right", fontsize=8)

    axM.plot(delta_um, s_geom, label="Gaussian PSF (c⁻⁵)", color="C0")
    axM.plot(delta_um, s_diff, label="+ diffraction & sensor", color="C1")
    axM.plot(
        delta_um,
        s_gauss,
        label="Gaussian (reference)",
        color="C3",
        linestyle="--",
    )
    axM.set_xlabel("defocus δ (µm)")
    axM.set_yscale("log")
    axM.set_ylim(1e-4, 1.5)
    axM.axvline(0.0, color="k", linestyle="--", alpha=0.5, linewidth=1)
    axM.set_ylabel("normalised sharpness (log)")
    axM.set_title("Log-linear — Gaussian falls vs power-law")
    axM.legend(loc="upper right", fontsize=8)

    # Third panel: log-log of |δ| — power-law shows as a straight line.
    pos = delta_um > 0
    neg = delta_um < 0
    axR.loglog(
        delta_um[pos], s_geom[pos], color="C0", label="δ > 0 (far), c⁻⁵"
    )
    axR.loglog(
        -delta_um[neg],
        s_geom[neg],
        color="C0",
        linestyle=":",
        label="δ < 0 (near), c⁻⁵",
    )
    axR.loglog(
        delta_um[pos], s_diff[pos], color="C1", label="+ diff & sensor floor"
    )
    # Reference: pure ‒5 power-law slope guide.
    ref_x = np.array([5.0, 200.0])
    ref_y = (ref_x / ref_x[0]) ** (-5.0) * 0.5
    axR.loglog(
        ref_x, ref_y, color="0.4", linestyle="--", label="slope −5 reference"
    )
    axR.set_xlabel("|defocus δ| (µm, log)")
    axR.set_ylabel("normalised sharpness (log)")
    axR.set_title("Log-log |δ|: power-law tail = straight line")
    axR.set_xlim(0.3, window_mm * 1000.0)
    axR.set_ylim(1e-5, 2.0)
    axR.grid(True, which="both", alpha=0.2)
    axR.legend(loc="lower left", fontsize=8)
    fig.suptitle(
        "Defocus sharpness is a power-law cusp (NOT Gaussian); "
        f"current setup: F/{CAMERA_100.f_number:.1f}, e={CAMERA_100.extension_tube:.0f} mm",
        y=1.02,
        fontsize=12,
    )
    fig.savefig(out_path)
    plt.close(fig)


def fig_dof_envelope(out_path: Path) -> None:
    """Depth-of-field as a function of F-number.

    Plant question: how far in front of and behind the focused plane is a
    crystal still acceptably sharp? Answer depends on F-number and on the
    blur threshold the user picks (typically 1–2 sensor pixels).
    """
    half = max(1.0, D_FOCUS * 0.05)
    d_o = np.linspace(D_FOCUS - half, D_FOCUS + half, 1600)
    pitch = CAMERA_100.pixel_pitch_um

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    for idx, fn in enumerate(_CFG.iris_stops):
        color = f"C{idx}"
        lens_f = LensSetup(
            focal_length=CAMERA_100.focal_length,
            f_number=fn,
            extension_tube=CAMERA_100.extension_tube,
            pixel_pitch_um=CAMERA_100.pixel_pitch_um,
            sensor_width=CAMERA_100.sensor_width,
            sensor_height=CAMERA_100.sensor_height,
        )
        c = circle_of_confusion(lens_f, D_FOCUS, d_o) * 1000.0
        ax.plot(d_o, c, color=color, label=f"F/{fn:.1f}")
    ax.axhline(
        pitch,
        color="k",
        linestyle=":",
        alpha=0.7,
        label=f"1-pixel threshold ({pitch:.1f} µm)",
    )
    ax.axhline(
        2.0 * pitch,
        color="k",
        linestyle="--",
        alpha=0.5,
        label=f"2-pixel threshold ({2.0 * pitch:.1f} µm)",
    )
    ax.set_xlabel("object distance d_o (mm)")
    ax.set_ylabel("circle of confusion c (µm at sensor)")
    ax.set_title(
        "Depth of field shrinks dramatically with aperture\n"
        f"focus={D_FOCUS:.0f} mm, f={CAMERA_100.focal_length:.0f} mm, "
        f"e={CAMERA_100.extension_tube:.0f} mm"
    )
    ax.set_ylim(0, 8 * pitch)
    _annotate_focus(ax, D_FOCUS, label="focus")
    ax.legend(loc="upper right", fontsize=9)
    fig.savefig(out_path)
    plt.close(fig)


def fig_sight_glass_shift(out_path: Path) -> None:
    """Apparent object distance with vs without the sight glass."""
    d_o = np.linspace(max(20.0, D_FOCUS - 30.0), D_FOCUS * 5.0, 400)
    apparent = d_o - SIGHT_GLASS.apparent_shift

    fig, ax = plt.subplots(figsize=(6.5, 4.0))
    ax.plot(
        d_o, d_o, color="0.6", linestyle="--", label="no glass (reference)"
    )
    ax.plot(
        d_o,
        apparent,
        color="C0",
        label=f"through DIN 8902 (t={SIGHT_GLASS.thickness:.0f} mm, n={SIGHT_GLASS.refractive_index:.2f})",
    )
    ax.set_xlabel("real object distance d_o (mm)")
    ax.set_ylabel("apparent object distance (mm)")
    ax.set_title(
        f"Sight-glass refractive shift Δ = t·(1−1/n_g) = {SIGHT_GLASS.apparent_shift:.2f} mm\n(constant, independent of distance)"
    )
    ax.legend(loc="lower right")
    fig.savefig(out_path)
    plt.close(fig)


def fig_extension_tube_sweep(out_path: Path) -> None:
    """Show how FOV / µm-per-px change with extension tube length."""
    tubes = [*_FIG["extension_sweep_mm"], _CFG.extension_tube_mm]
    d_o = np.linspace(D_FOCUS * 0.75, D_FOCUS * 7.5, 400)

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    for e in tubes:
        lens_e = LensSetup(
            focal_length=CAMERA_100.focal_length,
            f_number=CAMERA_100.f_number,
            extension_tube=e,
            pixel_pitch_um=CAMERA_100.pixel_pitch_um,
            sensor_width=CAMERA_100.sensor_width,
            sensor_height=CAMERA_100.sensor_height,
        )
        i_fixed = lens_e.focal_length + e + 1e-9
        if i_fixed <= lens_e.focal_length:
            continue
        # For a fixed sensor distance i = f + e (focus ring at infinity),
        # the focused object distance is set by 1/f = 1/d_o + 1/i:
        if e == 0:
            d_focus_e = 1e6
        else:
            d_focus_e = (
                lens_e.focal_length * i_fixed / (i_fixed - lens_e.focal_length)
            )
        px = CAMERA_100.pixel_pitch_um * d_o / i_fixed
        ax.plot(
            d_o,
            px,
            label=f"e={e:.0f} mm  →  d_focus={d_focus_e:.0f} mm",
        )
    ax.set_xlabel("object distance d_o (mm)")
    ax.set_ylabel("object-plane pixel size (µm/px)")
    ax.set_title("Extension-tube sweep — how the macro range depends on e")
    ax.set_ylim(0, 40)
    ax.legend(loc="upper left", fontsize=9)
    fig.savefig(out_path)
    plt.close(fig)


def main() -> None:
    """Render every figure to ``docs/optics/figures/``."""
    _setup_style()
    out_dir = Path("docs/optics/figures")
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_mm_per_pixel(out_dir / "01_mm_per_pixel.png")
    fig_coc_vs_distance(out_dir / "02_coc_vs_distance.png")
    fig_sharpness_vs_distance(out_dir / "03_sharpness_vs_distance.png")
    fig_dof_envelope(out_dir / "04_dof_envelope.png")
    fig_sight_glass_shift(out_dir / "05_sight_glass_shift.png")
    fig_extension_tube_sweep(out_dir / "06_extension_tube_sweep.png")
    print(f"Wrote 6 figures to {out_dir.resolve()}")


if __name__ == "__main__":
    main()
