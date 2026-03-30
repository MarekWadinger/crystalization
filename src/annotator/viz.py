"""Visualization helpers for crystal analysis."""

from __future__ import annotations

import cv2
import numpy as np
from numpy.typing import NDArray

from annotator.depth import normalize
from annotator.types import Crystal, Detection, Mat

# Layer colors (BGR): far (sharp) = blue, mid = green, near (blurry) = red
LAYER_COLORS: list[tuple[int, int, int]] = [
    (255, 150, 50),  # blue-ish (far/sharp)
    (50, 220, 50),  # green (mid)
    (50, 50, 255),  # red (near/blurry)
    (255, 255, 50),  # cyan
    (255, 50, 255),  # magenta
]


def downscale(frame: Mat, max_dim: int) -> Mat:
    """Downscale frame so its largest dimension is at most max_dim."""
    h, w = frame.shape[:2]
    if max(h, w) <= max_dim:
        return frame
    scale = max_dim / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    result: Mat = cv2.resize(
        frame, (new_w, new_h), interpolation=cv2.INTER_AREA
    )
    return result


def colorize_map(
    arr: NDArray[np.float64], colormap: int = cv2.COLORMAP_INFERNO
) -> Mat:
    """Convert a float64 map to a BGR colorized image."""
    norm = normalize(arr)
    gray = (norm * 255).astype(np.uint8)
    colored: Mat = cv2.applyColorMap(gray, colormap)
    return colored


def colorize_layers(layer_map: NDArray[np.int32], num_layers: int) -> Mat:
    """Render layer segmentation as a colored overlay."""
    h, w = layer_map.shape
    overlay = np.zeros((h, w, 3), dtype=np.uint8)
    for layer_id in range(num_layers):
        color = LAYER_COLORS[layer_id % len(LAYER_COLORS)]
        mask = layer_map == layer_id
        overlay[mask] = color
    return overlay


def draw_crystals(
    frame: Mat,
    crystals: list[Crystal],
    color: tuple[int, int, int],
    *,
    thickness: int = 2,
) -> None:
    """Draw oriented bounding rectangles for detected crystals (in-place)."""
    for c in crystals:
        rect = ((c.x, c.y), (c.width, c.height), c.angle)
        box = cv2.boxPoints(rect)
        box_int = box.astype(np.int32)
        cv2.drawContours(frame, [box_int], 0, color, thickness)


def draw_cross(
    frame: Mat,
    x: int,
    y: int,
    size: int,
    color: tuple[int, int, int],
    thickness: int,
) -> None:
    """Draw a cross marker at (x, y)."""
    cv2.line(
        frame, (x - size, y - size), (x + size, y + size), color, thickness
    )
    cv2.line(
        frame, (x - size, y + size), (x + size, y - size), color, thickness
    )


def draw_legend(frame: Mat, num_layers: int) -> None:
    """Draw a layer color legend on the frame."""
    labels = ["far/sharp", "mid", "near/blurry", "layer 3", "layer 4"]
    x = 20
    y_start = 40
    line_h = 30
    box_size = 16

    for i in range(num_layers):
        y = y_start + i * line_h
        color = LAYER_COLORS[i % len(LAYER_COLORS)]
        label = labels[i] if i < len(labels) else f"layer {i}"
        cv2.rectangle(frame, (x, y - box_size), (x + box_size, y), color, -1)
        cv2.putText(
            frame,
            label,
            (x + box_size + 8, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
        )


def draw_stats(
    frame: Mat,
    layer_counts: list[int],
    frame_idx: int,
    total_frames: int,
) -> None:
    """Draw crystal count stats on the frame."""
    h = frame.shape[0]
    x = 20
    line_h = 25

    y = h - 20 - len(layer_counts) * line_h
    cv2.putText(
        frame,
        f"Frame {frame_idx}/{total_frames}",
        (x, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2,
    )
    y += line_h
    total = 0
    for i, count in enumerate(layer_counts):
        color = LAYER_COLORS[i % len(LAYER_COLORS)]
        cv2.putText(
            frame,
            f"L{i}: {count} crystals",
            (x, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
        )
        total += count
        y += line_h
    cv2.putText(
        frame,
        f"Total: {total}",
        (x, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2,
    )


def add_label(frame: Mat, text: str) -> None:
    """Add a title label to a panel."""
    cv2.putText(
        frame,
        text,
        (11, 26),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 0, 0),
        3,
    )
    cv2.putText(
        frame,
        text,
        (10, 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
    )


def annotate_frame(
    frame: Mat,
    detections: list[Detection],
    thickness: int,
) -> None:
    """Draw oriented rectangles for all detections on frame (in-place)."""
    for d in detections:
        color = LAYER_COLORS[d.layer % len(LAYER_COLORS)]
        rect = ((d.x, d.y), (d.width, d.height), d.angle)
        box = cv2.boxPoints(rect)
        box_int = box.astype(np.int32)
        cv2.drawContours(frame, [box_int], 0, color, thickness)


def bgr_to_rgb(img: Mat) -> Mat:
    """Convert BGR image to RGB for display in web UIs."""
    result: Mat = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return result
