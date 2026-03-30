"""Optical flow computation using Farneback method."""

from __future__ import annotations

import cv2
import numpy as np
from numpy.typing import NDArray

from annotator.types import Mat


def compute_flow_magnitude(
    prev_gray: Mat, curr_gray: Mat
) -> NDArray[np.float64]:
    """Compute dense optical flow magnitude using Farneback method."""
    flow_init = np.zeros((*prev_gray.shape, 2), dtype=np.float32)
    flow: Mat = cv2.calcOpticalFlowFarneback(
        prev_gray,
        curr_gray,
        flow_init,
        0.5,
        3,
        15,
        3,
        5,
        1.2,
        0,
    )
    mag: NDArray[np.float64] = np.sqrt(
        flow[..., 0].astype(np.float64) ** 2
        + flow[..., 1].astype(np.float64) ** 2
    )
    return mag
