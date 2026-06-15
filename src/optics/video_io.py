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


DEFAULT_CROP = CropBox()


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
