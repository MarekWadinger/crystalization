"""Per-axis pixel scale of the analog chain (optics.config, optics.scale_chain)."""

from __future__ import annotations

import numpy as np
import pytest

from optics.config import (
    lens_from_config,
    load_camera,
    um_per_px_xy_at_focus,
)
from optics.scale_chain import (
    nominal_scales,
    one_at_a_time,
    sample_budget,
    spectral_aspect,
)


@pytest.fixture(scope="module")
def cfg():
    return load_camera()


def test_pal_scale_in_slurry_is_about_3_98_by_3_65_um(cfg) -> None:
    # Arrange
    lens = lens_from_config(cfg, 720, 576)
    # Act
    ux, uy = um_per_px_xy_at_focus(cfg, lens)
    # Assert — 6.83 × 6.25 µm sensor pitch over M = 60/35 (lens at its FAR stop)
    assert ux == pytest.approx(3.98, abs=0.01)
    assert uy == pytest.approx(3.65, abs=0.01)


def test_1080p_scale_in_slurry_is_about_1_49_by_1_94_um(cfg) -> None:
    ux, uy = um_per_px_xy_at_focus(cfg, lens_from_config(cfg, 1920, 1080))
    assert ux == pytest.approx(1.488, abs=0.01)
    assert uy == pytest.approx(1.944, abs=0.01)


def test_1080p_pixel_is_anisotropic_about_1_3(cfg) -> None:
    # A clip pixel covers more slurry vertically than horizontally: the
    # display stretches 576 lines by 1.875 but a PAL sample by 2.68.
    lens = lens_from_config(cfg, 1920, 1080)
    ratio = lens.pixel_pitch_y_um / lens.pixel_pitch_x_um
    assert 1.25 < ratio < 1.36


def test_pal_sample_aspect_is_close_to_pal_par(cfg) -> None:
    # ITU-R BT.601 PAL pixel aspect 59/54 ≈ 1.093 for a 4:3 picture
    px, py = cfg.sample_pitch_um
    assert px / py == pytest.approx(59 / 54, rel=0.01)


def test_nominal_scales_match_runtime_path_within_rounding(cfg) -> None:
    # scale_chain uses f/(e+x); the runtime path uses the rounded d_focus 55.1
    nom = nominal_scales(cfg)
    for rec, size in (
        ("PAL 720×576", (720, 576)),
        ("1080p clip", (1920, 1080)),
    ):
        ux, uy = um_per_px_xy_at_focus(cfg, lens_from_config(cfg, *size))
        assert nom[rec][0] == pytest.approx(ux, rel=2e-3)
        assert nom[rec][1] == pytest.approx(uy, rel=2e-3)


def test_budget_interval_contains_nominal_and_ring_shifts_up(cfg) -> None:
    base = sample_budget(cfg, n=20_000)
    ring = sample_budget(cfg, n=20_000, ring=True)
    nom = nominal_scales(cfg)
    for key, s in base.items():
        rec, axis = key.rsplit(" ", 1)
        lo, hi = np.percentile(s, [2.5, 97.5])
        assert lo < nom[rec][0 if axis == "x" else 1] < hi
        # the tube dominates: about ±8–10 % half-width
        assert 0.06 < (hi - lo) / 2 / np.median(s) < 0.12
        assert np.median(ring[key]) / np.median(s) == pytest.approx(
            61 / 56, rel=0.01
        )


def test_glass_does_not_change_scale_at_focus(cfg) -> None:
    assert one_at_a_time(cfg)["n, t, a"] == (0.0, 0.0, "–")


@pytest.mark.parametrize("squeeze", [0.8, 1.0, 1.25])
def test_spectral_aspect_recovers_known_anisotropy(squeeze: float) -> None:
    # Arrange — isotropic power-law texture (amplitude ∝ k^-1.3, like a
    # natural image), resampled in x so µm_x/µm_y = 1/squeeze
    import cv2

    n = 1200
    rng = np.random.default_rng(1)
    k = np.hypot(np.fft.fftfreq(n)[:, None], np.fft.fftfreq(n)[None, :])
    k[0, 0] = 1.0
    field = np.real(
        np.fft.ifft2(np.fft.fft2(rng.normal(size=(n, n))) * k**-1.3)
    )
    w = int(n * squeeze)
    frame = cv2.resize(field, (w, n), interpolation=cv2.INTER_LINEAR)
    # Act
    r = spectral_aspect([frame], (50, n - 50, 50, w - 50), (0.01, 0.05))
    # Assert
    assert r == pytest.approx(1 / squeeze, rel=0.05)
