"""Sub-pixel image registration for static-rig frame subtraction.

Use case: RQ4-style analyses subtract a temporal-median empty-tank
reference from per-frame intensity to isolate the slurry-contributed
signal. Even with a rigidly mounted camera, sub-pixel jitter from
mechanical vibration and sensor read-out timing contaminates the
residual — the rupture-baseline figures from the prior session show
edge-derivative artefacts that track this jitter.

This module provides minimal translation-only registration via
``cv2.phaseCorrelate`` followed by ``cv2.warpAffine`` resampling.
Translation-only is the right model for this rig because the camera
is bolted to a flange and the only inter-frame motion is small
linear drift — full affine would over-fit and add noise.

API
---

``estimate_translation(reference, target) -> (dy, dx)``
    Returns the sub-pixel shift that, when applied to ``target``,
    aligns it with ``reference``. Both inputs must be 2-D float
    arrays of the same shape.

``apply_translation(image, dy, dx) -> aligned``
    Resamples ``image`` by the given (dy, dx) shift using bilinear
    interpolation. Out-of-frame regions are filled with zeros.

``register_to(reference, target) -> (aligned, dy, dx)``
    Convenience wrapper that estimates the shift and applies it.
"""

from __future__ import annotations

import cv2
import numpy as np
from numpy.typing import NDArray

__all__ = [
    "apply_translation",
    "estimate_translation",
    "register_to",
]


def _as_float32(
    img: NDArray[np.floating] | NDArray[np.integer],
) -> NDArray[np.float32]:
    if img.dtype == np.float32:
        return img  # type: ignore[return-value]
    return img.astype(np.float32, copy=False)


def estimate_translation(
    reference: NDArray[np.floating] | NDArray[np.integer],
    target: NDArray[np.floating] | NDArray[np.integer],
) -> tuple[float, float]:
    """Estimate sub-pixel (dy, dx) shift that aligns ``target`` to ``reference``.

    Uses ``cv2.phaseCorrelate`` which returns the shift of ``target`` relative
    to ``reference`` in (dx, dy) convention. We transpose to (dy, dx) and
    negate so the returned shift is what ``apply_translation`` should apply
    to ``target`` to bring it into ``reference``'s frame.
    """
    if reference.shape != target.shape:
        raise ValueError(
            f"shape mismatch: reference={reference.shape} target={target.shape}"
        )
    if reference.ndim != 2:
        raise ValueError(f"expected 2-D arrays, got {reference.ndim}-D")

    ref32 = _as_float32(reference)
    tgt32 = _as_float32(target)
    # phaseCorrelate returns the shift FROM reference TO target in (x, y) order.
    # To register target onto reference we want the inverse — apply -shift.
    (shift_x, shift_y), _peak_response = cv2.phaseCorrelate(ref32, tgt32)
    return -float(shift_y), -float(shift_x)


def apply_translation(
    image: NDArray[np.floating] | NDArray[np.integer],
    dy: float,
    dx: float,
) -> NDArray[np.float32]:
    """Resample ``image`` by ``(dy, dx)`` shift via bilinear warpAffine.

    Returns a float32 array of the same shape as ``image``. Border pixels
    that fall outside the original frame are filled with 0.
    """
    if image.ndim != 2:
        raise ValueError(f"expected 2-D array, got {image.ndim}-D")
    h, w = image.shape
    m = np.array([[1.0, 0.0, dx], [0.0, 1.0, dy]], dtype=np.float32)
    warped = cv2.warpAffine(
        _as_float32(image),
        m,
        (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0.0,
    )
    return warped.astype(np.float32, copy=False)


def register_to(
    reference: NDArray[np.floating] | NDArray[np.integer],
    target: NDArray[np.floating] | NDArray[np.integer],
) -> tuple[NDArray[np.float32], float, float]:
    """Estimate shift and return ``(aligned_target, dy, dx)``."""
    dy, dx = estimate_translation(reference, target)
    aligned = apply_translation(target, dy, dx)
    return aligned, dy, dx
