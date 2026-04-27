"""Visualization utilities for LLM crystal annotations."""

from __future__ import annotations

import json

import cv2
import numpy as np
from numpy.typing import NDArray

from llm_annotator.types import (
    DepthLayer,
    FrameAnnotation,
)

# Layer colours (BGR): far = blue-ish, mid = green, near = red
LAYER_COLORS: dict[DepthLayer, tuple[int, int, int]] = {
    DepthLayer.FAR: (255, 150, 50),
    DepthLayer.MID: (50, 220, 50),
    DepthLayer.NEAR: (50, 50, 255),
}

_LEGEND_LABELS: dict[DepthLayer, str] = {
    DepthLayer.FAR: "far / sharp",
    DepthLayer.MID: "mid",
    DepthLayer.NEAR: "near / blurry",
}


def draw_annotations(
    frame_bgr: NDArray,
    annotation: FrameAnnotation,
    *,
    thickness: int = 2,
    show_ids: bool = True,
    show_system: bool = False,
) -> NDArray:
    """Draw crystal bounding boxes coloured by layer.

    Returns a copy of the frame; the original is unchanged.
    """
    out = frame_bgr.copy()

    for crystal in annotation.crystals:
        color = LAYER_COLORS.get(crystal.layer, (200, 200, 200))
        bb = crystal.bbox
        rect = ((bb.x, bb.y), (bb.width, bb.height), bb.angle)
        box = cv2.boxPoints(rect)
        box_int = box.astype(np.int32)
        cv2.drawContours(out, [box_int], 0, color, thickness)

        if show_ids or show_system:
            label_parts: list[str] = []
            if show_ids:
                label_parts.append(crystal.crystal_id)
            if show_system:
                label_parts.append(crystal.crystal_system.value)
            label = " | ".join(label_parts)
            tx = int(bb.x - bb.width / 2)
            ty = int(bb.y - bb.height / 2) - 6
            cv2.putText(
                out,
                label,
                (tx, ty),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                color,
                1,
            )

    return out


def draw_legend(
    frame: NDArray,
    position: str = "top-left",
) -> None:
    """Draw layer colour legend on *frame* (in-place)."""
    box_size = 16
    line_h = 26
    margin = 12
    h, w = frame.shape[:2]

    if position == "top-right":
        x0 = w - 140
    elif position == "bottom-left":
        x0 = margin
    elif position == "bottom-right":
        x0 = w - 140
    else:  # top-left (default)
        x0 = margin

    if position.startswith("bottom"):
        y_start = h - margin - len(LAYER_COLORS) * line_h
    else:
        y_start = margin + line_h

    for i, layer in enumerate(DepthLayer):
        y = y_start + i * line_h
        color = LAYER_COLORS[layer]
        label = _LEGEND_LABELS.get(layer, layer.value)
        cv2.rectangle(
            frame,
            (x0, y - box_size),
            (x0 + box_size, y),
            color,
            -1,
        )
        cv2.putText(
            frame,
            label,
            (x0 + box_size + 6, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
        )


def render_tracking_overlay(
    frame_bgr: NDArray,
    current: FrameAnnotation,
    previous: FrameAnnotation | None,
    *,
    show_trajectories: bool = True,
) -> NDArray:
    """Draw tracking arrows between matched crystals.

    Matches by ``crystal_id`` between *current* and
    *previous*.  Returns a copy of the frame.
    """
    out = draw_annotations(frame_bgr, current)

    if previous is None or not show_trajectories:
        return out

    prev_map = {c.crystal_id: c for c in previous.crystals}
    for crystal in current.crystals:
        prev = prev_map.get(crystal.crystal_id)
        if prev is None:
            continue
        pt1 = (int(prev.bbox.x), int(prev.bbox.y))
        pt2 = (
            int(crystal.bbox.x),
            int(crystal.bbox.y),
        )
        color = LAYER_COLORS.get(crystal.layer, (200, 200, 200))
        cv2.arrowedLine(out, pt1, pt2, color, 2, tipLength=0.25)

    return out


def bgr_to_rgb(img: NDArray) -> NDArray:
    """Convert BGR to RGB for Gradio display."""
    result: NDArray = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return result


def annotation_to_json_str(
    annotation: FrameAnnotation,
) -> str:
    """Format annotation as indented JSON string."""
    return json.dumps(annotation.model_dump(mode="json"), indent=2)
