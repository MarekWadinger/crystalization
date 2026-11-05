"""Rule-based crystal candidates, ported from Ananya Lohani's Cryst_CNN notebook.

https://github.com/ananyalohani-bit/Cryst_CNN (``CNN_Classification_V3.ipynb``,
``detect_candidates`` and ``measure_body``). A candidate is a bright body; it
is labelled **crystal** when it is brighter than the band around it, that band
is mostly dark rim, and its outline is rectangular, not elongated, of
plausible size and not cut by the frame; **hard_neg** when it is barely
brighter than its surroundings or clearly not rectangular; **skip** otherwise.

:func:`detect` is her code with her settings, on her pixel grid: her frames
are the PAL channel upscaled to 1080 rows. :func:`frame_candidates` runs it on
our annotation frames by resampling them to her grid (scale from
``configs/camera_100.toml``) and mapping the boxes back.
"""

from __future__ import annotations

from typing import TypedDict

import cv2
import numpy as np

from optics.config import lens_from_config, load_camera, um_per_px_xy_at_focus

PAL_WIDTH, PAL_HEIGHT, HER_HEIGHT = 720, 576, 1080
# annotation frame width -> source video size (export_frames.crop keeps 90 %)
ANNOTATION_WIDTHS = {648: (PAL_WIDTH, PAL_HEIGHT), 1728: (1920, 1080)}

# her settings cell; lengths in pixels of her frames
EDGE_PERCENTILE = 30
CENTER_PERCENTILE = 75
CONTRAST_FRACTION = 0.25
MIN_EDGE_DARK_FRACTION = 0.40
RING_WIDTH = 8
MIN_SIDE_PX, MAX_SIDE_PX = 12, 160
MIN_RECTANGULARITY = 0.70
MAX_ASPECT = 2.5
HARD_NEG_MAX_CONTRAST = 10
HARD_NEG_MAX_RECTANGULARITY = 0.55
RIM_PX = 3
MIN_RING_PIXELS = 30  # inline constant in her detect_candidates

Rect = tuple[tuple[float, float], tuple[float, float], float]


class Candidate(TypedDict):
    label: str  # "crystal" | "hard_neg" | "skip"
    rect: Rect  # rotated box of body + test band (her annotation boxes)
    body_rect: Rect  # body + dark rim, +1 px as in her length/width (masks)


def um_per_px_xy(width_px: int, height_px: int) -> tuple[float, float]:
    """Object-plane µm per pixel ``(x, y)`` of a video frame of this size."""
    cfg = load_camera()
    return um_per_px_xy_at_focus(
        cfg, lens_from_config(cfg, width_px, height_px)
    )


def frame_scale(width_px: int) -> tuple[float, float]:
    """Pixels of an exported annotation frame per pixel of hers, ``(x, y)``.

    Her frames are taken as PAL upscaled isotropically to 1080 rows
    (pillarboxed); the DVR 1080p clips are PAL stretched anisotropically, so
    the two axes differ there.
    """
    if width_px not in ANNOTATION_WIDTHS:
        raise ValueError(
            f"{width_px} px wide is not an exported annotation frame "
            f"({' or '.join(map(str, ANNOTATION_WIDTHS))} px); scale unknown"
        )
    # ponytail: isotropic ×1.875. Her ~1285 px active width (pillarboxed) is within
    # ~5 % of 1316–1350 px isotropic and far from the DVR's ×2.677 (1927 px).
    up = HER_HEIGHT / PAL_HEIGHT
    px, py = um_per_px_xy(PAL_WIDTH, PAL_HEIGHT)
    ax, ay = um_per_px_xy(*ANNOTATION_WIDTHS[width_px])
    return px / up / ax, py / up / ay


def _box(cnt: np.ndarray, x0: int, y0: int) -> Rect:
    (cx, cy), (w, h), ang = cv2.minAreaRect(cnt)
    return (cx + x0, cy + y0), (w, h), ang


def _label(
    comp: np.ndarray,
    win: np.ndarray,
    dark_win: np.ndarray,
    valid_win: np.ndarray,
    on_border: bool,
    k_ring: np.ndarray,
    min_contrast: float,
) -> tuple[str, np.ndarray] | None:
    """Her rules on one bright component; None when she skips it silently."""
    ring = (cv2.dilate(comp, k_ring) - comp) & valid_win
    if ring.sum() < MIN_RING_PIXELS:
        return None
    contrast = float(win[comp > 0].mean() - win[ring > 0].mean())
    dark_frac = float(dark_win[ring > 0].mean())
    cnts = cv2.findContours(
        cv2.dilate(comp, k_ring), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )[0]
    cnt = cnts[int(np.argmax([cv2.contourArea(c) for c in cnts]))]
    _, (rw, rh), _ = cv2.minAreaRect(cnt)
    rectangularity = float(cv2.contourArea(cnt) / max(rw * rh, 1.0))
    side_long, side_short = max(rw, rh), max(min(rw, rh), 1.0)
    crystal = (
        contrast >= min_contrast
        and dark_frac >= MIN_EDGE_DARK_FRACTION
        and rectangularity >= MIN_RECTANGULARITY
        and side_long / side_short <= MAX_ASPECT
        and side_short >= MIN_SIDE_PX
        and side_long <= MAX_SIDE_PX
        and not on_border
    )
    hard_neg = (
        contrast <= HARD_NEG_MAX_CONTRAST
        or rectangularity <= HARD_NEG_MAX_RECTANGULARITY
    )
    label = "crystal" if crystal else ("hard_neg" if hard_neg else "skip")
    return label, cnt


def _body(
    comp: np.ndarray, dark_win: np.ndarray, valid_win: np.ndarray
) -> np.ndarray:
    """Her measure_body outline: body grown into its dark rim, ≤ RIM_PX."""
    cross = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    allowed = (dark_win | comp) & valid_win
    body = comp.copy()
    for _ in range(RIM_PX):
        body = cv2.dilate(body, cross) & allowed
    cnts = cv2.findContours(body, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0]
    return cnts[int(np.argmax([cv2.contourArea(c) for c in cnts]))]


def detect(
    gray: np.ndarray, valid: np.ndarray | None = None
) -> list[Candidate]:
    """Her ``detect_candidates`` on a denoised grey frame on her pixel grid.

    ``valid`` masks out overlays (1 = usable pixel).
    """
    g = gray.astype(np.uint8)
    valid = np.ones_like(g) if valid is None else valid.astype(np.uint8)
    p = np.percentile(
        g[valid > 0], [10, EDGE_PERCENTILE, CENTER_PERCENTILE, 90]
    )
    edge, center = int(p[1]), int(p[2])
    min_contrast = CONTRAST_FRACTION * (p[3] - p[0])
    dark = (g <= edge).astype(np.uint8)
    bright = (g >= center).astype(np.uint8)
    bright = (
        cv2.morphologyEx(bright, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        & valid
    )
    k_ring = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (2 * RING_WIDTH + 1,) * 2
    )
    grey = g.astype(np.float32)
    H, W = g.shape
    n, lab, stats, _ = cv2.connectedComponentsWithStats(bright, connectivity=4)
    out: list[Candidate] = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area < (MIN_SIDE_PX * 0.6) ** 2 or max(w, h) > MAX_SIDE_PX * 1.5:
            continue
        pad = RING_WIDTH + 2
        x0, y0 = max(x - pad, 0), max(y - pad, 0)
        x1, y1 = min(x + w + pad, W), min(y + h + pad, H)
        comp = (lab[y0:y1, x0:x1] == i).astype(np.uint8)
        comp = cv2.morphologyEx(
            comp, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)
        )
        dark_win, valid_win = dark[y0:y1, x0:x1], valid[y0:y1, x0:x1]
        on_border = x0 == 0 or y0 == 0 or x1 == W or y1 == H
        res = _label(
            comp,
            grey[y0:y1, x0:x1],
            dark_win,
            valid_win,
            on_border,
            k_ring,
            min_contrast,
        )
        if res is None:
            continue
        label, cnt = res
        (bx, by), (bw, bh), ba = _box(_body(comp, dark_win, valid_win), x0, y0)
        out.append(
            Candidate(
                label=label,
                rect=_box(cnt, x0, y0),
                body_rect=((bx, by), (bw + 1, bh + 1), ba),
            )
        )
    return out


def _to_frame(r: Rect, s: tuple[float, float]) -> Rect:
    """Rect on her grid -> rect on a frame ``s = (sx, sy)`` times her pixel size."""
    pts = (cv2.boxPoints(r) + 0.5) * s - 0.5
    (cx, cy), (w, h), ang = cv2.minAreaRect(pts.astype(np.float32))
    return (cx, cy), (w, h), ang


def frame_candidates(gray: np.ndarray) -> list[Candidate]:
    """Her rules (and her 3×3 median denoise) on an annotation frame."""
    g = np.clip(gray, 0, 255).astype(np.uint8)
    h, w = g.shape
    s = frame_scale(w)
    hers = cv2.resize(
        g, (round(w / s[0]), round(h / s[1])), interpolation=cv2.INTER_CUBIC
    )
    return [
        Candidate(
            label=c["label"],
            rect=_to_frame(c["rect"], s),
            body_rect=_to_frame(c["body_rect"], s),
        )
        for c in detect(cv2.medianBlur(hers, 3))
    ]


def masks(
    shape: tuple[int, int],
    cands: list[Candidate],
    labels: tuple[str, ...] = ("crystal",),
) -> np.ndarray:
    """Label image of filled body boxes; earlier candidates keep overlaps."""
    out = np.zeros(shape, np.uint16)
    for c in cands:
        if c["label"] not in labels:
            continue
        sel = np.zeros(shape, np.uint8)
        pts = cv2.boxPoints(c["body_rect"]).round().astype(np.int32)
        cv2.fillPoly(sel, [pts], 1)
        free = (sel > 0) & (out == 0)
        if free.any():
            out[free] = out.max() + 1
    return out


def add_missing(masks: np.ndarray, extra: np.ndarray) -> np.ndarray:
    """Append ``extra`` objects that do not touch any existing mask."""
    out = masks.astype(np.uint32)
    nxt = int(out.max())
    for e in range(1, int(extra.max()) + 1):
        sel = extra == e
        if sel.any() and not out[sel].any():
            nxt += 1
            out[sel] = nxt
    return out
