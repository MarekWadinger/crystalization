"""Gradio app for LLM-powered crystal annotation."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import gradio as gr
import numpy as np
from numpy.typing import NDArray

from llm_annotator.agent import build_agent
from llm_annotator.io import annotate_video, extract_frames, get_video_info
from llm_annotator.types import AnnotatorConfig, VideoAnnotation
from llm_annotator.viz import (
    annotation_to_json_str,
    bgr_to_rgb,
    draw_annotations,
    render_tracking_overlay,
)


def _on_video_upload(video_path: str) -> str:
    """Populate video info on upload."""
    if not video_path:
        return ""
    info = get_video_info(video_path)
    return (
        f"Frames: {info['frame_count']}  |  "
        f"FPS: {info['fps']:.1f}  |  "
        f"{info['width']}x{info['height']}"
    )


async def _run_annotation(
    video_path: str,
    model_name: str,
    frame_interval: int,
    max_frames: int,
    process_size: int,
    use_classical: bool,
) -> tuple[
    VideoAnnotation | None,
    dict[int, NDArray[np.uint8]],
    dict[str, Any],
    dict[str, Any],
    str,
]:
    """Run the LLM annotation pipeline."""
    if not video_path:
        return (
            None,
            {},
            gr.update(maximum=0, value=0, visible=False),
            gr.update(visible=False),
            "No video loaded.",
        )

    config = AnnotatorConfig(
        model_name=model_name,
        frame_interval=int(frame_interval),
        max_frames=int(max_frames),
        process_size=int(process_size),
        use_classical=use_classical,
    )

    agent = build_agent(config)
    result = await annotate_video(Path(video_path), config, agent)

    # Cache extracted frames to avoid re-reading on each
    # slider change
    raw_frames = extract_frames(Path(video_path), config)
    frame_map: dict[int, NDArray[np.uint8]] = {
        fi: img for fi, _, img in raw_frames
    }

    n_frames = len(result.frames)
    total_crystals = sum(len(f.crystals) for f in result.frames)

    status = (
        f"Done. Annotated {n_frames} frames, {total_crystals} crystals found."
    )

    slider_max = max(0, n_frames - 1)

    return (
        result,
        frame_map,
        gr.update(
            maximum=slider_max,
            value=0,
            visible=True,
        ),
        gr.update(visible=True),
        status,
    )


def _update_frame_display(
    annotation_state: VideoAnnotation | None,
    frame_map_state: dict[int, NDArray[np.uint8]],
    frame_slider: int,
) -> tuple[
    NDArray[np.uint8] | None,
    NDArray[np.uint8] | None,
    str,
    str,
]:
    """Update the frame display when the slider changes."""
    if annotation_state is None or not frame_map_state:
        return None, None, "", ""

    result = annotation_state
    idx = int(frame_slider)

    if idx < 0 or idx >= len(result.frames):
        return None, None, "", ""

    frame_ann = result.frames[idx]

    raw_frame = frame_map_state.get(frame_ann.frame_index)
    if raw_frame is None:
        return None, None, "Frame not found in video.", ""

    annotated = draw_annotations(raw_frame.copy(), frame_ann)
    annotated_rgb = bgr_to_rgb(annotated)

    tracking_rgb = None
    if idx > 0:
        prev_ann = result.frames[idx - 1]
        prev_frame = frame_map_state.get(prev_ann.frame_index)
        if prev_frame is not None:
            overlay = render_tracking_overlay(
                raw_frame.copy(), frame_ann, prev_ann
            )
            tracking_rgb = bgr_to_rgb(overlay)

    summary = (
        f"Frame {frame_ann.frame_index} "
        f"(t={frame_ann.timestamp:.2f}s): "
        f"{len(frame_ann.crystals)} crystals"
    )
    details = annotation_to_json_str(frame_ann)

    return annotated_rgb, tracking_rgb, summary, details


def _prepare_download(
    annotation_state: VideoAnnotation | None,
) -> str | None:
    """Write annotation JSON to a temp file for download."""
    if annotation_state is None:
        return None

    tmp = tempfile.NamedTemporaryFile(
        suffix=".json",
        prefix="llm_annotations_",
        delete=False,
    )
    tmp.write(annotation_state.model_dump_json(indent=2).encode())
    tmp.close()
    return tmp.name


def build_app() -> gr.Blocks:
    """Build the Gradio interface."""
    with gr.Blocks(title="LLM Crystal Annotator") as app:
        gr.Markdown("# LLM Crystal Annotator")

        annotation_state = gr.State(value=None)
        frame_map_state = gr.State(value={})

        # --- Phase 1: Configuration ---
        with gr.Row():
            with gr.Column(scale=1):
                video = gr.Video(label="Input Video")
                video_info = gr.Textbox(
                    label="Video Info",
                    interactive=False,
                )
            with gr.Column(scale=1):
                gr.Markdown("### Configuration")
                model_name = gr.Textbox(
                    label="Model",
                    value="openai:gpt-4o",
                )
                frame_interval = gr.Slider(
                    1,
                    100,
                    value=30,
                    step=1,
                    label="Frame interval",
                )
                max_frames = gr.Slider(
                    0,
                    50,
                    value=0,
                    step=1,
                    label="Max frames (0 = all)",
                )
                process_size = gr.Slider(
                    240,
                    1920,
                    value=960,
                    step=40,
                    label="Process size (px)",
                )
                use_classical = gr.Checkbox(
                    value=True,
                    label="Include classical annotator",
                )

        with gr.Row():
            run_btn = gr.Button("Run Annotation", variant="primary")
            status = gr.Textbox(label="Status", interactive=False)

        # --- Phase 2: Results ---
        gr.Markdown("---")
        with gr.Row(visible=False) as results_row:
            with gr.Column(scale=1):
                frame_slider = gr.Slider(
                    0,
                    0,
                    value=0,
                    step=1,
                    label="Annotated frame",
                    visible=False,
                )
                frame_summary = gr.Textbox(
                    label="Frame Summary",
                    interactive=False,
                )
                crystal_details = gr.Textbox(
                    label="Crystal Details (JSON)",
                    lines=10,
                    interactive=False,
                )
                download_btn = gr.Button("Download JSON")
                download_file = gr.File(label="Annotations JSON")
            with gr.Column(scale=2):
                with gr.Row():
                    img_annotated = gr.Image(label="Annotated Frame")
                    img_tracking = gr.Image(label="Tracking Overlay")

        # --- Callbacks ---
        video.change(
            fn=_on_video_upload,
            inputs=[video],
            outputs=[video_info],
        )

        run_btn.click(
            fn=_run_annotation,
            inputs=[
                video,
                model_name,
                frame_interval,
                max_frames,
                process_size,
                use_classical,
            ],
            outputs=[
                annotation_state,
                frame_map_state,
                frame_slider,
                results_row,
                status,
            ],
        )

        frame_slider.change(
            fn=_update_frame_display,
            inputs=[
                annotation_state,
                frame_map_state,
                frame_slider,
            ],
            outputs=[
                img_annotated,
                img_tracking,
                frame_summary,
                crystal_details,
            ],
        )

        download_btn.click(
            fn=_prepare_download,
            inputs=[annotation_state],
            outputs=[download_file],
        )

    return app


def main() -> None:
    """Launch the LLM annotator app."""
    import logfire

    logfire.configure(send_to_logfire="if-token-present")
    app = build_app()
    app.launch()


if __name__ == "__main__":
    main()
