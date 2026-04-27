"""Pydantic models for LLM-based crystal annotation."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class DepthLayer(StrEnum):
    """Depth layer inferred from focus, speed, and apparent size."""

    NEAR = "near"
    MID = "mid"
    FAR = "far"


class CrystalSystem(StrEnum):
    """Crystallographic system classified from 2-D projected shape."""

    CUBIC = "cubic"
    TETRAGONAL = "tetragonal"
    ORTHORHOMBIC = "orthorhombic"
    HEXAGONAL = "hexagonal"
    TRIGONAL = "trigonal"
    MONOCLINIC = "monoclinic"
    TRICLINIC = "triclinic"
    UNKNOWN = "unknown"


# ── Core geometry ────────────────────────────────────────────────


class BoundingBox(BaseModel):
    """Oriented bounding rectangle around a crystal."""

    x: float = Field(description="Center x coordinate (pixels)")
    y: float = Field(description="Center y coordinate (pixels)")
    width: float = Field(description="Box width (pixels)")
    height: float = Field(description="Box height (pixels)")
    angle: float = Field(
        default=0.0,
        description="Rotation angle in degrees",
    )


# ── Per-crystal annotation ───────────────────────────────────────


class CrystalAnnotation(BaseModel):
    """Single crystal observed in one frame."""

    crystal_id: str = Field(
        description=(
            "Persistent tracking ID across frames, e.g. 'crystal_001'"
        ),
    )
    bbox: BoundingBox
    layer: DepthLayer
    crystal_system: CrystalSystem = Field(
        default=CrystalSystem.UNKNOWN,
        description="Crystallographic system from 2-D shape",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Detection confidence score",
    )
    size_um: float | None = Field(
        default=None,
        description="Estimated crystal size in micrometres",
    )
    growth_rate: float | None = Field(
        default=None,
        description="Estimated growth rate in um/s",
    )
    notes: str = Field(
        default="",
        description="Free-text observation notes",
    )


# ── Frame / video containers ─────────────────────────────────────


class FrameAnnotation(BaseModel):
    """All crystal annotations for a single video frame."""

    frame_idx: int = Field(description="Zero-based frame index")
    timestamp_s: float = Field(
        description="Frame timestamp in seconds",
    )
    crystals: list[CrystalAnnotation] = Field(
        default_factory=list,
        description="Crystals detected in this frame",
    )
    summary: str = Field(
        description="Brief natural-language frame summary",
    )
    layer_counts: dict[DepthLayer, int] = Field(
        default_factory=dict,
        description="Crystal count per depth layer",
    )


class VideoAnnotation(BaseModel):
    """Aggregated annotation spanning an entire video."""

    video_path: str = Field(description="Path to the source video")
    total_frames: int = Field(
        description="Total frames in the video",
    )
    sampled_frames: int = Field(
        description="Number of frames actually annotated",
    )
    fps: float = Field(description="Video frame rate")
    frame_annotations: list[FrameAnnotation] = Field(
        default_factory=list,
        description="Per-frame annotation results",
    )
    overall_summary: str = Field(
        description="High-level summary of the full video",
    )


# ── Configuration ────────────────────────────────────────────────


class AnnotatorConfig(BaseModel):
    """Runtime configuration for the LLM annotator."""

    model_name: str = Field(
        default="openai:gpt-4o",
        description="pydantic-ai model identifier",
    )
    frame_interval: int = Field(
        default=30,
        description="Process every N-th frame",
    )
    max_frames: int = Field(
        default=0,
        description="Max frames to process (0 = all)",
    )
    process_size: int = Field(
        default=960,
        description=("Max dimension for resizing before sending to LLM"),
    )
    include_classical: bool = Field(
        default=True,
        description=("Overlay classical CV detections as extra context"),
    )


# ── Tool result models ───────────────────────────────────────────


class MeasureResult(BaseModel):
    """Result of measuring a single crystal's bounding box."""

    width_px: float = Field(
        description="Bounding-box width in pixels",
    )
    height_px: float = Field(
        description="Bounding-box height in pixels",
    )
    area_px: float = Field(
        description="Bounding-box area in pixels squared",
    )
    aspect_ratio: float = Field(
        description="Width / height ratio",
    )


class CountResult(BaseModel):
    """Crystal counts grouped by depth layer."""

    layer_counts: dict[DepthLayer, int] = Field(
        default_factory=dict,
        description="Count per depth layer",
    )
    total: int = Field(description="Total crystal count")


class CompareResult(BaseModel):
    """Comparison between two consecutive frames."""

    appeared: int = Field(
        description="Crystals present in new frame only",
    )
    disappeared: int = Field(
        description="Crystals present in old frame only",
    )
    persistent: int = Field(
        description="Crystals matched across both frames",
    )
    mean_displacement_px: float = Field(
        description=(
            "Mean centre displacement of persistent crystals (pixels)"
        ),
    )


class GrowthRateResult(BaseModel):
    """Estimated growth rate for a tracked crystal."""

    crystal_id: str = Field(
        description="Tracking ID of the crystal",
    )
    growth_rate_px_per_frame: float = Field(
        description="Size change in pixels per frame",
    )
    frames_observed: int = Field(
        description="Number of frames the crystal was tracked",
    )


class HistogramResult(BaseModel):
    """Size-distribution histogram returned as a PNG image."""

    bin_edges: list[float] = Field(
        default_factory=list,
        description="Histogram bin edges",
    )
    counts: list[int] = Field(
        default_factory=list,
        description="Number of crystals in each bin",
    )
    image_base64: str = Field(
        description="Base64-encoded PNG histogram",
    )
