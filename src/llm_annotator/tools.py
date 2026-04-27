"""Agent tools for crystal measurement and analysis."""

from __future__ import annotations

import base64
import io
import math

import cv2
import logfire
import numpy as np
from numpy.typing import NDArray
from pydantic_ai import RunContext

from llm_annotator.agent import FrameContext
from llm_annotator.types import (
    CompareResult,
    CountResult,
    CrystalSystem,
    DepthLayer,
    FeatureMapResult,
    GrowthRateResult,
    HistogramResult,
    MeasureResult,
)

# Map classical annotator layer_id to DepthLayer.
# layer 0 = far (sharpest), 1 = mid, 2 = near (blurriest)
_LAYER_MAP: dict[int, DepthLayer] = {
    0: DepthLayer.FAR,
    1: DepthLayer.MID,
    2: DepthLayer.NEAR,
}


def _crop_region(
    frame_bgr: NDArray[np.uint8],
    x: float,
    y: float,
    radius: float,
) -> NDArray[np.uint8]:
    """Crop a square region centred on (x, y) with given radius."""
    h, w = frame_bgr.shape[:2]
    x0 = max(0, int(x - radius))
    y0 = max(0, int(y - radius))
    x1 = min(w, int(x + radius))
    y1 = min(h, int(y + radius))
    return frame_bgr[y0:y1, x0:x1]


# ── Tool 1: measure_crystal ────────────────────────────────────


async def measure_crystal(
    ctx: RunContext[FrameContext],
    x: float,
    y: float,
    radius: float,
) -> MeasureResult:
    """Measure crystal dimensions in a region around (x, y).

    Crops the frame, converts to grayscale, thresholds, and
    returns the bounding-box dimensions of the largest contour.
    """
    with logfire.span("measure_crystal"):
        crop = _crop_region(ctx.deps.frame_bgr, x, y, radius)
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
        contours, _ = cv2.findContours(
            thresh,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        if contours:
            largest = max(contours, key=lambda c: cv2.contourArea(c))
            _, (bw, bh), _ = cv2.minAreaRect(largest)
            if bw > bh:
                bw, bh = bh, bw
        else:
            ch, cw = crop.shape[:2]
            bw, bh = float(cw), float(ch)

        area = bw * bh
        aspect = bw / bh if bh > 1e-6 else 0.0

    return MeasureResult(
        width_px=bw,
        height_px=bh,
        area_px=area,
        aspect_ratio=aspect,
    )


# ── Tool 2: count_crystals ─────────────────────────────────────


async def count_crystals(
    ctx: RunContext[FrameContext],
) -> CountResult:
    """Run classical CV detection on the current frame.

    Uses ``annotator.detection.process_frame`` to count
    crystals per depth layer.
    """
    from annotator.detection import process_frame
    from annotator.types import LayerConfig

    with logfire.span("count_crystals"):
        gray = cv2.cvtColor(ctx.deps.frame_bgr, cv2.COLOR_BGR2GRAY)
        result, _ = process_frame(
            gray, None, ctx.deps.frame_idx, LayerConfig()
        )

        layer_counts: dict[DepthLayer, int] = {}
        total = 0
        for lr in result.layers:
            depth = _LAYER_MAP.get(lr.layer_id, DepthLayer.FAR)
            layer_counts[depth] = lr.count
            total += lr.count

    return CountResult(layer_counts=layer_counts, total=total)


# ── Tool 3: compare_frames ─────────────────────────────────────


async def compare_frames(
    ctx: RunContext[FrameContext],
    previous_frame_idx: int,
) -> CompareResult:
    """Compare current annotations with a previous frame's.

    Matches crystals by nearest-neighbour on bounding-box
    centres and reports appeared, disappeared, persistent
    counts and mean displacement.
    """
    prev_ann = None
    for ann in ctx.deps.previous_annotations:
        if ann.frame_idx == previous_frame_idx:
            prev_ann = ann
            break

    if prev_ann is None:
        return CompareResult(
            appeared=0,
            disappeared=0,
            persistent=0,
            mean_displacement_px=0.0,
        )

    with logfire.span("compare_frames"):
        prev_centres = [(c.bbox.x, c.bbox.y) for c in prev_ann.crystals]
        # Use the latest annotation as the current frame.
        curr_ann = (
            ctx.deps.previous_annotations[-1]
            if ctx.deps.previous_annotations
            else None
        )
        if curr_ann is None or curr_ann.frame_idx == prev_ann.frame_idx:
            return CompareResult(
                appeared=0,
                disappeared=0,
                persistent=len(prev_centres),
                mean_displacement_px=0.0,
            )

        curr_centres = [(c.bbox.x, c.bbox.y) for c in curr_ann.crystals]

        matched_prev: set[int] = set()
        displacements: list[float] = []

        for cx, cy in curr_centres:
            best_dist = float("inf")
            best_pi = -1
            for pi, (px, py) in enumerate(prev_centres):
                if pi in matched_prev:
                    continue
                d = math.hypot(cx - px, cy - py)
                if d < best_dist:
                    best_dist = d
                    best_pi = pi
            if best_pi >= 0 and best_dist < 100.0:
                matched_prev.add(best_pi)
                displacements.append(best_dist)

        persistent = len(displacements)
        appeared = len(curr_centres) - persistent
        disappeared = len(prev_centres) - persistent
        mean_disp = float(np.mean(displacements)) if displacements else 0.0

    return CompareResult(
        appeared=appeared,
        disappeared=disappeared,
        persistent=persistent,
        mean_displacement_px=mean_disp,
    )


# ── Tool 4: classify_crystal_system ────────────────────────────


async def classify_crystal_system(
    ctx: RunContext[FrameContext],
    x: float,
    y: float,
    radius: float,
) -> str:
    """Classify crystal system from shape at (x, y).

    Analyses contour vertices and angles to map the 2-D
    projected shape to a crystallographic system.
    """
    with logfire.span("classify_crystal_system"):
        crop = _crop_region(ctx.deps.frame_bgr, x, y, radius)
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
        contours, _ = cv2.findContours(
            thresh,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        if not contours:
            return CrystalSystem.UNKNOWN

        largest = max(contours, key=lambda c: cv2.contourArea(c))
        peri = cv2.arcLength(largest, closed=True)
        approx = cv2.approxPolyDP(largest, 0.04 * peri, closed=True)
        n_verts = len(approx)

        _, (bw, bh), _ = cv2.minAreaRect(largest)
        if bw > bh:
            bw, bh = bh, bw
        aspect = bw / bh if bh > 1e-6 else 1.0

    if n_verts == 3:
        return CrystalSystem.TRIGONAL
    if n_verts == 6:
        return CrystalSystem.HEXAGONAL
    if n_verts == 4:
        if 0.85 <= aspect <= 1.15:
            return CrystalSystem.CUBIC
        if aspect < 0.85:
            return CrystalSystem.ORTHORHOMBIC
        return CrystalSystem.TETRAGONAL
    return CrystalSystem.UNKNOWN


# ── Tool 5: estimate_growth_rate ────────────────────────────────


async def estimate_growth_rate(
    ctx: RunContext[FrameContext],
    crystal_id: str,
) -> GrowthRateResult:
    """Estimate growth rate of a tracked crystal.

    Searches previous annotations for the crystal and computes
    size change per frame using ``sqrt(width * height)``.
    """
    sizes: list[tuple[int, float]] = []

    with logfire.span("estimate_growth_rate"):
        for ann in ctx.deps.previous_annotations:
            for c in ann.crystals:
                if c.crystal_id == crystal_id:
                    size = math.sqrt(c.bbox.width * c.bbox.height)
                    sizes.append((ann.frame_idx, size))

    if len(sizes) < 2:
        return GrowthRateResult(
            crystal_id=crystal_id,
            growth_rate_px_per_frame=0.0,
            frames_observed=len(sizes),
        )

    sizes.sort(key=lambda t: t[0])
    first_frame, first_size = sizes[0]
    last_frame, last_size = sizes[-1]
    span = last_frame - first_frame
    rate = (last_size - first_size) / span if span else 0.0

    return GrowthRateResult(
        crystal_id=crystal_id,
        growth_rate_px_per_frame=rate,
        frames_observed=len(sizes),
    )


# ── Tool 6: generate_histogram ─────────────────────────────────


async def generate_histogram(
    ctx: RunContext[FrameContext],
    layer: str,
) -> HistogramResult:
    """Generate size-distribution histogram for a depth layer.

    Computes ``sqrt(w * h)`` for each crystal bounding box
    in the given layer, renders a histogram via matplotlib,
    and returns the PNG image as base64.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    target = DepthLayer(layer)
    sizes: list[float] = []

    with logfire.span("generate_histogram"):
        if ctx.deps.previous_annotations:
            latest = ctx.deps.previous_annotations[-1]
            for c in latest.crystals:
                if c.layer == target:
                    sizes.append(math.sqrt(c.bbox.width * c.bbox.height))

        if not sizes:
            return HistogramResult(
                bin_edges=[],
                counts=[],
                image_base64="",
            )

        fig, ax = plt.subplots(figsize=(6, 4))
        counts_arr, edges_arr, _ = ax.hist(
            sizes, bins="auto", edgecolor="black"
        )
        ax.set_xlabel("Crystal size (px)")
        ax.set_ylabel("Count")
        ax.set_title(f"Size distribution — {target.value} layer")
        fig.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100)
        plt.close(fig)
        buf.seek(0)
        img_b64 = base64.b64encode(buf.read()).decode()

    return HistogramResult(
        bin_edges=[float(e) for e in edges_arr],
        counts=[int(c) for c in counts_arr],
        image_base64=img_b64,
    )


# ── Tool 7: get_sharpness_map ────────────────────────────────


def _bgr_to_base64(img: NDArray) -> str:
    """Encode a BGR image as base64 PNG."""
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        return ""
    return base64.b64encode(bytes(buf)).decode()


async def get_sharpness_map(
    ctx: RunContext[FrameContext],
) -> FeatureMapResult:
    """Compute and return the sharpness (focus) map.

    Bright = sharp/in-focus (far layer),
    dark = blurry/out-of-focus (near layer).
    """
    from annotator.sharpness import compute_sharpness_map
    from annotator.viz import colorize_map

    with logfire.span("get_sharpness_map"):
        gray = cv2.cvtColor(ctx.deps.frame_bgr, cv2.COLOR_BGR2GRAY)
        sharpness = compute_sharpness_map(gray, kernel=15)
        colored = colorize_map(sharpness, cv2.COLORMAP_INFERNO)

    return FeatureMapResult(
        description=(
            "Sharpness map: bright = sharp/in-focus "
            "(far layer), dark = blurry (near layer)"
        ),
        image_base64=_bgr_to_base64(colored),
    )


# ── Tool 8: get_depth_map ────────────────────────────────────


async def get_depth_map(
    ctx: RunContext[FrameContext],
) -> FeatureMapResult:
    """Compute and return the depth layer map.

    Uses sharpness to estimate depth. Bright = near
    (blurry), dark = far (sharp). Shows which depth
    layer each pixel belongs to.
    """
    from annotator.depth import compute_depth_map
    from annotator.sharpness import compute_sharpness_map
    from annotator.types import LayerConfig
    from annotator.viz import colorize_map

    with logfire.span("get_depth_map"):
        gray = cv2.cvtColor(ctx.deps.frame_bgr, cv2.COLOR_BGR2GRAY)
        cfg = LayerConfig()
        sharpness = compute_sharpness_map(gray, cfg.blur_kernel)
        flow_mag = np.zeros_like(sharpness, dtype=np.float64)
        depth = compute_depth_map(sharpness, flow_mag, cfg)
        colored = colorize_map(depth, cv2.COLORMAP_VIRIDIS)

    return FeatureMapResult(
        description=("Depth map: bright = near (blurry), dark = far (sharp)"),
        image_base64=_bgr_to_base64(colored),
    )


# ── Tool 9: get_layer_map ────────────────────────────────────


async def get_layer_map(
    ctx: RunContext[FrameContext],
) -> FeatureMapResult:
    """Compute and return the segmented layer map.

    Shows the frame divided into discrete depth layers
    (far=blue, mid=green, near=red), matching the
    annotator module's layer decomposition.
    """
    from annotator.depth import (
        compute_depth_map,
        segment_layers,
    )
    from annotator.sharpness import compute_sharpness_map
    from annotator.types import LayerConfig
    from annotator.viz import colorize_layers

    with logfire.span("get_layer_map"):
        gray = cv2.cvtColor(ctx.deps.frame_bgr, cv2.COLOR_BGR2GRAY)
        cfg = LayerConfig()
        sharpness = compute_sharpness_map(gray, cfg.blur_kernel)
        flow_mag = np.zeros_like(sharpness, dtype=np.float64)
        depth = compute_depth_map(sharpness, flow_mag, cfg)
        layers = segment_layers(depth, cfg.num_layers)
        colored = colorize_layers(layers, cfg.num_layers)

    return FeatureMapResult(
        description=(
            "Layer segmentation: blue = far (sharp), "
            "green = mid, red = near (blurry)"
        ),
        image_base64=_bgr_to_base64(colored),
    )
