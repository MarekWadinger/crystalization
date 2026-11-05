"""Graphical abstract of the CEP paper (draft, preliminary).

Main row, from repo data only: the installation drawn to scale from
``configs/camera_100.toml``, three lossless strike-1 frames near the microscope
samples with the co-authors' crystal annotations (Cellpose GUI masks), and the
microscope size ranges against batch clock time.
Around it, pale: the seed pan and the size-feedback loop the sensor is for
(context, not a contribution). The camera's size curve joins panel 3 after
Phase 1 (Cellpose); no curve is drawn until then.

    uv run --frozen --group optics python scripts/graphical_abstract.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import patheffects
from matplotlib.colors import to_rgb
from matplotlib.ticker import FuncFormatter, MultipleLocator
from matplotlib.patches import (
    Circle,
    Ellipse,
    FancyBboxPatch,
    Polygon,
    Rectangle,
    RegularPolygon,
)

from optics.optical_layout import _geometry

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "datasets" / "2026-10-30 08-45-33.json"
FRAMES = ROOT / "src" / "crystal_detector" / "annotations"
OUT = ROOT / "papers" / "cep" / "figures" / "graphical_abstract"
CAMERA_SIZES = (
    ROOT / "results" / "camera_size_vs_time.csv"
)  # Phase 1: minute,p25_um,p50_um,p75_um

INK, TEAL, MICRO = "#1d4752", "#2a7f8a", "#f08a12"
PALE, PALE_FILL, GREY = "#bfc6cb", "#f2f4f5", "#8b969e"
STEEL, BODY, GLASS, MASSE = "#dfe3e6", "#c4ccd1", "#d3eef2", "#f7ad3a"
LW = 2.0
BAND_ALPHA = 0.18
# camera band colour, opaque: TEAL at BAND_ALPHA over white
BAND = tuple(1 - BAND_ALPHA * (1 - c) for c in to_rgb(TEAL))
# The canvas is drawn at 14 in and printed at the elsarticle 5p text width (522 pt);
# text is set in the body font at the body size (10 pt) after that scaling.
CANVAS_IN, TEXTWIDTH_IN, BODY_PT = 14.0, 522 / 72.27, 10
plt.rcParams.update(
    {
        "text.usetex": True,
        "text.latex.preamble": r"\usepackage[T1]{fontenc}",
        "font.family": "serif",
        "font.size": BODY_PT * CANVAS_IN / TEXTWIDTH_IN,
    }
)
# Microscope ranges (µm) per lab sample, from datasets/README.md (values burned
# into the microscope photos, transcribed 2026-11-02).
# ponytail: copied here; move into the sidecar JSON when more of the 54 photos are read.
# Strike 1 only; b2-s09 (306-743 µm, POSUS-18-04.jpg) is strike 2, whose clock restarts.
MICRO_UM = {"b1-s03": (22, 35), "b1-s10": (228, 821)}
SEED_UM = (
    10,
    19,
)  # MICRO.jpg, seed-slurry reference, drawn at seeding (no sample time)
# Annotated strike-1 frames near b1-s03 (11:32), mid-boiling, and b1-s10 (13:32).
# File names are video time HHMMSS; masks are the annotators' saved Cellpose GUI output.
ANNOTATED = (
    "erika/boiling/025346",
    "marian/boiling/035426",
    "marian/drying/044548",
)


def _minutes_since_seeding() -> dict[str, float]:
    run = json.loads(RUN.read_text())
    seeds = [e["t"] for e in run["events"] if e["is_seeding"]]
    return {
        s["id"]: (s["t"] - max(t for t in seeds if t <= s["t"])) / 60
        for s in run["samples"]
        if s["t"] >= min(seeds)
    }


def _clock_h(t_s: float) -> float:
    """Wall-clock hour of video time t_s (recorder start + t_s)."""
    run = json.loads(RUN.read_text())
    hh, mm, ss = run["media"]["start_wallclock"][11:19].split(":")
    return int(hh) + int(mm) / 60 + (int(ss) + t_s) / 3600


def _seed_clock_h() -> float:
    """Wall-clock hour of the strike-1 seeding."""
    run = json.loads(RUN.read_text())
    return _clock_h(next(e["t"] for e in run["events"] if e["is_seeding"]))


def _hhmm(h: float, _pos: object = None) -> str:
    m = round(h * 60)
    return f"{m // 60:02d}:{m % 60:02d}"


def _camera_curve(
    t: dict[str, float],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, bool]:
    """Camera size quartiles per minute (µm), from the Phase 1 results file.

    Without it, a PLACEHOLDER: log size fitted linear in sqrt(time) to the
    strike-1 lab midpoints, ±0.15 decades. Not data; the output is renamed.
    """
    if CAMERA_SIZES.exists():
        d = np.genfromtxt(CAMERA_SIZES, delimiter=",", names=True)
        return d["minute"], d["p25_um"], d["p50_um"], d["p75_um"], False
    tp = [0.0, t["b1-s03"], t["b1-s10"]]
    mid = [
        np.sqrt(a * b)
        for a, b in (SEED_UM, MICRO_UM["b1-s03"], MICRO_UM["b1-s10"])
    ]
    m = np.arange(
        0, _strike1_minutes(), 8.0
    )  # the camera covers the whole strike
    fit = np.polyfit(np.sqrt(tp), np.log10(mid), 1)
    # ponytail: placeholder jitter for the look only (fixed seed); real data brings its own
    rng = np.random.default_rng(0)
    log50 = np.polyval(fit, np.sqrt(m)) + rng.normal(0, 0.03, m.size)
    half = 0.15 + np.abs(rng.normal(0, 0.03, m.size))
    return m, 10 ** (log50 - half), 10**log50, 10 ** (log50 + half), True


def _strike1_minutes() -> float:
    """Video span of strike 1, seeding to end of drying (sidecar segments)."""
    run = json.loads(RUN.read_text())
    seed = next(e["t"] for e in run["events"] if e["is_seeding"])
    end = max(
        g["t_end"] for g in run["segments"] if g["t_end"] < 21867
    )  # before batch 2 (b2-e01)
    return (end - seed) / 60


def _lab_path(bg: plt.Axes) -> None:
    """Status quo: a sample leaves the pan, waits, and is sized under the microscope."""
    lab = "#f5c48c"
    kw: dict[str, Any] = {"color": lab, "lw": 2}
    bg.plot([0.048, 0.048, 0.712], [0.17, 0.05, 0.05], **kw)
    xh, yh, w, h = 0.40, 0.05, 0.007, 0.026  # hourglass = delay
    for sgn in (1, -1):
        bg.add_patch(
            Polygon(
                [(xh - w, yh + sgn * h), (xh + w, yh + sgn * h), (xh, yh)],
                fc="white",
                ec=lab,
                lw=2,
            )
        )
    bg.text(
        xh + 0.015,
        yh + 0.012,
        "lab sample: hours, sparse",
        color=MICRO,
        alpha=0.8,
    )
    bg.plot([0.757, 0.765, 0.765, 0.775], [0.10, 0.10, 0.355, 0.355], **kw)
    bg.annotate(
        "",
        (0.79, 0.355),
        (0.775, 0.355),
        arrowprops={"arrowstyle": "-|>", "color": lab, "lw": 2},
    )


def _microscope(ax: plt.Axes) -> None:
    """Lab microscope icon in the camera's drawing style (arbitrary units)."""
    _box(ax, 0, 0, 50, 8, STEEL, 2)  # base
    _box(ax, 34, 8, 9, 52, BODY, 2)  # arm
    _box(ax, 12, 52, 31, 9, BODY, 2)
    _box(ax, 4, 30, 34, 5, STEEL)  # stage
    _box(ax, 15, 37, 6, 15, INK)  # objective
    ax.add_patch(
        Polygon([(12, 61), (22, 61), (16, 84), (7, 82)], fc=INK, ec=INK, lw=LW)
    )  # tube
    ax.add_patch(
        Polygon(
            [(7, 82), (16, 84), (15, 90), (6, 88)], fc=MICRO, ec=INK, lw=LW
        )
    )  # eyepiece
    ax.add_patch(Circle((38.5, 22), 4.5, fc=BODY, ec=INK, lw=LW))  # focus knob
    ax.set_xlim(-2, 52)
    ax.set_ylim(-2, 92)
    ax.set_aspect("equal")
    ax.axis("off")


def _box(
    ax: plt.Axes, x: float, y: float, w: float, h: float, fc: str, r: float = 0
) -> None:
    style = f"round,pad=0,rounding_size={r}" if r else "square,pad=0"
    ax.add_patch(
        FancyBboxPatch((x, y), w, h, boxstyle=style, fc=fc, ec=INK, lw=LW)
    )


def _installation(ax: plt.Axes) -> None:
    """Side section; horizontal lengths to scale (mm), heights are drawing choices."""
    g = _geometry()
    x_tube = g["camera"]
    x_lens = x_tube + g["e"]
    x_air = x_lens + g["body"]
    x_glass = x_air + g["air"]
    x_in = x_glass + g["t"]
    r_glass, top, depth = 75.0, 150.0, 60.0  # DN150 glass (config diameter_mm)

    # vessel wall: hatched section whose inner face curves away from the glass
    y = np.linspace(r_glass, top, 30)
    curve = x_in + 0.006 * (y - r_glass) ** 2
    for s in (1, -1):
        wall = [
            (x_glass, s * r_glass),
            (x_glass, s * top),
            *zip(curve[::-1], s * y[::-1], strict=True),
        ]
        ax.add_patch(Polygon(wall, fc="white", ec=INK, lw=LW, hatch="///"))
    edge = [
        *zip(curve[::-1], y[::-1], strict=True),
        *zip(curve, -y, strict=True),
    ]
    xr = (
        x_in + depth + 3 * np.sin(np.linspace(0, 3 * np.pi, 30))
    )  # cut edge of the massecuite
    ax.add_patch(
        Polygon(
            [*edge, *zip(xr, np.linspace(-top, top, 30), strict=True)][::1],
            fc=MASSE,
            ec="none",
        )
    )
    ax.plot(xr, np.linspace(-top, top, 30), color="#c9801c", lw=1)
    ax.add_patch(
        Rectangle(
            (x_glass, -r_glass), g["t"], 2 * r_glass, fc=GLASS, ec=INK, lw=LW
        )
    )
    ax.plot(
        [x_glass + 4] * 2, [-r_glass + 8, r_glass - 8], color="white", lw=3
    )  # glint

    for s in (1, -1):  # outer flange and bolts
        _box(ax, x_glass - 7, s * r_glass - 22 * (s < 0), 7, 22, STEEL)
        _box(ax, x_glass - 13, s * (r_glass + 24) - 5, 6, 10, BODY, 1.5)
        ax.add_patch(
            RegularPolygon(
                (x_glass - 18, s * (r_glass + 24)),
                6,
                radius=7,
                fc=BODY,
                ec=INK,
                lw=LW,
            )
        )

    # no focal-plane marker or light cone: where the focal plane sits is not known
    # (assumption dropped 2026-11-05, paper §sec:slab removed)

    _box(ax, x_tube, -13, g["e"], 26, INK)
    _box(ax, x_air - 5, -17, 5, 34, INK)  # front collar
    _box(ax, x_lens, -15, g["body"] - 5, 30, TEAL)
    for k in range(1, 7):
        xx = x_lens + k * (g["body"] - 5) / 7
        ax.plot([xx, xx], [-15, 15], color=INK, lw=1.5)
    _box(ax, -6, -6, 6, 12, BODY, 1.5)  # connector
    _box(ax, 0, -24, g["camera"], 48, STEEL, 4)
    for sx in (5, g["camera"] - 5):
        for sy in (-18, 18):
            ax.add_patch(Circle((sx, sy), 1.6, fc=INK))
    ax.set_xlim(-8, x_in + depth + 6)
    ax.set_ylim(-top, top)
    ax.set_aspect("equal")
    ax.axis("off")


def _frames(
    fig: plt.Figure, x0: float, y: float, w: float, h: float, gap: float
) -> None:
    """Tall crops of the annotated frames, outlines of every saved mask."""
    aspect = w * fig.get_figwidth() / (h * fig.get_figheight())
    for k, name in enumerate(ANNOTATED):
        ax = fig.add_axes((x0 + k * (w + gap), y, w, h))
        img = plt.imread(FRAMES / f"{name}.png")
        seg = np.load(FRAMES / f"{name}_seg.npy", allow_pickle=True).item()
        cw = round(img.shape[0] * aspect)
        # full height; the column strip with the most annotated pixels
        c0 = int(
            np.argmax(
                np.convolve((seg["masks"] > 0).sum(0), np.ones(cw), "valid")
            )
        )
        crop = np.s_[:, c0 : c0 + cw]
        ax.imshow(img[crop], cmap="gray")  # pixels unaltered
        m = seg["masks"][crop]
        for lab in np.unique(m[m > 0]):
            cs = ax.contour(
                m == lab, levels=[0.5], colors=[BAND], linewidths=1.4
            )
            # camera colours: band-coloured core shows on dark, trace-coloured rim on light
            cs.set_path_effects(
                [
                    patheffects.Stroke(linewidth=3.4, foreground=TEAL),
                    patheffects.Normal(),
                ]
            )
        ax.set_xticks([])
        ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_color(INK)
            sp.set_linewidth(2.5)
        ax.text(
            0.5,
            -0.03,
            _hhmm(
                _clock_h(
                    int(name[-6:-4]) * 3600
                    + int(name[-4:-2]) * 60
                    + int(name[-2:])
                )
            ),
            transform=ax.transAxes,
            ha="center",
            va="top",
            color=INK,
        )
        if k < 2:  # chevron to the next frame
            cx, cy = x0 + (k + 1) * (w + gap) - gap / 2, y + h / 2
            fig.lines.append(
                plt.Line2D(
                    [cx - 0.004, cx + 0.004, cx - 0.004],
                    [cy + 0.03, cy, cy - 0.03],
                    color=GREY,
                    lw=4,
                    transform=fig.transFigure,
                    solid_capstyle="round",
                    solid_joinstyle="round",
                )
            )


def _chart(ax: plt.Axes, t: dict[str, float]) -> None:
    """Strike 1 in wall-clock time: camera curve (teal) under lab ranges (orange)."""
    h0 = _seed_clock_h()
    m, p25, p50, p75, placeholder = _camera_curve(t)
    x = h0 + m / 60
    band = ax.fill_between(x, p25, p75, color=TEAL, alpha=BAND_ALPHA, lw=0)
    (line,) = ax.plot(
        x, p50, color=TEAL, lw=3, marker="o", ms=7, mfc=TEAL, mec=INK, mew=1
    )
    bars = [(0.0, SEED_UM), *((t[s], r) for s, r in MICRO_UM.items())]
    for tm, (lo, hi) in bars:
        mid = np.sqrt(lo * hi)
        lab = ax.errorbar(
            h0 + tm / 60,
            mid,
            yerr=[[mid - lo], [hi - mid]],
            fmt="none",
            ecolor=MICRO,
            elinewidth=4,
            capsize=8,
            capthick=4,
            zorder=5,
        )
    ax.legend(
        [(band, line), lab],
        [
            "camera soft sensor"
            + ("\n" + r"\textit{(placeholder)}" if placeholder else ""),
            "lab microscope\n(verifies)",
        ],
        loc="upper center",
        bbox_to_anchor=(0.45, -0.09),
        borderpad=0,
        labelspacing=0.3,
        handletextpad=0.6,
        frameon=False,
        labelcolor=[TEAL, MICRO],
        handlelength=2.2,
    )
    ax.set_yscale("log")
    ax.set_ylim(5, 2000)
    ax.set_xlim(h0 - 0.3, h0 + m[-1] / 60 + 0.1)
    ax.xaxis.set_major_locator(MultipleLocator(1))
    ax.xaxis.set_minor_locator(MultipleLocator(0.25))
    ax.xaxis.set_major_formatter(FuncFormatter(_hhmm))
    ax.text(
        0.04, 0.96, "30 Oct 2026", transform=ax.transAxes, va="top", color=INK
    )
    ax.set_ylabel(r"crystal size (\textmu m)", color=INK)
    ax.tick_params(colors=INK, which="both", direction="in", width=1.5)
    ax.tick_params(which="major", length=7)
    for sp in ax.spines.values():
        sp.set_color(INK)
        sp.set_linewidth(2.5)


def _context(bg: plt.Axes) -> None:
    """Pale seed pan and the size-feedback loop it would close, in figure coordinates.

    Block-diagram convention: setpoint and measured size meet at a summing
    junction, the controller C drives the steam valve on the pan.
    """
    kw: dict[str, Any] = {"color": PALE, "lw": 2}
    dash: dict[str, Any] = {**kw, "ls": "--"}
    head: dict[str, Any] = {
        "arrowstyle": "-|>",
        "color": PALE,
        "lw": 2,
        "mutation_scale": 14,
    }
    bg.add_patch(
        Rectangle((0.012, 0.30), 0.072, 0.40, fc=PALE_FILL, ec=PALE, lw=2)
    )
    bg.add_patch(
        Polygon(
            [(0.012, 0.30), (0.084, 0.30), (0.048, 0.17)],
            fc=PALE_FILL,
            ec=PALE,
            lw=2,
        )
    )
    bg.add_patch(
        Rectangle((0.081, 0.455), 0.006, 0.045, fc=TEAL, ec="none")
    )  # sight glass
    bg.plot([0.087, 0.12], [0.50, 0.86], ls=":", **kw)  # zoom into panel 1
    bg.plot([0.087, 0.12], [0.455, 0.14], ls=":", **kw)

    xv, yv = (
        0.048,
        0.80,
    )  # steam pipe into the pan, control valve with actuator
    bg.plot([xv, xv], [0.99, 0.72], color=PALE, lw=4, solid_capstyle="butt")
    bg.annotate("", (xv, 0.70), (xv, 0.73), arrowprops={**head, "lw": 4})
    bg.add_patch(
        Polygon(
            [
                (xv - 0.009, yv + 0.025),
                (xv + 0.009, yv + 0.025),
                (xv - 0.009, yv - 0.025),
                (xv + 0.009, yv - 0.025),
            ],
            fc="white",
            ec=PALE,
            lw=2,
        )
    )
    bg.plot([xv, xv + 0.016], [yv, yv], **kw)
    bg.add_patch(
        Rectangle(
            (xv + 0.016, yv - 0.022), 0.009, 0.044, fc="white", ec=PALE, lw=2
        )
    )

    xc, xs, y = (
        0.20,
        0.42,
        0.90,
    )  # controller block, summing junction (clear of the installation panel)
    bg.add_patch(
        FancyBboxPatch(
            (xc, y - 0.045),
            0.05,
            0.09,
            boxstyle="round,pad=0,rounding_size=0.01",
            fc="white",
            ec=PALE,
            lw=2,
        )
    )
    bg.text(
        xc + 0.025,
        y,
        "$C$",
        ha="center",
        va="center",
        color=GREY,
    )
    bg.plot([xc, xv + 0.0205, xv + 0.0205], [y, y, yv + 0.04], **dash)
    bg.annotate(
        "",
        (xv + 0.0205, yv + 0.022),
        (xv + 0.0205, yv + 0.042),
        arrowprops=head,
    )
    rx = 0.012
    ry = rx * bg.bbox.width / bg.bbox.height  # bg spans the whole figure
    bg.add_patch(Ellipse((xs, y), 2 * rx, 2 * ry, fc="white", ec=PALE, lw=2))
    bg.annotate("", (xc + 0.05, y), (xs - rx, y), arrowprops=head)
    bg.annotate("", (xs, y + ry), (xs, 0.995), arrowprops=head)  # setpoint
    bg.text(
        xs - 0.006,
        y + ry + 0.01,
        "+",
        ha="right",
        va="bottom",
        color=GREY,
    )
    bg.plot(
        [0.875, 0.875, xs + rx + 0.012], [0.84, y, y], **dash
    )  # measured size
    bg.annotate("", (xs + rx, y), (xs + rx + 0.013, y), arrowprops=head)
    bg.text(
        xs + rx + 0.004,
        y - 0.012,
        "$-$",
        ha="left",
        va="top",
        color=GREY,
    )
    txt: dict[str, Any] = {"color": GREY}
    bg.text(
        0.048, 0.50, "seed pan", rotation=90, ha="center", va="center", **txt
    )
    bg.text(xv + 0.012, 0.995, "steam", va="top", **txt)
    bg.text(xs + 0.01, 0.995, "setpoint", va="top", **txt)
    bg.text(0.56, y + 0.015, r"\textit{crystal-size control (future)}", **txt)
    bg.text(0.18, 0.36, "camera", color=INK, ha="center", va="top")
    _lab_path(bg)
    bg.set_xlim(0, 1)
    bg.set_ylim(0, 1)
    bg.axis("off")


def main() -> None:
    t = _minutes_since_seeding()
    fig = plt.figure(figsize=(CANVAS_IN, 5.6))
    _context(fig.add_axes((0, 0, 1, 1), zorder=-1))
    _installation(fig.add_axes((0.11, 0.12, 0.25, 0.74)))
    _frames(fig, 0.38, 0.25, 0.095, 0.55, 0.02)
    _chart(fig.add_axes((0.79, 0.34, 0.19, 0.50)), t)
    _microscope(fig.add_axes((0.712, 0.0, 0.045, 0.16)))
    out = (
        OUT
        if CAMERA_SIZES.exists()
        else OUT.with_name(OUT.name + "_PLACEHOLDER")
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        out.with_suffix(".pdf"), dpi=200
    )  # PDF only: usetex PNG needs dvipng
    assert out.with_suffix(".pdf").stat().st_size > 0
    print(
        out.with_suffix(".pdf").relative_to(ROOT),
        {s: round(t[s], 1) for s in MICRO_UM},
    )


if __name__ == "__main__":
    main()
