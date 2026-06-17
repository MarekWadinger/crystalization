"""Tests for sub-pixel registration utility."""

from __future__ import annotations

import numpy as np
import pytest

from optics.registration import (
    apply_translation,
    estimate_translation,
    register_to,
)


def _make_textured_frame(seed: int = 0) -> np.ndarray:
    """Frame with distinctive structured features phaseCorrelate can lock onto.

    Phase correlation needs a non-flat phase spectrum — pure noise or
    over-smoothed noise produces unstable peaks. A mix of sinusoids
    plus a faint noise floor gives a sharp correlation peak.
    """
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[:256, :256].astype(np.float32)
    return (
        np.sin(x * 0.1) * np.cos(y * 0.15)
        + np.sin((x + y) * 0.05) * 0.5
        + np.cos((x - 0.7 * y) * 0.08) * 0.3
        + 0.1 * rng.standard_normal((256, 256)).astype(np.float32)
    )


@pytest.mark.parametrize(
    "true_dy,true_dx",
    [
        (5.0, -3.0),
        (-7.2, 4.1),
        (-1.3, 2.6),
        (0.0, 0.0),
    ],
)
def test_estimate_translation_recovers_known_shift(
    true_dy: float, true_dx: float
) -> None:
    """Estimator recovers an integer or near-integer synthetic shift."""
    ref = _make_textured_frame(seed=42)
    shifted = apply_translation(ref, true_dy, true_dx)

    # phaseCorrelate has a small bias near the image edge from the
    # zero-fill border; crop to the interior region before estimating.
    crop = (slice(64, -64), slice(64, -64))
    est_dy, est_dx = estimate_translation(ref[crop], shifted[crop])

    # We applied (true_dy, true_dx) to obtain `shifted`. estimate_translation
    # returns the shift to apply to `shifted` to bring it back — i.e. the
    # negative of (true_dy, true_dx).
    assert est_dy == pytest.approx(-true_dy, abs=0.4)
    assert est_dx == pytest.approx(-true_dx, abs=0.4)


def test_register_to_reduces_residual() -> None:
    """register_to() makes the aligned target closer to reference."""
    ref = _make_textured_frame(seed=7)
    shifted = apply_translation(ref, 2.4, -1.8)

    crop = (slice(64, -64), slice(64, -64))
    aligned, dy, dx = register_to(ref[crop], shifted[crop])

    interior = ref[crop]
    residual_before = float(np.std(shifted[crop] - interior))
    residual_after = float(np.std(aligned - interior))
    # Registration should at least halve the misalignment residual; the
    # remaining residual is from bilinear-interpolation softening and
    # the small zero-fill border that the crop doesn't fully exclude.
    assert residual_after < residual_before * 0.6
    assert dy == pytest.approx(-2.4, abs=0.5)
    assert dx == pytest.approx(1.8, abs=0.5)


def test_shape_mismatch_raises() -> None:
    a = np.zeros((10, 10), dtype=np.float32)
    b = np.zeros((10, 12), dtype=np.float32)
    with pytest.raises(ValueError, match="shape mismatch"):
        estimate_translation(a, b)


def test_non_2d_raises() -> None:
    a = np.zeros((4, 4, 3), dtype=np.float32)
    with pytest.raises(ValueError, match="2-D"):
        estimate_translation(a, a)
    with pytest.raises(ValueError, match="2-D"):
        apply_translation(a, 0.0, 0.0)
