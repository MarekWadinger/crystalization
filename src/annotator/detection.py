"""Crystal detection via edge-based contour analysis.

Crystals are white shapes with dark edges on a white background.
Detection strategy per layer:
  1. Adaptive threshold to isolate dark edges
  2. Morphological closing to connect edge fragments into closed contours
     (kernel size scales with layer — thicker for blurry near-layers)
  3. Find contours → fit minimum-area rotated rectangles
  4. Filter by area and aspect ratio (reject noodles, keep squares/rectangles)
"""

from __future__ import annotations

import cv2
import numpy as np
from numpy.typing import NDArray

from annotator.depth import (
    compute_depth_map,
    extract_layer_mask,
    segment_layers,
)
from annotator.flow import compute_flow_magnitude
from annotator.sharpness import compute_sharpness_map
from annotator.types import Crystal, FrameResult, LayerConfig, LayerResult, Mat


def _morph_kernel_for_layer(layer_id: int, config: LayerConfig) -> int:
    """Compute morphological kernel size for a given layer.

    Layer 0 = far/sharp (thin edges) → small kernel.
    Higher layers = near/blurry (thick edges) → larger kernel.
    """
    k = config.morph_base + layer_id * config.morph_scale
    return k | 1  # ensure odd


def detect_crystals_in_layer(
    gray: Mat,
    mask: NDArray[np.uint8],
    config: LayerConfig,
    layer_id: int = 0,
) -> list[Crystal]:
    """Detect crystals within a masked layer region using edge contours."""
    # Apply mask: set non-layer pixels to white (background)
    masked = gray.copy()
    masked[mask == 0] = 255

    # Ensure block_size is odd and >= 3
    block_size = max(3, config.edge_block_size | 1)

    # Adaptive threshold: dark edges become white on black background
    thresh: Mat = cv2.adaptiveThreshold(
        masked,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        block_size,
        config.edge_c,
    )

    # Zero out areas outside layer mask
    thresh[mask == 0] = 0

    # Morphological closing to connect edge fragments into closed shapes.
    # Kernel size is layer-dependent: bigger for blurry near-layers.
    k = _morph_kernel_for_layer(layer_id, config)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    closed: Mat = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    # Find contours
    contours, _ = cv2.findContours(
        closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    crystals: list[Crystal] = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < config.min_area or area > config.max_area:
            continue

        # Need at least 5 points for minAreaRect
        if len(contour) < 5:
            continue

        rect = cv2.minAreaRect(contour)
        (cx, cy), (w, h), angle = rect

        # Normalize so width <= height
        if w > h:
            w, h = h, w
            angle = (angle + 90) % 180

        # Aspect ratio filter: reject noodle shapes
        if min(w, h) < 1e-3:
            continue
        aspect = max(w, h) / min(w, h)
        if aspect > config.max_aspect_ratio:
            continue

        crystals.append(
            Crystal(
                y=float(cy),
                x=float(cx),
                width=float(w),
                height=float(h),
                angle=float(angle),
            )
        )

    return crystals


def process_frame(
    gray: Mat,
    prev_gray: Mat | None,
    frame_idx: int,
    config: LayerConfig,
) -> tuple[FrameResult, NDArray[np.int32]]:
    """Process a single frame: compute layers, detect crystals."""
    sharpness = compute_sharpness_map(gray, config.blur_kernel)

    if prev_gray is not None:
        flow_mag = compute_flow_magnitude(prev_gray, gray)
    else:
        flow_mag = np.zeros_like(sharpness)

    depth_map = compute_depth_map(sharpness, flow_mag, config)
    layer_map = segment_layers(depth_map, config.num_layers)

    frame_result = FrameResult(frame_idx=frame_idx)
    for layer_id in range(config.num_layers):
        mask = extract_layer_mask(layer_map, layer_id)
        crystals = detect_crystals_in_layer(
            gray, mask, config, layer_id=layer_id
        )
        frame_result.layers.append(
            LayerResult(layer_id=layer_id, crystals=crystals)
        )

    return frame_result, layer_map
