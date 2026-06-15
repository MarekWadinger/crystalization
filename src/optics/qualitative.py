"""Qualitative figures: detection overlay and sharpness-layer decomposition.

Produces two illustrative figures from a single frame of the plant video:

* ``11_detection_overlay.png`` — a single frame with every detected crystal's
  rotated bounding rectangle drawn, coloured by its layer assignment, plus a
  legend and title summarising the count.
* ``12_sharpness_layers.png`` — a 2x2 matplotlib grid showing how the layer
  decomposition is built: original frame, per-pixel sharpness map, the
  three-layer segmentation overlay, and the resulting detections.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import matplotlib.pyplot as plt

from annotator.detection import process_frame
from annotator.sharpness import compute_sharpness_map
from annotator.types import LayerConfig, Mat
from annotator.viz import (
    LAYER_COLORS,
    bgr_to_rgb,
    colorize_layers,
    colorize_map,
    draw_crystals,
    draw_legend,
)
from optics.video_io import DEFAULT_CROP, CropBox

VIDEO_PATH = "datasets/2026-02-05 10-36-32.mp4"
FRAME_IDX = 750


def _read_cropped_bgr(video_path: str, frame_idx: int, crop: CropBox) -> Mat:
    """Read ``frame_idx`` from the video, applying ``crop``."""
    cap = cv2.VideoCapture(video_path)
    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_idx))
        ret, frame = cap.read()
    finally:
        cap.release()
    if not ret:
        raise RuntimeError(
            f"Failed to read frame {frame_idx} from {video_path}"
        )
    return crop.apply(frame)


def fig_detection_overlay(
    video_path: str,
    frame_idx: int,
    out_path: Path,
    config: LayerConfig,
    crop: CropBox = DEFAULT_CROP,
) -> int:
    """Render detections coloured by layer onto a single frame.

    Returns the total number of crystal bounding rectangles drawn.
    """
    frame = _read_cropped_bgr(video_path, frame_idx, crop)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    frame_result, _ = process_frame(gray, None, frame_idx, config)

    overlay = frame.copy()
    n_total = 0
    for layer in frame_result.layers:
        color = LAYER_COLORS[layer.layer_id % len(LAYER_COLORS)]
        draw_crystals(overlay, layer.crystals, color, thickness=2)
        n_total += layer.count

    draw_legend(overlay, config.num_layers)

    title = (
        f"Frame {frame_idx}: {n_total} detections across "
        f"{config.num_layers} layers"
    )
    h, w = overlay.shape[:2]
    (text_w, _), _ = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    x = max(10, w - text_w - 20)
    y = 35
    cv2.putText(
        overlay,
        title,
        (x + 1, y + 1),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 0, 0),
        3,
    )
    cv2.putText(
        overlay,
        title,
        (x, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), overlay)
    return n_total


def fig_sharpness_layers(
    video_path: str,
    frame_idx: int,
    out_path: Path,
    config: LayerConfig,
    crop: CropBox = DEFAULT_CROP,
) -> None:
    """Four-panel decomposition: frame, sharpness, layers, detections."""
    frame = _read_cropped_bgr(video_path, frame_idx, crop)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    frame_result, layer_map = process_frame(gray, None, frame_idx, config)

    sharpness = compute_sharpness_map(gray, config.blur_kernel)
    sharp_bgr = colorize_map(sharpness)
    layers_bgr = colorize_layers(layer_map, config.num_layers)
    blended = cv2.addWeighted(frame, 0.5, layers_bgr, 0.5, 0.0)

    detections = frame.copy()
    for layer in frame_result.layers:
        color = LAYER_COLORS[layer.layer_id % len(LAYER_COLORS)]
        draw_crystals(detections, layer.crystals, color, thickness=2)

    fig, axes = plt.subplots(2, 2, figsize=(12, 8), dpi=180)
    panels: list[tuple[Mat, str]] = [
        (frame, "Original frame"),
        (sharp_bgr, "Sharpness map (log Laplacian variance)"),
        (blended, "3-layer segmentation (50% overlay)"),
        (detections, "Detections by layer"),
    ]
    for ax, (img, label) in zip(axes.flat, panels, strict=True):
        ax.imshow(bgr_to_rgb(img))
        ax.set_title(label, fontsize=11)
        ax.axis("off")

    fig.suptitle(
        f"Sharpness-layer decomposition - frame {frame_idx}",
        fontsize=13,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    """Generate both qualitative figures from frame 750."""
    config = LayerConfig(
        num_layers=3,
        sharpness_weight=0.7,
        flow_weight=0.3,
        blur_kernel=15,
        min_area=80.0,
        max_area=8000.0,
        max_aspect_ratio=3.0,
    )
    out_dir = Path("docs/optics/figures")
    overlay_path = out_dir / "11_detection_overlay.png"
    layers_path = out_dir / "12_sharpness_layers.png"

    print(f"Rendering detection overlay for frame {FRAME_IDX}...")
    n = fig_detection_overlay(VIDEO_PATH, FRAME_IDX, overlay_path, config)
    print(f"  drew {n} detections -> {overlay_path}")

    print(f"Rendering sharpness-layer decomposition for frame {FRAME_IDX}...")
    fig_sharpness_layers(VIDEO_PATH, FRAME_IDX, layers_path, config)
    print(f"  wrote {layers_path}")

    for p in (overlay_path, layers_path):
        size_kb = p.stat().st_size / 1024.0
        print(f"  {p}: {size_kb:.1f} KB")


if __name__ == "__main__":
    main()
