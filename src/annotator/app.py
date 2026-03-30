"""Interactive crystal detection tuning app using Gradio."""

from __future__ import annotations

from typing import Any

import cv2
import gradio as gr
import numpy as np
from numpy.typing import NDArray

from annotator.depth import (
    compute_depth_map,
    extract_layer_mask,
    segment_layers,
)
from annotator.detection import detect_crystals_in_layer
from annotator.flow import compute_flow_magnitude
from annotator.sharpness import compute_sharpness_map
from annotator.types import LayerConfig, Mat
from annotator.viz import (
    LAYER_COLORS,
    bgr_to_rgb,
    colorize_layers,
    colorize_map,
    downscale,
    draw_crystals,
    draw_legend,
    draw_stats,
)


def _read_frame(video_path: str, frame_idx: int) -> Mat | None:
    """Seek to a specific frame and read it."""
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return None
    return frame


def _get_frame_count(video_path: str) -> int:
    """Get total frame count for a video."""
    cap = cv2.VideoCapture(video_path)
    count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return count


def on_video_load(
    video_path: str,
) -> dict[str, Any]:
    """When a video is uploaded, update the frame slider range."""
    if not video_path:
        return gr.update(maximum=0, value=0)
    count = _get_frame_count(video_path)
    return gr.update(maximum=max(0, count - 1), value=0)


def process_single_frame(
    video_path: str,
    frame_idx: int,
    process_size: int,
    num_layers: int,
    sharpness_weight: float,
    blur_kernel: int,
    edge_block_size: int,
    edge_c: int,
    morph_base: int,
    morph_scale: int,
    min_area: float,
    max_area: float,
    max_aspect_ratio: float,
) -> tuple[
    NDArray[np.uint8] | None,
    NDArray[np.uint8] | None,
    NDArray[np.uint8] | None,
    NDArray[np.uint8] | None,
    str,
]:
    """Run the full pipeline on a single frame and return 4 panel images + stats."""
    if not video_path:
        return None, None, None, None, "No video loaded"

    blur_kernel = blur_kernel | 1

    config = LayerConfig(
        num_layers=num_layers,
        sharpness_weight=sharpness_weight,
        flow_weight=1.0 - sharpness_weight,
        blur_kernel=blur_kernel,
        edge_block_size=edge_block_size,
        edge_c=edge_c,
        morph_base=morph_base,
        morph_scale=morph_scale,
        min_area=min_area,
        max_area=max_area,
        max_aspect_ratio=max_aspect_ratio,
    )

    frame = _read_frame(video_path, frame_idx)
    if frame is None:
        return None, None, None, None, "Cannot read frame"

    prev_frame = (
        _read_frame(video_path, frame_idx - 1) if frame_idx > 0 else None
    )

    small = downscale(frame, process_size)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

    prev_gray: Mat | None = None
    if prev_frame is not None:
        prev_small = downscale(prev_frame, process_size)
        prev_gray = cv2.cvtColor(prev_small, cv2.COLOR_BGR2GRAY)

    # Pipeline
    sharpness = compute_sharpness_map(gray, config.blur_kernel)
    flow_mag = (
        compute_flow_magnitude(prev_gray, gray)
        if prev_gray is not None
        else np.zeros_like(sharpness)
    )
    depth_map = compute_depth_map(sharpness, flow_mag, config)
    layer_map = segment_layers(depth_map, config.num_layers)

    # Detect crystals per layer
    layer_counts: list[int] = []
    annotated: Mat = small.copy()
    stats_lines: list[str] = []
    total_count = 0

    for lid in range(config.num_layers):
        mask = extract_layer_mask(layer_map, lid)
        crystals = detect_crystals_in_layer(gray, mask, config, layer_id=lid)
        color = LAYER_COLORS[lid % len(LAYER_COLORS)]
        draw_crystals(annotated, crystals, color, thickness=1)
        layer_counts.append(len(crystals))
        total_count += len(crystals)

        mean_sz = (
            float(np.mean([c.size for c in crystals])) if crystals else 0.0
        )
        stats_lines.append(
            f"Layer {lid}: {len(crystals)} crystals, mean size {mean_sz:.1f}px"
        )

    total_frames = _get_frame_count(video_path)
    draw_legend(annotated, config.num_layers)
    draw_stats(annotated, layer_counts, frame_idx, total_frames)

    panel_detect = bgr_to_rgb(annotated)
    panel_sharp = bgr_to_rgb(colorize_map(sharpness, cv2.COLORMAP_INFERNO))
    panel_flow = bgr_to_rgb(colorize_map(flow_mag, cv2.COLORMAP_MAGMA))
    panel_layers = bgr_to_rgb(colorize_layers(layer_map, config.num_layers))

    stats_text = (
        f"Frame {frame_idx}/{total_frames} | "
        f"Processing at {gray.shape[1]}x{gray.shape[0]}\n"
        + "\n".join(stats_lines)
        + f"\nTotal: {total_count} crystals"
    )

    return panel_detect, panel_sharp, panel_flow, panel_layers, stats_text


def build_app() -> gr.Blocks:
    """Build the Gradio app interface."""
    with gr.Blocks(title="Crystal Detector Tuner") as demo:
        gr.Markdown("## Crystal Detection Parameter Tuner")
        gr.Markdown(
            "Detects crystals via dark-edge contours on white background. "
            "Rectangles are fitted per layer with layer-aware morphological closing."
        )

        with gr.Row():
            video_input = gr.Video(label="Input Video")

        with gr.Row():
            frame_slider = gr.Slider(
                0,
                100,
                value=0,
                step=1,
                label="Frame",
            )
            process_size = gr.Slider(
                240,
                1920,
                value=480,
                step=40,
                label="Process Size (px)",
            )

        gr.Markdown("### Layer Decomposition")
        with gr.Row():
            num_layers = gr.Slider(
                2,
                6,
                value=3,
                step=1,
                label="Number of Layers",
            )
            sharpness_weight = gr.Slider(
                0.0,
                1.0,
                value=0.6,
                step=0.05,
                label="Sharpness Weight (flow = 1 - this)",
            )
            blur_kernel = gr.Slider(
                3,
                31,
                value=15,
                step=2,
                label="Blur Kernel Size",
            )

        gr.Markdown("### Edge Detection")
        with gr.Row():
            edge_block_size = gr.Slider(
                3,
                51,
                value=11,
                step=2,
                label="Adaptive Threshold Block Size",
            )
            edge_c = gr.Slider(
                -10,
                20,
                value=2,
                step=1,
                label="Threshold C (higher = fewer edges)",
            )

        gr.Markdown("### Morphology (connect edges into shapes)")
        with gr.Row():
            morph_base = gr.Slider(
                1,
                15,
                value=3,
                step=1,
                label="Morph Kernel Base (far layer)",
            )
            morph_scale = gr.Slider(
                0,
                10,
                value=4,
                step=1,
                label="Morph Kernel Scale (per layer step)",
            )

        gr.Markdown("### Contour Filtering")
        with gr.Row():
            min_area = gr.Slider(
                1,
                500,
                value=50,
                step=5,
                label="Min Crystal Area (px²)",
            )
            max_area = gr.Slider(
                500,
                2000,
                value=1000,
                step=100,
                label="Max Crystal Area (px²)",
            )
            max_aspect_ratio = gr.Slider(
                1.5,
                10.0,
                value=4.0,
                step=0.5,
                label="Max Aspect Ratio (reject noodles)",
            )

        with gr.Row():
            with gr.Column():
                img_detect = gr.Image(label="Detections")
            with gr.Column():
                img_sharp = gr.Image(label="Sharpness Map")
        with gr.Row():
            with gr.Column():
                img_flow = gr.Image(label="Optical Flow")
            with gr.Column():
                img_layers = gr.Image(label="Depth Layers")

        stats_box = gr.Textbox(label="Stats", lines=6, interactive=False)

        video_input.change(
            on_video_load,
            inputs=[video_input],
            outputs=[frame_slider],
        )

        all_inputs = [
            video_input,
            frame_slider,
            process_size,
            num_layers,
            sharpness_weight,
            blur_kernel,
            edge_block_size,
            edge_c,
            morph_base,
            morph_scale,
            min_area,
            max_area,
            max_aspect_ratio,
        ]
        all_outputs = [img_detect, img_sharp, img_flow, img_layers, stats_box]

        for inp in all_inputs:
            inp.change(
                process_single_frame,
                inputs=all_inputs,
                outputs=all_outputs,
            )

    return demo


def main() -> None:
    """Launch the interactive crystal detection tuner."""
    demo = build_app()
    demo.launch()


if __name__ == "__main__":
    main()
