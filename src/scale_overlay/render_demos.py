"""Render the 07_overlay_{near,at_focus,far}.png demo images.

Each output is a horizontal 2-panel composite:

* **Left** — the cropped frame with a real-world millimetre grid +
  ruler + HUD, parameterised at one specific object distance ``d_o``.
* **Right** — the per-pixel sharpness map (Laplacian-variance smoothed
  by a Gaussian kernel, colourised with INFERNO) with the *same* grid
  + ruler + HUD overlaid. This shows the reader *which pixels are
  actually in focus* at that depth — and at the verified F/1.6
  aperture the three demos look nearly identical because the DoF is
  only ±6 µm.

Run with ``uv run python -m scale_overlay.render_demos``.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from annotator.sharpness import compute_sharpness_map
from annotator.viz import colorize_map
from optics.config import lens_from_config, load_camera
from optics import LensSetup, mm_per_pixel_at
from optics.video_io import DEFAULT_CROP
from scale_overlay.overlay import (
    annotate_optics_info,
    draw_grid,
    draw_ruler,
)

Mat = NDArray[np.uint8]


def render_pair(
    frame_bgr: Mat,
    lens: LensSetup,
    d_focus: float,
    d_o: float,
    sharpness_color: Mat,
    *,
    grid_mm: float = 0.1,
    ruler_mm: float = 1.0,
    sharp_label: str = "sharpness map (Laplacian-variance, smoothed)",
) -> Mat:
    """Compose the (frame+grid) | (sharpness+grid) side-by-side panel."""
    left = draw_grid(frame_bgr, lens, d_focus, d_o, grid_mm=grid_mm)
    left = draw_ruler(left, lens, d_focus, d_o, length_mm=ruler_mm)
    left = annotate_optics_info(left, lens, d_focus, d_o)

    right = draw_grid(sharpness_color, lens, d_focus, d_o, grid_mm=grid_mm)
    right = draw_ruler(right, lens, d_focus, d_o, length_mm=ruler_mm)
    cv2.putText(
        right,
        sharp_label,
        (20, right.shape[0] - 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (0, 0, 0),
        4,
    )
    cv2.putText(
        right,
        sharp_label,
        (20, right.shape[0] - 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        1,
    )

    # 8-px black divider between the two panels for clarity.
    divider = np.zeros((left.shape[0], 8, 3), dtype=np.uint8)
    out: Mat = np.hstack([left, divider, right])
    return out


def main() -> None:
    """Render the three demo pairs."""
    cfg = load_camera()
    lens = lens_from_config(cfg)
    d_focus = cfg.focus_object_distance_mm

    frame = cv2.imread("docs/optics/frame_0.png")
    if frame is None:
        raise FileNotFoundError("docs/optics/frame_0.png missing")
    frame_cropped = DEFAULT_CROP.apply(frame)

    gray = cv2.cvtColor(frame_cropped, cv2.COLOR_BGR2GRAY)
    sharpness = compute_sharpness_map(gray, kernel=15)
    sharp_color = colorize_map(sharpness, cv2.COLORMAP_INFERNO)

    out_dir = Path("docs/optics/figures")
    out_dir.mkdir(parents=True, exist_ok=True)
    cases = [
        ("near", 62.0),
        ("at_focus", d_focus),
        ("far", 62.4),
    ]
    for label, d_o in cases:
        composite = render_pair(frame_cropped, lens, d_focus, d_o, sharp_color)
        path = out_dir / f"07_overlay_{label}.png"
        cv2.imwrite(str(path), composite)
        mm_per_px_um = (
            float(mm_per_pixel_at(lens, d_focus, np.array([d_o]))[0]) * 1000.0
        )
        print(
            f"{path.name}: d_o={d_o} mm, {mm_per_px_um:.3f} µm/px, "
            f"shape={composite.shape}"
        )


if __name__ == "__main__":
    main()
