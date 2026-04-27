"""Frame extraction and LLM annotation pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import cv2
import logfire
from numpy.typing import NDArray
from pydantic_ai import BinaryContent

from llm_annotator.agent import FrameContext
from llm_annotator.types import (
    AnnotatorConfig,
    FrameAnnotation,
    VideoAnnotation,
)

if TYPE_CHECKING:
    from pydantic_ai import Agent


def get_video_info(
    video_path: str | Path,
) -> dict[str, int | float]:
    """Get video metadata: frame_count, fps, width, height."""
    cap = cv2.VideoCapture(str(video_path))
    try:
        return {
            "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            "fps": cap.get(cv2.CAP_PROP_FPS),
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        }
    finally:
        cap.release()


def downscale(frame: NDArray, max_dim: int) -> NDArray:
    """Downscale maintaining aspect ratio."""
    h, w = frame.shape[:2]
    if max(h, w) <= max_dim:
        return frame
    scale = max_dim / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    result: NDArray = cv2.resize(
        frame, (new_w, new_h), interpolation=cv2.INTER_AREA
    )
    return result


def encode_frame_jpeg(frame_bgr: NDArray, max_dim: int) -> bytes:
    """Downscale frame to *max_dim* and JPEG-encode."""
    small = downscale(frame_bgr, max_dim)
    ok, buf = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        msg = "JPEG encoding failed"
        raise RuntimeError(msg)
    return bytes(buf)


def extract_frames(
    video_path: str | Path,
    config: AnnotatorConfig,
) -> list[tuple[int, float, NDArray]]:
    """Extract sampled frames from video.

    Returns list of (frame_idx, timestamp_s, bgr_frame).
    Samples every ``config.frame_interval`` frames.
    Caps at ``config.max_frames`` (0 = all sampled).
    """
    cap = cv2.VideoCapture(str(video_path))
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 1.0
        frames: list[tuple[int, float, NDArray]] = []
        idx = 0

        while True:
            ok, frame = cap.read()
            if not ok:
                break

            if idx % config.frame_interval == 0:
                timestamp_s = idx / fps
                frames.append((idx, timestamp_s, frame))

                if config.max_frames > 0 and len(frames) >= config.max_frames:
                    break

            idx += 1
    finally:
        cap.release()

    return frames


def _build_tracking_context(
    previous: list[FrameAnnotation],
) -> str:
    """Build text summary of previous annotations."""
    if not previous:
        return "No previous frames annotated yet."

    lines: list[str] = []
    for ann in previous:
        lines.append(
            f"Frame {ann.frame_idx} "
            f"(t={ann.timestamp_s:.2f}s): "
            f"{len(ann.crystals)} crystals"
        )
        for c in ann.crystals:
            lines.append(
                f"  {c.crystal_id}: "
                f"layer={c.layer.value}, "
                f"pos=({c.bbox.x:.0f},{c.bbox.y:.0f}), "
                f"size=({c.bbox.width:.0f}"
                f"x{c.bbox.height:.0f}), "
                f"system={c.crystal_system.value}"
            )
    return "\n".join(lines)


def _next_crystal_id(
    previous: list[FrameAnnotation],
) -> int:
    """Compute next available crystal ID number."""
    max_id = 0
    for ann in previous:
        for c in ann.crystals:
            # Extract number from 'crystal_NNN'
            parts = c.crystal_id.rsplit("_", 1)
            if len(parts) == 2 and parts[1].isdigit():
                max_id = max(max_id, int(parts[1]))
    return max_id + 1


def _build_user_prompt(
    frame_idx: int,
    timestamp_s: float,
    jpeg_bytes: bytes,
    previous: list[FrameAnnotation],
) -> list[Any]:
    """Build multimodal prompt with image and context."""
    context = _build_tracking_context(previous)
    next_id = _next_crystal_id(previous)
    prev_count = len(previous[-1].crystals) if previous else None

    lines: list[str] = []

    if prev_count is None:
        lines.append(
            "This is a crystal growth microscopy video"
            " showing crystals at different depths in a"
            " liquid medium. Crystals appear as bright"
            " shapes with dark edges against a bright"
            " background. Expect 50-500+ crystals per"
            " frame."
        )
        lines.append("")

    lines.append(f"Annotate frame {frame_idx} (timestamp {timestamp_s:.2f}s).")
    lines.append("")

    lines.append(
        "Use the count_crystals tool FIRST to get the"
        " baseline detection count per layer. Then"
        " annotate ALL crystals you can identify -- not"
        " just the prominent ones. Your count must reach"
        " at least 80% of the baseline."
    )

    if prev_count is not None:
        lines.append("")
        lines.append(
            f"The previous frame had {prev_count} crystals."
            " Expect a similar number in this frame"
            " (crystals persist between frames with small"
            " position changes)."
        )

    lines.append("")
    lines.append(f"Previous annotations:\n{context}")
    lines.append("")
    lines.append(f"Next available crystal ID number: {next_id}")
    lines.append(
        "Reuse IDs for crystals that match previous"
        " positions. Assign new sequential IDs for newly"
        " appeared crystals."
    )

    text = "\n".join(lines)

    return [
        text,
        BinaryContent(data=jpeg_bytes, media_type="image/jpeg"),
    ]


async def annotate_video(
    video_path: str | Path,
    config: AnnotatorConfig,
    agent: Agent[Any, FrameAnnotation],
) -> VideoAnnotation:
    """Run sequential frame annotation with tracking.

    Pipeline:
    1. Extract sampled frames.
    2. For each frame sequentially, encode as JPEG,
       build user prompt with previous context, call
       agent, and collect the result.
    3. Return aggregated ``VideoAnnotation``.
    """
    with logfire.span("annotate_video", video=str(video_path)):
        info = get_video_info(video_path)
        sampled = extract_frames(video_path, config)

        annotations: list[FrameAnnotation] = []

        for frame_idx, timestamp_s, bgr in sampled:
            with logfire.span("annotate_frame", frame_idx=frame_idx):
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

        return VideoAnnotation(
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
