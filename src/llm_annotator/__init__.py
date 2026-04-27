"""LLM-powered crystal annotation with depth layer tracking."""

from __future__ import annotations

from llm_annotator.agent import FrameContext, build_agent
from llm_annotator.io import annotate_video, extract_frames, get_video_info
from llm_annotator.types import (
    AnnotatorConfig,
    BoundingBox,
    CompareResult,
    CountResult,
    CrystalAnnotation,
    CrystalSystem,
    DepthLayer,
    FrameAnnotation,
    GrowthRateResult,
    HistogramResult,
    MeasureResult,
    VideoAnnotation,
)
from llm_annotator.viz import (
    LAYER_COLORS,
    draw_annotations,
    render_tracking_overlay,
)

__all__ = [
    "LAYER_COLORS",
    "AnnotatorConfig",
    "BoundingBox",
    "CompareResult",
    "CountResult",
    "CrystalAnnotation",
    "CrystalSystem",
    "DepthLayer",
    "FrameAnnotation",
    "FrameContext",
    "GrowthRateResult",
    "HistogramResult",
    "MeasureResult",
    "VideoAnnotation",
    "annotate_video",
    "build_agent",
    "draw_annotations",
    "extract_frames",
    "get_video_info",
    "render_tracking_overlay",
]
