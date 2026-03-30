"""Video I/O and snapshot matrix construction."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from predictor.types import PreprocessConfig


def get_video_info(video_path: str) -> dict[str, int | float]:
    """Return frame count, FPS, width, height of a video."""
    cap = cv2.VideoCapture(video_path)
    try:
        return {
            "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            "fps": cap.get(cv2.CAP_PROP_FPS),
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        }
    finally:
        cap.release()


def load_video_snapshots(
    video_path: Path | str,
    config: PreprocessConfig,
) -> tuple[NDArray[np.float64], tuple[int, int], float]:
    """Load video into a snapshot matrix.

    Returns:
        X: snapshot matrix of shape (n_pixels, n_frames), float64 in [0, 1]
        frame_shape: (height, width) after downsampling
        fps: effective FPS after frame_skip
    """
    cap = cv2.VideoCapture(str(video_path))
    try:
        orig_fps = cap.get(cv2.CAP_PROP_FPS)
        orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        scale = config.target_height / orig_h
        new_h = config.target_height
        new_w = int(orig_w * scale)
        frame_shape = (new_h, new_w)

        frames: list[NDArray[np.float64]] = []
        frame_idx = 0
        while len(frames) < config.max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            if frame_idx % config.frame_skip == 0:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                resized = cv2.resize(
                    gray, (new_w, new_h), interpolation=cv2.INTER_AREA
                )
                frames.append(
                    resized.astype(np.float64).ravel() / 255.0
                )
            frame_idx += 1
    finally:
        cap.release()

    X = np.column_stack(frames)  # (n_pixels, n_frames)
    effective_fps = orig_fps / config.frame_skip
    return X, frame_shape, effective_fps


def apply_hankel(
    X: NDArray[np.float64], delay: int
) -> NDArray[np.float64]:
    """Apply time-delay (Hankel) embedding.

    For delay=1, returns X unchanged.
    For delay=d, stacks d time-shifted copies vertically,
    producing shape (n_pixels * d, n_frames - d + 1).
    """
    if delay <= 1:
        return X
    n_pixels, n_frames = X.shape
    n_cols = n_frames - delay + 1
    blocks = [X[:, i : i + n_cols] for i in range(delay)]
    return np.vstack(blocks)
