"""Depth map computation and layer segmentation."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from annotator.types import LayerConfig


def normalize(arr: NDArray[np.float64]) -> NDArray[np.float64]:
    """Min-max normalize to [0, 1]."""
    mn = arr.min()
    mx = arr.max()
    if mx - mn < 1e-10:
        return np.zeros_like(arr)
    result: NDArray[np.float64] = (arr - mn) / (mx - mn)
    return result


def compute_depth_map(
    sharpness: NDArray[np.float64],
    flow_mag: NDArray[np.float64],
    config: LayerConfig,
) -> NDArray[np.float64]:
    """Combine sharpness and flow into a depth score.

    Higher score = closer to camera (blurry + fast).
    Lower score = further from camera (sharp + slow).

    We invert sharpness so that low-sharpness (blurry) = high depth score.
    """
    inv_sharpness = 1.0 - normalize(sharpness)
    norm_flow = normalize(flow_mag)
    depth: NDArray[np.float64] = (
        config.sharpness_weight * inv_sharpness
        + config.flow_weight * norm_flow
    )
    return depth


def segment_layers(
    depth_map: NDArray[np.float64], num_layers: int
) -> NDArray[np.int32]:
    """Segment depth map into discrete layers via uniform quantization."""
    norm = normalize(depth_map)
    layers: NDArray[np.int32] = np.clip(
        (norm * num_layers).astype(np.int32), 0, num_layers - 1
    )
    return layers


def extract_layer_mask(
    layer_map: NDArray[np.int32], layer_id: int
) -> NDArray[np.uint8]:
    """Get binary mask for a specific layer."""
    mask: NDArray[np.uint8] = (layer_map == layer_id).astype(np.uint8) * 255
    return mask
