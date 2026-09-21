"""Publication-quality block diagram of the optics pipeline.

Renders a single landscape figure summarising the end-to-end
through-sight-glass crystal-size measurement pipeline. Pure matplotlib
implementation — no graphviz dependency.

Run with:
    uv run python -m optics.pipeline_diagram
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

# Stage colours (light pastels with a strong accent for the final output).
COLOR_A: str = "#cfe2f3"  # ingest — light blue
COLOR_B: str = "#d9ead3"  # per-frame analysis — light green
COLOR_C: str = "#fce5cd"  # per-crystal defocus inversion — light orange
COLOR_D: str = "#e6d6f2"  # optics model — light purple
COLOR_E: str = "#f6b26b"  # aggregation/final — strong orange
COLOR_F: str = "#dddddd"  # validation bar — light grey

EDGE_COLOR: str = "#333333"
TEXT_COLOR: str = "#111111"

OUTPUT_PATH: Path = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "optics"
    / "figures"
    / "13_pipeline.png"
)


def _add_box(
    ax: Axes,
    x: float,
    y: float,
    width: float,
    height: float,
    text: str,
    facecolor: str,
    fontsize: float = 8.5,
    fontweight: str = "normal",
    textcolor: str | None = None,
) -> tuple[float, float, float, float]:
    """Draw a rounded box with centred text. Returns the bounding box."""
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.02,rounding_size=0.12",
        linewidth=1.2,
        edgecolor=EDGE_COLOR,
        facecolor=facecolor,
        zorder=2,
    )
    ax.add_patch(patch)
    ax.text(
        x + width / 2.0,
        y + height / 2.0,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight=fontweight,
        color=textcolor if textcolor is not None else TEXT_COLOR,
        zorder=3,
    )
    return (x, y, width, height)


def _arrow(
    ax: Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    color: str = EDGE_COLOR,
    linewidth: float = 1.4,
    linestyle: str = "-",
) -> None:
    """Draw a styled arrow between two points."""
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=14,
        linewidth=linewidth,
        linestyle=linestyle,
        color=color,
        zorder=1,
    )
    ax.add_patch(arrow)


def _bottom_center(
    box: tuple[float, float, float, float],
) -> tuple[float, float]:
    x, y, w, _ = box
    return (x + w / 2.0, y)


def _top_center(box: tuple[float, float, float, float]) -> tuple[float, float]:
    x, y, w, h = box
    return (x + w / 2.0, y + h)


def _left_center(
    box: tuple[float, float, float, float],
) -> tuple[float, float]:
    x, y, _, h = box
    return (x, y + h / 2.0)


def _right_center(
    box: tuple[float, float, float, float],
) -> tuple[float, float]:
    x, y, w, h = box
    return (x + w, y + h / 2.0)


def build_figure() -> plt.Figure:
    """Build the pipeline figure and return it."""
    fig, ax = plt.subplots(figsize=(14.0, 9.0))
    ax.set_xlim(0.0, 14.0)
    ax.set_ylim(0.0, 9.0)
    ax.set_axis_off()

    # Title.
    ax.text(
        7.0,
        8.65,
        "Through-sight-glass crystal-size measurement pipeline",
        ha="center",
        va="center",
        fontsize=15.5,
        fontweight="bold",
        color=TEXT_COLOR,
    )

    # Column geometry. Five columns across [0.2, 13.8].
    col_width: float = 2.5
    col_x: list[float] = [0.25, 3.0, 5.75, 8.5, 11.25]
    box_h: float = 1.05
    # Vertical band for stages A-E (validation bar sits below).
    top_y: float = 7.6

    # --- Stage A: Ingest (column 0, 2 boxes) ---
    a1 = _add_box(
        ax,
        col_x[0],
        top_y - box_h,
        col_width,
        box_h,
        "Raw sight-glass video\n1920×1080, 30 fps",
        COLOR_A,
    )
    a2 = _add_box(
        ax,
        col_x[0],
        top_y - 2 * box_h - 0.45,
        col_width,
        box_h,
        "DVR-overlay crop\nremove timestamp + CH01 band",
        COLOR_A,
    )
    _arrow(ax, _bottom_center(a1), _top_center(a2))

    # --- Stage B: Per-frame analysis (column 1, 3 boxes) ---
    b_top_y: float = top_y
    b1 = _add_box(
        ax,
        col_x[1],
        b_top_y - box_h,
        col_width,
        box_h,
        "Per-pixel Laplacian²\nsmoothed by Gaussian kernel",
        COLOR_B,
    )
    b2 = _add_box(
        ax,
        col_x[1],
        b_top_y - 2 * box_h - 0.35,
        col_width,
        box_h,
        "Sharpness-layer decomposition\nsegment into N depth slices",
        COLOR_B,
    )
    b3 = _add_box(
        ax,
        col_x[1],
        b_top_y - 3 * box_h - 0.70,
        col_width,
        box_h,
        "Edge-based crystal detector\nrotated rects per layer",
        COLOR_B,
    )
    _arrow(ax, _bottom_center(b1), _top_center(b2))
    _arrow(ax, _bottom_center(b2), _top_center(b3))

    # Arrow from Stage A → Stage B (a2 right side → b1 left side).
    _arrow(ax, _right_center(a2), _left_center(b1))

    # --- Stage C: Per-crystal defocus inversion (column 2, 3 boxes) ---
    c_top_y: float = top_y
    c1 = _add_box(
        ax,
        col_x[2],
        c_top_y - box_h,
        col_width,
        box_h,
        "Focal-plane subset\n(top-quantile sharpness)\n→ apparent-size prior",
        COLOR_C,
        fontsize=8.2,
    )
    c2 = _add_box(
        ax,
        col_x[2],
        c_top_y - 2 * box_h - 0.35,
        col_width,
        box_h,
        "Off-focus crystals\n→ Gaussian-PSF inversion\n→ CoC, then d_near, d_far",
        COLOR_C,
        fontsize=8.2,
    )
    c3 = _add_box(
        ax,
        col_x[2],
        c_top_y - 3 * box_h - 0.70,
        col_width,
        box_h,
        "Bayesian near/far\ndisambiguation under prior",
        COLOR_C,
    )
    _arrow(ax, _bottom_center(c1), _top_center(c2))
    _arrow(ax, _bottom_center(c2), _top_center(c3))

    # Arrows from B3 (edge-based detector) → C1 and → C2.
    _arrow(ax, _right_center(b3), _left_center(c1))
    # Curved-ish arrow from b3 to c2: draw from right edge of b3 to left of c2.
    _arrow(
        ax,
        (b3[0] + b3[2], b3[1] + b3[3] * 0.3),
        _left_center(c2),
        linestyle="--",
    )

    # --- Stage D: Optics model (column 3, 2 boxes) ---
    d_top_y: float = top_y
    d1 = _add_box(
        ax,
        col_x[3],
        d_top_y - box_h,
        col_width,
        box_h,
        "Lens datasheet\nf=35mm, F/N, pitch",
        COLOR_D,
    )
    d2 = _add_box(
        ax,
        col_x[3],
        d_top_y - 2 * box_h - 0.35,
        col_width,
        box_h,
        "Thin-lens scale\nmm/px(d_o) = pitch · d_o / i",
        COLOR_D,
    )
    _arrow(ax, _bottom_center(d1), _top_center(d2))

    # Arrow from D2 (thin-lens scale) → C2 (off-focus crystals).
    _arrow(ax, _left_center(d2), _right_center(c2), linestyle="--")

    # --- Stage E: Aggregation (column 4, 2 boxes, larger emphasis) ---
    e_top_y: float = top_y
    e_box_h: float = 1.15
    e1 = _add_box(
        ax,
        col_x[4],
        e_top_y - e_box_h,
        col_width,
        e_box_h,
        "Depth-corrected\nphysical sizes per crystal",
        COLOR_E,
        fontsize=9.0,
        fontweight="bold",
        textcolor="#111111",
    )
    e2 = _add_box(
        ax,
        col_x[4],
        e_top_y - 2 * e_box_h - 0.35,
        col_width,
        e_box_h,
        "Final CSD\nmedian / CV / shape fit",
        COLOR_E,
        fontsize=9.0,
        fontweight="bold",
        textcolor="#111111",
    )
    _arrow(ax, _bottom_center(e1), _top_center(e2))

    # Arrow from Stage C (c3) and D (d2) into E1.
    _arrow(ax, _right_center(c3), _left_center(e1))

    # --- Horizontal separator above Stage F ---
    sep_y: float = 1.55
    ax.plot(
        [0.25, 13.75],
        [sep_y, sep_y],
        color="#888888",
        linewidth=0.9,
        linestyle="--",
        zorder=1,
    )

    # --- Stage F: Validation bar (full-width single elongated box) ---
    f_text: str = (
        "Cross-batch growth-curve self-calibration   ←   "
        "median(t-into-strike) collapses across batches   →   "
        "identifies extension tube + F-number"
    )
    _add_box(
        ax,
        0.25,
        0.55,
        13.5,
        0.75,
        f_text,
        COLOR_F,
        fontsize=9.0,
        fontweight="bold",
    )
    ax.text(
        0.30,
        1.40,
        "Stage F — Validation",
        ha="left",
        va="bottom",
        fontsize=9.5,
        fontweight="bold",
        color="#555555",
    )

    # Stage labels (column headers).
    stage_labels: list[tuple[float, str]] = [
        (col_x[0] + col_width / 2.0, "A — Ingest"),
        (col_x[1] + col_width / 2.0, "B — Per-frame analysis"),
        (col_x[2] + col_width / 2.0, "C — Defocus inversion"),
        (col_x[3] + col_width / 2.0, "D — Optics model"),
        (col_x[4] + col_width / 2.0, "E — Aggregation"),
    ]
    for cx, label in stage_labels:
        ax.text(
            cx,
            8.05,
            label,
            ha="center",
            va="center",
            fontsize=10.5,
            fontweight="bold",
            color="#444444",
        )

    # Footnote.
    ax.text(
        13.75,
        0.18,
        "All blocks implemented in src/optics/; "
        "reproducible via uv run python -m optics.{module}",
        ha="right",
        va="bottom",
        fontsize=8.5,
        style="italic",
        color="#555555",
    )

    return fig


def main() -> Path:
    """Render the pipeline diagram and save it to disk."""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig = build_figure()
    fig.savefig(OUTPUT_PATH, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return OUTPUT_PATH


if __name__ == "__main__":
    path = main()
    print(f"Wrote {path}")
