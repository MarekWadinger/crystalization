"""CLI entry points for LLM-powered crystal annotation."""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

from llm_annotator.agent import FrameContext, build_agent
from llm_annotator.io import (
    _build_user_prompt,
    encode_frame_jpeg,
    extract_frames,
    get_video_info,
)
from llm_annotator.types import AnnotatorConfig, VideoAnnotation


def _fmt_duration(seconds: float) -> str:
    """Format seconds as compact string."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    m, s = divmod(int(seconds), 60)
    return f"{m}m{s:02d}s"


async def _run_pipeline(
    video: Path,
    config: AnnotatorConfig,
) -> VideoAnnotation:
    """Run annotation pipeline with per-frame progress."""
    agent = build_agent(config)
    info = get_video_info(str(video))
    sampled = extract_frames(video, config)
    total = len(sampled)

    print(
        f"Video: {info['width']}x{info['height']}, "
        f"{info['frame_count']} frames "
        f"@ {info['fps']:.1f} fps"
    )
    print(f"Sampling {total} frames (every {config.frame_interval}th)\n")

    from llm_annotator.types import FrameAnnotation

    annotations: list[FrameAnnotation] = []
    start = time.monotonic()

    for i, (frame_idx, ts, bgr) in enumerate(sampled):
        from llm_annotator.io import downscale

        small = downscale(bgr, config.process_size)
        jpeg = encode_frame_jpeg(bgr, config.process_size)
        prompt = _build_user_prompt(
            frame_idx,
            ts,
            jpeg,
            annotations[-3:],
        )
        ctx = FrameContext(
            frame_bytes=jpeg,
            frame_bgr=small,
            frame_idx=frame_idx,
            timestamp_s=ts,
            fps=float(info["fps"]),
            previous_annotations=list(annotations[-3:]),
            config=config,
        )
        result = await agent.run(prompt, deps=ctx)
        ann = result.output
        annotations.append(ann)

        elapsed = time.monotonic() - start
        avg = elapsed / (i + 1)
        remaining = avg * (total - i - 1)

        print(
            f"  Frame {i + 1}/{total} "
            f"(idx={frame_idx}, t={ts:.2f}s) "
            f"— {len(ann.crystals)} crystals "
            f"[{_fmt_duration(elapsed)} elapsed, "
            f"~{_fmt_duration(remaining)} remaining]"
        )

    return VideoAnnotation(
        video_path=str(video),
        total_frames=int(info["frame_count"]),
        sampled_frames=len(sampled),
        fps=float(info["fps"]),
        frame_annotations=annotations,
        overall_summary=(
            f"Annotated {len(annotations)} frames "
            f"from {info['frame_count']} total."
        ),
    )


def main_annotate() -> None:
    """CLI entry point: annotate a video with the LLM agent."""
    parser = argparse.ArgumentParser(
        description=("Annotate a crystal video using an LLM agent")
    )
    parser.add_argument("video", type=Path, help="Path to input video file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("llm_annotations.json"),
        help="Output JSON path (default: llm_annotations.json)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="openai:gpt-4o",
        help="Pydantic-ai model string (default: openai:gpt-4o)",
    )
    parser.add_argument(
        "--frame-interval",
        type=int,
        default=30,
        help="Sample every Nth frame (default: 30)",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=0,
        help="Max frames to process, 0 = all (default: 0)",
    )
    parser.add_argument(
        "--process-size",
        type=int,
        default=960,
        help="Max dimension for processing (default: 960)",
    )
    parser.add_argument(
        "--logfire-token",
        type=str,
        default=None,
        help="Logfire token for observability",
    )

    args = parser.parse_args()
    load_dotenv()

    if not args.video.exists():
        print(
            f"Error: video not found: {args.video}",
            file=sys.stderr,
        )
        sys.exit(1)

    import logfire

    logfire.configure(
        send_to_logfire="if-token-present",
        token=args.logfire_token,
    )

    config = AnnotatorConfig(
        model_name=args.model,
        frame_interval=args.frame_interval,
        max_frames=args.max_frames,
        process_size=args.process_size,
    )

    start = time.monotonic()
    result = asyncio.run(_run_pipeline(args.video, config))
    elapsed = time.monotonic() - start

    args.output.write_text(result.model_dump_json(indent=2))

    total_crystals = sum(len(a.crystals) for a in result.frame_annotations)
    layer_totals: Counter[str] = Counter()
    for ann in result.frame_annotations:
        for c in ann.crystals:
            layer_totals[c.layer] += 1

    print(f"\nDone in {_fmt_duration(elapsed)}")
    print(f"  Frames: {len(result.frame_annotations)}")
    print(f"  Total crystals: {total_crystals}")
    for layer in ["far", "mid", "near"]:
        print(f"    {layer}: {layer_totals.get(layer, 0)}")
    print(f"  Output: {args.output}")
