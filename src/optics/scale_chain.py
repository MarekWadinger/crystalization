"""Pixel scale of the Camera 100 analog chain, per axis, with its uncertainty.

Chain (``configs/camera_100.toml``)::

    CCD cell ──(CCD clock)──▶ analog PAL line ──(DVR, 13.5 MHz)──▶ PAL sample
    PAL raster 720 × 576 ──(DVR monitor output; 1080p clips only)──▶ 1920 × 1080
    sensor plane ──(thin lens, M = (e + x) / f)──▶ object plane at focus

* PAL sample, x: ``cell_width · pixel_clock / sampling_rate``; y: one cell row.
* 1080p clip: the PAL raster stretched by ``display_1080p.stretch_x/_y``,
  measured here from the DVR's OSD glyphs.
* object plane at focus: ``µm/px = pitch · f / (e + x)``. The sight glass
  moves the focused plane (Δ = t(1 − 1/n)) but a parallel plate does not
  change lateral magnification, so ``n``, ``t`` and the air gap drop out.

Running the module prints the budget and the empirical checks and writes
``docs/optics/scale_chain.md``::

    uv run python -m optics.scale_chain            # budget + video checks
    uv run python -m optics.scale_chain --no-video # budget only (no md written)

The empirical checks use no camera datasheet: (a) the DVR draws the same
on-screen display (date, ``CH01``) into the PAL recording and into the 1080p
clips, so registering the PAL glyphs onto a clip measures the display stretch
in x and y; (b) the slurry texture is statistically isotropic in the object
plane, so the low-frequency power spectrum is an ellipse whose axis ratio is
µm_x / µm_y.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from optics.config import (
    CameraConfig,
    display_factors,
    load_camera,
    source_classes,
)

REPO = Path(__file__).resolve().parents[2]
DOC_PATH = REPO / "docs" / "optics" / "scale_chain.md"
CLIPS = tuple(
    REPO / "datasets" / f"2026-02-05 {s}.mp4"
    for s in ("10-18-50", "10-36-32", "10-37-26")
)
_PAL_NAME = "2026-02-04 11-08-51.mp4"
PAL_CANDIDATES = (
    REPO / "datasets" / _PAL_NAME,
    Path.home()
    / "Library/CloudStorage/GoogleDrive-marek.wadinger@stuba.sk/My Drive"
    / "sugar_plant/video"
    / _PAL_NAME,
)

RING_MM = 5.0  # CS→C adapter ring that the "≈ 6 cm" tube may already include
N_MC = 200_000

# OSD glyph boxes in the PAL raster (rows y0:y1, columns x0:x1): the static
# date string "2018-11-09" and the channel label "CH01". Placed by eye on the
# PAL recording; the matching is automatic.
OSD_BOXES = {"date": (2, 27, 220, 400), "CH01": (505, 540, 335, 410)}
CLIP_TIMES_S = (5.0, 20.0, 40.0)  # clip frames used for the OSD match
# Spectral-isotropy bands in cycles per PAL line (object-equivalent; on the
# clips the band is divided by stretch_y so both recordings see one band).
BANDS = ((0.005, 0.03), (0.01, 0.05), (0.02, 0.08))
DARK_LUMA = 12.0  # letterbox threshold, as in optics.video_io.CropBox


# ── nominal chain ────────────────────────────────────────────────────────


def object_scale(pitch_um: float, f: float, e: float, x: float) -> float:
    """Object-plane µm per pixel at focus for a sensor-plane pitch."""
    return pitch_um * f / (e + x)


RECORDINGS = ("PAL 720×576", "1080p clip")


def _frame_size(cfg: CameraConfig, rec: str) -> tuple[int, int]:
    if rec == RECORDINGS[0]:
        return cfg.native_width_px, cfg.native_height_px
    return cfg.display_width_px, cfg.display_height_px


def nominal_scales(cfg: CameraConfig) -> dict[str, tuple[float, float]]:
    """``{recording: (µm/px x, µm/px y)}`` in the object plane at focus."""
    px, py = cfg.sample_pitch_um
    f, e, x = cfg.focal_length_mm, cfg.extension_tube_mm, cfg.focus_travel_mm
    out = {}
    for rec in RECORDINGS:
        sx, sy = display_factors(cfg, *_frame_size(cfg, rec))
        out[rec] = (
            object_scale(px / sx, f, e, x),
            object_scale(py / sy, f, e, x),
        )
    return out


# ── uncertainty budget ───────────────────────────────────────────────────


@dataclass(frozen=True)
class Input:
    symbol: str
    meaning: str
    nominal: str
    spread: str
    config_key: str


def budget_inputs(cfg: CameraConfig) -> list[Input]:
    """The inputs the Monte Carlo samples, with their stated spread."""
    px, _ = cfg.sample_pitch_um
    line_route = (
        cfg.sensor_width_mm
        * 1000.0
        / (cfg.active_line_us * cfg.sampling_rate_mhz)
    )
    sx, sy = cfg.display_stretch
    return [
        Input(
            "e",
            "extension tube",
            f"{cfg.extension_tube_mm:g} mm",
            'uniform ±5 mm ("≈ 6 cm" read as rounded to the cm)',
            "lens.extension_tube_mm",
        ),
        Input(
            "ring",
            "5 mm CS→C ring counted in the tube",
            "absent",
            f"scenario e − {RING_MM:g} mm, reported separately",
            "camera.flange_distance_mm",
        ),
        Input(
            "x",
            "focus-helicoid travel",
            f"{cfg.focus_travel_mm:g} mm",
            "none: lens at its FAR stop (author decision 2026-11-05)",
            "lens.focus_travel_mm",
        ),
        Input(
            "f",
            "focal length",
            f"{cfg.focal_length_mm:g} mm",
            "normal σ = 2 % (CCTV tolerance, ASSUMED)",
            "lens.focal_length_mm",
        ),
        Input(
            "n, t, a",
            "glass index, thickness, air gap",
            f"{cfg.sight_glass_index:g}, {cfg.sight_glass_thickness_mm:g} mm, "
            f"{cfg.air_gap_mm:g} mm",
            "none at focus: a parallel plate moves the plane, not the scale",
            "sight_glass.refractive_index",
        ),
        Input(
            "line",
            "analog line → DVR sample (x only)",
            f"CCD-clock route {px:.3f} µm/sample",
            f"uniform ±2 % (the 752 cells spread over the nominal 52 µs "
            f"active line would give {line_route:.3f}, "
            f"{100 * (line_route / px - 1):+.1f} %)",
            "dvr.active_line_us",
        ),
        Input(
            "disp",
            "1080p stretch (OSD lever arm)",
            f"x {sx:g}, y {sy:g}",
            "uniform ±0.1 % (spread over the three clips)",
            "display_1080p.stretch_x",
        ),
    ]


def sample_budget(
    cfg: CameraConfig, n: int = N_MC, *, ring: bool = False, seed: int = 0
) -> dict[str, NDArray[np.float64]]:
    """Monte-Carlo samples of µm/px at focus, keyed ``"<recording> <axis>"``."""
    rng = np.random.default_rng(seed)
    u = rng.uniform
    px0, py0 = cfg.sample_pitch_um
    e = cfg.extension_tube_mm + u(-5.0, 5.0, n) - (RING_MM if ring else 0.0)
    x = np.full(n, cfg.focus_travel_mm)  # at the FAR stop: no spread
    f = rng.normal(cfg.focal_length_mm, 0.02 * cfg.focal_length_mm, n)
    # No camera-candidate term: the plant gives 752 × 582 cells, and every Sony
    # 1/3" CCIR B/W CCD of that count has the same 6.50 × 6.25 µm cell.
    px = px0 * (1.0 + u(-0.02, 0.02, n))
    py = np.full(n, py0)
    sx0, sy0 = cfg.display_stretch
    sx = sx0 * (1.0 + u(-1e-3, 1e-3, n))
    sy = sy0 * (1.0 + u(-1e-3, 1e-3, n))
    k = f / (e + x)
    return {
        "PAL 720×576 x": px * k,
        "PAL 720×576 y": py * k,
        "1080p clip x": px / sx * k,
        "1080p clip y": py / sy * k,
    }


def one_at_a_time(cfg: CameraConfig) -> dict[str, tuple[float, float, str]]:
    """``{input: (low %, high %, axes)}``: µm/px change over the input's spread.

    Same for both recordings: the display stretch is a separate measured factor.
    """
    e, x = cfg.extension_tube_mm, cfg.focus_travel_mm
    px0, py0 = cfg.sample_pitch_um

    def pct(ratio: float) -> float:
        return 100.0 * (ratio - 1.0)

    return {
        "e ±5 mm": (
            pct((e + x) / (e + 5 + x)),
            pct((e + x) / (e - 5 + x)),
            "x, y",
        ),
        "ring (e − 5 mm)": (0.0, pct((e + x) / (e - RING_MM + x)), "x, y"),
        "f ±2 %": (-2.0, 2.0, "x, y"),
        "n, t, a": (0.0, 0.0, "–"),
        "line ±2 %": (-2.0, 2.0, "x"),
        "disp ±0.1 %": (-0.1, 0.1, "x, y (1080p)"),
    }


# ── video access ─────────────────────────────────────────────────────────


def pal_video() -> Path | None:
    """The long PAL recording, from datasets/ or the synced Drive folder."""
    return next((p for p in PAL_CANDIDATES if p.exists()), None)


def _gray(frame: np.ndarray) -> NDArray[np.float64]:
    return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float64)


def read_gray(path: Path, times_s: list[float]) -> list[NDArray[np.float64]]:
    """Grey frames at the given times (seeking)."""
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    out = []
    try:
        for t in times_s:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
            ok, frame = cap.read()
            if ok:
                out.append(_gray(frame))
    finally:
        cap.release()
    return out


def read_gray_sequential(
    path: Path, n: int, stride: int
) -> list[NDArray[np.float64]]:
    """``n`` grey frames every ``stride`` frames from the start (no seeking)."""
    cap = cv2.VideoCapture(str(path))
    out: list[NDArray[np.float64]] = []
    try:
        i = 0
        while len(out) < n and cap.grab():
            if i % stride == 0:
                _, frame = cap.retrieve()
                out.append(_gray(frame))
            i += 1
    finally:
        cap.release()
    return out


def clip_duration_s(path: Path) -> float:
    cap = cv2.VideoCapture(str(path))
    try:
        n = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    finally:
        cap.release()
    return float(n / fps)


def is_camera_frame(g: NDArray[np.float64]) -> bool:
    """A 1080p clip frame shows the camera: dark pillarbox, lit picture.

    The tail of 10-37-26 is a different screen (dark, then another layout).
    """
    col = g.mean(axis=0)
    return bool(
        col[:40].max() < DARK_LUMA and col[60:1860].min() > 3 * DARK_LUMA
    )


# ── empirical checks ─────────────────────────────────────────────────────


def half_level_edges(
    g: NDArray[np.float64], inset: int
) -> tuple[float, float]:
    """Sub-pixel left and right picture edges at half the adjacent level."""
    col = g.mean(axis=0)
    lit = np.flatnonzero(col >= DARK_LUMA)
    a, b = int(lit[0]), int(lit[-1])

    def cross(i: int, step: int, level: float) -> float:
        while col[i] < level / 2:
            i += step
        j = i - step
        return j + (level / 2 - col[j]) / (col[i] - col[j]) * step

    left_level = float(np.median(col[a + inset // 4 : a + inset]))
    right_level = float(np.median(col[b - inset : b - inset // 4]))
    return cross(max(a - 2, 0), 1, left_level), cross(
        min(b + 2, col.size - 1), -1, right_level
    )


def _subpixel_peak(r: np.ndarray) -> tuple[float, float, float]:
    _, mv, _, (x, y) = cv2.minMaxLoc(r)

    def vertex(a: float, b: float, c: float) -> float:
        d = a - 2 * b + c
        return 0.0 if d == 0 else 0.5 * (a - c) / d

    dx = (
        vertex(r[y, x - 1], r[y, x], r[y, x + 1])
        if 0 < x < r.shape[1] - 1
        else 0.0
    )
    dy = (
        vertex(r[y - 1, x], r[y, x], r[y + 1, x])
        if 0 < y < r.shape[0] - 1
        else 0.0
    )
    return x + dx, y + dy, float(mv)


def _locate(
    pal: NDArray[np.float64], clip: NDArray[np.float64], sx: float, sy: float
) -> dict[str, tuple[float, float, float]]:
    """Sub-pixel clip position of each OSD box's top-left PAL pixel edge."""
    out = {}
    h = clip.shape[0]
    for name, (y0, y1, x0, x1) in OSD_BOXES.items():
        t = cv2.resize(
            pal[y0:y1, x0:x1].astype(np.float32),
            None,
            fx=sx,
            fy=sy,
            interpolation=cv2.INTER_LINEAR,
        )
        top = 0 if y0 < pal.shape[0] / 2 else (3 * h) // 4
        target = clip[top : top + h // 4].astype(np.float32)
        x, y, ncc = _subpixel_peak(
            cv2.matchTemplate(target, t, cv2.TM_CCOEFF_NORMED)
        )
        out[name] = (x, y + top, ncc)
    return out


@dataclass(frozen=True)
class OsdFit:
    sx: float
    sy: float
    offset_x: float  # clip column of PAL column 0 (x = sx · x_pal + offset)
    ncc: float


def osd_lever_fit(
    pal: NDArray[np.float64], clip: NDArray[np.float64], iterations: int = 4
) -> OsdFit:
    """Display stretch from the displacement between the two OSD boxes.

    Each box is located at sub-pixel precision with the template resampled at
    the current stretch; the box-to-box displacement over the PAL lever arm
    (115 samples, 503 lines) is the new stretch. A wrong template scale biases
    the displacement towards itself, so the update is iterated to its fixed
    point (it converges in 2–3 steps from 1920/720, 1080/576).
    """
    (ya, _, xa, _), (yb, _, xb, _) = OSD_BOXES["date"], OSD_BOXES["CH01"]
    sx, sy = 1920 / 720, 1080 / 576
    loc = _locate(pal, clip, sx, sy)
    for _ in range(iterations):
        loc = _locate(pal, clip, sx, sy)
        sx = (loc["CH01"][0] - loc["date"][0]) / (xb - xa)
        sy = (loc["CH01"][1] - loc["date"][1]) / (yb - ya)
    loc = _locate(pal, clip, sx, sy)
    return OsdFit(
        sx,
        sy,
        loc["date"][0] - sx * xa,
        min(loc["date"][2], loc["CH01"][2]),
    )


def spectral_aspect(
    frames: list[NDArray[np.float64]],
    box: tuple[int, int, int, int],
    band: tuple[float, float],
    y_stretch: float = 1.0,
) -> float:
    """µm_x / µm_y of a frame pixel from the power-spectrum ellipse.

    The slurry texture is statistically isotropic in the object plane, so the
    summed power spectrum depends on ``(kx/µm_x)² + (ky/µm_y)²``. Its second
    moments over a self-consistent elliptical band give
    ``sqrt(Σ P kx² / Σ P ky²) = µm_x / µm_y``. ``band`` is in cycles per PAL
    line; on an upscaled frame it is divided by ``y_stretch``.
    """
    y0, y1, x0, x1 = box
    win = np.outer(np.hanning(y1 - y0), np.hanning(x1 - x0))
    power = np.zeros((y1 - y0, x1 - x0))
    for g in frames:
        a = g[y0:y1, x0:x1]
        power += np.abs(np.fft.fft2((a - a.mean()) * win)) ** 2
    ky = np.fft.fftfreq(y1 - y0)[:, None]
    kx = np.fft.fftfreq(x1 - x0)[None, :]
    lo, hi = band[0] / y_stretch, band[1] / y_stretch
    r = 1.0
    for _ in range(50):
        rho = np.sqrt((kx / r) ** 2 + ky**2)
        m = (rho > lo) & (rho < hi)
        r_new = math.sqrt(
            float((power * kx**2)[m].sum()) / float((power * ky**2)[m].sum())
        )
        if abs(r_new - r) < 1e-6:
            break
        r = r_new
    return r


@dataclass
class ClipCheck:
    osd: list[OsdFit]
    left_edges: NDArray[np.float64]
    right_edges: NDArray[np.float64]
    camera_frames: int
    sampled_frames: int
    spectral: dict[tuple[float, float], float]


@dataclass
class VideoChecks:
    pal_edges: tuple[float, float]
    pal_spectral: dict[tuple[float, float], float]
    clips: dict[str, ClipCheck]


def run_video_checks(cfg: CameraConfig) -> VideoChecks | None:
    pal_path = pal_video()
    clips = [c for c in CLIPS if c.exists()]
    if pal_path is None or not clips:
        return None
    # PAL: 25 frames over the first minute, read without seeking (Drive file).
    pal_frames = read_gray_sequential(pal_path, n=25, stride=72)
    edges = np.array([half_level_edges(g, 30) for g in pal_frames])
    pal_edges = (float(np.median(edges[:, 0])), float(np.median(edges[:, 1])))
    pal_box = (40, 490, int(pal_edges[0]) + 15, int(pal_edges[1]) - 15)
    pal_spectral = {b: spectral_aspect(pal_frames, pal_box, b) for b in BANDS}
    sy = cfg.display_stretch[1]
    out: dict[str, ClipCheck] = {}
    for c in clips:
        name = c.stem.removeprefix("2026-02-05 ")
        osd = [
            osd_lever_fit(p, g)
            for g in read_gray(c, list(CLIP_TIMES_S))
            for p in pal_frames[:3]
        ]
        dur = clip_duration_s(c)
        sampled = read_gray(c, list(np.linspace(5.0, dur - 5.0, 25)))
        frames = [g for g in sampled if is_camera_frame(g)]
        e = np.array([half_level_edges(g, 60) for g in frames])
        box = (80, 920, int(e[:, 0].min()) + 40, int(e[:, 1].min()) - 40)
        out[name] = ClipCheck(
            osd,
            e[:, 0],
            e[:, 1],
            len(frames),
            len(sampled),
            {b: spectral_aspect(frames, box, b, y_stretch=sy) for b in BANDS},
        )
    return VideoChecks(pal_edges, pal_spectral, out)


# ── report ───────────────────────────────────────────────────────────────


def _interval(s: NDArray[np.float64]) -> tuple[float, float, float]:
    lo, med, hi = np.percentile(s, [2.5, 50.0, 97.5])
    return float(med), float(lo), float(hi)


def _budget_section(cfg: CameraConfig, w) -> None:  # noqa: ANN001
    classes = source_classes(cfg.source_path)
    px, py = cfg.sample_pitch_um
    sx, sy = cfg.display_stretch
    nominal = nominal_scales(cfg)
    base = sample_budget(cfg)
    ring = sample_budget(cfg, ring=True)
    k = cfg.focal_length_mm / (cfg.extension_tube_mm + cfg.focus_travel_mm)
    w("## Chain\n")
    w("| Step | x | y | Inputs (class) |\n|---|---:|---:|---|")
    w(
        f"| CCD cell | {cfg.cell_width_um:g} µm | {cfg.cell_height_um:g} µm | "
        f"`camera.cell_*_um` ({classes['camera.cell_width_um']}) |"
    )
    w(
        f"| PAL sample / line, sensor plane | {px:.3f} µm | {py:.3f} µm | "
        f"x × CCD clock {cfg.pixel_clock_mhz:g} MHz "
        f"({classes['camera.pixel_clock_mhz']}) / DVR {cfg.sampling_rate_mhz:g} MHz "
        f"({classes['dvr.sampling_rate_mhz']}) |"
    )
    w(
        f"| 1080p display stretch | ×{sx:g} | ×{sy:g} | "
        f"`display_1080p.stretch_*` ({classes['display_1080p.stretch_x']}, "
        "OSD lever arm below) |"
    )
    w(f"| 1080p pixel, sensor plane | {px / sx:.3f} µm | {py / sy:.3f} µm | |")
    w(
        f"| object plane at focus: × f/(e+x) = {k:.4f} | | | "
        f"f ({classes['lens.focal_length_mm']}), e ({classes['lens.extension_tube_mm']}), "
        f"x ({classes['lens.focus_travel_mm']}) |"
    )
    w(
        "\nPixel aspect µm_x/µm_y: "
        f"PAL {px / py:.4f}, 1080p {(px / sx) / (py / sy):.4f} "
        f"(a 1080p pixel covers {(py / sy) / (px / sx):.3f}× more slurry "
        "vertically than horizontally).\n"
    )
    w("## µm per pixel in the slurry, at the focused plane\n")
    w(
        "Monte Carlo, 200 000 draws; median and 95 % interval. Class of every "
        'row: ESTIMATE (inherits the plant\'s "≈ 6 cm" tube and the '
        "unconfirmed camera).\n"
    )
    w(
        "| Recording | axis | nominal | median | 95 % interval | ± % | "
        "with 5 mm ring: median [95 %] |\n|---|---|---:|---:|---:|---:|---:|"
    )
    for key in base:
        rec, axis = key.rsplit(" ", 1)
        nom = nominal[rec][0 if axis == "x" else 1]
        med, lo, hi = _interval(base[key])
        rmed, rlo, rhi = _interval(ring[key])
        w(
            f"| {rec} | {axis} | {nom:.3f} | {med:.3f} | {lo:.3f}–{hi:.3f} | "
            f"{100 * (hi - lo) / 2 / med:.1f} | {rmed:.3f} [{rlo:.3f}–{rhi:.3f}] |"
        )
    gm = ", ".join(
        f"{r} {math.sqrt(vx * vy):.3f} µm" for r, (vx, vy) in nominal.items()
    )
    w(
        f"\nGeometric mean (side of the equal-area square; for areas only): "
        f"{gm}. The superseded isotropic model (Hanwha 2.9 µm, µm/px = sensor "
        "width / frame width) gave 4.44 µm on PAL and 1.66 µm on the clips.\n"
    )
    w("## Inputs\n")
    w(
        "| Symbol | Meaning | Nominal | Spread | Config key (class) |\n"
        "|---|---|---|---|---|"
    )
    for i in budget_inputs(cfg):
        w(
            f"| {i.symbol} | {i.meaning} | {i.nominal} | {i.spread} | "
            f"`{i.config_key}` ({classes.get(i.config_key, '–')}) |"
        )
    w("\n### One input at a time (% change of µm/px)\n")
    w("| Input | axes | low | high |\n|---|---|---:|---:|")
    for name, (lo, hi, axes) in one_at_a_time(cfg).items():
        w(f"| {name} | {axes} | {lo:+.1f} | {hi:+.1f} |")
    w(
        "\nThe tube length dominates (±5 mm on e + x = 61 mm). Whether a 5 mm "
        "CS→C ring is counted in the 60 mm is a discrete +9 % and is kept out "
        "of the interval.\n"
    )


def _checks_section(cfg: CameraConfig, checks: VideoChecks, w) -> None:  # noqa: ANN001
    px, py = cfg.sample_pitch_um
    sx, sy = cfg.display_stretch
    w("## Empirical checks (no datasheet input)\n")
    w(
        "**(a) OSD lever arm → display stretch.** The DVR draws the same date "
        "and `CH01` glyphs into both recordings. Each PAL glyph box is "
        "resampled and located in the clip at sub-pixel precision; the "
        "box-to-box displacement over the PAL lever arm "
        f"({OSD_BOXES['CH01'][2] - OSD_BOXES['date'][2]} samples, "
        f"{OSD_BOXES['CH01'][0] - OSD_BOXES['date'][0]} lines) is the stretch, "
        "iterated to a fixed point. 3 PAL frames × 3 clip frames "
        f"(t = {', '.join(f'{t:g}' for t in CLIP_TIMES_S)} s) per clip.\n"
    )
    w(
        "| Clip | stretch x | stretch y | x offset (px) | min NCC |\n"
        "|---|---:|---:|---:|---:|"
    )
    all_sx, all_sy = [], []
    for name, c in checks.clips.items():
        a = np.array([[o.sx, o.sy, o.offset_x, o.ncc] for o in c.osd])
        all_sx += list(a[:, 0])
        all_sy += list(a[:, 1])
        w(
            f"| {name} | {a[:, 0].mean():.4f} ± {a[:, 0].std():.4f} | "
            f"{a[:, 1].mean():.4f} ± {a[:, 1].std():.4f} | "
            f"{a[:, 2].mean():+.1f} | {a[:, 3].min():.2f} |"
        )
    w(
        f"\nAll clips: x {np.mean(all_sx):.4f} (range {min(all_sx):.4f}–"
        f"{max(all_sx):.4f}), y {np.mean(all_sy):.4f} (range "
        f"{min(all_sy):.4f}–{max(all_sy):.4f}); config "
        f"`display_1080p.stretch_x/_y` = {sx:g}, {sy:g}. A plain "
        f"720 → 1920 scaler would be {1920 / 720:.4f}; the y stretch is "
        f"1080/576 = {1080 / 576:.4f}. The x offset is where PAL column 0 "
        "lands; it differs between clips (the whole picture shifts by a few "
        "samples), which moves features but not their scale.\n"
    )
    pl, pr = checks.pal_edges
    w(
        "**Picture edges** (half-level, sub-pixel; camera frames only). PAL "
        f"recording: left {pl:.1f}, right {pr:.1f} (first minute, 25 frames). "
        "The left edge is a hard step (a DVR mask), the right edge a "
        "4-sample analog ramp.\n"
    )
    w(
        "| Clip | camera frames | left edge | right edge (min–max) | "
        "left / stretch_x |\n|---|---:|---:|---:|---:|"
    )
    for name, c in checks.clips.items():
        w(
            f"| {name} | {c.camera_frames}/{c.sampled_frames} | "
            f"{np.median(c.left_edges):.1f} | {c.right_edges.min():.1f}–"
            f"{c.right_edges.max():.1f} | {np.median(c.left_edges) / sx:.2f} |"
        )
    w(
        "\nThe clips' left edge is PAL column "
        f"{pl:.0f} × stretch_x, so the pillarbox starts at the DVR mask. The "
        "right edge jumps by ~8 px (~3 samples), between clips and within "
        "10-36-32 (near t = 45 s), because the "
        "analog picture shifts against the DVR's sampling; the width between "
        "the two edges therefore is not a scale measurement, and the "
        "auto-crop of `optics.video_io` (threshold 12, all frames) is not "
        "either: on 10-37-26 it includes the non-camera tail of the clip.\n"
    )
    pred_pal = px / py
    pred_clip = (px / sx) / (py / sy)
    w(
        "**(b) Spectral isotropy → pixel aspect.** µm_x/µm_y from the "
        "power-spectrum ellipse of the slurry texture (25 frames per "
        "recording; bands in cycles per PAL line, so one object band on both "
        "recordings). Chain prediction: PAL "
        f"{pred_pal:.3f}, 1080p {pred_clip:.3f}. The last column converts "
        "the clips' mean into a PAL value through the measured stretch "
        "(× stretch_x / stretch_y), without the datasheet.\n"
    )
    names = list(checks.clips)
    w(
        "| Band (cyc/line) | PAL direct | "
        + " | ".join(f"1080p {n}" for n in names)
        + " | PAL via 1080p |"
    )
    w("|---|---:|" + "---:|" * (len(names) + 1))
    for b in BANDS:
        vals = [checks.clips[n].spectral[b] for n in names]
        w(
            f"| {b[0]:g}–{b[1]:g} | {checks.pal_spectral[b]:.3f} | "
            + " | ".join(f"{v:.3f}" for v in vals)
            + f" | {float(np.mean(vals)) * sx / sy:.3f} |"
        )
    w(
        "\nThe spectral ratio rises with the band on every recording "
        "(illumination gradients at the lowest frequencies, anisotropic "
        "analog bandwidth, interlace and flow blur at the higher ones). It "
        "brackets the chain prediction but cannot pin the pitch better than "
        "about ±10 %: a consistency check, not a measurement. On synthetic "
        "power-law textures with a known squeeze (tests/test_scale_chain.py) "
        "the estimator is within 5 % in the middle band, and biased by up "
        "to +10 % in the lowest band when the spectrum is shallow.\n"
    )


def report(cfg: CameraConfig, checks: VideoChecks | None) -> str:
    lines: list[str] = []
    w = lines.append
    w("# Pixel scale of the Camera 100 analog chain\n")
    w(
        "Generated by `uv run python -m optics.scale_chain` from "
        "`configs/camera_100.toml`; do not edit by hand. Derivation in the "
        "module docstring of `src/optics/scale_chain.py`.\n"
    )
    _budget_section(cfg, w)
    if checks is None:
        w("## Empirical checks\n\nVideos not available; checks not run.\n")
    else:
        _checks_section(cfg, checks, w)
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="Camera 100 pixel-scale budget")
    ap.add_argument(
        "--no-video", action="store_true", help="skip video checks"
    )
    args = ap.parse_args()
    cfg = load_camera()
    checks = None if args.no_video else run_video_checks(cfg)
    text = report(cfg, checks)
    print(text)
    if checks is not None:
        DOC_PATH.write_text(text)
        print(f"wrote {DOC_PATH.relative_to(REPO)}")


if __name__ == "__main__":
    main()
