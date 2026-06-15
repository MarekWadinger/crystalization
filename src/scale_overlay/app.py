"""Gradio app: slide d_o to see the real-world grid on a video frame.

Launch with::

    uv run scale-overlay-app
"""

from __future__ import annotations

from pathlib import Path

import cv2
import gradio as gr
import numpy as np

from annotator.sharpness import compute_sharpness_map
from annotator.viz import colorize_map
from optics import (
    LensSetup,
    circle_of_confusion,
    image_distance_for_focus,
    mm_per_pixel_at,
)
from optics.config import load_camera
from scale_overlay.overlay import (
    annotate_optics_info,
    draw_grid,
    draw_ruler,
)

Mat = np.ndarray

# Defaults loaded from versioned config (configs/camera_100.toml).
_CFG = load_camera(
    Path(__file__).resolve().parents[2] / "configs" / "camera_100.toml"
)
DEFAULT_FOCAL = _CFG.focal_length_mm
DEFAULT_FNUMBER = _CFG.f_number
DEFAULT_EXTENSION = _CFG.extension_tube_mm
DEFAULT_PITCH = _CFG.native_pixel_pitch_um
DEFAULT_FOCUS = _CFG.focus_object_distance_mm


def _make_lens(
    f_mm: float, f_number: float, e_mm: float, pitch: float
) -> LensSetup:
    return LensSetup(
        focal_length=float(f_mm),
        f_number=float(f_number),
        extension_tube=float(e_mm),
        pixel_pitch_um=float(pitch),
    )


def _read_frame(video_path: str, frame_idx: int) -> Mat | None:
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_idx))
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return None
    out: Mat = frame
    return out


def _video_info(video_path: str) -> tuple[int, float]:
    cap = cv2.VideoCapture(video_path)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.release()
    return n, fps


def _on_video_load(video_path: str | None) -> dict[str, object]:
    if not video_path:
        return gr.update(maximum=0, value=0)
    n, _ = _video_info(video_path)
    return gr.update(maximum=max(0, n - 1), value=0)


def _render(
    video_path: str | None,
    frame_idx: int,
    f_mm: float,
    f_number: float,
    e_mm: float,
    pitch_um: float,
    d_focus: float,
    d_o: float,
    grid_mm: float,
    blur_kernel: int,
) -> tuple[Mat | None, Mat | None, Mat | None, str]:
    """Compute the three preview panels + a status string."""
    if not video_path:
        return None, None, None, "Load a video to begin."
    frame = _read_frame(video_path, int(frame_idx))
    if frame is None:
        return None, None, None, "Could not read frame."
    lens = _make_lens(f_mm, f_number, e_mm, pitch_um)
    try:
        i_fixed = image_distance_for_focus(lens, float(d_focus))
    except ValueError as exc:
        return None, None, None, f"Bad focus distance: {exc}"

    # --- Panel 1: original + grid + ruler + HUD --------------------
    with_grid = draw_grid(
        frame,
        lens,
        float(d_focus),
        float(d_o),
        grid_mm=float(grid_mm),
        major_every=5,
        color=(0, 255, 255),
    )
    with_grid = draw_ruler(with_grid, lens, float(d_focus), float(d_o))
    with_grid = annotate_optics_info(
        with_grid, lens, float(d_focus), float(d_o)
    )

    # --- Panel 2: sharpness map -----------------------------------
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    bk = int(blur_kernel) | 1
    sharp = compute_sharpness_map(gray, bk)
    heat = colorize_map(sharp, cv2.COLORMAP_INFERNO)
    # Also overlay a ruler so the user can read scale on the heatmap
    heat = draw_ruler(heat, lens, float(d_focus), float(d_o))

    # --- Panel 3: CoC envelope around d_focus ---------------------
    d_range = np.linspace(d_focus - 5.0, d_focus + 5.0, 600)
    c_arr = circle_of_confusion(lens, float(d_focus), d_range) * 1000.0
    info: str = (
        f"d_focus = {d_focus:.1f} mm  →  i_fixed = {i_fixed:.2f} mm\n"
        f"At d_o = {d_o:.1f} mm:  "
        f"{float(mm_per_pixel_at(lens, d_focus, np.array([d_o]))[0]) * 1000.0:.2f} µm/px"
        f"  (grid step {grid_mm:.2f} mm)\n"
        f"CoC at d_o = "
        f"{float(circle_of_confusion(lens, d_focus, np.array([d_o]))[0]) * 1000.0:.2f} µm"
        f"  (sensor pixel = {pitch_um:.1f} µm)\n"
        f"Range where CoC <= 1 px: "
        f"{float(d_range[c_arr <= pitch_um].min()) if np.any(c_arr <= pitch_um) else float('nan'):.1f}"
        f" .. {float(d_range[c_arr <= pitch_um].max()) if np.any(c_arr <= pitch_um) else float('nan'):.1f} mm"
    )

    grid_rgb: Mat = cv2.cvtColor(with_grid, cv2.COLOR_BGR2RGB)
    heat_rgb: Mat = cv2.cvtColor(heat, cv2.COLOR_BGR2RGB)
    return grid_rgb, heat_rgb, None, info


def build_app() -> gr.Blocks:
    """Construct the Gradio interface."""
    with gr.Blocks(title="Camera 100 — Scale Overlay") as demo:
        gr.Markdown(
            "## Camera 100 — depth-aware millimetre overlay\n"
            "Loads a video, draws a real-world grid on the chosen frame, "
            "and lets you slide through object distance to see how mm/px "
            "changes with depth. Pair with the sharpness map to read "
            "scale on the in-focus slice only.\n\n"
            "Lens defaults are the Fujinon HF35HA-1B + ~10 mm extension "
            "tube derived in `docs/optics/README.md`. Override them if "
            "you measure something different."
        )
        with gr.Row():
            video_in = gr.Video(label="Sight-glass video")
        with gr.Row():
            frame_idx = gr.Slider(0, 100, value=0, step=1, label="Frame")

        gr.Markdown("### Lens setup (override as you learn more)")
        with gr.Row():
            f_mm = gr.Number(value=DEFAULT_FOCAL, label="Focal length f (mm)")
            f_number = gr.Number(value=DEFAULT_FNUMBER, label="F-number N")
            e_mm = gr.Number(
                value=DEFAULT_EXTENSION, label="Extension tube e (mm)"
            )
            pitch = gr.Number(value=DEFAULT_PITCH, label="Pixel pitch (µm)")

        gr.Markdown("### Geometry sliders")
        with gr.Row():
            d_focus = gr.Slider(
                50.0,
                1000.0,
                value=DEFAULT_FOCUS,
                step=1.0,
                label="d_focus — focused object distance (mm)",
            )
            d_o = gr.Slider(
                50.0,
                1000.0,
                value=DEFAULT_FOCUS,
                step=0.5,
                label="d_o — depth to display grid for (mm)",
            )
            grid_mm = gr.Slider(
                0.1,
                5.0,
                value=0.5,
                step=0.1,
                label="grid spacing (mm)",
            )
            blur_kernel = gr.Slider(
                3,
                31,
                value=15,
                step=2,
                label="sharpness blur kernel (px)",
            )

        with gr.Row():
            img_main = gr.Image(label="Frame + scale grid + ruler")
            img_sharp = gr.Image(
                label="Sharpness map (in-focus pixels brightest)"
            )
        info_box = gr.Markdown()

        controls: list[gr.components.Component] = [
            video_in,
            frame_idx,
            f_mm,
            f_number,
            e_mm,
            pitch,
            d_focus,
            d_o,
            grid_mm,
            blur_kernel,
        ]

        video_in.change(_on_video_load, inputs=[video_in], outputs=[frame_idx])

        outputs = [img_main, img_sharp, gr.State(value=None), info_box]
        for c in controls:
            # gradio Component subclasses all carry .change; ty's typed base
            # class doesn't expose it. Safe in practice.
            c.change(_render, inputs=controls, outputs=outputs)  # type: ignore[attr-defined]

    return demo


def main() -> None:
    """Launch the scale-overlay viewer."""
    demo = build_app()
    demo.launch()


if __name__ == "__main__":
    main()
