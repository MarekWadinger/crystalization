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


def _dispose(w, app) -> None:
    """Delete the window in Qt now; left to Python's GC, Qt objects of an old
    window can be freed mid-way through building the next one (segfault)."""
    from qtpy.QtCore import QEvent

    w.close()
    w.deleteLater()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


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
    _dispose(w, app)


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
    w.filterChooser.setCurrentText("Ananya")
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
    assert w.ViewDropDown.isHidden()  # the filter buttons switch the view
    boxes = (
        w.howToBox,
        w.framesBox,
        w.satBox,
        w.filterBox,
        w.drawBox,
        w.modelBox,
    )
    rows = [
        w.l0.getItemPosition(w.l0.indexOf(b))[0] for b in (*boxes, w.statsBox)
    ]
    assert rows == sorted(rows)  # How to first, Progress last
    assert all(s.isHidden() for s in w.sliders[1:])
    assert not w.sliders[0].isHidden()
    for hidden in (w.segBox, w.filtBox, buttons["filter"], buttons["none"]):
        assert hidden.isHidden()
    filters = [
        w.filterChooser.itemText(i) for i in range(w.filterChooser.count())
    ]
    assert filters == ["none", *gui_filters.FILTERS]
    assert not w.filterChooser.isHidden()
    assert w.modelBox.isAncestorOf(w.progress)  # shows once a run starts
    assert w.framesBox.isAncestorOf(w.roi_count) and not w.roi_count.isHidden()
    assert w.roi_count.text().endswith("crystals on this frame")
    assert not buttons["add rule candidates"].isHidden()
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
    w.filterChooser.setCurrentText("Ananya")
    assert "showing Ananya" in w.statusLabel.text()


def test_filters_explain_themselves(window):
    from qtpy.QtCore import Qt

    w, buttons, _ = window
    for i in range(1, w.filterChooser.count()):
        tip = w.filterChooser.itemData(i, Qt.ItemDataRole.ToolTipRole)
        assert "run segments" in tip
    assert "region-select" in buttons["add rule candidates"].toolTip()


def test_added_rule_candidates_are_saved(window):
    w, buttons, png = window
    buttons["add rule candidates"].click()  # autosaves, no Ctrl+S needed
    assert "rule candidates · saved ✓" in w.statusLabel.text()
    seg = np.load(png.with_name("frame_seg.npy"), allow_pickle=True).item()
    assert np.array_equal(seg["masks"], w.cellpix[0])
    assert seg["masks"][115, 295] > 0 and seg["masks"][315, 295] > 0


@pytest.fixture
def team_window(tmp_path, crystal_frame, monkeypatch):
    """A person's three frames across two stages under a fake annotations/."""
    import crystal_detector.annotate as annotate

    img, paint = crystal_frame
    paint(280, 100, 30, 30)
    ann = tmp_path / "annotations"
    frames = [
        ann / "marek" / stage / f"2026-10-30_08-45-33_{t}.png"
        for stage, t in (
            ("boiling", "010000"),
            ("boiling", "020000"),
            ("seeding", "000500"),
        )
    ]
    for p in frames:
        p.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(p), img)
    monkeypatch.setattr(annotate, "ANNOTATIONS", ann)
    gui_filters.install()
    app = QApplication.instance() or QApplication([])
    w = gui.MainW(image=str(frames[0]), logger=logging.getLogger(__name__))
    yield w, {b.text(): b for b in w.findChildren(QPushButton)}, frames
    _dispose(w, app)


def test_frame_switcher_walks_all_my_frames_across_stages(team_window):
    w, buttons, frames = team_window
    assert w.frameChooser.count() == 3
    assert w.windowTitle().endswith("· 1/3")
    buttons["▶"].click()
    buttons["▶"].click()  # past the stage folder
    assert w.filename == str(frames[2]) and w.windowTitle().endswith("· 3/3")
    assert all(s.isHidden() for s in w.sliders[1:])  # stays hidden per load
    buttons["▶"].click()  # wraps
    assert w.filename == str(frames[0])
    w.frameChooser.setCurrentIndex(1)
    assert w.filename == str(frames[1])


def test_no_crystals_saves_empty_label_and_moves_on(team_window):
    w, buttons, frames = team_window
    buttons["no crystals"].click()
    seg = np.load(
        frames[0].with_name(frames[0].stem + "_seg.npy"), allow_pickle=True
    )
    assert seg.item()["masks"].max() == 0
    assert w.filename == str(frames[1])  # next frame to do
    assert w.frameChooser.itemText(0).startswith("●")
    buttons["add rule candidates"].click()  # now it has outlines
    buttons["no crystals"].click()
    assert "delete them first" in w.statusLabel.text()
    assert w.filename == str(frames[1])


def test_switching_saves_untouched_proposals(team_window):
    w, buttons, frames = team_window
    buttons["add rule candidates"].click()
    label = frames[0].with_name(frames[0].stem + "_seg.npy")
    label.unlink()  # as if run's proposals were never saved
    buttons["▶"].click()
    assert label.exists()


def test_switching_leaves_existing_labels_untouched(team_window):
    w, buttons, frames = team_window
    buttons["add rule candidates"].click()  # autosaves frame 0
    label = frames[0].with_name(frames[0].stem + "_seg.npy")
    before = label.stat().st_mtime_ns
    buttons["▶"].click()
    buttons["◀"].click()
    buttons["▶"].click()
    assert label.stat().st_mtime_ns == before


def test_autosave_alone_leaves_the_frame_in_progress(team_window):
    from crystal_detector.annotate import done, scores

    w, buttons, frames = team_window
    buttons["add rule candidates"].click()  # autosaves
    assert frames[0].with_suffix(".wip").exists() and not done(frames[0])
    assert w.frameChooser.itemText(0).startswith("◐")
    assert scores()[0][0] == 0  # not on the leaderboard yet


def test_all_crystals_marked_counts_the_frame_and_moves_on(team_window):
    from crystal_detector.annotate import done, scores

    w, buttons, frames = team_window
    marked = buttons["✓ all crystals marked · next"]
    marked.click()  # nothing outlined yet
    assert "use no crystals" in w.statusLabel.text()
    assert w.filename == str(frames[0])
    assert w.roi_count.text() == "0 crystals on this frame"
    buttons["add rule candidates"].click()
    assert w.roi_count.text() == "1 crystal on this frame"
    marked.click()
    assert done(frames[0]) and not frames[0].with_suffix(".wip").exists()
    assert w.filename == str(frames[1])
    assert w.frameChooser.itemText(0).startswith("●")
    assert scores()[0][0] == 1
    buttons["no crystals"].click()
    buttons["no crystals"].click()
    assert "all frames done" in w.statusLabel.text()


def test_undo_buttons_follow_cellpose_undo(team_window):
    w, buttons, frames = team_window
    undo, undelete = buttons["↶ undo"], buttons["↷ undelete"]
    assert not undo.isEnabled() and not undelete.isEnabled()
    buttons["add rule candidates"].click()
    w.undo.setEnabled(True)  # what Cellpose does once outlines exist
    assert undo.isEnabled()
    undo.click()
    assert w.roi_count.text() == "0 crystals on this frame"


def test_filter_dropdown_none_restores_and_follows_frame_switches(team_window):
    w, buttons, frames = team_window
    w.filterChooser.setCurrentText("flat-field")
    assert w.restore == "filter"
    w.filterChooser.setCurrentText("none")
    assert w.restore is None and "original" in w.statusLabel.text()
    mirrored = np.fliplr(w.stack[0, :, :, 0]).astype(np.uint8)  # another frame
    cv2.imwrite(str(frames[1]), mirrored)
    w.filterChooser.setCurrentText("Ananya")
    buttons["▶"].click()
    assert w.filterChooser.currentText() == "Ananya" and w.restore == "filter"
    want = gui_filters.ananya(w.stack[0].mean(axis=-1))
    assert np.allclose(
        w.stack_filtered[0, :, :, 0], want, atol=1
    )  # new frame's
