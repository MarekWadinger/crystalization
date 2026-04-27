"""CLI entry points for LLM-powered crystal annotation."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

from llm_annotator.agent import build_agent
from llm_annotator.io import annotate_video
from llm_annotator.types import AnnotatorConfig


def main_annotate() -> None:
    """CLI entry point: annotate a video with the LLM agent."""
    parser = argparse.ArgumentParser(
        description="Annotate a crystal video using an LLM agent"
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
        "--no-classical",
        action="store_true",
        help="Disable classical annotator tool",
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
        include_classical=not args.no_classical,
    )

    agent = build_agent(config)
    result = asyncio.run(annotate_video(args.video, config, agent))

    args.output.write_text(result.model_dump_json(indent=2))

    total_crystals = sum(len(f.crystals) for f in result.frame_annotations)
    print(
        f"Annotated {len(result.frame_annotations)} frames, "
        f"{total_crystals} crystals total. "
        f"Output: {args.output}"
    )
