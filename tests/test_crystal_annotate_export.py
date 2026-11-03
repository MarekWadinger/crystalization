"""Tests for exporting annotation frames from a video and its sidecar."""

from __future__ import annotations

import json

import cv2
import numpy as np
import pytest

from crystal_detector import annotate


@pytest.fixture
def video(tmp_path, monkeypatch):
    """100 s synthetic PAL video, sidecar in datasets/, two seeded batches."""
    root, ann = tmp_path / "repo", tmp_path / "repo" / "annotations"
    (root / "datasets").mkdir(parents=True)
    monkeypatch.setattr(annotate, "ROOT", root)
    monkeypatch.setattr(annotate, "ANNOTATIONS", ann)
    path = tmp_path / "nas" / "2026-10-30 08-45-33.mkv"
    path.parent.mkdir()
    out = cv2.VideoWriter(
        str(path.with_suffix(".avi")),
        cv2.VideoWriter.fourcc(*"MJPG"),
        1,
        (720, 576),
    )
    for i in range(100):
        out.write(np.full((576, 720, 3), 100 + i, np.uint8))
    out.release()
    path.with_suffix(".avi").rename(path)
    segments = [
        {"phase": "filling", "t_start": 0, "t_end": 20},
        {"phase": "boiling", "t_start": 20, "t_end": 60},
        {"phase": "drying", "t_start": 60, "t_end": 80},
        {"phase": "boiling", "t_start": 80, "t_end": 100},  # batch 2
    ]
    sidecar = root / "datasets" / "2026-10-30 08-45-33.json"
    sidecar.write_text(json.dumps({"segments": segments}))
    return path, ann


def test_export_samples_every_crystal_segment_per_person(video):
    path, ann = video
    annotate.export(path, ["ana", "bob"], per_stage=2)
    for name in ("ana", "bob"):
        boiling = sorted((ann / name / "boiling").glob("*.png"))
        assert len(boiling) == 4  # 2 batches × 2 frames
        assert len(list((ann / name / "drying").glob("*.png"))) == 2
        assert not (ann / name / "filling").exists()  # no crystals yet
        assert all(p.name.startswith("2026-10-30_08-45-33_") for p in boiling)
    stamps = {p.name for p in ann.rglob("*.png")}
    assert len(stamps) == 12  # distinct timestamps across people


def test_export_skips_frames_already_exported_under_old_names(video):
    path, ann = video
    annotate.export(path, ["ana"], per_stage=1)
    first = sorted((ann / "ana" / "boiling").glob("*.png"))[0]
    legacy = first.with_name(first.name.split("_")[-1])  # HHMMSS.png
    first.rename(legacy)
    annotate.export(path, ["ana"], per_stage=1)
    assert legacy.exists() and not first.exists()


def test_export_without_sidecar_fails_clearly(video, tmp_path):
    path, _ = video
    other = tmp_path / "nas" / "2026-11-01 09-00-00.mkv"
    path.rename(other)
    with pytest.raises(SystemExit, match="no sidecar"):
        annotate.export(other, ["ana"])
