"""Shared fixtures for llm_annotator tests."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from llm_annotator.types import (
    BoundingBox,
    CrystalAnnotation,
    CrystalSystem,
    DepthLayer,
    FrameAnnotation,
)


@pytest.fixture
def sample_frame() -> np.ndarray:
    """Create a 480x640 BGR frame with dark rectangles."""
    frame = np.ones((480, 640, 3), dtype=np.uint8) * 200
    # Dark rectangles simulate crystals on a light background
    cv2.rectangle(frame, (100, 100), (150, 140), (50, 50, 50), -1)
    cv2.rectangle(frame, (300, 200), (380, 260), (40, 40, 40), -1)
    cv2.rectangle(frame, (450, 350), (490, 380), (60, 60, 60), -1)
    return frame


@pytest.fixture
def crystal_frame():
    """Annotation-sized grey frame (461×648, a PAL crop) and a crystal painter.

    The liquor ramps 60→200 left to right so the notebook's percentile
    thresholds split it; a crystal is a 250 body inside a 6 px dark rim.
    """
    img = np.tile(np.linspace(60, 200, 648), (461, 1)).astype(np.uint8)

    def paint(x: int, y: int, w: int, h: int, rim: int = 6) -> None:
        if rim:
            cv2.rectangle(
                img, (x - rim, y - rim), (x + w + rim, y + h + rim), 10, -1
            )
        cv2.rectangle(img, (x, y), (x + w, y + h), 250, -1)

    return img, paint


@pytest.fixture
def sample_annotation() -> FrameAnnotation:
    """Create a FrameAnnotation with 3 crystals."""
    return FrameAnnotation(
        frame_idx=0,
        timestamp_s=0.0,
        crystals=[
            CrystalAnnotation(
                crystal_id="crystal_001",
                bbox=BoundingBox(x=125, y=120, width=50, height=40),
                layer=DepthLayer.FAR,
                crystal_system=CrystalSystem.CUBIC,
            ),
            CrystalAnnotation(
                crystal_id="crystal_002",
                bbox=BoundingBox(x=340, y=230, width=80, height=60),
                layer=DepthLayer.MID,
            ),
            CrystalAnnotation(
                crystal_id="crystal_003",
                bbox=BoundingBox(x=470, y=365, width=40, height=30),
                layer=DepthLayer.NEAR,
            ),
        ],
        summary="3 crystals at different depths",
        layer_counts={
            DepthLayer.FAR: 1,
            DepthLayer.MID: 1,
            DepthLayer.NEAR: 1,
        },
    )
