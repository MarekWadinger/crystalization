"""Tests for the optics module — invariants only, no fixture videos."""

from __future__ import annotations

import numpy as np
import pytest

from optics import (
    LensSetup,
    SightGlass,
    apparent_object_distance,
    circle_of_confusion,
    image_distance_for_focus,
    magnification,
    mm_per_pixel_at,
    object_distance,
    sharpness_gaussian,
    sharpness_vs_object_distance,
)


@pytest.fixture
def hf35() -> LensSetup:
    return LensSetup(
        focal_length=35.0,
        f_number=4.0,
        extension_tube=10.0,
        pixel_pitch_um=2.9,
        sensor_width=5.568,
        sensor_height=3.132,
    )


def test_thin_lens_round_trip_finite_distance(hf35: LensSetup) -> None:
    d_focus = 165.0
    i = image_distance_for_focus(hf35, d_focus)
    assert object_distance(hf35, i) == pytest.approx(d_focus, rel=1e-9)


def test_magnification_matches_textbook_form(hf35: LensSetup) -> None:
    d_focus = 165.0
    m_direct = magnification(hf35, d_focus)
    i = image_distance_for_focus(hf35, d_focus)
    m_via_image = i / d_focus
    assert m_direct == pytest.approx(m_via_image, rel=1e-9)


def test_mm_per_pixel_is_linear_in_d_o(hf35: LensSetup) -> None:
    d_focus = 165.0
    d_o = np.array([100.0, 150.0, 200.0, 300.0, 400.0])
    px = mm_per_pixel_at(hf35, d_focus, d_o)
    ratios = px[1:] / px[:-1]
    assert ratios == pytest.approx(d_o[1:] / d_o[:-1], rel=1e-9)


def test_coc_is_zero_at_focus(hf35: LensSetup) -> None:
    d_focus = 165.0
    c = circle_of_confusion(hf35, d_focus, d_focus)
    assert float(c) == pytest.approx(0.0, abs=1e-12)


def test_coc_is_asymmetric_in_object_space(hf35: LensSetup) -> None:
    d_focus = 165.0
    delta = 20.0
    c_near = circle_of_confusion(hf35, d_focus, d_focus - delta)
    c_far = circle_of_confusion(hf35, d_focus, d_focus + delta)
    assert float(c_near) > float(c_far)


def test_coc_is_symmetric_in_reciprocal_distance(hf35: LensSetup) -> None:
    d_focus = 165.0
    u_focus = 1.0 / d_focus
    du = 0.0005
    d_near = 1.0 / (u_focus + du)
    d_far = 1.0 / (u_focus - du)
    c_near = circle_of_confusion(hf35, d_focus, d_near)
    c_far = circle_of_confusion(hf35, d_focus, d_far)
    assert float(c_near) == pytest.approx(float(c_far), rel=1e-6)


def test_coc_far_limit_matches_hyperfocal(hf35: LensSetup) -> None:
    d_focus = 165.0
    c_inf = circle_of_confusion(hf35, d_focus, 1e9)
    c_limit = (
        hf35.aperture_diameter
        * hf35.focal_length
        / (d_focus - hf35.focal_length)
    )
    assert float(c_inf) == pytest.approx(c_limit, rel=1e-6)


def test_sharpness_peaks_at_focus(hf35: LensSetup) -> None:
    d_focus = 165.0
    d_o = np.linspace(100.0, 250.0, 301)
    s = sharpness_vs_object_distance(hf35, d_focus, d_o, diffraction=True)
    idx_peak = int(np.argmax(s))
    assert d_o[idx_peak] == pytest.approx(d_focus, abs=0.5)


def test_diffraction_uses_working_f_number_at_macro_magnification() -> None:
    from optics.psf import sharpness_diffraction, working_f_number

    # Arrange: M = 1.743 as in the installed setup; N_w = N (1 + M)
    m = 1.743
    assert working_f_number(16.0, m) == pytest.approx(16.0 * 2.743)
    c = np.linspace(0.0, 0.05, 200)  # CoC in mm
    # Act: same geometric blur, nominal vs working F-number
    s_nom = sharpness_diffraction(c, 16.0, sensor_floor_mm=3.27e-3)
    s_mac = sharpness_diffraction(
        c, 16.0, sensor_floor_mm=3.27e-3, magnification=m
    )
    # Assert: a larger diffraction floor flattens the cusp (wider FWHM)
    assert (s_mac >= 0.5).sum() > (s_nom >= 0.5).sum()


def test_fit_power_law_tail_recovers_exponent_on_its_band() -> None:
    from optics.measure import fit_band, fit_power_law_tail

    # Arrange: a pure power law density ∝ x^-4
    x = np.linspace(1.0, 10.0, 400)
    y = x**-4.0
    # Act
    alpha, _ = fit_power_law_tail(x, y)
    lo, hi = fit_band(y)
    # Assert: exponent recovered and the band lies inside the histogram
    assert alpha == pytest.approx(4.0, rel=1e-6)
    assert 0 < lo < hi <= len(x)


def test_sharpness_gaussian_is_monotone_in_coc() -> None:
    coc = np.array([0.0, 0.005, 0.01, 0.02, 0.05])
    s = sharpness_gaussian(coc, sigma_floor=1e-3)
    assert np.all(np.diff(s) < 0.0)


def test_sight_glass_shift_independent_of_distance() -> None:
    glass = SightGlass(thickness=20.0, refractive_index=1.47)
    d = np.array([100.0, 500.0, 1000.0])
    shifted = apparent_object_distance(d, glass)
    delta = d - shifted
    assert np.allclose(delta, delta[0])
    assert delta[0] == pytest.approx(20.0 * (1.0 - 1.0 / 1.47), rel=1e-9)


def test_load_camera_config_returns_pal_sample_pitch() -> None:
    from optics.config import (
        lens_from_config,
        load_camera,
        sight_glass_from_config,
    )

    cfg = load_camera()
    assert cfg.focal_length_mm == 35.0
    assert cfg.f_number == 1.6
    assert cfg.extension_tube_mm == 60.0
    assert cfg.flange_distance_mm == pytest.approx(17.526)
    # One DVR sample spans cell × CCD clock / 13.5 MHz; one line = one CCD row.
    px, py = cfg.sample_pitch_um
    assert px == pytest.approx(6.50 * 14.1875 / 13.5, rel=1e-9)
    assert py == pytest.approx(6.25)
    # No frame size: the pixel is a PAL sample, anisotropic.
    lens = lens_from_config(cfg)
    assert lens.pixel_pitch_x_um == pytest.approx(px, rel=1e-9)
    assert lens.pixel_pitch_y_um == pytest.approx(py, rel=1e-9)
    assert lens.pixel_pitch_um == pytest.approx((px * py) ** 0.5, rel=1e-9)
    glass = sight_glass_from_config(cfg)
    assert glass.thickness == 20.0


def test_lens_from_config_1080p_clip_is_stretched_pal() -> None:
    from optics.config import lens_from_config, load_camera

    cfg = load_camera()
    pal = lens_from_config(cfg, 720, 576)
    clip = lens_from_config(cfg, 1920, 1080)
    sx, sy = cfg.display_stretch
    assert clip.pixel_pitch_x_um == pytest.approx(pal.pixel_pitch_x_um / sx)
    assert clip.pixel_pitch_y_um == pytest.approx(pal.pixel_pitch_y_um / sy)
    # Sensor size is a camera property, independent of the recording.
    assert clip.sensor_width == pal.sensor_width == cfg.sensor_width_mm


def test_lens_from_config_refuses_unknown_frame_geometry() -> None:
    from optics.config import lens_from_config, load_camera

    with pytest.raises(ValueError, match="no scale chain"):
        lens_from_config(load_camera(), 1914, 1600)


def test_observations_schema_catches_stale_t(tmp_path) -> None:
    import json

    from pydantic import ValidationError

    from optics.observations_schema import load_validated

    path = tmp_path / "obs.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "2.0",
                "media": {
                    "stem": "test",
                    "start_wallclock": "2026-02-04T11:08:51",
                    "timezone": "Europe/Bratislava",
                },
                "events": [
                    {
                        "id": "e0",
                        "wallclock": "2026-02-04T11:46:10",
                        "t": 2349,
                        "phase": "discharge",
                        "label": "discharge",
                    }
                ],
            }
        )
    )
    with pytest.raises(ValidationError) as exc_info:
        load_validated(path)
    msg = str(exc_info.value)
    assert "2239" in msg and "t=2349" in msg


def test_observations_schema_fix_recomputes_t(tmp_path) -> None:
    import json

    from optics.observations_schema import load_validated, recompute_and_write

    path = tmp_path / "obs.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "2.0",
                "media": {
                    "stem": "test",
                    "start_wallclock": "2026-02-04T11:08:51",
                    "timezone": "Europe/Bratislava",
                },
                "events": [
                    {
                        "id": "e0",
                        "wallclock": "2026-02-04T11:46:10",
                        "t": 9999,
                        "phase": "discharge",
                        "label": "discharge",
                    }
                ],
            }
        )
    )
    changes = recompute_and_write(path)
    assert len(changes) == 1
    obs = load_validated(path)
    assert obs.events[0].t == 2239


@pytest.mark.parametrize("frame_size", [(1920, 1080), (720, 576)])
def test_detection_area_px_window_matches_config_in_um(
    frame_size: tuple[int, int],
) -> None:
    # Arrange — the 1080p clips and the PAL recordings share one config
    from optics.config import (
        detection_area_px,
        lens_from_config,
        load_camera,
        um_per_px_xy_at_focus,
    )

    cfg = load_camera()
    lens = lens_from_config(cfg, *frame_size)
    ux, uy = um_per_px_xy_at_focus(cfg, lens)

    # Act
    min_area, max_area = detection_area_px(cfg, lens)

    # Assert — lower bound is the pixel resolution limit; upper bound is the
    # pixel count of a max_size_um square, area per pixel ux · uy
    assert min_area == pytest.approx(cfg.min_side_px**2)
    assert max_area * ux * uy == pytest.approx(cfg.max_size_um**2)
