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
