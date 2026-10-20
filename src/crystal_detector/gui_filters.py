"""Add the repo's deterministic preprocessors to the Cellpose GUI filter box.

Buttons appear under *Image filtering* next to Cellpose's own ``none`` /
``filter``: **flat-field** (illumination + CLAHE, what ``analyze.py`` feeds
the model), **high-pass** (Gaussian residual, ``optics.highpass``) and
**sharpness** (local Laplacian variance, ``annotator.sharpness``). Each one
replaces the displayed image and the image ``run`` segments; the view
switches to *restored*; ``none`` goes back.

Labels stay bound to the original pixels: the filtered image is never
written into ``_seg.npy`` (Cellpose would otherwise train on it), so the
model is always trained on the same flat-field frames ``analyze.py`` uses.

    from crystal_detector import gui_filters; gui_filters.install()
    from cellpose.gui import gui; gui.run(image=...)
"""

from __future__ import annotations

from collections.abc import Callable

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


FILTERS: dict[str, Filter] = {
    "flat-field": _flat_field,
    "high-pass": _highpass,
    "sharpness": _sharpness,
}


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
        parent.stack_filtered = apply(parent.stack, FILTERS[name])
        parent.restore = (
            "filter"  # GUI then displays + segments stack_filtered
        )
        parent.enable_restored_view(True)
        parent.view = "restored"
        parent.compute_saturation()
        parent.update_plot()
        print(f"GUI_INFO: showing {name}; 'none' restores the original")

    orig_init = gui.MainW.__init__

    def init(self, *a, **kw):
        orig_init(self, *a, **kw)
        row = self.filterBox_grid_layout.rowCount()
        for col, name in enumerate(FILTERS):
            b = QPushButton(name)
            b.setFont(self.medfont)
            b.setFixedWidth(75)
            b.setEnabled(self.loaded)
            b.setToolTip(
                f"show {name} preprocessing (repo deterministic filter)"
            )
            b.clicked.connect(lambda _=False, n=name: press(self, n))
            self.filterBox_grid_layout.addWidget(b, row, 3 * col, 1, 3)
            b.show()  # MainW.__init__ already called show(); late widgets stay hidden
            self.FilterButtons.append(b)  # enable_buttons() toggles these

    setattr(gui.MainW, "__init__", init)  # noqa: B010

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

    setattr(io, "_save_sets", save)  # noqa: B010
