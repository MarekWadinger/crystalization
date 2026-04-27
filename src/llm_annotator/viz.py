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


def _layer_counts(
    annotation: FrameAnnotation,
) -> dict[DepthLayer, int]:
    """Return per-layer crystal counts.

    Uses the pre-computed ``layer_counts`` field when
    populated, otherwise derives counts from the crystal
    list.
    """
    if annotation.layer_counts:
        return annotation.layer_counts
    counts: dict[DepthLayer, int] = {}
    for c in annotation.crystals:
        counts[c.layer] = counts.get(c.layer, 0) + 1
    return counts


def _auto_thickness(frame: NDArray) -> int:
    """Compute line thickness from frame dimensions."""
    h, w = frame.shape[:2]
    return max(1, int(min(h, w) / 300))


def _draw_text_with_bg(
    frame: NDArray,
    text: str,
    org: tuple[int, int],
    font: int,
    font_scale: float,
    color: tuple[int, int, int],
    thickness: int,
) -> None:
    """Draw *text* with a dark background rectangle."""
    tx, ty = org
    (tw, th), _ = cv2.getTextSize(text, font, font_scale, thickness)
    cv2.rectangle(
        frame,
        (tx - 2, ty - th - 4),
        (tx + tw + 2, ty + 4),
        (0, 0, 0),
        -1,
    )
    cv2.putText(frame, text, (tx, ty), font, font_scale, color, thickness)


def _draw_crystal_count(
    frame: NDArray,
    annotation: FrameAnnotation,
    thickness: int,
) -> None:
    """Draw crystal count overlay in the bottom-right corner."""
    h, w = frame.shape[:2]
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    margin = 10

    counts = _layer_counts(annotation)
    total = len(annotation.crystals)

    parts = []
    for layer in DepthLayer:
        cnt = counts.get(layer, 0)
        if cnt > 0:
            parts.append(f"{cnt} {layer.value}")
    detail = ", ".join(parts)
    text = f"{total} crystals"
    if detail:
        text += f" ({detail})"

    (tw, th), _ = cv2.getTextSize(text, font, font_scale, thickness)
    tx = w - tw - margin
    ty = h - margin

    # Semi-transparent dark background strip
    overlay = frame.copy()
    cv2.rectangle(
        overlay,
        (tx - 4, ty - th - 6),
        (w, h),
        (0, 0, 0),
        -1,
    )
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, dst=frame)

    cv2.putText(
        frame,
        text,
        (tx, ty),
        font,
        font_scale,
        (255, 255, 255),
        thickness,
    )


def draw_annotations(
    frame_bgr: NDArray,
    annotation: FrameAnnotation,
    *,
    thickness: int = 0,
    show_ids: bool = True,
    show_system: bool = False,
    scale: float = 1.0,
) -> NDArray:
    """Draw crystal bounding boxes coloured by layer.

    Parameters
    ----------
    scale:
        Coordinate multiplier.  When annotations were
        produced at ``process_size`` resolution, pass
        ``original_dim / process_dim`` to draw on the
        original-resolution frame.

    Returns a copy of the frame; the original is unchanged.
    """
    out = frame_bgr.copy()
    effective_thickness = thickness or _auto_thickness(out)
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.4

    for crystal in annotation.crystals:
        color = LAYER_COLORS.get(crystal.layer, (200, 200, 200))
        bb = crystal.bbox
        bx = bb.x * scale
        by = bb.y * scale
        bw = bb.width * scale
        bh = bb.height * scale
        rect = ((bx, by), (bw, bh), bb.angle)
        box = cv2.boxPoints(rect)
        box_int = box.astype(np.int32)
        cv2.drawContours(out, [box_int], 0, color, effective_thickness)

        if show_ids or show_system:
            label_parts: list[str] = []
            if show_ids:
                label_parts.append(crystal.crystal_id)
            if show_system:
                label_parts.append(crystal.crystal_system.value)
            label = " | ".join(label_parts)
            tx = int(bx - bw / 2)
            ty = int(by - bh / 2) - 6
            _draw_text_with_bg(
                out,
                label,
                (tx, ty),
                font,
                font_scale,
                color,
                max(1, effective_thickness // 2),
            )

    draw_legend(out)
    _draw_crystal_count(out, annotation, effective_thickness)
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

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    thickness = 1

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
        _draw_text_with_bg(
            frame,
            label,
            (x0 + box_size + 6, y),
            font,
            font_scale,
            (255, 255, 255),
            thickness,
        )


def render_tracking_overlay(
    frame_bgr: NDArray,
    current: FrameAnnotation,
    previous: FrameAnnotation | None,
    *,
    show_trajectories: bool = True,
    scale: float = 1.0,
) -> NDArray:
    """Draw tracking arrows between matched crystals.

    Parameters
    ----------
    scale:
        Coordinate multiplier applied to all bbox
        coordinates (same semantics as in
        ``draw_annotations``).

    Matches by ``crystal_id`` between *current* and
    *previous*.  Returns a copy of the frame.
    """
    out = draw_annotations(frame_bgr, current, scale=scale)

    if previous is None or not show_trajectories:
        return out

    effective_thickness = _auto_thickness(out)
    prev_map = {c.crystal_id: c for c in previous.crystals}
    for crystal in current.crystals:
        prev = prev_map.get(crystal.crystal_id)
        if prev is None:
            continue
        pt1 = (
            int(prev.bbox.x * scale),
            int(prev.bbox.y * scale),
        )
        pt2 = (
            int(crystal.bbox.x * scale),
            int(crystal.bbox.y * scale),
        )
        color = LAYER_COLORS.get(crystal.layer, (200, 200, 200))
        cv2.arrowedLine(
            out,
            pt1,
            pt2,
            color,
            effective_thickness,
            tipLength=0.25,
        )

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


def annotation_to_summary(
    annotation: FrameAnnotation,
) -> str:
    """Format annotation as human-readable summary."""
    lines = [
        f"Frame {annotation.frame_idx} (t={annotation.timestamp_s:.2f}s)",
    ]
    lines.append(f"Total: {len(annotation.crystals)} crystals")
    counts = _layer_counts(annotation)
    for layer in DepthLayer:
        cnt = counts.get(layer, 0)
        if cnt > 0:
            lines.append(f"  {layer.value}: {cnt}")
    if annotation.summary:
        lines.append(f"\n{annotation.summary}")
    return "\n".join(lines)
