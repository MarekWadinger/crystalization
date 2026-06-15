"""Drawing primitives for the scale overlay.

Renders a real-world millimetre grid plus a ruler bar on top of a frame,
parameterised by object distance through the optics model.
"""

from __future__ import annotations

import cv2
import numpy as np

from optics import LensSetup, mm_per_pixel_at

Mat = np.ndarray


def draw_grid(
    frame: Mat,
    lens: LensSetup,
    d_focus: float,
    d_o: float,
    *,
    grid_mm: float = 1.0,
    major_every: int = 5,
    color: tuple[int, int, int] = (0, 255, 255),
    thickness: int = 1,
    alpha: float = 0.5,
) -> Mat:
    """Draw a real-world grid on a copy of ``frame`` at object distance ``d_o``.

    Parameters
    ----------
    frame:
        BGR or grayscale image. Returned with the grid blended in.
    lens, d_focus, d_o:
        Optical parameters. ``d_o`` is the depth the user wants the grid
        to refer to; ``d_focus`` is what the lens is focused on. They can
        differ (e.g. a crystal 2 mm in front of focus).
    grid_mm:
        Minor-grid spacing in millimetres.
    major_every:
        Every ``major_every``-th line is drawn brighter as a major tick.
    """
    img = frame.copy()
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    h, w = img.shape[:2]

    mm_per_px = (
        float(mm_per_pixel_at(lens, d_focus, np.array([d_o]))[0]) * 1000.0
    )
    # Treat ``mm_per_px`` as µm/px conversion guard
    px_per_mm = 1000.0 / mm_per_px

    spacing = px_per_mm * grid_mm
    if spacing < 2.0:  # too dense — bump to next decade
        grid_mm *= 10.0
        spacing *= 10.0

    cx, cy = w // 2, h // 2

    overlay = np.zeros_like(img)
    n_left = int(cx // spacing) + 1
    n_right = int((w - cx) // spacing) + 1
    n_up = int(cy // spacing) + 1
    n_down = int((h - cy) // spacing) + 1

    minor = (int(color[0] * 0.6), int(color[1] * 0.6), int(color[2] * 0.6))
    for sign, count in ((-1, n_left), (1, n_right)):
        for i in range(count + 1):
            x = int(round(cx + sign * i * spacing))
            if 0 <= x < w:
                c = color if (i % major_every == 0) else minor
                t = thickness + 1 if (i % major_every == 0) else thickness
                cv2.line(overlay, (x, 0), (x, h - 1), c, t)
    for sign, count in ((-1, n_up), (1, n_down)):
        for i in range(count + 1):
            y = int(round(cy + sign * i * spacing))
            if 0 <= y < h:
                c = color if (i % major_every == 0) else minor
                t = thickness + 1 if (i % major_every == 0) else thickness
                cv2.line(overlay, (0, y), (w - 1, y), c, t)

    mask = (overlay.sum(axis=2) > 0).astype(np.uint8)[:, :, None]
    blended = (
        img.astype(np.float32) * (1.0 - mask * alpha)
        + overlay.astype(np.float32) * (mask * alpha)
    ).astype(np.uint8)
    return np.ascontiguousarray(blended)


def draw_ruler(
    frame: Mat,
    lens: LensSetup,
    d_focus: float,
    d_o: float,
    *,
    length_mm: float = 5.0,
    margin_px: int = 30,
    color: tuple[int, int, int] = (255, 255, 255),
) -> Mat:
    """Draw a labelled ruler bar in the bottom-left corner."""
    img = frame.copy()
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    h, w = img.shape[:2]

    mm_per_px = (
        float(mm_per_pixel_at(lens, d_focus, np.array([d_o]))[0]) * 1000.0
    )
    px_per_mm = 1000.0 / mm_per_px

    bar_len_px = int(round(px_per_mm * length_mm))
    if bar_len_px < 20:
        length_mm *= 10.0
        bar_len_px = int(round(px_per_mm * length_mm))

    x0 = margin_px
    y0 = h - margin_px
    x1 = x0 + bar_len_px

    cv2.line(img, (x0, y0), (x1, y0), (0, 0, 0), 6)
    cv2.line(img, (x0, y0), (x1, y0), color, 3)
    for i in range(int(length_mm) + 1):
        x = int(round(x0 + i * px_per_mm))
        cv2.line(img, (x, y0 - 8), (x, y0 + 8), (0, 0, 0), 4)
        cv2.line(img, (x, y0 - 8), (x, y0 + 8), color, 2)

    label = f"{length_mm:.0f} mm @ d_o = {d_o:.0f} mm  ({mm_per_px:.2f} um/px)"
    cv2.putText(
        img, label, (x0, y0 - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 4
    )
    cv2.putText(
        img, label, (x0, y0 - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2
    )
    return img


def annotate_optics_info(
    frame: Mat,
    lens: LensSetup,
    d_focus: float,
    d_o: float,
) -> Mat:
    """Top-left HUD with the key numbers."""
    img = frame.copy()
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    mm_per_px = (
        float(mm_per_pixel_at(lens, d_focus, np.array([d_o]))[0]) * 1000.0
    )
    lines = [
        f"f = {lens.focal_length:.0f} mm   F/{lens.f_number:.1f}   e = {lens.extension_tube:.1f} mm",
        f"focus plane: d_focus = {d_focus:.0f} mm",
        f"grid depth: d_o = {d_o:.0f} mm   (delta = {d_o - d_focus:+.0f} mm)",
        f"scale at d_o:  {mm_per_px:.2f} um/px   ({1000.0 / mm_per_px:.1f} px/mm)",
    ]
    x, y = 20, 30
    for line in lines:
        cv2.putText(
            img, line, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 4
        )
        cv2.putText(
            img, line, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1
        )
        y += 22
    return img
