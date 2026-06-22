"""Video processing and CSV I/O."""

from __future__ import annotations

import csv
import sys
import time
from collections import defaultdict
from pathlib import Path

import cv2

from annotator.detection import process_frame
from annotator.types import Detection, FrameResult, LayerConfig, Mat


def fmt_duration(seconds: float) -> str:
    """Format seconds as a compact duration string."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes}m{secs:02d}s"


def print_progress(
    current: int,
    total: int,
    start: float,
    *,
    label: str = "",
    interval: int = 10,
) -> None:
    """Print a progress line with ETA every *interval* items."""
    if current % interval != 0 and current != total:
        return
    elapsed = time.monotonic() - start
    avg = elapsed / current
    remaining = avg * (total - current)
    parts = [
        f"  Frame {current}/{total}",
        f" {label}" if label else "",
        f" [{fmt_duration(elapsed)} elapsed, "
        f"~{fmt_duration(remaining)} remaining]",
    ]
    print("".join(parts))


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

    expected = total_frames // frame_skip
    if max_frames > 0:
        expected = min(expected, max_frames)
    print(f"Processing {expected} frames (every {frame_skip} frame(s))")
    print()

    results: list[FrameResult] = []
    prev_gray: Mat | None = None
    frame_idx = 0
    processed = 0
    start = time.monotonic()

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
        n_crystals = sum(lr.count for lr in frame_result.layers)
        print_progress(
            processed,
            expected,
            start,
            label=f"(idx={frame_idx}) -- {n_crystals} crystals",
        )

        if max_frames > 0 and processed >= max_frames:
            break

        frame_idx += 1

    cap.release()
    elapsed = time.monotonic() - start
    print(f"\nDone: processed {processed} frames in {fmt_duration(elapsed)}")
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
