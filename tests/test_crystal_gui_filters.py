"""Headless Cellpose GUI: the repo buttons exist and behave."""

from __future__ import annotations

import logging
import os

import cv2
import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_API", "pyqt6")
pytest.importorskip("qtpy")
gui = pytest.importorskip("cellpose.gui.gui")

from cellpose.gui import io  # noqa: E402
from qtpy.QtWidgets import QApplication, QPushButton  # noqa: E402

from crystal_detector import gui_filters  # noqa: E402


@pytest.fixture
def window(tmp_path, crystal_frame):
    img, paint = crystal_frame
    paint(280, 100, 30, 30)
    paint(280, 300, 30, 30)
    png = tmp_path / "frame.png"
    cv2.imwrite(str(png), img)
    gui_filters.install()
    app = QApplication.instance() or QApplication([])
    w = gui.MainW(image=str(png), logger=logging.getLogger(__name__))
    yield w, {b.text(): b for b in w.findChildren(QPushButton)}, png
    w.close()
    app.processEvents()


def test_add_rule_candidates_button_keeps_drawn_masks(window):
    w, buttons, _ = window
    drawn = np.zeros((1, 461, 648), np.uint16)
    drawn[0, 90:140, 270:320] = 1  # over the first crystal
    io._masks_to_gui(w, drawn, outlines=None)
    w.ismanual[:] = True
    buttons["add rule candidates"].click()
    n = int(w.cellpix.max())
    assert (w.cellpix[0, 90:140, 270:320] == 1).all()  # drawn mask kept
    assert w.cellpix[0, 315, 295] > 1  # the second crystal was added
    assert w.ismanual[0] and not w.ismanual[1:].any()
    buttons["add rule candidates"].click()
    assert w.cellpix.max() == n  # nothing duplicated


def test_ananya_filter_shows_her_enhancement_but_saves_original(window):
    w, buttons, png = window
    before = w.stack.copy()
    buttons["Ananya"].click()
    assert w.restore == "filter" and w.view == "restored"
    want = gui_filters.ananya(before[0].mean(axis=-1)).astype(np.float32)
    assert np.allclose(w.stack_filtered[0, :, :, 0], want, atol=1)
    assert np.array_equal(w.stack, before)
    buttons["add rule candidates"].click()  # autosave while filtered
    seg = np.load(png.with_name("frame_seg.npy"), allow_pickle=True).item()
    assert seg["restore"] is None  # labels stay on the original pixels


def test_panel_keeps_only_what_annotators_use(window):
    w, buttons, _ = window
    colors = [w.RGBDropDown.itemText(i) for i in range(w.RGBDropDown.count())]
    views = [w.ViewDropDown.itemText(i) for i in range(w.ViewDropDown.count())]
    assert colors == ["gray", "spectral"]
    assert w.color == "gray"
    assert views == ["image", "restored"]
    rows = [
        w.l0.getItemPosition(w.l0.indexOf(b))[0]
        for b in (w.satBox, w.filterBox, w.drawBox, w.modelBox)
    ]
    assert rows == sorted(rows)  # Views, Image filtering, Drawing, models
    assert all(s.isHidden() for s in w.sliders[1:])
    assert not w.sliders[0].isHidden()
    for hidden in (w.segBox, w.filtBox, buttons["filter"]):
        assert hidden.isHidden()
    for moved in (w.progress, w.roi_count):  # still needed by the model run
        assert w.modelBox.isAncestorOf(moved)
    assert not w.roi_count.isHidden()  # progress shows once a run starts
    for kept in (
        "none",
        "flat-field",
        "high-pass",
        "sharpness",
        "Ananya",
        "add rule candidates",
    ):
        assert not buttons[kept].isHidden()
    assert not w.ModelButtonC.isHidden()  # fine-tuned model's run


def test_model_is_preselected_and_progress_shows_only_on_run(window):
    w, _, _ = window
    from crystal_detector.analyze import HF_MODEL_FILE

    if w.ModelChooseC.findText(HF_MODEL_FILE) < 0:
        pytest.skip("fine-tuned model not registered on this machine")
    assert w.ModelChooseC.currentText() == HF_MODEL_FILE
    assert w.progress.isHidden()


def test_window_title_names_person_stage_video_and_progress():
    from crystal_detector.annotate import ANNOTATIONS

    new = ANNOTATIONS / "erika" / "boiling" / "2026-10-30_08-45-33_032557.png"
    old = ANNOTATIONS / "erika" / "boiling" / "023836.png"
    assert (
        gui_filters.frame_title(str(new), "13/27")
        == "erika · boiling · 2026-10-30 08-45-33 @ 03:25:57 · 13/27"
    )
    assert (
        gui_filters.frame_title(str(old))
        == "erika · boiling · 2026-02-04 11-08-51 @ 02:38:36"
    )
    assert gui_filters.frame_title("/tmp/x/frame.png") == "frame.png"


def test_window_shows_steps_and_save_confirmation(window):
    w, buttons, _ = window
    assert not w.howToBox.isHidden() and not w.statsBox.isHidden()
    from crystal_detector.annotate import scores

    for _, total, who in scores():
        assert who in w.leaderboardLabel.text()
        assert f"/{total}" in w.leaderboardLabel.text()
    from cellpose.gui import io

    io._save_sets(w)  # what every Cellpose edit triggers
    assert w.statusLabel.text().startswith("Last: saved ✓ 0 crystals")
    buttons["Ananya"].click()
    assert "showing Ananya" in w.statusLabel.text()


def test_filter_buttons_explain_themselves(window):
    _, buttons, _ = window
    for name in gui_filters.FILTERS:
        assert "run segments" in buttons[name].toolTip()
    assert "region-select" in buttons["add rule candidates"].toolTip()


def test_added_rule_candidates_are_saved(window):
    w, buttons, png = window
    buttons["add rule candidates"].click()  # autosaves, no Ctrl+S needed
    assert "rule candidates · saved ✓" in w.statusLabel.text()
    seg = np.load(png.with_name("frame_seg.npy"), allow_pickle=True).item()
    assert np.array_equal(seg["masks"], w.cellpix[0])
    assert seg["masks"][115, 295] > 0 and seg["masks"][315, 295] > 0
