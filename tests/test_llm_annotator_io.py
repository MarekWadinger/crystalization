"""Tests for llm_annotator.io — frame extraction and pipeline."""

from __future__ import annotations

import os

import numpy as np
import pytest

from llm_annotator.io import (
    _build_tracking_context,
    _next_crystal_id,
    downscale,
    encode_frame_jpeg,
)
from llm_annotator.types import (
    AnnotatorConfig,
    BoundingBox,
    CrystalAnnotation,
    DepthLayer,
    FrameAnnotation,
)


class TestEncodeFrameJpeg:
    def test_produces_valid_jpeg(self, sample_frame: np.ndarray) -> None:
        """JPEG encoding produces bytes starting with JPEG
        magic.
        """
        jpeg = encode_frame_jpeg(sample_frame, max_dim=240)
        assert len(jpeg) > 0
        assert jpeg[:2] == b"\xff\xd8"

    def test_jpeg_ends_with_eoi(self, sample_frame: np.ndarray) -> None:
        """JPEG encoding produces bytes ending with EOI
        marker.
        """
        jpeg = encode_frame_jpeg(sample_frame, max_dim=240)
        assert jpeg[-2:] == b"\xff\xd9"

    def test_smaller_max_dim_produces_smaller_file(
        self, sample_frame: np.ndarray
    ) -> None:
        """Smaller max_dim yields smaller JPEG output."""
        large = encode_frame_jpeg(sample_frame, max_dim=480)
        small = encode_frame_jpeg(sample_frame, max_dim=120)
        assert len(small) < len(large)


class TestDownscale:
    def test_preserves_aspect_ratio(self, sample_frame: np.ndarray) -> None:
        """Downscaled frame maintains aspect ratio."""
        small = downscale(sample_frame, max_dim=240)
        orig_ratio = sample_frame.shape[1] / sample_frame.shape[0]
        new_ratio = small.shape[1] / small.shape[0]
        assert abs(orig_ratio - new_ratio) < 0.05

    def test_max_dimension_respected(self, sample_frame: np.ndarray) -> None:
        """Largest dimension does not exceed max_dim."""
        small = downscale(sample_frame, max_dim=240)
        assert max(small.shape[:2]) <= 240

    def test_no_upscale(self) -> None:
        """Frame already within max_dim is returned as-is."""
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        result = downscale(frame, max_dim=200)
        # Should be same object (no copy needed)
        assert result is frame

    def test_large_frame_gets_shrunk(self) -> None:
        """1000px frame shrinks to 240 max."""
        frame = np.zeros((1000, 800, 3), dtype=np.uint8)
        result = downscale(frame, max_dim=240)
        assert max(result.shape[:2]) <= 240
        assert result.shape[0] == 240  # height was largest
        assert result.shape[1] == 192  # width scaled


class TestBuildTrackingContext:
    def test_empty_previous(self) -> None:
        """No previous frames yields placeholder text."""
        context = _build_tracking_context([])
        assert "No previous" in context

    def test_includes_crystal_ids(
        self,
        sample_annotation: FrameAnnotation,
    ) -> None:
        """Tracking context includes crystal IDs."""
        context = _build_tracking_context([sample_annotation])
        assert "crystal_001" in context
        assert "crystal_002" in context
        assert "crystal_003" in context

    def test_includes_layer_info(
        self,
        sample_annotation: FrameAnnotation,
    ) -> None:
        """Tracking context includes layer names."""
        context = _build_tracking_context([sample_annotation])
        assert "far" in context
        assert "mid" in context
        assert "near" in context

    def test_includes_positions(
        self,
        sample_annotation: FrameAnnotation,
    ) -> None:
        """Tracking context includes crystal positions."""
        context = _build_tracking_context([sample_annotation])
        assert "125" in context
        assert "120" in context


class TestNextCrystalId:
    def test_increments_from_max(
        self,
        sample_annotation: FrameAnnotation,
    ) -> None:
        """Next ID is one more than the max existing ID."""
        next_id = _next_crystal_id([sample_annotation])
        assert next_id == 4

    def test_starts_at_one_when_empty(self) -> None:
        """No previous annotations starts numbering at 1."""
        next_id = _next_crystal_id([])
        assert next_id == 1

    def test_handles_non_sequential_ids(self) -> None:
        """Skipped IDs still return max + 1."""
        ann = FrameAnnotation(
            frame_idx=0,
            timestamp_s=0.0,
            crystals=[
                CrystalAnnotation(
                    crystal_id="crystal_010",
                    bbox=BoundingBox(x=0, y=0, width=10, height=10),
                    layer=DepthLayer.FAR,
                ),
                CrystalAnnotation(
                    crystal_id="crystal_005",
                    bbox=BoundingBox(x=0, y=0, width=10, height=10),
                    layer=DepthLayer.MID,
                ),
            ],
            summary="sparse ids",
        )
        next_id = _next_crystal_id([ann])
        assert next_id == 11


class TestExtractFrames:
    def test_respects_interval(self) -> None:
        """extract_frames samples at the configured interval."""
        video = "datasets/Screen Recording 2026-03-09 at 17.25.02.mov"
        if not os.path.exists(video):
            pytest.skip("Sample video not available")
        from llm_annotator.io import extract_frames

        config = AnnotatorConfig(frame_interval=60, max_frames=3)
        frames = extract_frames(video, config)
        assert len(frames) <= 3
        if len(frames) >= 2:
            assert frames[1][0] - frames[0][0] == 60

    def test_max_frames_cap(self) -> None:
        """extract_frames respects max_frames limit."""
        video = "datasets/Screen Recording 2026-03-09 at 17.25.02.mov"
        if not os.path.exists(video):
            pytest.skip("Sample video not available")
        from llm_annotator.io import extract_frames

        config = AnnotatorConfig(frame_interval=1, max_frames=2)
        frames = extract_frames(video, config)
        assert len(frames) <= 2
