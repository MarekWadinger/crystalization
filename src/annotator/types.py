"""Shared types and dataclasses for crystal analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

# cv2 functions return MatLike which ty resolves as NDArray with generic dtype.
type Mat = NDArray[Any]


@dataclass
class LayerConfig:
    """Configuration for layer decomposition and crystal detection."""

    # Layer decomposition
    num_layers: int = 3
    sharpness_weight: float = 0.6
    flow_weight: float = 0.4
    blur_kernel: int = 15

    # Edge detection: adaptive threshold
    # block_size for adaptiveThreshold (must be odd, >= 3)
    edge_block_size: int = 11
    # C constant subtracted from mean in adaptive threshold
    edge_c: int = 2

    # Morphological closing kernel to connect edge fragments.
    # Actual kernel per layer is scaled: base + layer_index * morph_scale.
    morph_base: int = 3
    morph_scale: int = 4

    # Contour filtering
    min_area: float = 50.0
    max_area: float = 50000.0
    # Max aspect ratio (width/height or height/width, always >= 1).
    # Reject elongated "noodle" shapes. 1.0 = perfect square.
    max_aspect_ratio: float = 4.0


@dataclass
class Crystal:
    """A detected crystal with oriented bounding rectangle."""

    # Center
    y: float
    x: float
    # Bounding rect dimensions (always width <= height after normalization)
    width: float
    height: float
    # Rotation angle in degrees
    angle: float

    @property
    def area(self) -> float:
        """Bounding rectangle area."""
        return self.width * self.height

    @property
    def size(self) -> float:
        """Equivalent size as geometric mean of width and height."""
        return float(np.sqrt(self.width * self.height))

    @property
    def aspect_ratio(self) -> float:
        """Aspect ratio (>= 1.0, 1.0 = square)."""
        if self.width < 1e-6 or self.height < 1e-6:
            return 999.0
        return max(self.width, self.height) / min(self.width, self.height)


@dataclass
class LayerResult:
    """Results for a single layer in a single frame."""

    layer_id: int
    crystals: list[Crystal] = field(default_factory=list)

    @property
    def count(self) -> int:
        """Number of crystals detected in this layer."""
        return len(self.crystals)

    @property
    def mean_size(self) -> float:
        """Mean equivalent size of detected crystals, or 0 if none."""
        if not self.crystals:
            return 0.0
        return float(np.mean([c.size for c in self.crystals]))


@dataclass
class FrameResult:
    """Results for a single frame."""

    frame_idx: int
    layers: list[LayerResult] = field(default_factory=list)


@dataclass
class Detection:
    """A crystal detection loaded from CSV."""

    layer: int
    x: float
    y: float
    width: float
    height: float
    angle: float
