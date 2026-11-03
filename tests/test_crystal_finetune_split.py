"""Held-out frames must not leak into training through shared copies."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from crystal_detector.finetune import _split


def pair(who: str, stage: str, name: str):
    p = Path("annotations") / who / stage / name
    return p, np.zeros((4, 4, 3), np.uint8), np.ones((4, 4), np.int32)


def test_copies_of_a_held_out_frame_stay_out_of_training():
    pairs = [
        pair("ana", "boiling", "015306.png"),  # copy of patrik's frame
        pair("ana", "drying", "043428.png"),
        pair("patrik", "boiling", "010000.png"),
        pair("patrik", "boiling", "015306.png"),  # patrik's middle: held out
        pair("patrik", "boiling", "020000.png"),
    ]
    train, test = _split(pairs)
    train_names = {(p.parent.name, p.name) for p, _, _ in train}
    for p, _, _ in test:
        assert (p.parent.name, p.name) not in train_names
    assert ("boiling", "015306.png") not in train_names
    assert ("drying", "043428.png") in train_names


def test_frames_still_in_progress_are_not_trained_on(tmp_path, monkeypatch):
    import cv2

    from crystal_detector import finetune
    from crystal_detector.annotate import _label, _wip, _write_empty_label

    folder = tmp_path / "ana" / "boiling"
    folder.mkdir(parents=True)
    finished, started = folder / "010000.png", folder / "020000.png"
    for png in (finished, started):
        cv2.imwrite(str(png), np.zeros((4, 4), np.uint8))
        _write_empty_label(png)
    _wip(started).touch()  # autosaved halfway, never marked done
    monkeypatch.setattr(finetune, "ANNOTATIONS", tmp_path)
    assert [p for p, _, _ in finetune._pairs()] == [finished]
    assert _label(started).exists()
