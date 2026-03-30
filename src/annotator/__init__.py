"""Crystal video layer decomposition and object detection."""

from annotator.depth import (
    compute_depth_map,
    extract_layer_mask,
    normalize,
    segment_layers,
)
from annotator.detection import detect_crystals_in_layer, process_frame
from annotator.flow import compute_flow_magnitude
from annotator.io import (
    load_detections,
    process_video,
    write_csv,
    write_detailed_csv,
)
from annotator.sharpness import compute_sharpness_map
from annotator.types import (
    Crystal,
    Detection,
    FrameResult,
    LayerConfig,
    LayerResult,
    Mat,
)
from annotator.viz import (
    LAYER_COLORS,
    add_label,
    annotate_frame,
    bgr_to_rgb,
    colorize_layers,
    colorize_map,
    downscale,
    draw_crystals,
    draw_legend,
    draw_stats,
)

__all__ = [
    "LAYER_COLORS",
    "Crystal",
    "Detection",
    "FrameResult",
    "LayerConfig",
    "LayerResult",
    "Mat",
    "add_label",
    "annotate_frame",
    "bgr_to_rgb",
    "colorize_layers",
    "colorize_map",
    "compute_depth_map",
    "compute_flow_magnitude",
    "compute_sharpness_map",
    "detect_crystals_in_layer",
    "downscale",
    "draw_crystals",
    "draw_legend",
    "draw_stats",
    "extract_layer_mask",
    "load_detections",
    "normalize",
    "process_frame",
    "process_video",
    "segment_layers",
    "write_csv",
    "write_detailed_csv",
]
