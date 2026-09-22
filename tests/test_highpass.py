"""Tests for the sight-glass high-pass preprocessing filter."""

from __future__ import annotations

import numpy as np

from optics.highpass import highpass


def test_highpass_suppresses_smooth_gradient_keeps_edges():
    """A smooth illumination ramp is removed; a sharp edge survives."""
    y, x = np.mgrid[:128, :128].astype(np.float32)

    # Pure low-frequency gradient (the LED illumination analogue).
    gradient = x * 2.0
    residual_gradient = highpass(gradient, sigma_px=25.0)

    # Same gradient plus a hard vertical edge (crystal-edge analogue).
    with_edge = gradient.copy()
    with_edge[:, 64:] += 120.0
    residual_edge = highpass(with_edge, sigma_px=25.0)

    # The smooth gradient is almost entirely suppressed in the interior
    # (away from the inevitable Gaussian-blur border artefacts).
    interior_gradient = residual_gradient[:, 50:78]
    assert interior_gradient.mean() < 1.0
    # ...while the edge produces strong response right at the boundary.
    edge_band = residual_edge[:, 60:68]
    assert edge_band.max() > 20.0
    assert edge_band.max() > interior_gradient.max() * 5


def test_highpass_preserves_shape_and_is_nonnegative():
    rng = np.random.default_rng(0)
    img = rng.integers(0, 255, size=(64, 80, 3), dtype=np.uint8)
    out = highpass(img, sigma_px=10.0)
    assert out.shape == img.shape
    assert out.min() >= 0.0
