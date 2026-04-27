"""Pydantic-ai agent for LLM-based crystal annotation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic_ai import Agent

from llm_annotator.types import (
    AnnotatorConfig,
    FrameAnnotation,
)


@dataclass
class FrameContext:
    """Dependencies injected into every agent run."""

    frame_bytes: bytes
    """JPEG-encoded current frame."""
    frame_bgr: Any
    """NumPy BGR array of current frame."""
    frame_idx: int
    timestamp_s: float
    fps: float
    previous_annotations: list[FrameAnnotation] = field(
        default_factory=list,
    )
    config: AnnotatorConfig = field(
        default_factory=AnnotatorConfig,
    )


def _load_system_prompt() -> str:
    """Load system prompt from system_prompt.md."""
    path = Path(__file__).parent / "system_prompt.md"
    return path.read_text(encoding="utf-8")


def build_agent(
    config: AnnotatorConfig,
) -> Agent[FrameContext, FrameAnnotation]:
    """Build the pydantic-ai agent with tools registered."""
    from llm_annotator.tools import (
        classify_crystal_system,
        compare_frames,
        count_crystals,
        estimate_growth_rate,
        generate_histogram,
        get_depth_map,
        get_layer_map,
        get_sharpness_map,
        measure_crystal,
    )

    # ty can't infer OutputDataT from output_type arg
    agent: Agent[FrameContext, FrameAnnotation] = Agent(  # type: ignore[invalid-assignment]
        config.model_name,
        output_type=FrameAnnotation,
        system_prompt=_load_system_prompt(),
        deps_type=FrameContext,
        tools=[
            measure_crystal,
            count_crystals,
            compare_frames,
            classify_crystal_system,
            estimate_growth_rate,
            generate_histogram,
            get_sharpness_map,
            get_depth_map,
            get_layer_map,
        ],
    )
    return agent
