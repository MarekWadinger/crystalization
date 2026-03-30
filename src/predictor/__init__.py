"""Predictor module — mrDMD video decomposition and prediction."""

from predictor.dmd import (
    fit_mrdmd,
    get_mode_info,
    predict_frames,
    reconstruct_modes,
    snapshot_to_image,
    visualize_mode,
)
from predictor.io import apply_hankel, get_video_info, load_video_snapshots
from predictor.types import DMDConfig, DMDResult, PreprocessConfig

__all__ = [
    "DMDConfig",
    "DMDResult",
    "PreprocessConfig",
    "apply_hankel",
    "fit_mrdmd",
    "get_mode_info",
    "get_video_info",
    "load_video_snapshots",
    "predict_frames",
    "reconstruct_modes",
    "snapshot_to_image",
    "visualize_mode",
]
