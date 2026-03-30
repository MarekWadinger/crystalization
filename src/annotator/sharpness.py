"""Sharpness (focus) measurement using Laplacian variance."""

from __future__ import annotations

import cv2
import numpy as np
from numpy.typing import NDArray

from annotator.types import Mat


def compute_sharpness_map(gray: Mat, kernel: int) -> NDArray[np.float64]:
    """Compute per-pixel sharpness using Laplacian variance in a local window.

    Returns log-scaled sharpness to avoid extreme skew (a few sharp edges
    would otherwise dominate the entire range, making the map look flat).
    """
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    squared: NDArray[np.float64] = laplacian**2
    smoothed: NDArray[np.float64] = cv2.GaussianBlur(
        squared, (kernel, kernel), 0
    )
    sharpness: NDArray[np.float64] = np.log1p(smoothed)
    return sharpness
