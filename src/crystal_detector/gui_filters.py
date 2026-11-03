"""Add the repo's deterministic preprocessors to the Cellpose GUI filter box.

For grey annotation frames the panel is decluttered (:func:`declutter`): no
RGB/red/green/blue colour modes or their sliders, no gradXY/cellprob views,
no generic cpsam model box (the fine-tuned model runs from *user-trained
models*), no Cellpose ``filter`` and its settings; *Image filtering* sits
right under *Views*.

Buttons appear under *Image filtering* next to Cellpose's ``none``:
**flat-field** (illumination + CLAHE, what ``analyze.py`` feeds
the model), **high-pass** (Gaussian residual, ``optics.highpass``),
**sharpness** (local Laplacian variance, ``annotator.sharpness``) and
**Ananya** (her enhancement from ``enhance.py``: CLAHE + sharpen, leveling,
CLAHE + sharpen). Each one replaces the displayed image and the image ``run``
segments; the view switches to *restored*; ``none`` goes back.

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

import os
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
            ("close window", "next frame (edits autosave)"),
            ("no crystals", "close, answer y in terminal"),
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


def declutter(w) -> None:
    """Hide Cellpose controls that do nothing for grey annotation frames."""
    from qtpy.QtGui import QFont
    from qtpy.QtWidgets import QGroupBox, QLabel, QVBoxLayout

    for box, names in (
        (w.RGBDropDown, HIDDEN_COLORS),
        (w.ViewDropDown, HIDDEN_VIEWS),
    ):
        for name in names:  # removed, so the R/G/B and W/S keys skip them too
            box.removeItem(box.findText(name))
    for s in w.sliders[1:]:  # green, blue
        s.hide()
    for label in w.satBox.findChildren(QLabel):
        if label.text() in (
            "green:",
            "blue:",
            "[R / G / B \n toggles color ]",
        ):
            label.hide()
        elif "red" in label.text():
            label.setText("gray:")
            label.setStyleSheet("")
    # generic model box: the team runs the fine-tuned model under
    # user-trained models, so keep only its progress bar and ROI count there
    row = w.modelBoxG.rowCount()
    w.modelBoxG.addWidget(w.progress, row, 0, 1, 5)
    w.modelBoxG.addWidget(w.roi_count, row, 5, 1, 4)
    w.progress.hide()  # shown when a run starts (compute_segmentation patch)
    w.roi_count.show()  # re-parented after MainW.show(): hidden until shown
    from .analyze import HF_MODEL_FILE

    i = w.ModelChooseC.findText(HF_MODEL_FILE)  # the team's checkpoint
    if i > 0:
        w.ModelChooseC.setCurrentIndex(i)
    for widget in (
        w.segBox,
        w.FilterButtons[1],  # Cellpose's "filter"
        w.filtBox,  # its "custom filter settings"
    ):
        widget.hide()
    # the last repo filter takes the freed slot next to "none", the others
    # the row right below it (the rows between held the hidden settings)
    grid = w.filterBox_grid_layout
    r, c, _, _ = grid.getItemPosition(grid.indexOf(w.FilterButtons[1]))
    grid.addWidget(w.FilterButtons[-1], r, c, 1, 3)
    for col, b in enumerate(w.FilterButtons[2:-1]):
        grid.addWidget(b, r + 1, 3 * col, 1, 3)
    # Views, Image filtering, Drawing, user-trained models (in their slots)
    boxes = [w.satBox, w.drawBox, w.segBox, w.modelBox, w.filterBox]
    rows = sorted(w.l0.getItemPosition(w.l0.indexOf(b))[0] for b in boxes)
    order = [w.satBox, w.filterBox, w.drawBox, w.modelBox, w.segBox]
    for b in boxes:
        w.l0.removeWidget(b)
    for r, b in zip(rows, order):
        w.l0.addWidget(b, r, 0, 1, 9)
    # what annotate.py prints to the terminal, where annotators look:
    # the per-frame steps, then the team leaderboard + last action
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
    for i, box in enumerate((w.howToBox, w.statsBox)):
        w.l0.addWidget(box, max(rows) + 1 + i, 0, 1, 9)
        box.show()
    w.statusLabel.hide()  # say() shows it
    refresh_stats(w)
    # spare height goes below the boxes instead of into gaps inside them
    w.l0.setRowStretch(max(rows) + 3, 1)


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


def install() -> None:
    """Patch the GUI class once; call before ``cellpose.gui.gui.run``."""
    from cellpose.gui import gui, io
    from qtpy.QtWidgets import QPushButton

    if getattr(gui.MainW, "_crystal_filters", False):
        return
    setattr(gui.MainW, "_crystal_filters", True)  # noqa: B010

    def press(parent, name: str) -> None:
        try:
            parent.stack_filtered = apply(parent.stack, FILTERS[name])
        except ValueError as e:  # Ananya: not an exported annotation frame
            say(parent, str(e))
            return
        parent.restore = (
            "filter"  # GUI then displays + segments stack_filtered
        )
        parent.enable_restored_view(True)
        parent.view = "restored"
        parent.compute_saturation()
        parent.update_plot()
        say(parent, f"showing {name} · none = original")

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
        row = self.filterBox_grid_layout.rowCount()
        for col, name in enumerate(FILTERS):
            b = QPushButton(name)
            b.setFont(self.medfont)
            b.setFixedWidth(75)
            b.setEnabled(self.loaded)
            b.setToolTip(FILTER_TIPS[name])
            b.clicked.connect(lambda _=False, n=name: press(self, n))
            self.filterBox_grid_layout.addWidget(  # 3 per row fit the panel
                b, row + col // 3, 3 * (col % 3), 1, 3
            )
            b.show()  # MainW.__init__ already called show(); late widgets stay hidden
            self.FilterButtons.append(b)  # enable_buttons() toggles these
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
        progress = os.environ.get("CRYSTAL_PROGRESS", "")
        self.setWindowTitle(frame_title(str(self.filename), progress))
        if hasattr(self, "leaderboardLabel"):  # first load precedes declutter
            refresh_stats(self)

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
        restore = parent.restore
        parent.restore = None
        try:
            orig_save(parent)
        finally:
            parent.restore = restore
        n = int(parent.cellpix.max())
        # annotate.py prints its own saved line, so not to the terminal
        say(parent, f"saved ✓ {n} crystals · {time.strftime('%H:%M')}", False)
        refresh_stats(parent)  # a first label moves you up the board

    setattr(io, "_save_sets", save)  # noqa: B010
