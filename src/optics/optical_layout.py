"""Camera 100 optical-layout schematic (Figure 5b / 18_optical_layout*.png).

Reads ``configs/camera_100.toml`` and draws the sensor → slurry chain to
scale, in English (derived values annotated) and Slovak (measured values).

    uv run python -m optics.optical_layout
"""

from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import numpy as np
from matplotlib import font_manager as fm
from matplotlib.patches import (
    FancyBboxPatch,
    Polygon,
    Rectangle,
    RegularPolygon,
)

from optics.config import SOURCE_RANK, load_camera, source_classes

REPO = Path(__file__).resolve().parents[2]
FIG_DIR = REPO / "docs" / "optics" / "figures"
# Side view of the installation (Aug-photos 20260810_111738, resized to 2000 px).
# Only cropped and labelled here; the pixels are not altered.
PHOTO = REPO / "docs" / "lens" / "20260810_111738.jpg"
PHOTO_CROP = (650, 375, 2000, 1175)  # left, top, right, bottom in PHOTO pixels
# Label → (text x, text y, arrow tip x, arrow tip y) in PHOTO pixels.
PHOTO_LABELS = {
    "camera": (800, 1110, 880, 900),
    "tube": (1250, 1130, 1430, 880),
    "lens": (1620, 1130, 1585, 885),
    "sight glass": (1800, 500, 1780, 700),
    "tape measure (cm)": (1050, 470, 1150, 755),
}
# Arrow colour = how well the length is sourced (tags in configs/camera_100.toml).
# Dimension-arrow colour = how well the length is sourced (tags in
# configs/camera_100.toml). Black is kept for names, so no source class uses it.
BLUE, ORANGE = "#1f5fbf", "#c05800"
SOURCE_COLOR = {
    **dict.fromkeys(("MEASURED", "PHOTO", "DATASHEET", "CHOICE"), BLUE),
    **dict.fromkeys(("DERIVED", "PLANT", "ESTIMATE"), ORANGE),
    **dict.fromkeys(("ASSUMED", "UNSOURCED"), "red"),
}
NEUTRAL = "#333333"  # the sensor: a named feature, not a sourced length
# Legend: an arrow sample per source class (the caption names the classes).
SOURCE_LEGEND = {
    "en": [
        ("datasheet", BLUE),
        ("plant / estimate", ORANGE),
        ("assumed", "red"),
    ],
    "sk": [
        ("katalóg", BLUE),
        ("cukrovar / odhad", ORANGE),
        ("predpoklad", "red"),
    ],
}


def _weakest(cls: dict[str, str], *keys: str) -> str:
    """Weakest provenance class among the config keys a quantity uses."""
    return max((cls[k] for k in keys), key=lambda c: SOURCE_RANK.index(c))


def _sources() -> dict[str, str]:
    """Provenance class of each drawn length, from the config tags."""
    c = source_classes()
    return {
        "sensor": c["camera.flange_distance_mm"],
        "e": c["lens.extension_tube_mm"],
        "lens": _weakest(c, "lens.body_length_mm", "lens.focus_travel_mm"),
        "a": c["lens.air_gap_mm"],
        "t": c["sight_glass.thickness_mm"],
        "i": _weakest(
            c,
            "lens.focal_length_mm",
            "lens.extension_tube_mm",
            "lens.focus_travel_mm",
        ),
        "model": c["camera.model"],
        "pitch": _weakest(
            c,
            "camera.cell_width_um",
            "camera.pixel_clock_mhz",
            "dvr.sampling_rate_mhz",
            "lens.focal_length_mm",
            "lens.extension_tube_mm",
            "lens.focus_travel_mm",
        ),
    }


def _geometry() -> dict[str, float]:
    cfg = load_camera()
    f, e, t, n = (
        cfg.focal_length_mm,
        cfg.extension_tube_mm,
        cfg.sight_glass_thickness_mm,
        cfg.sight_glass_index,
    )
    i = f + e + cfg.focus_travel_mm
    d_focus = f * i / (i - f)
    delta = t * (1 - 1 / n)
    return {
        "f": f,
        "e": e,
        "t": t,
        "n": n,
        "i": i,
        "d_focus": d_focus,
        "delta": delta,
        "t_app": t - delta,
        "body": cfg.lens_body_length_mm + cfg.focus_travel_mm,
        "air": cfg.air_gap_mm,
        # Object-plane µm per PAL sample (x) and line (y) at focus.
        "um_px_x": cfg.sample_pitch_um[0] * (d_focus - f) / f,
        "um_px_y": cfg.sample_pitch_um[1] * (d_focus - f) / f,
        # Front principal plane H: d_focus back from the inner glass face in
        # apparent coordinates, i.e. this far behind the lens front element.
        "h_offset": d_focus - (t - delta) - cfg.air_gap_mm,
        # Rear principal plane H': i in front of the sensor, measured from
        # the lens front element. H != H' because the lens is thick.
        "flange": cfg.flange_distance_mm,
        "camera": cfg.body_length_mm,
        "slurry": tomllib.loads(cfg.source_path.read_text())["figures"][
            "slurry_depth_mm"
        ],
        "h2_offset": cfg.flange_distance_mm
        + e
        + cfg.lens_body_length_mm
        + cfg.focus_travel_mm
        - i,
    }


# Drawn at the printed size so text matches the paper body: elsarticle 5p
# \textwidth (522 pt), 10 pt Latin Modern (the T1 Computer Modern of LaTeX).
TEXTWIDTH_IN, BODY_PT = 522 / 72.27, 10
STEEL, BODY, LENS_RING, GLASS = "#b8bfc4", "#c4ccd1", "#d9d9d9", "#d3eef2"
MASSE, MASSE_EDGE = "#f7ad3a", "#c9801c"  # as in the graphical abstract
LW = 0.8


def _rc() -> dict[str, object]:
    """Body font and size; falls back to a generic serif without TeX Live."""
    lm = subprocess.run(
        ["kpsewhich", "lmroman10-regular.otf"], capture_output=True, text=True
    ).stdout.strip()
    if lm:
        fm.fontManager.addfont(lm)
    return {
        "font.family": "Latin Modern Roman" if lm else "serif",
        "font.size": BODY_PT,
        "mathtext.fontset": "cm",
        "hatch.linewidth": 0.5,
        "lines.linewidth": LW,
        "patch.linewidth": LW,
    }


def _photo(ax: plt.Axes) -> None:
    left, top, right, bottom = PHOTO_CROP
    ax.imshow(plt.imread(PHOTO)[top:bottom, left:right])
    halo = [pe.withStroke(linewidth=1.5, foreground="black")]
    for text, (tx, ty, ax_, ay) in PHOTO_LABELS.items():
        ax.annotate(
            text,
            (ax_ - left, ay - top),
            (tx - left, ty - top),
            color="white",
            ha="center",
            path_effects=halo,
            arrowprops={"arrowstyle": "->", "color": "white", "lw": 1},
        )
    ax.axis("off")


def _drawing() -> dict[str, float]:
    """Heights and decorations for the schema only (enter no number)."""
    raw = tomllib.loads(load_camera().source_path.read_text())
    fig = raw["figures"]
    return {
        "cam_h": raw["camera"]["body_height_mm"],
        "lens_d": raw["lens"]["diameter_mm"],
        "tube_d": fig["tube_diameter_mm"],
        "grooves": fig["tube_grooves"],
        "cut": fig["glass_cut_mm"],
    }


def _sight_glass(
    ax: plt.Axes, e: dict[str, float], g: dict[str, float], d: dict[str, float]
) -> None:
    """Glass seated in the hatched vessel wall, outer flange and bolts.

    Same drawing as the graphical abstract's installation. Only a band of the
    Ø150 disc fits the strip: it is drawn ±cut high (drawing only).
    """
    xg, xi, cut, top = e["glass"], e["slurry"], d["cut"], d["cam_h"] / 2
    y = np.linspace(cut, top, 20)
    curve = (
        xi + 10 * ((y - cut) / (top - cut)) ** 2
    )  # inner wall face curves away
    for s in (1, -1):
        wall = [
            (xg, s * cut),
            (xg, s * top),
            *zip(curve[::-1], s * y[::-1], strict=True),
        ]
        ax.add_patch(Polygon(wall, fc="white", ec="black", hatch="/////"))
        ax.add_patch(
            Rectangle(
                (xg - 4, min(s * cut, s * top)),
                4,
                top - cut,
                fc=STEEL,
                ec="black",
            )
        )
        yb = s * (cut + top) / 2  # bolt through the flange
        ax.add_patch(Rectangle((xg - 9, yb - 1.5), 5, 3, fc=BODY, ec="black"))
        ax.add_patch(
            RegularPolygon((xg - 11, yb), 6, radius=3, fc=BODY, ec="black")
        )
    edge = [
        *zip(curve[::-1], y[::-1], strict=True),
        (xi, cut),
        (xi, -cut),
        *zip(curve, -y, strict=True),
    ]
    xr = xi + g["slurry"] + 1.5 * np.sin(np.linspace(0, 3 * np.pi, 20))
    yr = np.linspace(-top, top, 20)
    ax.add_patch(
        Polygon([*edge, *zip(xr, yr, strict=True)], fc=MASSE, ec="none")
    )
    ax.plot(xr, yr, color=MASSE_EDGE, lw=0.6)
    ax.add_patch(Rectangle((xg, -cut), g["t"], 2 * cut, fc=GLASS, ec="black"))
    ax.plot([xg + 2] * 2, [-cut + 3, cut - 3], color="white", lw=1.5)  # glint


def _parts(
    ax: plt.Axes, g: dict[str, float], d: dict[str, float]
) -> dict[str, float]:
    """Side section of the chain, lengths to scale (mm); returns part edges."""
    e = {"body": 0.0}
    e["ext"] = g["camera"]
    e["lens"] = e["ext"] + g["e"]
    e["air"] = e["lens"] + g["body"]
    e["glass"] = e["air"] + g["air"]
    e["slurry"] = e["glass"] + g["t"]
    h, rl, rt = d["cam_h"] / 2, d["lens_d"] / 2, d["tube_d"] / 2

    # camera body: light-grey box, BNC out at the rear
    ax.add_patch(
        FancyBboxPatch(
            (0, -h),
            g["camera"],
            2 * h,
            boxstyle="round,pad=0,rounding_size=4",
            fc="#e9ecee",
            ec="black",
        )
    )
    ax.add_patch(Rectangle((-3, -6), 3, 12, fc=STEEL, ec="black"))
    # extension tube: one black piece with knurled grooves
    ax.add_patch(
        Rectangle((e["ext"], -rt), g["e"], 2 * rt, fc="#1c1c1c", ec="black")
    )
    n = int(d["grooves"])
    for k in range(n):
        xx = e["ext"] + g["e"] * (k + 1) / (n + 1)
        ax.plot([xx, xx], [-rt + 1, rt - 1], color="#5a5a5a", lw=1.2)
    # lens: black barrel, silver rear ring, front glass (plain, so the H' plane reads)
    L = g["body"]
    ax.add_patch(
        Rectangle((e["lens"], -rl), L, 2 * rl, fc="#141414", ec="black")
    )
    ax.add_patch(
        Rectangle((e["lens"], -rl), 0.12 * L, 2 * rl, fc=LENS_RING, ec="black")
    )
    ax.add_patch(
        Rectangle(
            (e["air"] - 1.2, -rl + 3),
            1.2,
            2 * rl - 6,
            fc="#7fa7c9",
            ec="black",
            lw=0.4,
        )
    )
    _sight_glass(ax, e, g, d)
    return e


def _legend(
    ax: plt.Axes, x: float, y: float, items: list[tuple[str, str]]
) -> None:
    """One row of arrow samples, each followed by its source class."""
    ax.apply_aspect()  # final limits before measuring
    for text, color in items:
        ax.annotate(
            "",
            (x, y),
            (x + 26, y),
            arrowprops={"arrowstyle": "<->", "color": color, "lw": LW},
        )
        t = ax.text(x + 29, y, text, color=color, va="center")
        bb = t.get_window_extent().transformed(ax.transData.inverted())
        x = bb.x1 + 10


def _draw(
    labels: dict[str, str],
    out: Path,
    g: dict[str, float],
    src: dict[str, str],
    legend: list[tuple[str, str]],
    photo: bool = False,
) -> None:
    d = _drawing()
    h, rl = d["cam_h"] / 2, d["lens_d"] / 2
    col = {k: SOURCE_COLOR[v] for k, v in src.items()}
    # paper variant keeps the 22:5 shape (page budget); the docs-only Slovak one is taller
    fig = plt.figure(
        figsize=(TEXTWIDTH_IN, TEXTWIDTH_IN * (5 / 22 if photo else 1 / 3))
    )
    if photo:
        _photo(fig.add_axes((0, 0.02, 0.37, 0.96)))
        ax = fig.add_axes((0.385, 0, 0.61, 1))
    else:
        ax = fig.add_axes((0.01, 0, 0.98, 1))
    edges = _parts(ax, g, d)
    x = edges["slurry"] + g["slurry"]
    sensor = g["camera"] - g["flange"]
    inside = {
        "body": (sensor / 2, "black", 0),
        "ext": (edges["ext"] + g["e"] / 2, "white", 0),
        "lens": (edges["lens"] + g["body"] / 2, "white", 0),
        "air": (edges["air"] + g["air"] / 2, "black", 0),
        "glass": (edges["glass"] + g["t"] / 2, "black", 90),
        "slurry": (edges["slurry"] + g["slurry"] / 2, "black", 0),
    }
    for key, (cx, tc, rot) in inside.items():
        ax.text(
            cx,
            0,
            labels[key],
            ha="center",
            va="center",
            color=tc,
            rotation=rot,
            zorder=8,  # the H' dots pass behind the lens label
            bbox={"fc": "#141414", "ec": "none", "pad": 0.3}
            if key == "lens"
            else None,
        )
    ax.plot([sensor] * 2, [-h, h], color=NEUTRAL, lw=1.5)
    top = h + 2
    ax.text(
        sensor, top, labels["sensor"], color=NEUTRAL, ha="center", va="bottom"
    )

    def dim(x0: float, x1: float, y: float, text: str, color: str) -> None:
        ax.annotate(
            "",
            (x0, y),
            (x1, y),
            arrowprops={"arrowstyle": "<->", "color": color, "lw": LW},
        )
        if text:
            ax.text(
                (x0 + x1) / 2,
                y - 1.5,
                text,
                ha="center",
                va="top",
                color=color,
            )

    r1, r2 = -h - 3, -h - 18
    # symbol-only labels (English) fit one row; value labels (Slovak) are staggered
    r_s = r1 if "dim_i" in labels else r2
    # no camera-length arrow: the body length enters no number
    dim(edges["ext"], edges["lens"], r1, labels["dim_e"], col["e"])
    dim(edges["lens"], edges["air"], r_s, labels["dim_body"], col["lens"])
    dim(edges["air"], edges["glass"], r1, labels["dim_a"], col["a"])
    dim(edges["glass"], edges["slurry"], r_s, labels["dim_t"], col["t"])
    used = {col[k] for k in ("e", "lens", "a", "t")}
    if "dim_i" in labels:
        # i = f + e + ξ ends at the rear principal plane H' (named in the caption):
        # a plane, white on the black lens and grey beyond it, no label
        h2 = sensor + g["i"]
        # dotted plane, full height; white across the black lens; named like the sensor
        dots: dict[str, Any] = {
            "lw": 1.5,
            "ls": (0, (1, 1.5)),
            "dash_capstyle": "round",
        }
        ax.plot([h2] * 2, [-h, h], color=NEUTRAL, zorder=6, **dots)
        ax.plot([h2] * 2, [-rl, rl], color="white", zorder=7, **dots)
        ax.text(
            h2, top, labels["H2"], color=col["i"], ha="center", va="bottom"
        )
        ax.annotate(
            "",
            (sensor, h - 6),
            (h2, h - 6),
            arrowprops={"arrowstyle": "<->", "color": col["i"], "lw": LW},
        )
        ax.text(
            (edges["ext"] + h2) / 2,
            h - 5,
            labels["dim_i"],
            color=col["i"],
            ha="center",
            va="bottom",
        )
        used.add(col["i"])
    ax.set_xlim(-6, x + 4)
    ax.set_ylim(r2 - 14, top + 11)
    ax.set_aspect("equal", adjustable="datalim")
    ax.axis("off")
    _legend(ax, 0, r2 - 6, [(w, c) for w, c in legend if c in used])
    fig.savefig(out, dpi=450)
    plt.close(fig)


def main() -> None:
    g = _geometry()
    src = _sources()
    sk = {
        "body": "telo kamery\nAdemco",
        "ext": "tubus",
        "lens": "objektív",
        "air": "vzduch",
        "glass": "priezor",
        "slurry": "cukrovina",
        "sensor": "snímač",
        "dim_e": f"(A) {g['e']:.0f} mm",
        "dim_a": f"(B) {g['air']:.0f} mm",
        "dim_t": f"(C) {g['t']:.0f} mm",
        "dim_body": f"{g['body']:.1f} mm",
    }
    en = {
        "body": "camera",  # same names as the photo panel; values in the caption
        "ext": "tube",
        "lens": "lens",
        "air": "air",
        "glass": "sight glass",
        "slurry": "slurry",
        "sensor": "image sensor",
        "dim_e": "$e$",
        "dim_body": r"$\ell_\mathrm{l}$",
        "dim_a": "$a$",
        "dim_t": "$t_g$",
        "dim_i": "$i$",
        "H2": "$H'$",
    }
    with plt.rc_context(_rc()):
        _draw(
            en,
            FIG_DIR / "18_optical_layout.png",
            g,
            src,
            SOURCE_LEGEND["en"],
            photo=True,
        )
        _draw(
            sk,
            FIG_DIR / "18_optical_layout_sk_variables.png",
            g,
            src,
            SOURCE_LEGEND["sk"],
        )
    for k, v in g.items():
        print(f"{k:>8} = {v:.3f}")


if __name__ == "__main__":
    main()
