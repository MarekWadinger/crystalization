"""CLI entry points for crystal analysis tools."""

from __future__ import annotations

import argparse
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np

from annotator.depth import (
    compute_depth_map,
    extract_layer_mask,
    segment_layers,
)
from annotator.detection import detect_crystals_in_layer
from annotator.flow import compute_flow_magnitude
from annotator.io import (
    fmt_duration,
    load_detections,
    print_progress,
    process_video,
    write_csv,
    write_detailed_csv,
)
from annotator.sharpness import compute_sharpness_map
from annotator.types import (
    Crystal,
    Detection,
    FrameResult,
    LayerConfig,
    Mat,
)
from annotator.viz import (
    LAYER_COLORS,
    add_label,
    annotate_frame,
    colorize_layers,
    colorize_map,
    downscale,
    draw_crystals,
    draw_legend,
    draw_stats,
)


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add detection parameters shared by analyze and visualize CLIs."""
    parser.add_argument(
        "-n",
        "--num-layers",
        type=int,
        default=3,
        help="Number of depth layers (default: 3)",
    )
    parser.add_argument(
        "--sharpness-weight",
        type=float,
        default=0.6,
        help="Weight for sharpness in depth map (default: 0.6)",
    )
    parser.add_argument(
        "--flow-weight",
        type=float,
        default=0.4,
        help="Weight for optical flow in depth map (default: 0.4)",
    )
    parser.add_argument(
        "--edge-block-size",
        type=int,
        default=11,
        help="Adaptive threshold block size (default: 11)",
    )
    parser.add_argument(
        "--edge-c",
        type=int,
        default=2,
        help="Threshold C constant (default: 2)",
    )
    parser.add_argument(
        "--morph-base",
        type=int,
        default=3,
        help="Morph kernel base size for far layer (default: 3)",
    )
    parser.add_argument(
        "--morph-scale",
        type=int,
        default=4,
        help="Morph kernel per-layer increment (default: 4)",
    )
    parser.add_argument(
        "--min-area",
        type=float,
        default=50.0,
        help="Min crystal area in px² (default: 50)",
    )
    parser.add_argument(
        "--max-area",
        type=float,
        default=50000.0,
        help="Max crystal area in px² (default: 50000)",
    )
    parser.add_argument(
        "--max-aspect-ratio",
        type=float,
        default=4.0,
        help="Max aspect ratio, reject noodles (default: 4.0)",
    )


def _config_from_args(args: argparse.Namespace) -> LayerConfig:
    """Build LayerConfig from parsed CLI args."""
    return LayerConfig(
        num_layers=args.num_layers,
        sharpness_weight=args.sharpness_weight,
        flow_weight=args.flow_weight,
        edge_block_size=args.edge_block_size,
        edge_c=args.edge_c,
        morph_base=args.morph_base,
        morph_scale=args.morph_scale,
        min_area=args.min_area,
        max_area=args.max_area,
        max_aspect_ratio=args.max_aspect_ratio,
    )


def _print_summary(
    results: list[FrameResult],
    output: Path,
    num_layers: int,
) -> None:
    """Print per-layer crystal summary after analysis."""
    total_crystals = sum(lr.count for fr in results for lr in fr.layers)
    layer_totals: Counter[int] = Counter()
    for fr in results:
        for lr in fr.layers:
            layer_totals[lr.layer_id] += lr.count

    print(f"  Frames analyzed: {len(results)}")
    print(f"  Total crystals: {total_crystals}")
    for layer_id in range(num_layers):
        print(f"    Layer {layer_id}: {layer_totals.get(layer_id, 0)}")
    print(f"  Output: {output}")


def main_analyze() -> None:
    """CLI entry point for crystal video analysis."""
    parser = argparse.ArgumentParser(
        description="Crystal video layer decomposition and detection"
    )
    parser.add_argument("video", type=Path, help="Path to input video file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("crystal_stats.csv"),
        help="Output CSV path (default: crystal_stats.csv)",
    )
    parser.add_argument(
        "--detailed",
        type=Path,
        default=None,
        help="Output detailed per-crystal CSV",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=0,
        help="Max frames to process (0 = all)",
    )
    parser.add_argument(
        "--frame-skip",
        type=int,
        default=1,
        help="Process every Nth frame (default: 1)",
    )
    _add_common_args(parser)

    args = parser.parse_args()
    config = _config_from_args(args)

    if not args.video.exists():
        print(f"Error: video not found: {args.video}", file=sys.stderr)
        sys.exit(1)

    results = process_video(
        args.video,
        config,
        max_frames=args.max_frames,
        frame_skip=args.frame_skip,
    )

    write_csv(results, args.output)
    if args.detailed is not None:
        write_detailed_csv(results, args.detailed)

    _print_summary(results, args.output, config.num_layers)


def main_visualize() -> None:
    """CLI entry point for crystal video visualization."""
    parser = argparse.ArgumentParser(
        description="Visualize crystal detection pipeline as annotated video"
    )
    parser.add_argument("video", type=Path, help="Path to input video file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("crystal_viz.mp4"),
        help="Output video path (default: crystal_viz.mp4)",
    )
    parser.add_argument(
        "-w",
        "--width",
        type=int,
        default=1920,
        help="Output video width in pixels (default: 1920)",
    )
    parser.add_argument(
        "--process-size",
        type=int,
        default=960,
        help="Max dimension for processing (default: 960, 0 = no downscale)",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=0,
        help="Max frames to process (0 = all)",
    )
    parser.add_argument(
        "--frame-skip",
        type=int,
        default=1,
        help="Process every Nth frame (default: 1)",
    )
    _add_common_args(parser)

    args = parser.parse_args()
    config = _config_from_args(args)

    if not args.video.exists():
        print(f"Error: video not found: {args.video}", file=sys.stderr)
        sys.exit(1)

    proc_size = args.process_size if args.process_size > 0 else 999999
    _run_visualize(
        args.video,
        args.output,
        config,
        args.width,
        proc_size,
        args.max_frames,
        args.frame_skip,
    )


def _build_viz_panel(
    color_small: Mat,
    gray_small: Mat,
    prev_gray_small: Mat | None,
    config: LayerConfig,
    frame_idx: int,
    total_frames: int,
    panel_w: int,
) -> Mat:
    """Build a 2x2 panel showing all pipeline stages."""
    sharpness = compute_sharpness_map(gray_small, config.blur_kernel)

    if prev_gray_small is not None:
        flow_mag = compute_flow_magnitude(prev_gray_small, gray_small)
    else:
        flow_mag = np.zeros_like(sharpness)

    depth_map = compute_depth_map(sharpness, flow_mag, config)
    layer_map = segment_layers(depth_map, config.num_layers)

    all_crystals: list[tuple[list[Crystal], tuple[int, int, int]]] = []
    layer_counts: list[int] = []
    for layer_id in range(config.num_layers):
        mask = extract_layer_mask(layer_map, layer_id)
        crystals = detect_crystals_in_layer(
            gray_small,
            mask,
            config,
            layer_id=layer_id,
        )
        color = LAYER_COLORS[layer_id % len(LAYER_COLORS)]
        all_crystals.append((crystals, color))
        layer_counts.append(len(crystals))

    half_w = panel_w // 2
    proc_h, proc_w = gray_small.shape[:2]
    out_scale = half_w / proc_w
    half_h = int(proc_h * out_scale)

    annotated: Mat = color_small.copy()
    for crystals_list, col in all_crystals:
        draw_crystals(annotated, crystals_list, col, thickness=1)
    annotated = cv2.resize(annotated, (half_w, half_h))
    draw_legend(annotated, config.num_layers)
    draw_stats(annotated, layer_counts, frame_idx, total_frames)

    sharp_viz = colorize_map(sharpness, cv2.COLORMAP_INFERNO)
    sharp_viz = cv2.resize(sharp_viz, (half_w, half_h))
    add_label(sharp_viz, "Sharpness (Laplacian)")

    flow_viz = colorize_map(flow_mag, cv2.COLORMAP_MAGMA)
    flow_viz = cv2.resize(flow_viz, (half_w, half_h))
    add_label(flow_viz, "Optical Flow")

    layer_viz = colorize_layers(layer_map, config.num_layers)
    layer_viz = cv2.resize(layer_viz, (half_w, half_h))
    add_label(layer_viz, "Depth Layers")

    top = np.hstack([annotated, sharp_viz])
    bottom = np.hstack([flow_viz, layer_viz])
    panel: Mat = np.vstack([top, bottom])
    return panel


def _run_visualize(
    video_path: Path,
    output_path: Path,
    config: LayerConfig,
    width: int,
    proc_size: int,
    max_frames: int,
    frame_skip: int,
) -> None:
    """Render visualization video."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"Error: cannot open video {video_path}", file=sys.stderr)
        sys.exit(1)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    in_fps = cap.get(cv2.CAP_PROP_FPS)
    out_fps = in_fps / frame_skip

    ret, first_frame = cap.read()
    if not ret:
        print("Error: cannot read first frame", file=sys.stderr)
        sys.exit(1)

    orig_h, orig_w = first_frame.shape[:2]
    first_small = downscale(first_frame, proc_size)
    first_gray = cv2.cvtColor(first_small, cv2.COLOR_BGR2GRAY)
    proc_h, proc_w = first_gray.shape[:2]

    sample = _build_viz_panel(
        first_small,
        first_gray,
        None,
        config,
        0,
        total_frames,
        width,
    )
    out_h, out_w = sample.shape[:2]

    expected = total_frames // frame_skip
    if max_frames > 0:
        expected = min(expected, max_frames)

    print(
        f"Input:   {orig_w}x{orig_h}, {total_frames} frames, {in_fps:.1f} fps"
    )
    print(f"Process: {proc_w}x{proc_h} (downscaled for speed)")
    print(f"Output:  {out_w}x{out_h}, {out_fps:.1f} fps -> {output_path}")
    print(f"Rendering {expected} frames")
    print()

    fourcc = cv2.VideoWriter.fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, out_fps, (out_w, out_h))

    writer.write(sample)
    prev_gray: Mat = first_gray
    frame_idx = 1
    processed = 1
    start = time.monotonic()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_skip != 0:
            frame_idx += 1
            continue

        small = downscale(frame, proc_size)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        panel = _build_viz_panel(
            small,
            gray,
            prev_gray,
            config,
            frame_idx,
            total_frames,
            width,
        )
        writer.write(panel)
        prev_gray = gray

        processed += 1
        print_progress(
            processed,
            expected,
            start,
            label=f"(idx={frame_idx})",
        )

        if max_frames > 0 and processed >= max_frames:
            break

        frame_idx += 1

    writer.release()
    cap.release()
    elapsed = time.monotonic() - start
    print(
        f"\nDone: rendered {processed} frames "
        f"to {output_path} in {fmt_duration(elapsed)}"
    )


def main_annotate() -> None:
    """CLI entry point for video annotation from CSV."""
    parser = argparse.ArgumentParser(
        description="Annotate video with crystal detections from CSV"
    )
    parser.add_argument("video", type=Path, help="Path to input video file")
    parser.add_argument("csv", type=Path, help="Path to detailed crystal CSV")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("crystal_annotated.mp4"),
        help="Output video path (default: crystal_annotated.mp4)",
    )
    parser.add_argument(
        "--thickness",
        type=int,
        default=2,
        help="Rectangle line thickness (default: 2)",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=0,
        help="Max frames to write (0 = all)",
    )

    args = parser.parse_args()

    if not args.video.exists():
        print(f"Error: video not found: {args.video}", file=sys.stderr)
        sys.exit(1)
    if not args.csv.exists():
        print(f"Error: CSV not found: {args.csv}", file=sys.stderr)
        sys.exit(1)

    detections = load_detections(args.csv)
    print(f"Loaded detections for {len(detections)} frames from {args.csv}")

    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        print(f"Error: cannot open video {args.video}", file=sys.stderr)
        sys.exit(1)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Video: {width}x{height}, {total_frames} frames, {fps:.1f} fps")

    expected = total_frames
    if args.max_frames > 0:
        expected = min(expected, args.max_frames)
    print(f"Writing {expected} annotated frames")
    print()

    fourcc = cv2.VideoWriter.fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(args.output), fourcc, fps, (width, height))

    frame_idx = 0
    written = 0
    start = time.monotonic()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx in detections:
            annotate_frame(frame, detections[frame_idx], args.thickness)
            _draw_annotate_counts(frame, detections[frame_idx], frame_idx)

        writer.write(frame)
        written += 1
        print_progress(written, expected, start, interval=50)

        if args.max_frames > 0 and written >= args.max_frames:
            break

        frame_idx += 1

    writer.release()
    cap.release()
    elapsed = time.monotonic() - start
    print(
        f"\nDone: {written} frames written "
        f"to {args.output} in {fmt_duration(elapsed)}"
    )


def _draw_annotate_counts(
    frame: Mat,
    detections: list[Detection],
    frame_idx: int,
) -> None:
    """Draw per-layer counts for annotation overlay."""
    counts: dict[int, int] = defaultdict(int)
    for d in detections:
        counts[d.layer] += 1

    x, y = 20, 40
    cv2.putText(
        frame,
        f"Frame {frame_idx}",
        (x, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2,
    )
    y += 30
    total = 0
    for layer_id in sorted(counts):
        color = LAYER_COLORS[layer_id % len(LAYER_COLORS)]
        count = counts[layer_id]
        cv2.putText(
            frame,
            f"L{layer_id}: {count}",
            (x, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            2,
        )
        total += count
        y += 28
    cv2.putText(
        frame,
        f"Total: {total}",
        (x, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
    )
