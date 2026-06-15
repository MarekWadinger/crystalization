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


def test_sharpness_gaussian_is_monotone_in_coc() -> None:
    coc = np.array([0.0, 0.005, 0.01, 0.02, 0.05])
    s = sharpness_gaussian(coc, sigma_floor=1e-3)
    assert np.all(np.diff(s) < 0.0)


def test_sight_glass_shift_independent_of_distance() -> None:
    glass = SightGlass(thickness=15.0, refractive_index=1.47)
    d = np.array([100.0, 500.0, 1000.0])
    shifted = apparent_object_distance(d, glass)
    delta = d - shifted
    assert np.allclose(delta, delta[0])
    assert delta[0] == pytest.approx(15.0 * (1.0 - 1.0 / 1.47), rel=1e-9)
