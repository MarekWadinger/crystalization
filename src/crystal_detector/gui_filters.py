"""Add the repo's deterministic preprocessors to the Cellpose GUI filter box.

For grey annotation frames the panel is decluttered (:func:`declutter`): no
RGB/red/green/blue colour modes or their sliders, no gradXY/cellprob views,
no generic cpsam model box (the fine-tuned model runs from *user-trained
models*), no Cellpose ``filter`` and its settings; *Image filtering* sits
right under *Views*, which loses the view dropdown (the filter buttons
switch to *restored*, ``none`` back). *How to* comes first and holds a frame
*Frames* box under it switches between all of the person's frames (◀ ▶,
list) and marks them done (**✓ all crystals marked**, **no crystals**).

*Image filtering* is one dropdown, ``none`` (the original) and:
**flat-field** (illumination + CLAHE, what ``analyze.py`` feeds
the model), **high-pass** (Gaussian residual, ``optics.highpass``),
**sharpness** (local Laplacian variance, ``annotator.sharpness``) and
**Ananya** (her enhancement from ``enhance.py``: CLAHE + sharpen, leveling,
CLAHE + sharpen). Each one replaces the displayed image and the image ``run``
segments, also on the next frame; the view switches to *restored*.

Under *user-trained models*, **add rule candidates** adds her *crystal*
candidates as filled boxes wherever there is no mask yet; on an empty frame
that is all of them, after ``run`` only those the model missed.

Labels stay bound to the original pixels: the filtered image is never
written into ``_seg.npy`` (Cellpose would otherwise train on it), so the
model is always trained on the same flat-field frames ``analyze.py`` uses.

    from crystal_detector import gui_filters; gui_filters.install()
    from cellpose.gui import gui; gui.run(image=...)
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

import cv2
import numpy as np

from .export_frames import flat_field_correction

Filter = Callable[
    [np.ndarray], np.ndarray
]  # gray float32 (Ly, Lx) -> any range


def _flat_field(gray: np.ndarray) -> np.ndarray:
    bgr = cv2.cvtColor(
        np.clip(gray, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR
    )
    return flat_field_correction(bgr)[..., 0].astype(np.float32)


def _highpass(gray: np.ndarray) -> np.ndarray:
    from optics.highpass import DEFAULT_SIGMA_PX, highpass

    res = highpass(gray, DEFAULT_SIGMA_PX)
    return np.minimum(
        res, np.percentile(res, 99.5)
    )  # ponytail: fixed σ, clip outliers


def _sharpness(gray: np.ndarray) -> np.ndarray:
    from annotator.sharpness import compute_sharpness_map

    return compute_sharpness_map(gray.astype(np.uint8), kernel=15).astype(
        np.float32
    )


def ananya(gray: np.ndarray) -> np.ndarray:
    """Her enhancement on an annotation frame; ValueError on other sizes."""
    from .enhance import ananya_enhance
    from .rules import frame_scale

    return ananya_enhance(gray, frame_scale(gray.shape[1]))


FILTERS: dict[str, Filter] = {
    "flat-field": _flat_field,
    "high-pass": _highpass,
    "sharpness": _sharpness,
    "Ananya": ananya,
}
_SEGMENTS = " Also what run segments; labels stay on the original."
FILTER_TIPS = {
    "none": "The original image.",
    "flat-field": "Even out the illumination and boost local contrast "
    "(what the model was trained on)." + _SEGMENTS,
    "high-pass": "Remove slow brightness changes, keep edges." + _SEGMENTS,
    "sharpness": "Show where the image is in focus (bright = sharp)."
    + _SEGMENTS,
    "Ananya": "Ananya's enhancement: crisp dark crystal outlines "
    "(CLAHE + sharpen, leveling, CLAHE + sharpen)." + _SEGMENTS,
}


def frame_title(filename: str, progress: str = "") -> str:
    """Window title: who · stage · video @ offset · progress."""
    from .annotate import ANNOTATIONS, frame_label

    png = Path(filename).resolve()
    if len(png.parents) > 2 and png.parents[2] == ANNOTATIONS.resolve():
        title = f"{png.parents[1].name} · {frame_label(png)}"
    else:
        title = png.name
    return f"{title} · {progress}" if progress else title


HOW_TO = (
    "<table cellspacing='2'>"
    + "".join(
        f"<tr><td><b>{key}</b>&nbsp;&nbsp;</td><td>{does}</td></tr>"
        for key, does in (
            ("run", "pre-draw outlines (optional)"),
            ("Shift+click", "draw an outline"),
            ("Ctrl/⌘+click", "delete one"),
            ("region-select", "delete many"),
        )
    )
    + "</table>"
)


def say(w, msg: str, terminal: bool = True) -> None:
    """Show the outcome of the last action under the leaderboard."""
    if terminal:
        print(f"GUI_INFO: {msg}")
    w.statusLabel.setText(f"Last: {msg}")
    w.statusLabel.show()  # hidden until the first action


# Cellpose dropdown entries annotators of grey frames never need
HIDDEN_COLORS = ("RGB", "red=R", "green=G", "blue=B")
HIDDEN_VIEWS = ("gradXY", "cellprob")  # model internals; blue before run


def _hide_channel_sliders(w) -> None:
    for s in w.sliders[1:]:  # green, blue: Cellpose re-shows them per load
        s.hide()


def my_frames(w) -> list[Path]:
    """All frames of the person whose frame is loaded, as annotate.py orders them."""
    from .annotate import ANNOTATIONS

    png = Path(str(getattr(w, "filename", ""))).resolve()
    if len(png.parents) > 2 and png.parents[2] == ANNOTATIONS.resolve():
        return sorted(png.parents[1].glob("*/*.png"))
    return []


def refresh_frames(w) -> None:
    """Frame list: ● done, ◐ in progress, ○ not started; current selected."""
    from qtpy.QtCore import Qt

    from .annotate import _label, done, frame_label

    frames = my_frames(w)
    cur = Path(str(w.filename)).resolve()
    w.frameChooser.blockSignals(True)  # repopulating is not a user switch
    w.frameChooser.clear()
    for i, p in enumerate(frames):
        stage, video_at = frame_label(p).split(" · ", 1)
        # not ✓: the native popup already ticks the open frame
        mark = "●" if done(p) else "◐" if _label(p).exists() else "○"
        w.frameChooser.addItem(f"{mark} {stage} @ {video_at.split(' @ ')[1]}")
        w.frameChooser.setItemData(
            i, frame_label(p), Qt.ItemDataRole.ToolTipRole
        )
    if cur in frames:
        w.frameChooser.setCurrentIndex(frames.index(cur))
    w.frameChooser.blockSignals(False)
    view = w.frameChooser.view()  # popup as wide as its longest entry
    view.setMinimumWidth(view.sizeHintForColumn(0) + 24)
    for widget in (w.frameChooser, *w.frameButtons):
        widget.setEnabled(bool(frames))


def go_to(w, i: int) -> None:
    """Load frame i of my_frames (wraps around)."""
    from cellpose.gui import io

    from .annotate import _label

    frames = my_frames(w)
    cur = Path(str(w.filename)).resolve()
    if not frames or frames[i % len(frames)] == cur:
        return
    # edits autosave; only run proposals accepted untouched have no label yet
    if w.loaded and int(w.cellpix.max()) > 0 and not _label(cur).exists():
        io._save_sets_with_check(w)
    name = w.filterChooser.currentText()
    w.clear_restore()  # Cellpose keeps the old frame's filtered image
    io._load_image(w, filename=str(frames[i % len(frames)]))
    if name != "none":
        w.filterChooser.setCurrentText(name)  # same filter on the new frame


def step(w, by: int) -> None:
    frames = my_frames(w)
    cur = Path(str(w.filename)).resolve()
    if cur in frames:
        go_to(w, frames.index(cur) + by)


def next_todo(w) -> None:
    """Go to the next frame that is not done, or say that all are."""
    from .annotate import done

    frames = my_frames(w)
    i = frames.index(Path(str(w.filename)).resolve())
    todo = [
        j
        for j in range(i + 1, i + len(frames))
        if not done(frames[j % len(frames)])
    ]
    if todo:
        go_to(w, todo[0])
    else:
        refresh_frames(w)
        refresh_stats(w)


def mark_done(w) -> None:
    """All crystals outlined: save, drop the in-progress marker, move on."""
    from cellpose.gui import io

    from .annotate import _wip

    if not w.loaded or not my_frames(w):
        return
    n = int(w.cellpix.max())
    if n == 0:
        say(w, "nothing outlined: use no crystals for an empty frame")
        return
    io._save_sets_with_check(w)  # also covers run proposals left untouched
    _wip(Path(str(w.filename))).unlink(missing_ok=True)
    next_todo(w)
    say(w, f"done ✓ {n} crystals" + _all_done(w))


def mark_empty(w) -> None:
    """Save an empty label (Cellpose greys out save at zero masks)."""
    from .annotate import _write_empty_label

    if not w.loaded or not my_frames(w):
        return
    if int(w.cellpix.max()) > 0:
        say(
            w,
            "frame has outlines: delete them first, or press ✓ all crystals marked",
        )
        return
    _write_empty_label(Path(str(w.filename)))
    next_todo(w)
    say(w, "done ✓ no crystals" + _all_done(w))


def _all_done(w) -> str:
    from .annotate import done

    return (
        " · all frames done, close the window"
        if all(map(done, my_frames(w)))
        else ""
    )


def declutter(w) -> None:
    """Hide Cellpose controls that do nothing for grey annotation frames."""
    from qtpy.QtCore import Qt
    from qtpy.QtGui import QFont
    from qtpy.QtWidgets import (
        QComboBox,
        QGridLayout,
        QGroupBox,
        QLabel,
        QPushButton,
        QVBoxLayout,
    )

    for box, names in (
        (w.RGBDropDown, HIDDEN_COLORS),
        (w.ViewDropDown, HIDDEN_VIEWS),
    ):
        for name in names:  # removed, so the R/G/B and W/S keys skip them too
            box.removeItem(box.findText(name))
    w.ViewDropDown.hide()  # image/restored: the filter buttons switch it
    _hide_channel_sliders(w)
    for label in w.satBox.findChildren(QLabel):
        if label.text() in (
            "green:",
            "blue:",
            "[R / G / B \n toggles color ]",
            "[pageup / pagedown]",
        ):
            label.hide()
        elif "red" in label.text():
            label.setText("gray:")
            label.setStyleSheet("")
    # generic model box: the team runs the fine-tuned model under
    # user-trained models, so keep only its progress bar there (the ROI
    # count goes to Frames, next to the done buttons it informs)
    w.modelBoxG.addWidget(w.progress, w.modelBoxG.rowCount(), 0, 1, 9)
    w.progress.hide()  # shown when a run starts (compute_segmentation patch)
    from .analyze import HF_MODEL_FILE

    i = w.ModelChooseC.findText(HF_MODEL_FILE)  # the team's checkpoint
    if i > 0:
        w.ModelChooseC.setCurrentIndex(i)
    for widget in (
        w.segBox,
        *w.FilterButtons,  # Cellpose's "none" / "filter": the dropdown's job
        w.filtBox,  # its "custom filter settings"
    ):
        widget.hide()
    grid = w.filterBox_grid_layout  # the dropdown takes the buttons' row
    r, _, _, _ = grid.getItemPosition(grid.indexOf(w.FilterButtons[0]))
    grid.addWidget(w.filterChooser, r, 0, 1, 9)
    w.filterChooser.show()  # added after MainW.show(): hidden until shown
    # what annotate.py prints to the terminal, where annotators look:
    # the per-frame steps + frame switcher, then the leaderboard + last action
    plain = QFont(w.medfont)
    plain.setBold(False)  # so <b> stands out
    w.statsBox, w.howToBox = QGroupBox("Progress"), QGroupBox("How to")
    w.leaderboardLabel, w.statusLabel = QLabel(""), QLabel("")
    for box, labels in (
        (w.statsBox, (w.leaderboardLabel, w.statusLabel)),
        (w.howToBox, (QLabel(HOW_TO),)),
    ):
        box.setFont(w.boldfont)
        lay = QVBoxLayout(box)
        for label in labels:
            label.setFont(plain)
            label.setWordWrap(True)
            lay.addWidget(label)
    w.statusLabel.setFont(w.boldmedfont)
    # frame switching + done buttons, in their own box under How to
    w.framesBox = QGroupBox("Frames")
    w.framesBox.setFont(w.boldfont)
    nav = QGridLayout(w.framesBox)  # Qt-owned: a parentless layout crashes GC
    w.frameChooser = QComboBox()
    w.frameChooser.setMaxVisibleItems(15)
    w.frameChooser.setFont(plain)
    w.frameChooser.setSizeAdjustPolicy(  # long labels must not widen the panel
        QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
    )
    w.frameChooser.setMinimumContentsLength(10)
    w.frameChooser.setToolTip(
        "your frames: ● done, ◐ in progress, ○ not started"
    )
    w.frameChooser.currentIndexChanged.connect(lambda i: go_to(w, i))
    w.frameButtons = []
    for col, (text, tip, slot) in enumerate(
        (
            ("◀", "previous frame", lambda: step(w, -1)),
            ("▶", "next frame", lambda: step(w, 1)),
            (
                "✓ all crystals marked · next",
                "Every crystal in this frame is outlined: count it as done "
                "and go to the next frame not done. Until then an autosaved "
                "frame is only in progress (◐).",
                lambda: mark_done(w),
            ),
            (
                "no crystals",
                "This frame has no crystals: save an empty label, count it "
                "as done, go to the next frame not done.",
                lambda: mark_empty(w),
            ),
        )
    ):
        b = QPushButton(text)
        b.setFont(w.medfont)
        b.setToolTip(tip)
        b.clicked.connect(lambda _=False, f=slot: f())
        w.frameButtons.append(b)
    nav.addWidget(w.frameButtons[0], 0, 0)
    nav.addWidget(w.frameChooser, 0, 1)
    nav.addWidget(w.frameButtons[1], 0, 2)

    def count(n: int) -> None:  # after Cellpose's "N ROIs", so it wins
        w.roi_count.setText(
            f"{n} crystal{'' if n == 1 else 's'} on this frame"
        )

    w.ncells.valueChanged.connect(count)
    count(w.ncells.get())
    w.roi_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
    nav.addWidget(w.roi_count, 1, 1)
    # Cellpose's Edit menu as buttons; enabled exactly when the menu item is
    for col, text, tip, action in (
        (
            0,
            "↶ undo",
            "Remove the outline drawn last (Ctrl/⌘+Z). Autosaves.",
            w.undo,
        ),
        (
            2,
            "↷ undelete",
            "Bring back the outline deleted last; only the "
            "last one (Ctrl/⌘+Y). Autosaves.",
            w.redo,
        ),
    ):
        b = QPushButton(text)
        b.setFont(w.medfont)
        b.setToolTip(tip)
        b.setEnabled(action.isEnabled())
        b.clicked.connect(lambda _=False, a=action: a.trigger())
        action.changed.connect(
            lambda b=b, a=action: b.setEnabled(a.isEnabled())
        )
        nav.addWidget(b, 1, col)
    nav.addWidget(w.frameButtons[2], 2, 0, 1, 2)
    nav.addWidget(w.frameButtons[3], 2, 2)
    nav.setColumnStretch(1, 1)
    # How to, Frames, Views, Image filtering, Drawing, models, Progress
    boxes = [w.satBox, w.drawBox, w.segBox, w.modelBox, w.filterBox]
    rows = sorted(w.l0.getItemPosition(w.l0.indexOf(b))[0] for b in boxes)
    rows += [max(rows) + 1, max(rows) + 2, max(rows) + 3]
    order = [
        w.howToBox,
        w.framesBox,
        w.satBox,
        w.filterBox,
        w.drawBox,
        w.modelBox,
        w.statsBox,
        w.segBox,
    ]  # segBox stays hidden
    for b in boxes:
        w.l0.removeWidget(b)
    for r, b in zip(rows, order):
        w.l0.addWidget(b, r, 0, 1, 9)
    for box in (w.howToBox, w.framesBox, w.statsBox):
        box.show()
    w.roi_count.show()  # re-parented after MainW.show(): hidden until shown
    w.statusLabel.hide()  # say() shows it
    refresh_stats(w)
    refresh_frames(w)
    # spare height goes below the boxes instead of into gaps inside them
    w.l0.setRowStretch(max(rows) + 1, 1)
    # sidebar as wide as what is left in it; the image gets the rest
    w.scrollarea.setVerticalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAsNeeded
    )
    w.scrollarea.setFixedWidth(
        w.swidget.sizeHint().width()
        + w.scrollarea.verticalScrollBar().sizeHint().width()
    )


def refresh_stats(w) -> None:
    """Leaderboard of labelled frames per annotator; you in bold."""
    from .annotate import ANNOTATIONS, MEDALS, scores

    png = Path(str(getattr(w, "filename", ""))).resolve()
    me = png.parents[1].name if len(png.parents) > 2 else ""
    if len(png.parents) > 2 and png.parents[2] != ANNOTATIONS.resolve():
        me = ""
    rows = []
    for rank, (done, total, who) in enumerate(scores()):
        n = round(10 * done / total) if total else 0
        bar = (  # green done, grey to go: readable in light and dark themes
            f"<span style='color:#3fb950'>{'█' * n}</span>"
            f"<span style='color:#8b949e'>{'█' * (10 - n)}</span>"
        )
        medal = MEDALS[min(rank, 3)] if done else ""
        name = f"<b>{who}</b>" if who == me else who
        rows.append(
            f"<tr><td>{medal}</td><td>{name}&nbsp;</td>"
            f"<td><tt>{bar}</tt>&nbsp;</td><td>{done}/{total}</td></tr>"
        )
    w.leaderboardLabel.setText(f"<table>{''.join(rows)}</table>")


def add_rule_candidates(stack: np.ndarray, masks: np.ndarray) -> np.ndarray:
    """(1, Ly, Lx, C) image + (1, Ly, Lx) masks -> masks with rule additions.

    Her pipeline: her rules on her enhanced frame.
    """
    from .rules import add_missing, frame_candidates
    from .rules import masks as rule_masks

    enhanced = ananya(stack[0].mean(axis=-1))
    extra = rule_masks(enhanced.shape, frame_candidates(enhanced))
    return add_missing(masks[0], extra)[np.newaxis]


def apply(stack: np.ndarray, f: Filter) -> np.ndarray:
    """(NZ, Ly, Lx, C) float32 -> same shape, 3 identical channels, 0..255."""
    out = np.empty((*stack.shape[:3], 3), np.float32)
    for z in range(stack.shape[0]):
        r = f(stack[z].mean(axis=-1).astype(np.float32))
        lo, hi = float(r.min()), float(r.max())
        r = (
            (r - lo) / (hi - lo) * 255.0
            if hi - lo > 1e-6
            else np.zeros_like(r)
        )
        out[z] = r[..., None]
    return out


def _filter_shows_none(w) -> None:
    w.filterChooser.blockSignals(True)  # a reset, not a user choice
    w.filterChooser.setCurrentIndex(0)
    w.filterChooser.blockSignals(False)


def _filter_enabled(w) -> None:
    w.filterChooser.setEnabled(True)


def install() -> None:
    """Patch the GUI class once; call before ``cellpose.gui.gui.run``."""
    from cellpose.gui import gui, io
    from qtpy.QtCore import Qt
    from qtpy.QtWidgets import QComboBox, QPushButton

    if getattr(gui.MainW, "_crystal_filters", False):
        return
    setattr(gui.MainW, "_crystal_filters", True)  # noqa: B010

    def show_none(parent) -> None:
        parent.clear_restore()  # what Cellpose's hidden "none" button does
        parent.update_plot()
        _filter_shows_none(parent)

    def choose(parent, name: str) -> None:
        if name == "none":
            show_none(parent)
            say(parent, "showing the original")
        else:
            press(parent, name)

    def press(parent, name: str) -> None:
        try:
            parent.stack_filtered = apply(parent.stack, FILTERS[name])
        except ValueError as e:  # Ananya: not an exported annotation frame
            show_none(parent)
            say(parent, str(e))
            return
        parent.restore = (
            "filter"  # GUI then displays + segments stack_filtered
        )
        parent.enable_restored_view(True)
        parent.view = "restored"
        parent.compute_saturation()
        parent.update_plot()
        say(parent, f"showing {name}")

    def add_rules(parent: gui.MainW) -> None:
        if not parent.loaded:
            return
        if parent.NZ != 1 or (parent.restore and "upsample" in parent.restore):
            say(parent, "rule candidates need a single 2D frame, not resized")
            return
        n_before = int(parent.cellpix.max())
        manual = parent.ismanual.copy()
        try:
            masks = add_rule_candidates(parent.stack, parent.cellpix)
        except ValueError as e:  # frame_scale: not an annotation frame
            say(parent, str(e))
            return
        # ids stay 1..n (contiguous), so _masks_to_gui does not renumber
        io._masks_to_gui(parent, masks, outlines=None)
        parent.ismanual[: len(manual)] = manual  # _masks_to_gui resets them
        parent.masksOn = True
        parent.MCheckBox.setChecked(True)
        parent.update_plot()
        io._save_sets_with_check(parent)  # autosave like Cellpose's own edits
        n_added = int(parent.cellpix.max()) - n_before
        say(parent, f"+{n_added} rule candidates · saved ✓")

    orig_init = gui.MainW.__init__

    def init(self, *a, **kw):
        orig_init(self, *a, **kw)
        self.filterChooser = QComboBox()
        self.filterChooser.setFont(self.medfont)
        for i, name in enumerate(["none", *FILTERS]):
            self.filterChooser.addItem(name)
            self.filterChooser.setItemData(
                i, FILTER_TIPS[name], Qt.ItemDataRole.ToolTipRole
            )
        self.filterChooser.setToolTip(
            "What you see and what run segments; labels stay on the original."
        )
        self.filterChooser.setEnabled(self.loaded)
        self.filterChooser.currentTextChanged.connect(
            lambda name: choose(self, name)
        )
        b = QPushButton("add rule candidates")
        b.setFont(self.medfont)
        b.setToolTip(
            "Add Ananya's rule-based crystal boxes where nothing is outlined "
            "yet (best after run). Many are false: Ctrl+click deletes one, "
            "Drawing → region-select deletes all in a dragged area."
        )
        b.clicked.connect(lambda _=False: add_rules(self))
        self.modelBoxG.addWidget(b, self.modelBoxG.rowCount(), 0, 1, 9)
        b.show()
        declutter(self)

    setattr(gui.MainW, "__init__", init)  # noqa: B010

    # Cellpose titles the window with the full path on every load
    orig_enable_buttons = gui.MainW.enable_buttons

    def enable_buttons(self: gui.MainW) -> None:
        orig_enable_buttons(self)
        frames = my_frames(self)
        cur = Path(str(self.filename)).resolve()
        progress = (
            f"{frames.index(cur) + 1}/{len(frames)}" if cur in frames else ""
        )
        self.setWindowTitle(frame_title(str(self.filename), progress))
        if hasattr(self, "filterChooser"):
            _filter_enabled(self)
            if self.restore is None:  # a load shows the original again
                _filter_shows_none(self)
        if hasattr(self, "leaderboardLabel"):  # first load precedes declutter
            _hide_channel_sliders(self)
            refresh_stats(self)
            refresh_frames(self)

    setattr(gui.MainW, "enable_buttons", enable_buttons)  # noqa: B010

    orig_compute = gui.MainW.compute_segmentation

    def compute_segmentation(self: gui.MainW, *a, **kw) -> None:
        self.progress.show()  # hidden by declutter until there is progress
        orig_compute(self, *a, **kw)

    setattr(gui.MainW, "compute_segmentation", compute_segmentation)  # noqa: B010

    # Never persist the filtered image: masks are on the original pixel grid
    # and training must see the same flat-field frames analyze.py uses.
    orig_save = io._save_sets

    def save(parent):
        from .annotate import _label, _wip

        png = Path(str(parent.filename))
        started = not _label(png).exists()
        restore = parent.restore
        parent.restore = None
        try:
            orig_save(parent)
        finally:
            parent.restore = restore
        if started and my_frames(parent):  # in progress until ✓ all marked
            _wip(png).touch()
        n = int(parent.cellpix.max())
        # annotate.py prints its own saved line, so not to the terminal
        say(parent, f"saved ✓ {n} crystals · {time.strftime('%H:%M')}", False)
        refresh_stats(parent)  # a first label moves you up the board
        if hasattr(parent, "frameChooser"):
            refresh_frames(parent)  # · becomes ✓

    setattr(io, "_save_sets", save)  # noqa: B010
