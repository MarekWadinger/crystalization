"""Frame I/O with DVR-overlay crop.

The Camera 100 video stream has a digital ``YYYY-MM-DD HH:MM:SS``
datetime overlay rendered at the top by the DVR and a ``CH01`` channel
label at the bottom. These overlays are **infinitely sharp** (perfect
glyph edges, fixed contrast) and overwhelm any per-pixel sharpness
statistic — see ``docs/optics/disambiguation_results.md`` §"DVR overlay
contamination" for the discussion. Every empirical measurement on the
video should run on the **cropped** frame.

Default crop is conservative for this specific DVR's layout:

* top 55 rows (timestamp band — sharpness drops by ~10× past row 45)
* bottom 120 rows (CH01 label + black border — text glyphs extend
  deeper than the row-mean sharpness signal suggests because they are
  thin verticals that don't dominate the row mean but still cause
  per-pixel sharpness spikes)
* **left 50 columns** (pitch-black analogue-aspect padding — columns
  0 – 40 have ``var(Laplacian)=0`` then a transition zone)
* **right 70 columns** (the right edge has a hard analogue-aspect
  border transition with a Laplacian² spike to ~110 at col 1865 —
  cropping past 1850 kills the spike and keeps a safety margin)

That keeps roughly 1800 × 905 = ~78 % of the original frame area
while removing all overlay glyphs and analogue-aspect black bars.
Override per-recording if the layout differs.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

DEFAULT_CROP_TOP = 55
DEFAULT_CROP_BOTTOM = 120
DEFAULT_CROP_LEFT = 50
DEFAULT_CROP_RIGHT = 70


@dataclass(frozen=True, slots=True)
class CropBox:
    """Pixels to remove from each edge of every frame."""

    top: int = DEFAULT_CROP_TOP
    bottom: int = DEFAULT_CROP_BOTTOM
    left: int = DEFAULT_CROP_LEFT
    right: int = DEFAULT_CROP_RIGHT

    def apply(self, frame: np.ndarray) -> np.ndarray:
        """Return ``frame`` cropped according to this box.

        ``frame`` is whatever OpenCV's VideoCapture.read returns
        (typed loosely in OpenCV stubs as a generic ndarray); the
        cropped array preserves the input dtype and channel layout.
        """
        h, w = frame.shape[:2]
        y0 = self.top
        y1 = h - self.bottom if self.bottom > 0 else h
        x0 = self.left
        x1 = w - self.right if self.right > 0 else w
        return np.ascontiguousarray(frame[y0:y1, x0:x1])

    @classmethod
    def auto_detect(
        cls,
        video_path: str,
        *,
        n_samples: int = 40,
        letterbox_luma_thresh: float = 12.0,
        overlay_sharpness_ratio: float = 3.0,
        margin_px: int = 5,
        max_edge_fraction: float = 0.25,
    ) -> CropBox:
        """Estimate per-edge crops from the video itself.

        Two signals, sampled from ``n_samples`` evenly-spaced frames:

        * **letterbox** — outer columns/rows whose mean luminance stays
          below ``letterbox_luma_thresh`` (analogue black bars).
        * **DVR overlay** — outer rows whose mean ``var(Laplacian)``
          exceeds ``overlay_sharpness_ratio`` × the interior median
          (timestamp/channel banners are an order of magnitude sharper
          than the underwater image).

        ``margin_px`` is added as a safety pad and each edge is capped at
        ``max_edge_fraction`` of the frame dimension so a pathological
        sample can never crop away the whole image.

        Decodes only the sampled frames; safe to call on multi-GB videos.
        """
        cap = cv2.VideoCapture(video_path)
        try:
            n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            if n_frames <= 0 or w <= 0 or h <= 0:
                raise RuntimeError(f"Bad video metadata for {video_path}")
            indices = np.linspace(
                0,
                max(0, n_frames - 1),
                num=min(n_samples, n_frames),
                dtype=int,
            )
            luma_sum = np.zeros((h, w), dtype=np.float64)
            sharp_sum = np.zeros((h, w), dtype=np.float64)
            taken = 0
            for idx in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
                ret, frame = cap.read()
                if not ret:
                    continue
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(
                    np.float64
                )
                lap = cv2.Laplacian(gray, cv2.CV_64F, ksize=3)
                luma_sum += gray
                sharp_sum += lap * lap
                taken += 1
            if taken == 0:
                raise RuntimeError(
                    f"Could not sample any frames from {video_path}"
                )
            luma_mean = luma_sum / taken
            sharp_mean = sharp_sum / taken
        finally:
            cap.release()

        max_top = int(h * max_edge_fraction)
        max_bottom = int(h * max_edge_fraction)
        max_left = int(w * max_edge_fraction)
        max_right = int(w * max_edge_fraction)

        col_luma = luma_mean.mean(axis=0)
        # Letterbox: last column from edge whose mean luminance is dark.
        left_dark = np.where(col_luma[:max_left] < letterbox_luma_thresh)[0]
        left = int(left_dark.max()) + 1 if left_dark.size else 0
        right_region = col_luma[w - max_right :]
        right_dark = np.where(right_region < letterbox_luma_thresh)[0]
        right = int(max_right - right_dark.min()) if right_dark.size else 0

        sharp_view = sharp_mean[:, left : (w - right) if right > 0 else w]
        row_sharp = sharp_view.mean(axis=1)
        interior_lo = int(h * 0.30)
        interior_hi = int(h * 0.70)
        interior_median = float(np.median(row_sharp[interior_lo:interior_hi]))
        sharp_thresh = overlay_sharpness_ratio * max(interior_median, 1e-6)
        # Overlay band: last row from edge whose mean sharpness exceeds threshold.
        top_hot = np.where(row_sharp[:max_top] > sharp_thresh)[0]
        top = int(top_hot.max()) + 1 if top_hot.size else 0
        bottom_region = row_sharp[h - max_bottom :]
        bottom_hot = np.where(bottom_region > sharp_thresh)[0]
        bottom = int(max_bottom - bottom_hot.min()) if bottom_hot.size else 0

        return cls(
            top=min(max_top, top + margin_px) if top > 0 else 0,
            bottom=min(max_bottom, bottom + margin_px) if bottom > 0 else 0,
            left=min(max_left, left + margin_px) if left > 0 else 0,
            right=min(max_right, right + margin_px) if right > 0 else 0,
        )


DEFAULT_CROP = CropBox()


def resolve_crop(video_path: str, crop: CropBox | None = None) -> CropBox:
    """Return ``crop`` if provided, else auto-detect from the video.

    Pipeline entry points should default ``crop=None`` and call this so
    each input video gets a layout-correct crop instead of silently
    inheriting the HD-tuned ``DEFAULT_CROP`` constants on, e.g., PAL SD
    sources. Auto-detection is cheap (samples ~40 frames once at the
    start of the run).
    """
    if crop is not None:
        return crop
    return CropBox.auto_detect(video_path)


def read_frame_cropped(
    cap: cv2.VideoCapture,
    frame_idx: int,
    crop: CropBox = DEFAULT_CROP,
) -> np.ndarray | None:
    """Seek to ``frame_idx`` and return the BGR frame with overlay cropped."""
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_idx))
    ret, frame = cap.read()
    if not ret:
        return None
    return crop.apply(frame)


def open_and_crop(
    video_path: str, crop: CropBox = DEFAULT_CROP
) -> tuple[cv2.VideoCapture, tuple[int, int], int, float]:
    """Open a video and return (cap, (cropped_w, cropped_h), n_frames, fps)."""
    cap = cv2.VideoCapture(video_path)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cropped_w = max(0, w - crop.left - crop.right)
    cropped_h = max(0, h - crop.top - crop.bottom)
    return cap, (cropped_w, cropped_h), n, fps
