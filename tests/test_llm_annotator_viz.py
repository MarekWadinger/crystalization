"""Tests for llm_annotator.viz — visualization correctness."""

from __future__ import annotations

import json

import numpy as np

from llm_annotator.types import (
    BoundingBox,
    CrystalAnnotation,
    DepthLayer,
    FrameAnnotation,
)
from llm_annotator.viz import (
    LAYER_COLORS,
    annotation_to_json_str,
    bgr_to_rgb,
    draw_annotations,
    draw_legend,
    render_tracking_overlay,
)


class TestDrawAnnotations:
    def test_modifies_frame(
        self,
        sample_frame: np.ndarray,
        sample_annotation: FrameAnnotation,
    ) -> None:
        """Annotations must produce visible changes."""
        original = sample_frame.copy()
        annotated = draw_annotations(sample_frame, sample_annotation)
        diff = np.sum(np.abs(annotated.astype(int) - original.astype(int)))
        assert diff > 1000, "Annotations should be visible on the frame"

    def test_returns_copy(
        self,
        sample_frame: np.ndarray,
        sample_annotation: FrameAnnotation,
    ) -> None:
        """draw_annotations must not modify the input frame."""
        original = sample_frame.copy()
        draw_annotations(sample_frame, sample_annotation)
        np.testing.assert_array_equal(sample_frame, original)

    def test_at_correct_positions(
        self,
        sample_frame: np.ndarray,
        sample_annotation: FrameAnnotation,
    ) -> None:
        """Bounding boxes appear near the crystal coordinates."""
        annotated = draw_annotations(sample_frame, sample_annotation)
        original = sample_frame.copy()
        # crystal_001 is at (125, 120); check the region
        region = annotated[100:145, 100:155]
        orig_region = original[100:145, 100:155]
        diff = np.sum(np.abs(region.astype(int) - orig_region.astype(int)))
        assert diff > 100, "Annotations should appear near crystal_001"

    def test_show_system_adds_label(
        self,
        sample_frame: np.ndarray,
        sample_annotation: FrameAnnotation,
    ) -> None:
        """show_system=True adds more drawn text."""
        ids_only = draw_annotations(
            sample_frame,
            sample_annotation,
            show_system=False,
        )
        with_system = draw_annotations(
            sample_frame,
            sample_annotation,
            show_system=True,
        )
        diff = np.sum(np.abs(with_system.astype(int) - ids_only.astype(int)))
        assert diff > 0, "show_system should add extra text labels"

    def test_empty_annotation_unchanged(
        self,
        sample_frame: np.ndarray,
    ) -> None:
        """Frame with no crystals only has legend drawn."""
        empty = FrameAnnotation(
            frame_idx=0,
            timestamp_s=0.0,
            summary="empty",
        )
        annotated = draw_annotations(sample_frame, empty)
        # Legend is always drawn, so frame won't be identical
        assert annotated is not sample_frame
        assert annotated.shape == sample_frame.shape


class TestLayerColors:
    def test_distinct_colors(self) -> None:
        """Each depth layer has a different colour."""
        colors = [LAYER_COLORS[ly] for ly in DepthLayer]
        assert len(set(colors)) == 3, "All 3 layers must have distinct colours"

    def test_all_layers_have_colors(self) -> None:
        """Every DepthLayer has a mapping in LAYER_COLORS."""
        for layer in DepthLayer:
            assert layer in LAYER_COLORS


class TestDrawLegend:
    def test_modifies_frame_in_place(
        self,
        sample_frame: np.ndarray,
    ) -> None:
        """draw_legend draws on the frame in-place."""
        original = sample_frame.copy()
        draw_legend(sample_frame)
        diff = np.sum(np.abs(sample_frame.astype(int) - original.astype(int)))
        assert diff > 0, "Legend should modify the frame"

    def test_position_variants(
        self,
        sample_frame: np.ndarray,
    ) -> None:
        """All position options produce visible output."""
        for pos in (
            "top-left",
            "top-right",
            "bottom-left",
            "bottom-right",
        ):
            frame = sample_frame.copy()
            original = frame.copy()
            draw_legend(frame, position=pos)
            diff = np.sum(np.abs(frame.astype(int) - original.astype(int)))
            assert diff > 0, f"Legend at {pos} should be visible"


class TestRenderTrackingOverlay:
    def test_without_previous(
        self,
        sample_frame: np.ndarray,
        sample_annotation: FrameAnnotation,
    ) -> None:
        """Without previous frame, behaves like draw_annotations."""
        result = render_tracking_overlay(sample_frame, sample_annotation, None)
        expected = draw_annotations(sample_frame, sample_annotation)
        np.testing.assert_array_equal(result, expected)

    def test_with_matched_previous_draws_arrows(
        self,
        sample_frame: np.ndarray,
    ) -> None:
        """Matched IDs across frames produce tracking arrows."""
        prev = FrameAnnotation(
            frame_idx=0,
            timestamp_s=0.0,
            crystals=[
                CrystalAnnotation(
                    crystal_id="crystal_001",
                    bbox=BoundingBox(x=100, y=100, width=50, height=40),
                    layer=DepthLayer.FAR,
                ),
            ],
            summary="prev",
        )
        curr = FrameAnnotation(
            frame_idx=1,
            timestamp_s=1.0,
            crystals=[
                CrystalAnnotation(
                    crystal_id="crystal_001",
                    bbox=BoundingBox(x=120, y=110, width=50, height=40),
                    layer=DepthLayer.FAR,
                ),
            ],
            summary="curr",
        )
        without_arrows = draw_annotations(sample_frame, curr)
        with_arrows = render_tracking_overlay(sample_frame, curr, prev)
        diff = np.sum(
            np.abs(with_arrows.astype(int) - without_arrows.astype(int))
        )
        assert diff > 0, "Tracking arrows should be visible"


class TestBgrToRgb:
    def test_swaps_channels(self) -> None:
        """BGR-to-RGB swaps first and last channels."""
        bgr = np.zeros((10, 10, 3), dtype=np.uint8)
        bgr[:, :, 0] = 255  # blue channel
        rgb = bgr_to_rgb(bgr)
        assert rgb[0, 0, 2] == 255  # now in red
        assert rgb[0, 0, 0] == 0  # blue is zero

    def test_preserves_shape(self) -> None:
        """Output shape matches input shape."""
        bgr = np.ones((20, 30, 3), dtype=np.uint8)
        rgb = bgr_to_rgb(bgr)
        assert rgb.shape == bgr.shape


class TestAnnotationToJsonStr:
    def test_returns_valid_json(
        self,
        sample_annotation: FrameAnnotation,
    ) -> None:
        """annotation_to_json_str produces parseable JSON."""
        result = annotation_to_json_str(sample_annotation)
        parsed = json.loads(result)
        assert parsed["frame_idx"] == 0
        assert len(parsed["crystals"]) == 3

    def test_contains_crystal_ids(
        self,
        sample_annotation: FrameAnnotation,
    ) -> None:
        """JSON output includes crystal IDs."""
        result = annotation_to_json_str(sample_annotation)
        assert "crystal_001" in result
        assert "crystal_002" in result
        assert "crystal_003" in result
