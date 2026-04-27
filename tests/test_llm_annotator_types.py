"""Tests for llm_annotator.types — Pydantic model validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from llm_annotator.types import (
    AnnotatorConfig,
    BoundingBox,
    CrystalAnnotation,
    CrystalSystem,
    DepthLayer,
    FrameAnnotation,
    VideoAnnotation,
)


class TestBoundingBox:
    def test_angle_defaults_to_zero(self) -> None:
        """BoundingBox angle defaults to 0.0."""
        bb = BoundingBox(x=10, y=20, width=30, height=40)
        assert bb.angle == 0.0

    def test_stores_all_fields(self) -> None:
        """BoundingBox preserves all provided values."""
        bb = BoundingBox(x=1.5, y=2.5, width=3.5, height=4.5, angle=45.0)
        assert bb.x == 1.5
        assert bb.y == 2.5
        assert bb.width == 3.5
        assert bb.height == 4.5
        assert bb.angle == 45.0


class TestCrystalAnnotation:
    def test_requires_id_and_bbox(self) -> None:
        """CrystalAnnotation must have crystal_id and bbox."""
        with pytest.raises(ValidationError):
            CrystalAnnotation(layer=DepthLayer.FAR)  # ty: ignore[missing-argument]

    def test_confidence_range_rejects_above_one(self) -> None:
        """Confidence > 1.0 must raise ValidationError."""
        with pytest.raises(ValidationError):
            CrystalAnnotation(
                crystal_id="c1",
                bbox=BoundingBox(x=0, y=0, width=10, height=10),
                layer=DepthLayer.FAR,
                confidence=1.5,
            )

    def test_confidence_range_rejects_negative(self) -> None:
        """Confidence < 0.0 must raise ValidationError."""
        with pytest.raises(ValidationError):
            CrystalAnnotation(
                crystal_id="c1",
                bbox=BoundingBox(x=0, y=0, width=10, height=10),
                layer=DepthLayer.FAR,
                confidence=-0.1,
            )

    def test_confidence_defaults_to_one(self) -> None:
        """Confidence defaults to 1.0."""
        ann = CrystalAnnotation(
            crystal_id="c1",
            bbox=BoundingBox(x=0, y=0, width=10, height=10),
            layer=DepthLayer.FAR,
        )
        assert ann.confidence == 1.0

    def test_crystal_system_defaults_to_unknown(self) -> None:
        """Crystal system defaults to UNKNOWN."""
        ann = CrystalAnnotation(
            crystal_id="c1",
            bbox=BoundingBox(x=0, y=0, width=10, height=10),
            layer=DepthLayer.MID,
        )
        assert ann.crystal_system == CrystalSystem.UNKNOWN


class TestDepthLayer:
    def test_has_exactly_three_values(self) -> None:
        """DepthLayer enum has exactly 3 values."""
        assert len(DepthLayer) == 3

    def test_values(self) -> None:
        """DepthLayer has near, mid, and far."""
        assert set(DepthLayer) == {
            DepthLayer.NEAR,
            DepthLayer.MID,
            DepthLayer.FAR,
        }


class TestCrystalSystem:
    def test_has_eight_values(self) -> None:
        """CrystalSystem enum covers 7 systems + unknown."""
        assert len(CrystalSystem) == 8

    def test_includes_unknown(self) -> None:
        """CrystalSystem includes UNKNOWN."""
        assert CrystalSystem.UNKNOWN == "unknown"


class TestFrameAnnotation:
    def test_serialization_roundtrip(
        self, sample_annotation: FrameAnnotation
    ) -> None:
        """FrameAnnotation round-trips through JSON."""
        data = sample_annotation.model_dump(mode="json")
        restored = FrameAnnotation.model_validate(data)
        assert restored.frame_idx == sample_annotation.frame_idx
        assert len(restored.crystals) == len(sample_annotation.crystals)
        assert (
            restored.crystals[0].crystal_id
            == sample_annotation.crystals[0].crystal_id
        )
        assert (
            restored.crystals[0].bbox.x == sample_annotation.crystals[0].bbox.x
        )

    def test_crystals_default_to_empty(self) -> None:
        """Frame with no crystals has empty list."""
        ann = FrameAnnotation(
            frame_idx=0,
            timestamp_s=0.0,
            summary="empty",
        )
        assert ann.crystals == []


class TestVideoAnnotation:
    def test_stores_metadata(self) -> None:
        """VideoAnnotation preserves video metadata."""
        va = VideoAnnotation(
            video_path="/tmp/vid.mp4",
            total_frames=300,
            sampled_frames=10,
            fps=30.0,
            overall_summary="test",
        )
        assert va.total_frames == 300
        assert va.fps == 30.0
        assert va.frame_annotations == []


class TestAnnotatorConfig:
    def test_defaults(self) -> None:
        """AnnotatorConfig has sensible defaults."""
        cfg = AnnotatorConfig()
        assert cfg.model_name == "openai:gpt-4o"
        assert cfg.frame_interval == 30
        assert cfg.max_frames == 0
        assert cfg.process_size == 960
