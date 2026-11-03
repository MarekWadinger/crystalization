"""Marker-controlled watershed crystal detector.

Drop-in replacement for ``annotator.detection.detect_crystals_in_layer``
and ``annotator.detection.process_frame``. The edge-based detector
(adaptive threshold + morphological closing + ``findContours``) fails on
dense in-focus clusters where neighbouring crystals share dark edges:
the closing step welds their boundaries together and a single
``cv2.findContours`` blob spans the whole agglomerate. Manuscript
Figure 11 (``papers/cep/manuscript.md`` §7.4) shows that failure mode.

The watershed pipeline implemented here is the textbook
"marker-controlled watershed" recipe used in cell-biology
segmentation:

1. Adaptive threshold to extract the dark-edge network.
2. Light 3x3 morphological opening to remove speckle.
3. Distance transform on the *non-edge* foreground.
4. Local maxima of the distance map -> seed markers (one per crystal
   interior).
5. ``skimage.segmentation.watershed`` flooding from the markers with
   the inverted distance map as topography; ridges of the edge image
   act as natural barriers.
6. Apply the existing area / aspect filters to every labelled basin
   and emit a :class:`~annotator.types.Crystal` per surviving basin.

Run ``uv run python -m optics.detect_watershed`` to render the
side-by-side comparison figure against the legacy detector.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray
from skimage.feature import peak_local_max
from skimage.morphology import h_maxima
from skimage.segmentation import watershed

from annotator.depth import (
    compute_depth_map,
    extract_layer_mask,
    segment_layers,
)
from annotator.detection import process_frame as process_frame_edge
from annotator.flow import compute_flow_magnitude
from annotator.sharpness import compute_sharpness_map
from annotator.types import (
    Crystal,
    FrameResult,
    LayerConfig,
    LayerResult,
    Mat,
)
from annotator.viz import LAYER_COLORS, draw_crystals
from optics.video_io import DEFAULT_CROP, CropBox

# --- Watershed tuning knobs --------------------------------------------------
# Calibrated for Camera 100 (configs/camera_100.toml, ~1.7 um/px) where the median
# in-focus crystal is ~24 px wide (≈ 0.040 mm at 1.66 µm/px). Adjust per-installation if the
# optical setup, pixel pitch, or expected crystal size changes.
#
# _PEAK_MIN_DISTANCE: minimum separation (px) between distance-transform
# seeds. Set to ~half the expected crystal diameter so neighbouring crystals
# get distinct seeds but a single crystal cannot spawn multiple basins.
_PEAK_MIN_DISTANCE = 12
# _PEAK_THRESHOLD_ABS: minimum value (px) in the distance transform for a
# seed candidate. A value of N means the seed sits at least N px from any
# edge, so thin slivers and edge speckle are discarded.
_PEAK_THRESHOLD_ABS = 6.0
# _H_MAXIMA_PARAM: h-maxima suppression height on the distance map. Only
# peaks that rise more than this above their surrounding region survive,
# which removes plateau speckle that local-maxima alone keeps. 1.5-3.0 is
# the practical range for this dataset; raise to merge more, lower to split.
_H_MAXIMA_PARAM = 2.5


def _crystal_from_region(
    region_mask: NDArray[np.uint8], config: LayerConfig
) -> Crystal | None:
    """Fit an oriented bounding rectangle and apply the legacy filters."""
    area = int(cv2.countNonZero(region_mask))
    if area < config.min_area or area > config.max_area:
        return None

    contours, _ = cv2.findContours(
        region_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    if not contours:
        return None
    contour = max(contours, key=cv2.contourArea)  # type: ignore[call-overload]
    if len(contour) < 5:
        return None

    (cx, cy), (w, h), angle = cv2.minAreaRect(contour)
    if w > h:
        w, h = h, w
        angle = (angle + 90.0) % 180.0

    if min(w, h) < 1e-3:
        return None
    aspect = max(w, h) / min(w, h)
    if aspect > config.max_aspect_ratio:
        return None

    return Crystal(
        y=float(cy),
        x=float(cx),
        width=float(w),
        height=float(h),
        angle=float(angle),
    )


def detect_crystals_watershed(
    gray: Mat,
    mask: NDArray[np.uint8],
    config: LayerConfig,
    layer_id: int = 0,
) -> list[Crystal]:
    """Detect crystals inside ``mask`` with marker-controlled watershed.

    Signature matches :func:`annotator.detection.detect_crystals_in_layer`
    so this function can be used as a drop-in replacement. ``layer_id``
    is accepted for API compatibility but the watershed has no
    layer-dependent morphology — barriers come from the distance map
    rather than from a closing kernel.
    """
    del layer_id  # kept for API parity with the edge-based detector

    masked = gray.copy()
    masked[mask == 0] = 255

    block_size = max(3, int(config.edge_block_size) | 1)

    edges: Mat = cv2.adaptiveThreshold(
        masked,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        block_size,
        int(config.edge_c),
    )
    edges[mask == 0] = 0

    kernel_3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    edges_cleaned: Mat = cv2.morphologyEx(edges, cv2.MORPH_OPEN, kernel_3)

    foreground = cv2.bitwise_and(
        cv2.bitwise_not(edges_cleaned),
        cv2.bitwise_not(edges_cleaned),
        mask=mask,
    )
    dist = cv2.distanceTransform(foreground, cv2.DIST_L2, 5)

    if not np.any(dist > _PEAK_THRESHOLD_ABS):
        return []

    # h-maxima suppression: keep only peaks that rise more than _H_MAXIMA_PARAM
    # above the surrounding distance-transform plateau. This is the principled
    # way to kill speckle over-segmentation -- many tiny local maxima inside a
    # single crystal interior collapse to one regional maximum.
    hmax_mask = h_maxima(dist, h=_H_MAXIMA_PARAM).astype(bool)
    hmax_mask &= dist >= _PEAK_THRESHOLD_ABS
    hmax_mask &= mask > 0
    if not np.any(hmax_mask):
        return []

    peak_coords = peak_local_max(
        dist,
        min_distance=_PEAK_MIN_DISTANCE,
        threshold_abs=_PEAK_THRESHOLD_ABS,
        labels=hmax_mask.astype(np.uint8),
    )
    if peak_coords.size == 0:
        return []

    seed_img = np.zeros(dist.shape, dtype=np.uint8)
    seed_img[peak_coords[:, 0], peak_coords[:, 1]] = 255
    # Dilate a touch so each peak becomes a small connected blob rather
    # than a single pixel — stabilises connectedComponents labelling.
    seed_img = cv2.dilate(seed_img, kernel_3, iterations=1)

    num_seeds, markers = cv2.connectedComponents(seed_img)
    if num_seeds <= 1:
        return []

    # Reserve label 0 for "unlabelled" so skimage.watershed treats it
    # as a region to flood. Background outside the layer mask gets a
    # dedicated label so it doesn't swallow crystal basins.
    markers = markers.astype(np.int32)
    bg_label = num_seeds  # one past the last seed label
    markers[mask == 0] = bg_label

    # Topography: low where the distance map is high (crystal interiors)
    # so watershed floods outward from the seeds until it hits an edge.
    topography = -dist
    labels = watershed(topography, markers=markers, mask=(mask > 0))

    crystals: list[Crystal] = []
    # Seeds are labelled 1..num_seeds-1; background got bg_label. Skip
    # both background labels and the unlabelled (0) ring.
    for label in range(1, num_seeds):
        region = (labels == label).astype(np.uint8) * 255
        crystal = _crystal_from_region(region, config)
        if crystal is not None:
            crystals.append(crystal)

    return crystals


def process_frame_watershed(
    gray: Mat,
    prev_gray: Mat | None,
    frame_idx: int,
    config: LayerConfig,
) -> tuple[FrameResult, NDArray[np.int32]]:
    """Watershed analogue of :func:`annotator.detection.process_frame`."""
    sharpness = compute_sharpness_map(gray, config.blur_kernel)
    if prev_gray is not None:
        flow_mag = compute_flow_magnitude(prev_gray, gray)
    else:
        flow_mag = np.zeros_like(sharpness)

    depth_map = compute_depth_map(sharpness, flow_mag, config)
    layer_map = segment_layers(depth_map, config.num_layers)

    frame_result = FrameResult(frame_idx=frame_idx)
    for layer_id in range(config.num_layers):
        mask = extract_layer_mask(layer_map, layer_id)
        crystals = detect_crystals_watershed(
            gray, mask, config, layer_id=layer_id
        )
        frame_result.layers.append(
            LayerResult(layer_id=layer_id, crystals=crystals)
        )

    return frame_result, layer_map


# ---------------------------------------------------------------------------
# Comparison figure
# ---------------------------------------------------------------------------

_DEFAULT_VIDEO = "datasets/2026-02-05 10-36-32.mp4"
_DEFAULT_FIG = Path("docs/optics/figures/17_watershed_vs_edge.png")
_DEFAULT_FRAME = 750


def _read_frame(
    video_path: str, frame_idx: int, crop: CropBox
) -> NDArray[np.uint8]:
    cap = cv2.VideoCapture(video_path)
    try:
        if not cap.isOpened():
            raise FileNotFoundError(f"cannot open video {video_path!r}")
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_idx))
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(
                f"failed to read frame {frame_idx} from {video_path!r}"
            )
    finally:
        cap.release()
    cropped = crop.apply(frame)
    return cropped


def _render_panel(
    frame_bgr: np.ndarray, result: FrameResult
) -> tuple[np.ndarray, int]:
    canvas = frame_bgr.copy()
    total = 0
    for layer in result.layers:
        color = LAYER_COLORS[layer.layer_id % len(LAYER_COLORS)]
        draw_crystals(canvas, layer.crystals, color, thickness=2)
        total += layer.count
    rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
    return rgb, total


def _build_comparison_figure(
    video_path: str,
    frame_idx: int,
    config: LayerConfig,
    crop: CropBox,
    out_path: Path,
) -> tuple[int, int]:
    frame_bgr = _read_frame(video_path, frame_idx, crop)
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

    edge_result, _ = process_frame_edge(gray, None, frame_idx, config)
    ws_result, _ = process_frame_watershed(gray, None, frame_idx, config)

    edge_rgb, edge_count = _render_panel(frame_bgr, edge_result)
    ws_rgb, ws_count = _render_panel(frame_bgr, ws_result)

    fig, axes = plt.subplots(1, 2, figsize=(20, 5.5))
    axes[0].imshow(edge_rgb)
    axes[0].set_title(f"Edge-based (legacy): {edge_count} detections")
    axes[0].set_axis_off()
    axes[1].imshow(ws_rgb)
    axes[1].set_title(f"Watershed (new): {ws_count} detections")
    axes[1].set_axis_off()
    fig.suptitle(
        f"Detector comparison on frame {frame_idx}: "
        "watershed recovers the dense in-focus cluster"
    )
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return edge_count, ws_count


def main() -> None:
    config = LayerConfig()
    edge_count, ws_count = _build_comparison_figure(
        _DEFAULT_VIDEO,
        _DEFAULT_FRAME,
        config,
        DEFAULT_CROP,
        _DEFAULT_FIG,
    )
    print(f"frame {_DEFAULT_FRAME}: edge-based detector -> {edge_count}")
    print(f"frame {_DEFAULT_FRAME}: watershed detector   -> {ws_count}")
    print(f"wrote {_DEFAULT_FIG}")


if __name__ == "__main__":
    main()
