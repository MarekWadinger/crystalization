"""Video processing and CSV I/O."""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

import cv2

from annotator.detection import process_frame
from annotator.types import Detection, FrameResult, LayerConfig, Mat


def process_video(
    video_path: Path,
    config: LayerConfig,
    *,
    max_frames: int = 0,
    frame_skip: int = 1,
) -> list[FrameResult]:
    """Process an entire video file."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"Error: cannot open video {video_path}", file=sys.stderr)
        sys.exit(1)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Video: {width}x{height}, {total_frames} frames, {fps:.1f} fps")

    results: list[FrameResult] = []
    prev_gray: Mat | None = None
    frame_idx = 0
    processed = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_skip != 0:
            frame_idx += 1
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame_result, _ = process_frame(gray, prev_gray, frame_idx, config)
        results.append(frame_result)
        prev_gray = gray

        processed += 1
        if processed % 10 == 0:
            print(
                f"  Processed {processed} frames (frame {frame_idx}/{total_frames})"
            )

        if max_frames > 0 and processed >= max_frames:
            break

        frame_idx += 1

    cap.release()
    print(f"Done: processed {processed} frames")
    return results


def write_csv(results: list[FrameResult], output_path: Path) -> None:
    """Write per-frame, per-layer crystal stats to CSV."""
    with output_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["frame", "layer", "crystal_count", "mean_size"])
        for fr in results:
            for lr in fr.layers:
                writer.writerow(
                    [
                        fr.frame_idx,
                        lr.layer_id,
                        lr.count,
                        f"{lr.mean_size:.2f}",
                    ]
                )
    print(f"Results written to {output_path}")


def write_detailed_csv(results: list[FrameResult], output_path: Path) -> None:
    """Write individual crystal detections to CSV."""
    with output_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "frame",
                "layer",
                "crystal_id",
                "x",
                "y",
                "width",
                "height",
                "angle",
                "area",
            ]
        )
        for fr in results:
            for lr in fr.layers:
                for i, c in enumerate(lr.crystals):
                    writer.writerow(
                        [
                            fr.frame_idx,
                            lr.layer_id,
                            i,
                            f"{c.x:.1f}",
                            f"{c.y:.1f}",
                            f"{c.width:.1f}",
                            f"{c.height:.1f}",
                            f"{c.angle:.1f}",
                            f"{c.area:.1f}",
                        ]
                    )
    print(f"Detailed results written to {output_path}")


def load_detections(csv_path: Path) -> dict[int, list[Detection]]:
    """Load per-frame detections from detailed CSV."""
    by_frame: dict[int, list[Detection]] = defaultdict(list)
    with csv_path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            frame_idx = int(row["frame"])
            by_frame[frame_idx].append(
                Detection(
                    layer=int(row["layer"]),
                    x=float(row["x"]),
                    y=float(row["y"]),
                    width=float(row["width"]),
                    height=float(row["height"]),
                    angle=float(row["angle"]),
                )
            )
    return dict(by_frame)
