"""Gradio interactive UI for mrDMD video decomposition."""

from __future__ import annotations

import tempfile

import cv2
import gradio as gr
import numpy as np

from predictor.dmd import (
    fit_mrdmd,
    get_mode_info,
    predict_frames,
    reconstruct_modes,
    snapshot_to_image,
    visualize_mode,
)
from predictor.io import apply_hankel, get_video_info, load_video_snapshots
from predictor.types import DMDConfig, DMDResult, PreprocessConfig


def _render_video(
    frames: list[np.ndarray],
    fps: float,
    frame_shape: tuple[int, int],
) -> str:
    """Write frames to a temporary mp4 and return the path."""
    h, w = frame_shape
    path = tempfile.mktemp(suffix=".mp4")
    writer = cv2.VideoWriter(
        path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h),
        isColor=False,
    )
    for frame in frames:
        writer.write(frame)
    writer.release()
    return path


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


def _fit(
    video_path: str,
    target_height: int,
    frame_skip: int,
    max_frames: int,
    hankel_delay: int,
    svd_rank: int,
    max_level: int,
    max_cycles: int,
) -> tuple:
    """Run preprocessing + mrDMD fit. Returns state for explore phase."""
    if not video_path:
        return (
            None, None, None,
            "No video loaded.", gr.update(choices=[]),
        )

    preprocess = PreprocessConfig(
        target_height=int(target_height),
        frame_skip=int(frame_skip),
        max_frames=int(max_frames),
        hankel_delay=int(hankel_delay),
    )
    dmd_config = DMDConfig(
        svd_rank=int(svd_rank),
        max_level=int(max_level),
        max_cycles=int(max_cycles),
    )

    X_raw, frame_shape, eff_fps = load_video_snapshots(
        video_path, preprocess
    )
    n_pixels = X_raw.shape[0]
    n_raw_frames = X_raw.shape[1]
    X = apply_hankel(X_raw, preprocess.hankel_delay)

    dt = 1.0 / eff_fps if eff_fps > 0 else 1.0
    result = fit_mrdmd(X, dmd_config, frame_shape, n_pixels, dt)

    # Build mode labels
    infos = get_mode_info(result)
    choices = [
        f"Mode {m['index']} (L{m['level']}, "
        f"f={m['frequency']:.4f}, "
        f"g={m['growth_rate']:.4f})"
        for m in infos
    ]

    n_modes = result.modes.shape[1]
    matrix_shape = X.shape
    status = (
        f"Fit complete.  "
        f"Snapshots: {n_raw_frames} frames -> "
        f"matrix {matrix_shape[0]}x{matrix_shape[1]}  |  "
        f"Modes: {n_modes}  |  "
        f"Frame: {frame_shape[1]}x{frame_shape[0]}"
    )

    return (
        result,
        X_raw,
        eff_fps,
        status,
        gr.update(choices=choices, value=choices),
    )


def _explore(
    dmd_result_state,
    snapshots_state,
    fps_state,
    selected_mode_labels: list[str],
    frame_idx: int,
    n_predict: int,
    stabilize: bool = True,
) -> tuple:
    """Reconstruct and predict from selected modes."""
    empty = np.zeros((64, 64), dtype=np.uint8)

    if dmd_result_state is None or snapshots_state is None:
        return empty, empty, empty, None, ""

    result: DMDResult = dmd_result_state
    X_raw = snapshots_state
    fps = fps_state or 5.0

    # Parse selected mode indices from labels
    selected = _parse_mode_indices(selected_mode_labels)

    frame_idx = min(int(frame_idx), X_raw.shape[1] - 1)

    # Original frame
    orig_img = snapshot_to_image(
        X_raw[:, frame_idx], result.frame_shape
    )

    # Reconstructed frame from selected modes
    if selected:
        recon = reconstruct_modes(result, selected)
        recon_img = snapshot_to_image(
            recon[:, frame_idx], result.frame_shape
        )
    else:
        recon_img = empty

    # Mode visualization (first selected mode's spatial pattern)
    if selected:
        mode_img = visualize_mode(result, selected[0])
    else:
        mode_img = empty

    # Prediction video: reconstructed tail + predicted future
    n_predict = int(n_predict)
    pred_video = None
    if selected and n_predict > 0:
        pred = predict_frames(
            result, n_predict, selected, stabilize=stabilize
        )
        recon_full = reconstruct_modes(result, selected)

        # Last N training frames as context, then predicted
        n_context = min(10, recon_full.shape[1])
        frames = []
        for i in range(
            recon_full.shape[1] - n_context, recon_full.shape[1]
        ):
            frames.append(
                snapshot_to_image(
                    recon_full[:, i], result.frame_shape
                )
            )
        for i in range(n_predict):
            frames.append(
                snapshot_to_image(
                    pred[:, i], result.frame_shape
                )
            )
        pred_video = _render_video(
            frames, fps, result.frame_shape
        )

    # Stats
    stats = _format_stats(result, selected)

    return orig_img, recon_img, mode_img, pred_video, stats


def _parse_mode_indices(labels: list[str] | None) -> list[int]:
    selected = []
    for label in (labels or []):
        try:
            idx = int(label.split("Mode ")[1].split(" ")[0])
            selected.append(idx)
        except (IndexError, ValueError):
            continue
    return selected


def _format_stats(
    result: DMDResult, selected: list[int]
) -> str:
    infos = get_mode_info(result)
    lines = ["idx | lvl | freq     | growth   | |eig|"]
    lines.append("--- | --- | -------- | -------- | ------")
    for m in infos:
        marker = "*" if m["index"] in selected else " "
        lines.append(
            f"{marker}{m['index']:3d} | "
            f"  {m['level']} | "
            f"{m['frequency']:8.5f} | "
            f"{m['growth_rate']:+8.5f} | "
            f"{m['eigenvalue_abs']:.4f}"
        )
    return "\n".join(lines)


def build_app() -> gr.Blocks:
    """Build the Gradio interface."""
    with gr.Blocks(title="mrDMD Video Predictor") as app:
        gr.Markdown("# mrDMD Video Decomposition & Prediction")

        # State
        dmd_result_state = gr.State(value=None)
        snapshots_state = gr.State(value=None)
        fps_state = gr.State(value=None)

        # --- Phase 1: Fit ---
        with gr.Row():
            with gr.Column(scale=1):
                video = gr.Video(label="Video")
                video_info = gr.Textbox(
                    label="Video Info", interactive=False
                )
            with gr.Column(scale=1):
                gr.Markdown("### Preprocessing")
                target_height = gr.Slider(
                    120, 480, value=120, step=40,
                    label="Target height (px)",
                )
                frame_skip = gr.Slider(
                    1, 20, value=10, step=1, label="Frame skip"
                )
                max_frames = gr.Slider(
                    50, 500, value=200, step=50, label="Max frames"
                )
                hankel_delay = gr.Slider(
                    1, 10, value=1, step=1, label="Hankel delay"
                )
            with gr.Column(scale=1):
                gr.Markdown("### DMD Parameters")
                svd_rank = gr.Slider(
                    -1, 50, value=5, step=1,
                    label="SVD rank (-1 = auto)",
                )
                max_level = gr.Slider(
                    1, 6, value=2, step=1, label="mrDMD max level"
                )
                max_cycles = gr.Slider(
                    1, 4, value=1, step=1, label="Max cycles"
                )

        with gr.Row():
            fit_btn = gr.Button("Fit mrDMD", variant="primary")
            status = gr.Textbox(label="Status", interactive=False)

        # --- Phase 2: Explore ---
        gr.Markdown("---")
        with gr.Row():
            with gr.Column(scale=1):
                mode_select = gr.CheckboxGroup(
                    choices=[], label="Selected Modes",
                )
                frame_slider = gr.Slider(
                    0, 199, value=0, step=1,
                    label="Training frame",
                )
                n_predict = gr.Slider(
                    1, 50, value=10, step=1,
                    label="Prediction horizon",
                )
                stabilize = gr.Checkbox(
                    value=True, label="Stabilize eigenvalues"
                )
            with gr.Column(scale=2):
                with gr.Row():
                    orig_img = gr.Image(label="Original")
                    recon_img = gr.Image(label="Reconstructed")
                with gr.Row():
                    mode_img = gr.Image(
                        label="Mode spatial pattern"
                    )
                    pred_video = gr.Video(
                        label="Prediction (context + future)",
                    )
                stats_box = gr.Textbox(
                    label="Mode Info", lines=10, interactive=False
                )

        # --- Callbacks ---
        video.change(
            fn=_on_video_upload,
            inputs=[video],
            outputs=[video_info],
        )

        fit_btn.click(
            fn=_fit,
            inputs=[
                video, target_height, frame_skip, max_frames,
                hankel_delay, svd_rank, max_level, max_cycles,
            ],
            outputs=[
                dmd_result_state, snapshots_state, fps_state,
                status, mode_select,
            ],
        )

        explore_inputs = [
            dmd_result_state, snapshots_state, fps_state,
            mode_select, frame_slider, n_predict, stabilize,
        ]
        explore_outputs = [
            orig_img, recon_img, mode_img, pred_video, stats_box,
        ]

        mode_select.change(
            fn=_explore,
            inputs=explore_inputs,
            outputs=explore_outputs,
        )
        frame_slider.change(
            fn=_explore,
            inputs=explore_inputs,
            outputs=explore_outputs,
        )
        n_predict.change(
            fn=_explore,
            inputs=explore_inputs,
            outputs=explore_outputs,
        )
        stabilize.change(
            fn=_explore,
            inputs=explore_inputs,
            outputs=explore_outputs,
        )

    return app


def main() -> None:
    """Launch the predictor app."""
    app = build_app()
    app.launch()
