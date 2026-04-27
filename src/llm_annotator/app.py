"""Gradio app for LLM-powered crystal annotation."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Any

import gradio as gr
import numpy as np
from numpy.typing import NDArray

from llm_annotator.agent import FrameContext, build_agent
from llm_annotator.io import (
    _build_user_prompt,
    downscale,
    encode_frame_jpeg,
    extract_frames,
    get_video_info,
)
from llm_annotator.types import (
    AnnotatorConfig,
    DepthLayer,
    FrameAnnotation,
    VideoAnnotation,
)
from llm_annotator.viz import (
    annotation_to_json_str,
    bgr_to_rgb,
    draw_annotations,
    draw_legend,
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
    include_classical: bool,
    progress: gr.Progress = gr.Progress(),  # noqa: B008
) -> tuple[
    VideoAnnotation | None,
    dict[int, NDArray[np.uint8]],
    dict[str, Any],
    dict[str, Any],
    str,
]:
    """Run the LLM annotation pipeline with progress."""
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
        include_classical=include_classical,
    )

    agent = build_agent(config)

    # Extract frames and annotate inline for progress
    info = get_video_info(video_path)
    sampled = extract_frames(Path(video_path), config)
    total = len(sampled)

    annotations: list[FrameAnnotation] = []
    start_time = time.time()

    for i, (frame_idx, timestamp_s, bgr) in enumerate(sampled):
        progress((i, total), desc=f"Frame {i + 1}/{total}")

        jpeg = encode_frame_jpeg(bgr, config.process_size)
        prompt = _build_user_prompt(
            frame_idx,
            timestamp_s,
            jpeg,
            annotations[-3:],
        )
        frame_ctx = FrameContext(
            frame_bytes=jpeg,
            frame_bgr=bgr,
            frame_idx=frame_idx,
            timestamp_s=timestamp_s,
            fps=float(info["fps"]),
            previous_annotations=list(annotations[-3:]),
            config=config,
        )
        result = await agent.run(prompt, deps=frame_ctx)
        annotations.append(result.output)

    elapsed = time.time() - start_time

    video_ann = VideoAnnotation(
        video_path=str(video_path),
        total_frames=int(info["frame_count"]),
        sampled_frames=len(sampled),
        fps=float(info["fps"]),
        frame_annotations=annotations,
        overall_summary=(
            f"Annotated {len(annotations)} frames "
            f"from {info['frame_count']} total."
        ),
    )

    # Cache downscaled frames for correct annotation display
    frame_map: dict[int, NDArray[np.uint8]] = {
        fi: downscale(img, config.process_size) for fi, _, img in sampled
    }

    total_crystals = sum(len(a.crystals) for a in annotations)
    layer_counts: dict[str, int] = {}
    for ann in annotations:
        for c in ann.crystals:
            key = c.layer.value
            layer_counts[key] = layer_counts.get(key, 0) + 1
    layer_summary = ", ".join(
        f"{k}: {v}" for k, v in sorted(layer_counts.items())
    )

    n_frames = len(video_ann.frame_annotations)
    slider_max = max(0, n_frames - 1)

    status = (
        f"Done. {n_frames} frames, "
        f"{total_crystals} crystals "
        f"({layer_summary}). "
        f"({elapsed:.1f}s)"
    )

    return (
        video_ann,
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

    if idx < 0 or idx >= len(result.frame_annotations):
        return None, None, "", ""

    frame_ann = result.frame_annotations[idx]

    raw_frame = frame_map_state.get(frame_ann.frame_idx)
    if raw_frame is None:
        return None, None, "Frame not found in video.", ""

    annotated = draw_annotations(raw_frame.copy(), frame_ann)
    draw_legend(annotated)
    annotated_rgb = bgr_to_rgb(annotated)

    tracking_rgb = None
    if idx > 0:
        prev_ann = result.frame_annotations[idx - 1]
        prev_frame = frame_map_state.get(prev_ann.frame_idx)
        if prev_frame is not None:
            overlay = render_tracking_overlay(
                raw_frame.copy(), frame_ann, prev_ann
            )
            tracking_rgb = bgr_to_rgb(overlay)

    # Per-layer crystal counts
    counts: dict[str, int] = {}
    for c in frame_ann.crystals:
        key = c.layer.value
        counts[key] = counts.get(key, 0) + 1
    layer_detail = ", ".join(
        f"{layer.value}: {counts.get(layer.value, 0)}" for layer in DepthLayer
    )

    summary = (
        f"Frame {frame_ann.frame_idx} "
        f"(t={frame_ann.timestamp_s:.2f}s): "
        f"{len(frame_ann.crystals)} crystals "
        f"[{layer_detail}]"
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
        gr.Markdown(
            "Analyze crystal microscopy video using a "
            "vision LLM. "
            "Crystals are classified into three depth "
            "layers based on "
            "focus (sharp to blurry), motion speed "
            "(slow to fast), and "
            "apparent size (small to large)."
        )

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
                model_name = gr.Dropdown(
                    choices=[
                        "openai:gpt-5.4",
                        "openai:gpt-5.4-mini",
                        "openai:gpt-5.4-nano",
                        "openai:gpt-5.3-chat-latest",
                        "openai:gpt-5.2",
                        "openai:gpt-5.1",
                        "openai:gpt-5",
                        "openai:gpt-5-mini",
                        "openai:gpt-4o",
                        "openai:gpt-4o-mini",
                        "openai:gpt-4.1",
                        "openai:gpt-4.1-mini",
                        "openai:gpt-4.1-nano",
                        "openai:o3",
                        "openai:o4-mini",
                    ],
                    value="openai:gpt-4o",
                    label="LLM Model",
                    info=("Vision-capable OpenAI model for crystal analysis"),
                    allow_custom_value=True,
                )
                frame_interval = gr.Slider(
                    1,
                    100,
                    value=30,
                    step=1,
                    label="Frame interval",
                    info=(
                        "Extract every Nth frame from "
                        "the video. Lower = more frames "
                        "analyzed but slower and more "
                        "expensive."
                    ),
                )
                max_frames = gr.Slider(
                    0,
                    50,
                    value=0,
                    step=1,
                    label="Max frames (0 = all)",
                    info=(
                        "Maximum number of frames to "
                        "analyze. 0 = analyze all "
                        "sampled frames. Start with "
                        "3-5 for testing."
                    ),
                )
                process_size = gr.Slider(
                    240,
                    1920,
                    value=960,
                    step=40,
                    label="Process size (px)",
                    info=(
                        "Downscale frames to this max "
                        "dimension before sending to "
                        "the LLM. Lower = faster but "
                        "less detail."
                    ),
                )
                include_classical = gr.Checkbox(
                    value=True,
                    label="Use CV pre-detection",
                    info=(
                        "Run classical computer vision "
                        "crystal detector first to give "
                        "the LLM a detection baseline."
                    ),
                )

        with gr.Row():
            run_btn = gr.Button("Run Annotation", variant="primary")
            status = gr.Textbox(label="Status", interactive=False)

        # --- Phase 2: Results ---
        gr.Markdown("### Results")
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
                    img_annotated = gr.Image(
                        label="Annotated Frame",
                        scale=2,
                    )
                    img_tracking = gr.Image(
                        label="Tracking Overlay",
                    )

        # --- How It Works ---
        gr.Markdown(
            "### How It Works\n"
            "The system analyzes crystal microscopy "
            "video by:\n"
            "1. **Sampling frames** at regular "
            "intervals\n"
            "2. **Running CV pre-detection** to "
            "establish a baseline crystal count\n"
            "3. **LLM vision analysis** to classify "
            "each crystal by depth layer, shape, "
            "and growth\n"
            "4. **Tracking crystals** across frames "
            "using persistent IDs\n\n"
            "Crystals at different depths exhibit "
            "correlated properties:\n"
            "| Layer | Focus | Motion | Size |\n"
            "|-------|-------|--------|------|\n"
            "| Near | Blurry | Fast | Large |\n"
            "| Mid | Moderate | Medium | Medium |\n"
            "| Far | Sharp | Slow | Small |"
        )

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
                include_classical,
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
    from dotenv import load_dotenv

    load_dotenv()

    import logfire

    logfire.configure(send_to_logfire="if-token-present")
    app = build_app()
    app.launch()


if __name__ == "__main__":
    main()
