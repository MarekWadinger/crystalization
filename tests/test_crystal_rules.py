"""Tests for the port of Ananya's rule-based crystal candidates."""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from crystal_detector import gui_filters
from crystal_detector.rules import (
    add_missing,
    detect,
    frame_candidates,
    frame_scale,
    masks,
)

MID = 280  # x where the ramped liquor is mid-grey (~120)
DATA = Path(__file__).parent / "data"


def labels_at(cands, x: float, y: float) -> list[str]:
    return [
        c["label"]
        for c in cands
        if abs(c["rect"][0][0] - x) < 8 and abs(c["rect"][0][1] - y) < 8
    ]


def test_frame_scale_converts_her_pixels_for_pal_and_1080p():
    # her frames are PAL upscaled 1080/576 = 1.875× on both axes; our PAL crops are not
    assert frame_scale(648) == pytest.approx(
        (576 / 1080, 576 / 1080), rel=1e-3
    )
    # DVR 1080p clips are the same PAL upscaled to 1080 rows (y: same pixel as hers)
    # but stretched ×2.677 horizontally (x: 2.677 / 1.875 her pixels per clip pixel)
    sx, sy = frame_scale(1728)
    assert sy == pytest.approx(1.0, abs=0.01)
    assert sx == pytest.approx(2.677 / 1.875, abs=0.01)


def test_frame_scale_refuses_frames_of_unknown_geometry():
    with pytest.raises(ValueError, match="not an exported annotation frame"):
        frame_scale(1920)  # e.g. her own frames: guessing would be wrong


def test_detect_reproduces_frozen_output_on_her_frame():
    # Crop of her Step-4 frame_00000. The expected boxes are this port's
    # output, frozen after the port matched her notebook candidate for
    # candidate (1845 candidates on her frames 0, 60, 120; 2026-10-21).
    crop = cv2.imread(str(DATA / "ananya_step4_crop.png"), 0)
    assert crop is not None
    want = json.loads((DATA / "ananya_step4_crop_candidates.json").read_text())
    got = detect(cv2.medianBlur(crop, 3))
    assert [c["label"] for c in got] == [c["label"] for c in want]
    for g, w in zip(got, want):
        for key in ("rect", "body_rect"):
            assert np.allclose(np.hstack(g[key]), np.hstack(w[key]))


def test_bright_body_inside_dark_rim_is_crystal(crystal_frame):
    img, paint = crystal_frame
    paint(MID, 200, 30, 30)
    assert labels_at(frame_candidates(img), MID + 15, 215) == ["crystal"]


def test_body_without_dark_rim_is_skip(crystal_frame):
    img, paint = crystal_frame
    paint(MID, 100, 30, 30)  # a real crystal so the frame has rims
    paint(MID, 300, 30, 30, rim=0)
    assert labels_at(frame_candidates(img), MID + 15, 315) == ["skip"]


def test_elongated_or_cut_by_frame_is_not_crystal(crystal_frame):
    img, paint = crystal_frame
    paint(MID, 100, 120, 20)  # aspect ≈ 4 > 2.5
    paint(3, 300, 30, 30)  # body + test band reach the left edge
    cands = frame_candidates(img)
    assert labels_at(cands, MID + 60, 110) == ["skip"]
    assert labels_at(cands, 18, 315) == ["skip"]


def test_specks_below_her_min_size_are_ignored(crystal_frame):
    img, paint = crystal_frame
    paint(MID, 200, 3, 3, rim=2)  # area < (12 px · 0.533 · 0.6)²
    assert labels_at(frame_candidates(img), MID + 1, 201) == []


def test_size_limits_scale_with_the_frame(crystal_frame):
    img, paint = crystal_frame
    paint(MID, 150, 100, 100)  # > 160 her px on PAL, < 160 her px at 1080p
    assert labels_at(frame_candidates(img), MID + 50, 200) == ["skip"]
    hd = np.tile(np.linspace(60, 200, 1728), (1230, 1)).astype(np.uint8)
    cv2.rectangle(hd, (794, 394), (906, 506), 10, -1)  # same px on 1080p
    cv2.rectangle(hd, (800, 400), (900, 500), 250, -1)
    assert labels_at(frame_candidates(hd), 850, 450) == ["crystal"]


def test_boxes_map_back_onto_the_crystal(crystal_frame):
    img, paint = crystal_frame
    paint(MID, 200, 30, 30)
    (c,) = [c for c in frame_candidates(img) if c["label"] == "crystal"]
    (cx, cy), (w, h), _ = c["body_rect"]
    assert cx == pytest.approx(MID + 15, abs=1.5)
    assert cy == pytest.approx(215, abs=1.5)
    assert 30 < min(w, h) < 40  # body + up to 3 her px of rim


def test_masks_fill_body_and_rim_for_crystals_only(crystal_frame):
    img, paint = crystal_frame
    paint(MID, 200, 30, 30)
    paint(MID, 350, 30, 30, rim=0)  # skip: no mask
    lab = masks(img.shape, frame_candidates(img))
    assert lab.max() == 1
    assert lab[215, MID + 15] == 1  # body
    assert lab[215, MID - 1] == 1  # first rim pixel
    assert lab[215, MID - 6] == 0  # past her 3 px (2 px here) rim
    assert lab[365, MID + 15] == 0


def test_add_missing_keeps_existing_and_skips_overlaps():
    existing = np.zeros((20, 20), np.uint16)
    existing[2:6, 2:6] = 1
    extra = np.zeros((20, 20), np.uint16)
    extra[4:8, 4:8] = 1  # overlaps mask 1
    extra[10:14, 10:14] = 2  # free
    out = add_missing(existing, extra)
    assert out.max() == 2
    assert (out[2:6, 2:6] == 1).all()  # existing mask untouched
    assert out[7, 7] == 0  # overlapping candidate dropped whole
    assert (out[10:14, 10:14] == 2).all()


def test_add_rule_candidates_keeps_drawn_masks(crystal_frame):
    img, paint = crystal_frame
    paint(MID, 100, 30, 30)
    paint(MID, 300, 30, 30)
    stack = np.repeat(img[None, :, :, None], 3, axis=-1).astype(np.float32)
    drawn = np.zeros((1, *img.shape), np.uint16)
    drawn[0, 90:140, MID - 10 : MID + 40] = 1  # annotator drew the first
    out = gui_filters.add_rule_candidates(stack, drawn)
    assert out.shape == drawn.shape
    assert out.max() == 2
    assert (out[0, 90:140, MID - 10 : MID + 40] == 1).all()
    assert out[0, 315, MID + 15] == 2
