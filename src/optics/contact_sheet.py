"""Visual QA contact sheet of crystal detections across six video frames.

Produces a single PNG laying out six annotated frames in a 2×3 grid so a
reader can eyeball **what the detector found and what it missed**. Each
crystal is drawn as a rotated bounding rectangle coloured by its layer
assignment with a sequential index and apparent-size label next to it.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from annotator.detection import process_frame
from annotator.types import FrameResult, LayerConfig, Mat
from annotator.viz import LAYER_COLORS
from optics.config import (
    detection_area_px,
    lens_from_config_and_video,
    load_camera,
)
from optics.model import LensSetup, mm_per_pixel_at
from optics.video_io import DEFAULT_CROP, CropBox


def annotate_frame(
    frame_bgr: np.ndarray,
    frame_result: FrameResult,
    mm_per_px_at_focus: float,
    *,
    draw_indices: bool = True,
) -> Mat:
    """Draw rotated rects and labels for every crystal in ``frame_result``."""
    out: Mat = frame_bgr.copy()
    idx = 0
    total = 0
    for layer in frame_result.layers:
        total += len(layer.crystals)
    for layer in frame_result.layers:
        color = LAYER_COLORS[layer.layer_id % len(LAYER_COLORS)]
        for cry in layer.crystals:
            rect = ((cry.x, cry.y), (cry.width, cry.height), cry.angle)
            box = cv2.boxPoints(rect).astype(np.int32)
            cv2.drawContours(out, [box], 0, color, 2)
            if draw_indices:
                label = f"{idx} ({int(cry.size)}px)"
                org = (int(cry.x) + 4, int(cry.y) - 4)
                cv2.putText(
                    out,
                    label,
                    org,
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (0, 0, 0),
                    2,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    out,
                    label,
                    org,
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA,
                )
            idx += 1

    header = f"frame {frame_result.frame_idx}: {total} detections"
    _stroked_text(out, header, (15, 40), 0.9, 2)

    scale_txt = f"scale: {mm_per_px_at_focus * 1000:.2f} um/px at d_focus"
    (tw, _), _ = cv2.getTextSize(scale_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
    _stroked_text(out, scale_txt, (out.shape[1] - tw - 15, 30), 0.55, 1)
    return out


def _stroked_text(
    img: Mat, text: str, org: tuple[int, int], scale: float, thickness: int
) -> None:
    cv2.putText(
        img,
        text,
        org,
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        (0, 0, 0),
        thickness + 2,
        cv2.LINE_AA,
    )
    cv2.putText(
        img,
        text,
        org,
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        (255, 255, 255),
        thickness,
        cv2.LINE_AA,
    )


def _resize_to_width(img: Mat, target_w: int) -> Mat:
    h, w = img.shape[:2]
    if w == target_w:
        return img
    scale = target_w / w
    new_h = int(round(h * scale))
    result: Mat = cv2.resize(
        img, (target_w, new_h), interpolation=cv2.INTER_AREA
    )
    return result


def build_contact_sheet(
    video_path: str,
    frame_indices: list[int],
    out_path: Path,
    config: LayerConfig,
    lens: LensSetup,
    d_focus: float,
    *,
    crop: CropBox = DEFAULT_CROP,
) -> dict[str, int]:
    """Render annotated detections on ``frame_indices`` into a 2×3 grid PNG."""
    if len(frame_indices) != 6:
        raise ValueError(
            f"frame_indices must have exactly 6 entries, got {len(frame_indices)}"
        )

    mm_per_px = float(mm_per_pixel_at(lens, d_focus, np.array([d_focus]))[0])

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_path}")

    panels: list[Mat] = []
    counts: dict[str, int] = {}
    prev_gray: np.ndarray | None = None
    target_w = 960
    for idx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ret, frame = cap.read()
        if not ret:
            raise RuntimeError(f"Failed to read frame {idx} from {video_path}")
        cropped = crop.apply(frame)
        gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
        frame_result, _ = process_frame(gray, prev_gray, idx, config)
        annotated = annotate_frame(cropped, frame_result, mm_per_px)
        panels.append(_resize_to_width(annotated, target_w))
        total = sum(len(layer.crystals) for layer in frame_result.layers)
        counts[f"frame_{idx}"] = total
        prev_gray = gray
    cap.release()

    border = 8
    bordered = [
        cv2.copyMakeBorder(
            p,
            border,
            border,
            border,
            border,
            cv2.BORDER_CONSTANT,
            value=(0, 0, 0),
        )
        for p in panels
    ]
    row1 = cv2.hconcat(bordered[0:3])
    row2 = cv2.hconcat(bordered[3:6])
    sheet: Mat = cv2.vconcat([row1, row2])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    ok = cv2.imwrite(str(out_path), sheet)
    if not ok:
        raise RuntimeError(f"cv2.imwrite failed for {out_path}")

    counts["total"] = sum(
        v for k, v in counts.items() if k.startswith("frame_")
    )
    return counts


def main() -> None:
    """Build the detection contact sheet for the plant video."""
    cfg = load_camera()
    lens = lens_from_config_and_video(cfg, "datasets/2026-02-05 10-36-32.mp4")
    min_area, max_area = detection_area_px(cfg, lens)
    config = LayerConfig(
        num_layers=3,
        sharpness_weight=0.7,
        flow_weight=0.3,
        blur_kernel=15,
        min_area=min_area,
        max_area=max_area,
        max_aspect_ratio=3.0,
    )
    d_focus = cfg.focus_object_distance_mm
    frame_indices = [100, 370, 640, 910, 1180, 1450]
    out_path = Path("docs/optics/figures/16_detection_contact.png")

    counts = build_contact_sheet(
        "datasets/2026-02-05 10-36-32.mp4",
        frame_indices,
        out_path,
        config,
        lens,
        d_focus,
    )

    print("=== Per-frame detection counts ===")
    for idx in frame_indices:
        print(f"  frame {idx:5d}: {counts[f'frame_{idx}']}")
    print(f"  total       : {counts['total']}")
    size_kb = out_path.stat().st_size / 1024.0
    print(f"\nWrote {out_path} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
