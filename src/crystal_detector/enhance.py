"""Ananya Lohani's crystal image enhancement, ported from Cryst_CNN.

https://github.com/ananyalohani-bit/Cryst_CNN (``Image enhancement.ipynb``):
the chain behind her ``frame_XXXXX_enhanced_processed_enhanced.png`` frames,
**enhance → level → enhance**, where *enhance* is CLAHE plus a 3×3 sharpen
(``enhance_crystal_image``) and *level* removes slow brightness variation
with a Gaussian of the clipped frame (her ``process_image`` second pass).

Left out: her first pass divides by a background reference (``back.png``,
not in her repo); on her raw frames the chain without it still correlates
r ≈ 0.97 with her Step-4 output. Her black-border crop is a no-op on both her
frames and ours and would shift the image against the masks, so it is
dropped too. Her kernels (3×3 sharpen, 20 px Gaussian) are in pixels of her
frames (PAL upscaled to 1080 rows), so other frames are resampled to her
pixel grid, enhanced, and resampled back (scale as in ``rules.py``). CLAHE
tiles are relative to the image: her 8×8 grid spanned her full pillarboxed
frame, ours spans the annotation crop, so tiles cover ~1.6× less scene.
"""

from __future__ import annotations

import cv2
import numpy as np

CLAHE_CLIP, CLAHE_TILES = 3.0, (8, 8)
SHARPEN = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
RESIDUAL_SIGMA_PX = 20.0  # her frames
ACTIVE_LEVEL, ACTIVE_FRACTION = 10, 0.50  # her find_active_region


def enhance(gray: np.ndarray) -> np.ndarray:
    """Her ``enhance_crystal_image``: CLAHE (clip 3, 8×8 tiles) + sharpen."""
    clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP, tileGridSize=CLAHE_TILES)
    return cv2.filter2D(clahe.apply(gray), -1, SHARPEN)


def _active_region(gray: np.ndarray) -> tuple[int, int, int, int]:
    lit = gray > ACTIVE_LEVEL
    cols = np.where(lit.mean(axis=0) > ACTIVE_FRACTION)[0]
    rows = np.where(lit.mean(axis=1) > ACTIVE_FRACTION)[0]
    if len(cols) == 0 or len(rows) == 0:
        return 0, 0, gray.shape[1], gray.shape[0]
    return int(cols[0]), int(rows[0]), int(cols[-1] + 1), int(rows[-1] + 1)


def level(gray: np.ndarray, sigma_px: float) -> np.ndarray:
    """Her residual tone leveling: subtract the blur of the p10–p90 clip."""
    x1, y1, x2, y2 = _active_region(gray)
    roi = gray[y1:y2, x1:x2].astype(np.float32)
    lo, hi = np.percentile(roi, [10, 90])
    field = cv2.GaussianBlur(
        np.clip(roi, lo, hi),
        (0, 0),
        sigmaX=sigma_px,
        sigmaY=sigma_px,
        borderType=cv2.BORDER_REFLECT,
    )
    corrected = roi - (field - np.median(field))
    corrected += np.median(roi) - np.median(corrected)
    out = gray.copy()
    out[y1:y2, x1:x2] = np.clip(corrected, 0, 255).astype(np.uint8)
    return out


def ananya_enhance(gray: np.ndarray, scale: float = 1.0) -> np.ndarray:
    """Her full chain on a grey frame; ``scale`` = px here per px of hers."""
    g = np.clip(gray, 0, 255).astype(np.uint8)
    if scale == 1.0:
        return enhance(level(enhance(g), RESIDUAL_SIGMA_PX))
    h, w = g.shape
    hers = cv2.resize(
        g, (round(w / scale), round(h / scale)), interpolation=cv2.INTER_CUBIC
    )
    out = ananya_enhance(hers)
    return cv2.resize(out, (w, h), interpolation=cv2.INTER_AREA)
