"""Tests for the port of Ananya's image enhancement."""

from __future__ import annotations

import numpy as np
import pytest

from crystal_detector.enhance import ananya_enhance, enhance, level


def test_level_flattens_slow_brightness_but_keeps_edges():
    ramp = np.tile(np.linspace(60, 200, 400), (300, 1)).astype(np.uint8)
    img = ramp.copy()
    img[140:160, 190:210] = 10  # a dark crystal edge
    out = level(img, sigma_px=20.0).astype(float)
    interior = out[50:100, 50:350]
    assert interior.std() < ramp[50:100, 50:350].std() / 4
    assert out[150, 200] < interior.mean() - 50


def test_level_leaves_black_borders_alone():
    img = np.full((300, 400), 150, np.uint8)
    img[:, :60] = 0  # pillarbox bars like her raw frames
    img[:, -60:] = 0
    out = level(img, sigma_px=20.0)
    assert (out[:, :60] == 0).all() and (out[:, -60:] == 0).all()


def test_enhance_raises_local_contrast():
    rng = np.random.default_rng(0)
    img = (120 + rng.normal(0, 5, (200, 200))).clip(0, 255).astype(np.uint8)
    assert enhance(img).std() > 3 * img.std()


def test_ananya_enhance_keeps_frame_shape_and_alignment(crystal_frame):
    img, paint = crystal_frame
    paint(280, 200, 30, 30)
    out = ananya_enhance(img, scale=(576 / 1080, 576 / 1080))
    assert out.shape == img.shape and out.dtype == np.uint8
    # the resample round trip must not shift the crystal against the masks
    rim_cols = np.where(out[215, 260:330] < 60)[0] + 260
    assert rim_cols.min() == pytest.approx(274, abs=2)
    assert rim_cols.max() == pytest.approx(316, abs=2)
