"""Sharpness layer decomposition with cached recompose.

Render once to cache per-layer sharpness data, then
toggle layers without recomputing.
"""

from __future__ import annotations

import os
import tempfile
from typing import Any

import cv2
import gradio as gr
import numpy as np

from annotator.depth import normalize
from annotator.sharpness import compute_sharpness_map
from annotator.types import Mat
from annotator.viz import (
    LAYER_COLORS,
    colorize_map,
    downscale,
)


def _get_video_info(
    video_path: str,
) -> tuple[int, float]:
    cap = cv2.VideoCapture(video_path)
    count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.release()
    return count, fps


def _on_video_load(
    video_path: str,
) -> tuple[dict[str, Any], float]:
    if not video_path:
        return gr.update(maximum=0, value=0), 30.0
    count, fps = _get_video_info(video_path)
    return (
        gr.update(maximum=max(0, count - 1), value=0),
        fps,
    )


def _layer_choices(n: int) -> list[str]:
    return [f"Layer {i}" for i in range(n)]


def _on_layers_change(
    num_layers: int,
) -> dict[str, Any]:
    choices = _layer_choices(num_layers)
    return gr.update(choices=choices, value=choices)


def _selected_ids(selected: list[str]) -> set[int]:
    return {int(s.split()[-1]) for s in selected if s.startswith("Layer")}


def _layer_masks(
    norm: Mat,
    num_layers: int,
    overlap: float,
) -> list[Mat]:
    """Per-layer masks with overlapping ranges."""
    width = 1.0 / num_layers
    extra = overlap * width / 2.0
    masks: list[Mat] = []
    for i in range(num_layers):
        lo = max(0.0, i * width - extra)
        hi = min(1.0, (i + 1) * width + extra)
        m: Mat = ((norm >= lo) & (norm < hi)).astype(np.uint8) * 255
        masks.append(m)
    return masks


def _colorize(masks: list[Mat], shape: tuple[int, int]) -> Mat:
    """Blend per-layer colours (supports overlap)."""
    out = np.zeros((*shape, 3), dtype=np.float32)
    cnt = np.zeros((*shape, 1), dtype=np.float32)
    for i, m in enumerate(masks):
        sel = m > 0
        c = LAYER_COLORS[i % len(LAYER_COLORS)]
        for ch in range(3):
            out[:, :, ch] += sel * c[ch]
        cnt[:, :, 0] += sel
    cnt = np.maximum(cnt, 1.0)
    result: Mat = (out / cnt).astype(np.uint8)
    return result


def _mask_frame(
    frame: Mat,
    norm: Mat,
    num_layers: int,
    overlap: float,
    ids: set[int],
) -> Mat:
    """Show selected layers bright, rest dimmed."""
    masks = _layer_masks(norm, num_layers, overlap)
    combined = np.zeros(frame.shape[:2], dtype=np.uint8)
    for lid in ids:
        if lid < len(masks):
            combined |= masks[lid]
    m3 = np.stack([combined] * 3, axis=-1)
    dim = (frame.astype(np.float32) * 0.15).astype(np.uint8)
    result: Mat = np.where(m3 > 0, frame, dim)
    return result


def _make_writer(fps: float, w: int, h: int) -> tuple[str, cv2.VideoWriter]:
    fd, path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    writer = cv2.VideoWriter(
        path,
        cv2.VideoWriter.fourcc(*"mp4v"),
        fps,
        (w, h),
    )
    return path, writer


# ── preview (single frame) ───────────────────────────


def _preview(
    video_path: str,
    frame_idx: int,
    process_size: int,
    num_layers: int,
    blur_kernel: int,
    overlap: float,
    selected: list[str],
) -> tuple[
    Mat | None,
    Mat | None,
    Mat | None,
    Mat | None,
]:
    """Render one frame for the 4 preview panels."""
    if not video_path:
        return None, None, None, None

    bk = blur_kernel | 1
    ids = _selected_ids(selected)

    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return None, None, None, None

    sm = downscale(frame, process_size)
    gray = cv2.cvtColor(sm, cv2.COLOR_BGR2GRAY)
    sharp = compute_sharpness_map(gray, bk)
    norm = normalize(sharp)
    masks = _layer_masks(norm, num_layers, overlap)

    rgb: Mat = cv2.cvtColor(sm, cv2.COLOR_BGR2RGB)

    masked = _mask_frame(sm, norm, num_layers, overlap, ids)
    masked_rgb: Mat = cv2.cvtColor(masked, cv2.COLOR_BGR2RGB)

    colored = _colorize(masks, gray.shape[:2])
    ov: Mat = cv2.addWeighted(sm, 0.6, colored, 0.4, 0)
    ov_rgb: Mat = cv2.cvtColor(ov, cv2.COLOR_BGR2RGB)

    hmap = colorize_map(sharp, cv2.COLORMAP_INFERNO)
    hmap_rgb: Mat = cv2.cvtColor(hmap, cv2.COLOR_BGR2RGB)

    return rgb, masked_rgb, ov_rgb, hmap_rgb


# ── render (full pipeline, caches sharpness) ─────────


def _render(
    video_path: str,
    process_size: int,
    num_layers: int,
    blur_kernel: int,
    overlap: float,
    selected: list[str],
    fps_state: float,
    progress: gr.Progress = gr.Progress(),
) -> tuple[
    str | None,
    str | None,
    str | None,
    str | None,
    dict[str, Any],
]:
    """Render 4 videos + cache normalised sharpness."""
    if not video_path:
        return None, None, None, None, {}

    bk = blur_kernel | 1
    ids = _selected_ids(selected)
    count, fps = _get_video_info(video_path)
    fps = fps_state or fps

    cap = cv2.VideoCapture(video_path)
    ret, first = cap.read()
    cap.release()
    if not ret:
        return None, None, None, None, {}
    sm = downscale(first, process_size)
    h, w = sm.shape[:2]

    p_orig, w_orig = _make_writer(fps, w, h)
    p_mask, w_mask = _make_writer(fps, w, h)
    p_over, w_over = _make_writer(fps, w, h)
    p_shrp, w_shrp = _make_writer(fps, w, h)

    fd, p_cache = tempfile.mkstemp(suffix=".bin")
    os.close(fd)

    cap = cv2.VideoCapture(video_path)
    n = 0
    with open(p_cache, "wb") as cf:
        for _ in progress.tqdm(range(count), desc="Rendering"):
            ret, frame = cap.read()
            if not ret:
                break
            n += 1
            sm = downscale(frame, process_size)
            gray = cv2.cvtColor(sm, cv2.COLOR_BGR2GRAY)
            sharp = compute_sharpness_map(gray, bk)
            norm = normalize(sharp)
            masks = _layer_masks(norm, num_layers, overlap)

            cf.write((np.clip(norm, 0, 1) * 255).astype(np.uint8).tobytes())

            w_orig.write(sm)
            w_mask.write(_mask_frame(sm, norm, num_layers, overlap, ids))

            colored = _colorize(masks, (h, w))
            ov: Mat = cv2.addWeighted(sm, 0.6, colored, 0.4, 0)
            w_over.write(ov)
            w_shrp.write(colorize_map(sharp, cv2.COLORMAP_INFERNO))

    cap.release()
    for wr in (w_orig, w_mask, w_over, w_shrp):
        wr.release()

    cache: dict[str, Any] = {
        "orig": p_orig,
        "bin": p_cache,
        "fps": fps,
        "w": w,
        "h": h,
        "n": n,
        "num_layers": num_layers,
        "overlap": overlap,
    }
    return p_orig, p_mask, p_over, p_shrp, cache


# ── recompose (fast, no sharpness recomputation) ─────


def _recompose(
    selected: list[str],
    cache: dict[str, Any],
    progress: gr.Progress = gr.Progress(),
) -> str | None:
    """Rebuild selected-layers video from cache."""
    if not cache or "bin" not in cache:
        return None

    ids = _selected_ids(selected)
    fps: float = cache["fps"]
    w: int = cache["w"]
    h: int = cache["h"]
    n: int = cache["n"]
    num_layers: int = cache["num_layers"]
    overlap: float = cache["overlap"]
    frame_sz = h * w

    cap = cv2.VideoCapture(cache["orig"])
    p_out, w_out = _make_writer(fps, w, h)

    with open(cache["bin"], "rb") as f:
        for _ in progress.tqdm(range(n), desc="Updating layers"):
            ret, frame = cap.read()
            raw = f.read(frame_sz)
            if not ret or len(raw) < frame_sz:
                break
            norm = (
                np.frombuffer(raw, dtype=np.uint8)
                .reshape(h, w)
                .astype(np.float64)
                / 255.0
            )
            w_out.write(
                _mask_frame(
                    frame,
                    norm,
                    num_layers,
                    overlap,
                    ids,
                )
            )

    cap.release()
    w_out.release()
    return p_out


# ── UI ────────────────────────────────────────────────


def build_app() -> gr.Blocks:
    """Build the Gradio app interface."""
    with gr.Blocks(title="Sharpness Layer Viewer") as demo:
        gr.Markdown("## Sharpness Layer Viewer")
        gr.Markdown(
            "Decompose video into sharpness layers. "
            "Tune with preview, render once, "
            "toggle layers to recompose."
        )

        fps_state = gr.State(value=30.0)
        cache_state = gr.State(value={})

        with gr.Row():
            video_in = gr.Video(label="Input Video")

        with gr.Row():
            process_size = gr.Slider(
                240,
                1920,
                value=480,
                step=40,
                label="Process Size (px)",
            )
            num_layers = gr.Slider(
                2,
                8,
                value=3,
                step=1,
                label="Number of Layers",
            )
        with gr.Row():
            blur_kernel = gr.Slider(
                3,
                31,
                value=15,
                step=2,
                label="Blur Kernel Size",
            )
            overlap = gr.Slider(
                0.0,
                1.0,
                value=0.5,
                step=0.1,
                label="Layer Overlap",
            )

        layer_sel = gr.CheckboxGroup(
            choices=_layer_choices(3),
            value=_layer_choices(3),
            label="Visible Layers",
        )

        gr.Markdown("### Preview")
        frame_sl = gr.Slider(0, 100, value=0, step=1, label="Frame")
        with gr.Row():
            img_orig = gr.Image(label="Original")
            img_mask = gr.Image(label="Selected Layers")
        with gr.Row():
            img_over = gr.Image(label="Layer Map")
            img_shrp = gr.Image(label="Sharpness Map")

        gr.Markdown("### Video")
        render_btn = gr.Button("Render Videos", variant="primary")
        with gr.Row():
            vid_orig = gr.Video(label="Original")
            vid_mask = gr.Video(label="Selected Layers")
        with gr.Row():
            vid_over = gr.Video(label="Layer Map")
            vid_shrp = gr.Video(label="Sharpness Map")

        # -- wiring --
        video_in.change(
            _on_video_load,
            inputs=[video_in],
            outputs=[frame_sl, fps_state],
        )
        num_layers.change(
            _on_layers_change,
            inputs=[num_layers],
            outputs=[layer_sel],
        )

        prev_in = [
            video_in,
            frame_sl,
            process_size,
            num_layers,
            blur_kernel,
            overlap,
            layer_sel,
        ]
        prev_out = [
            img_orig,
            img_mask,
            img_over,
            img_shrp,
        ]
        for inp in prev_in:
            inp.change(
                _preview,
                inputs=prev_in,
                outputs=prev_out,
            )

        render_btn.click(
            _render,
            inputs=[
                video_in,
                process_size,
                num_layers,
                blur_kernel,
                overlap,
                layer_sel,
                fps_state,
            ],
            outputs=[
                vid_orig,
                vid_mask,
                vid_over,
                vid_shrp,
                cache_state,
            ],
        )

        layer_sel.change(
            _recompose,
            inputs=[layer_sel, cache_state],
            outputs=[vid_mask],
        )

    return demo


def main() -> None:
    """Launch the sharpness layer viewer."""
    demo = build_app()
    demo.launch()


if __name__ == "__main__":
    main()
