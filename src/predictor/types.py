"""Data types for the predictor module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

type Mat = NDArray[Any]


@dataclass
class PreprocessConfig:
    """Video preprocessing parameters."""

    target_height: int = 120
    frame_skip: int = 10
    max_frames: int = 200
    hankel_delay: int = 1


@dataclass
class DMDConfig:
    """mrDMD fitting parameters."""

    svd_rank: int = 5
    max_level: int = 2
    max_cycles: int = 1


@dataclass
class DMDResult:
    """Fitted mrDMD decomposition."""

    modes: NDArray[np.complex128]
    dynamics: NDArray[np.complex128]
    eigs: NDArray[np.complex128]
    n_frames_train: int
    frame_shape: tuple[int, int]
    n_pixels: int  # original pixel count (before Hankel)
    mrdmd: Any  # fitted MrDMD object
    mode_levels: list[int] = field(default_factory=list)
