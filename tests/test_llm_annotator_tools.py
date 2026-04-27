"""Tests for llm_annotator.tools — agent tool functions."""

from __future__ import annotations

import base64
import math
from unittest.mock import MagicMock

import cv2
import numpy as np
import pytest

from llm_annotator.agent import FrameContext
from llm_annotator.tools import (
    _crop_region,
    classify_crystal_system,
    compare_frames,
    estimate_growth_rate,
    generate_histogram,
    measure_crystal,
)
from llm_annotator.types import (
    AnnotatorConfig,
    BoundingBox,
    CrystalAnnotation,
    CrystalSystem,
    DepthLayer,
    FrameAnnotation,
)

_DUMMY_BGR = np.zeros((10, 10, 3), dtype=np.uint8)


def _make_ctx(
    frame_bgr: np.ndarray = _DUMMY_BGR,
    *,
    previous: list[FrameAnnotation] | None = None,
    frame_idx: int = 0,
    timestamp_s: float = 0.0,
) -> MagicMock:
    """Build a mock RunContext wrapping a FrameContext."""
    ctx = MagicMock()
    ctx.deps = FrameContext(
        frame_bytes=b"",
        frame_bgr=frame_bgr,
        frame_idx=frame_idx,
        timestamp_s=timestamp_s,
        fps=30.0,
        previous_annotations=previous or [],
        config=AnnotatorConfig(),
    )
    return ctx


@pytest.fixture
def mock_run_context(
    sample_frame: np.ndarray,
    sample_annotation: FrameAnnotation,
) -> MagicMock:
    """Create a mock RunContext with FrameContext deps."""
    return _make_ctx(sample_frame, previous=[sample_annotation])


class TestCropRegion:
    def test_crops_correct_size(self, sample_frame: np.ndarray) -> None:
        """Crop returns the expected region dimensions."""
        crop = _crop_region(sample_frame, 200.0, 200.0, 50.0)
        assert crop.shape[0] == 100  # height: 150-250
        assert crop.shape[1] == 100  # width: 150-250

    def test_clamps_to_frame_bounds(self, sample_frame: np.ndarray) -> None:
        """Crop at frame edge clamps without error."""
        crop = _crop_region(sample_frame, 0.0, 0.0, 50.0)
        assert crop.shape[0] == 50  # y: 0 to 50
        assert crop.shape[1] == 50  # x: 0 to 50

    def test_bottom_right_corner(self, sample_frame: np.ndarray) -> None:
        """Crop at bottom-right edge clamps correctly."""
        h, w = sample_frame.shape[:2]
        crop = _crop_region(sample_frame, float(w), float(h), 30.0)
        assert crop.shape[0] == 30  # clamped to [h-30, h]
        assert crop.shape[1] == 30  # clamped to [w-30, w]


class TestMeasureCrystal:
    @pytest.mark.asyncio
    async def test_returns_positive_dimensions(
        self, mock_run_context: MagicMock
    ) -> None:
        """measure_crystal returns non-zero dimensions for
        a region containing a dark rectangle.
        """
        # Dark rectangle is at (100,100)-(150,140)
        result = await measure_crystal(
            mock_run_context, x=125.0, y=120.0, radius=40.0
        )
        assert result.width_px > 0
        assert result.height_px > 0
        assert result.area_px > 0

    @pytest.mark.asyncio
    async def test_aspect_ratio_is_valid(
        self, mock_run_context: MagicMock
    ) -> None:
        """Aspect ratio equals width / height."""
        result = await measure_crystal(
            mock_run_context, x=125.0, y=120.0, radius=40.0
        )
        expected_aspect = (
            result.width_px / result.height_px
            if result.height_px > 1e-6
            else 0.0
        )
        assert abs(result.aspect_ratio - expected_aspect) < 0.01

    @pytest.mark.asyncio
    async def test_uniform_region_falls_back(self) -> None:
        """Uniform region (no contours) falls back to
        crop dimensions.
        """
        uniform = np.ones((100, 100, 3), dtype=np.uint8) * 128
        ctx = _make_ctx(uniform)
        result = await measure_crystal(ctx, x=50.0, y=50.0, radius=20.0)
        assert result.width_px > 0
        assert result.height_px > 0


class TestCompareFrames:
    @pytest.mark.asyncio
    async def test_no_previous_returns_zeros(self) -> None:
        """Missing previous frame returns all-zero result."""
        ctx = _make_ctx(frame_idx=1, timestamp_s=1.0)
        result = await compare_frames(ctx, previous_frame_idx=0)
        assert result.appeared == 0
        assert result.disappeared == 0
        assert result.persistent == 0

    @pytest.mark.asyncio
    async def test_same_frame_all_persistent(
        self,
        mock_run_context: MagicMock,
        sample_annotation: FrameAnnotation,
    ) -> None:
        """Comparing a frame with itself shows all crystals
        as persistent.
        """
        # Only one annotation with frame_idx=0
        mock_run_context.deps.previous_annotations = [sample_annotation]
        result = await compare_frames(mock_run_context, previous_frame_idx=0)
        assert result.persistent == len(sample_annotation.crystals)
        assert result.appeared == 0
        assert result.disappeared == 0

    @pytest.mark.asyncio
    async def test_new_crystals_count_as_appeared(self) -> None:
        """Crystals in current but not previous are 'appeared'."""
        prev = FrameAnnotation(
            frame_idx=0,
            timestamp_s=0.0,
            crystals=[
                CrystalAnnotation(
                    crystal_id="c1",
                    bbox=BoundingBox(x=100, y=100, width=20, height=20),
                    layer=DepthLayer.FAR,
                ),
            ],
            summary="one",
        )
        curr = FrameAnnotation(
            frame_idx=1,
            timestamp_s=1.0,
            crystals=[
                CrystalAnnotation(
                    crystal_id="c1",
                    bbox=BoundingBox(x=105, y=105, width=20, height=20),
                    layer=DepthLayer.FAR,
                ),
                CrystalAnnotation(
                    crystal_id="c2",
                    bbox=BoundingBox(x=400, y=400, width=20, height=20),
                    layer=DepthLayer.MID,
                ),
            ],
            summary="two",
        )
        ctx = _make_ctx(
            previous=[prev, curr],
            frame_idx=1,
            timestamp_s=1.0,
        )
        result = await compare_frames(ctx, previous_frame_idx=0)
        assert result.persistent == 1
        assert result.appeared == 1
        assert result.disappeared == 0

    @pytest.mark.asyncio
    async def test_displacement_computed(self) -> None:
        """Mean displacement reflects actual movement."""
        prev = FrameAnnotation(
            frame_idx=0,
            timestamp_s=0.0,
            crystals=[
                CrystalAnnotation(
                    crystal_id="c1",
                    bbox=BoundingBox(x=100, y=100, width=20, height=20),
                    layer=DepthLayer.FAR,
                ),
            ],
            summary="one",
        )
        curr = FrameAnnotation(
            frame_idx=1,
            timestamp_s=1.0,
            crystals=[
                CrystalAnnotation(
                    crystal_id="c1",
                    bbox=BoundingBox(x=103, y=104, width=20, height=20),
                    layer=DepthLayer.FAR,
                ),
            ],
            summary="moved",
        )
        ctx = _make_ctx(
            previous=[prev, curr],
            frame_idx=1,
            timestamp_s=1.0,
        )
        result = await compare_frames(ctx, previous_frame_idx=0)
        expected = math.hypot(3, 4)
        assert abs(result.mean_displacement_px - expected) < 0.1


class TestClassifyCrystalSystem:
    @pytest.mark.asyncio
    async def test_returns_valid_system(
        self, mock_run_context: MagicMock
    ) -> None:
        """classify_crystal_system returns a valid
        CrystalSystem value.
        """
        result = await classify_crystal_system(
            mock_run_context, x=125.0, y=120.0, radius=40.0
        )
        assert result in [s.value for s in CrystalSystem]

    @pytest.mark.asyncio
    async def test_square_classified_as_cubic(self) -> None:
        """A square shape should classify as cubic."""
        frame = np.ones((200, 200, 3), dtype=np.uint8) * 200
        cv2.rectangle(frame, (70, 70), (130, 130), (30, 30, 30), -1)
        ctx = _make_ctx(frame)
        result = await classify_crystal_system(
            ctx, x=100.0, y=100.0, radius=50.0
        )
        assert result == CrystalSystem.CUBIC

    @pytest.mark.asyncio
    async def test_elongated_rect_not_cubic(self) -> None:
        """An elongated rectangle should not classify as
        cubic.
        """
        frame = np.ones((200, 200, 3), dtype=np.uint8) * 200
        cv2.rectangle(frame, (50, 80), (150, 120), (30, 30, 30), -1)
        ctx = _make_ctx(frame)
        result = await classify_crystal_system(
            ctx, x=100.0, y=100.0, radius=70.0
        )
        assert result != CrystalSystem.CUBIC

    @pytest.mark.asyncio
    async def test_uniform_returns_unknown(self) -> None:
        """Uniform image (no contours) returns UNKNOWN."""
        uniform = np.ones((100, 100, 3), dtype=np.uint8) * 128
        ctx = _make_ctx(uniform)
        result = await classify_crystal_system(
            ctx, x=50.0, y=50.0, radius=30.0
        )
        assert result == CrystalSystem.UNKNOWN


class TestEstimateGrowthRate:
    @pytest.mark.asyncio
    async def test_single_observation_zero_rate(self) -> None:
        """One observation gives growth rate of 0."""
        ann = FrameAnnotation(
            frame_idx=0,
            timestamp_s=0.0,
            crystals=[
                CrystalAnnotation(
                    crystal_id="c1",
                    bbox=BoundingBox(x=100, y=100, width=20, height=20),
                    layer=DepthLayer.FAR,
                ),
            ],
            summary="one",
        )
        ctx = _make_ctx(previous=[ann])
        result = await estimate_growth_rate(ctx, "c1")
        assert result.growth_rate_px_per_frame == 0.0
        assert result.frames_observed == 1

    @pytest.mark.asyncio
    async def test_growing_crystal_positive_rate(self) -> None:
        """Growing crystal yields positive growth rate."""
        ann0 = FrameAnnotation(
            frame_idx=0,
            timestamp_s=0.0,
            crystals=[
                CrystalAnnotation(
                    crystal_id="c1",
                    bbox=BoundingBox(x=100, y=100, width=20, height=20),
                    layer=DepthLayer.FAR,
                ),
            ],
            summary="small",
        )
        ann1 = FrameAnnotation(
            frame_idx=10,
            timestamp_s=1.0,
            crystals=[
                CrystalAnnotation(
                    crystal_id="c1",
                    bbox=BoundingBox(x=100, y=100, width=40, height=40),
                    layer=DepthLayer.FAR,
                ),
            ],
            summary="bigger",
        )
        ctx = _make_ctx(
            previous=[ann0, ann1],
            frame_idx=10,
            timestamp_s=1.0,
        )
        result = await estimate_growth_rate(ctx, "c1")
        assert result.growth_rate_px_per_frame > 0
        assert result.frames_observed == 2

    @pytest.mark.asyncio
    async def test_unknown_crystal_zero_observed(self) -> None:
        """Unknown crystal ID gives 0 observations."""
        ctx = _make_ctx()
        result = await estimate_growth_rate(ctx, "nonexistent")
        assert result.frames_observed == 0
        assert result.growth_rate_px_per_frame == 0.0


class TestGenerateHistogram:
    @pytest.mark.asyncio
    async def test_empty_layer_returns_empty(self) -> None:
        """No crystals in target layer gives empty result."""
        ann = FrameAnnotation(
            frame_idx=0,
            timestamp_s=0.0,
            crystals=[
                CrystalAnnotation(
                    crystal_id="c1",
                    bbox=BoundingBox(x=100, y=100, width=20, height=20),
                    layer=DepthLayer.FAR,
                ),
            ],
            summary="far only",
        )
        ctx = _make_ctx(previous=[ann])
        result = await generate_histogram(ctx, "near")
        assert result.bin_edges == []
        assert result.counts == []
        assert result.image_base64 == ""

    @pytest.mark.asyncio
    async def test_populated_layer_returns_image(self) -> None:
        """Layer with crystals returns a base64 PNG."""
        crystals = [
            CrystalAnnotation(
                crystal_id=f"c{i}",
                bbox=BoundingBox(
                    x=float(i * 20),
                    y=float(i * 20),
                    width=float(10 + i * 5),
                    height=float(10 + i * 3),
                ),
                layer=DepthLayer.FAR,
            )
            for i in range(1, 6)
        ]
        ann = FrameAnnotation(
            frame_idx=0,
            timestamp_s=0.0,
            crystals=crystals,
            summary="five far crystals",
        )
        ctx = _make_ctx(previous=[ann])
        result = await generate_histogram(ctx, "far")
        assert len(result.bin_edges) > 0
        assert len(result.counts) > 0
        # Verify it is valid base64
        decoded = base64.b64decode(result.image_base64)
        # PNG magic bytes
        assert decoded[:4] == b"\x89PNG"
