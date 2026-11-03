"""Versioned camera configuration loader.

Hardware constants live in ``configs/<camera>.toml`` (CCD cells, DVR sampling,
lens focal length, F-number, extension tube, sight-glass geometry, nominal
focus distance). They are *not* secrets and do not belong in ``.env``:
every figure and KPI snapshot is invalidated if a constant changes, so
they must be versioned with the code.

The pixel scale is per axis and per recording type, not one number. The
camera is an analog PAL CCD: the DVR samples each analog line at 13.5 MHz,
so one PAL sample spans ``cell_width × pixel_clock / sampling_rate`` on the
sensor and one line spans one cell row (:meth:`CameraConfig.sample_pitch_um`).
The 1080p clips are the DVR's monitor output, i.e. that PAL picture stretched
again by different factors in x and y (:func:`display_factors`). Derivation,
uncertainty budget and empirical checks: ``python -m optics.scale_chain``
and ``docs/optics/scale_chain.md``.

Typical use::

    from optics.config import load_camera, lens_from_config_and_video

    cfg = load_camera()  # configs/camera_100.toml
    lens = lens_from_config_and_video(cfg, video_path)
    lens.pixel_pitch_x_um, lens.pixel_pitch_y_um  # sensor-plane µm per frame px
    lens.pixel_pitch_um  # geometric mean, for areas only
"""

from __future__ import annotations

import math
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from optics.model import LensSetup, SightGlass, mm_per_pixel_at

_REPO_CONFIG = (
    Path(__file__).resolve().parents[2] / "configs" / "camera_100.toml"
)
# Repo checkout first; otherwise the copy hatch force-includes into the wheel.
DEFAULT_CONFIG_PATH = (
    _REPO_CONFIG
    if _REPO_CONFIG.exists()
    else Path(__file__).with_name("camera_100.toml")
)


@dataclass(frozen=True, slots=True)
class CameraConfig:
    """Hardware constants for one camera+lens+sight-glass installation."""

    name: str
    cell_width_um: float
    cell_height_um: float
    cells_h: int
    cells_v: int
    pixel_clock_mhz: float
    sampling_rate_mhz: float
    active_line_us: float
    native_width_px: int
    """DVR samples per PAL line (the PAL recordings' frame width)."""
    native_height_px: int
    """PAL active lines (the PAL recordings' frame height)."""
    display_width_px: int
    display_height_px: int
    display_stretch: tuple[float, float]
    """1080p clip pixels per PAL sample (x) and per PAL line (y), from the OSD."""
    body_length_mm: float
    flange_distance_mm: float
    focal_length_mm: float
    f_number: float
    iris_stops: tuple[float, ...]
    extension_tube_mm: float
    lens_body_length_mm: float
    focus_travel_mm: float
    air_gap_mm: float
    sight_glass_thickness_mm: float
    sight_glass_index: float
    focus_object_distance_mm: float
    min_side_px: float
    max_size_um: float
    source_path: Path

    @property
    def sensor_width_mm(self) -> float:
        """CCD active width, ``cells_h × cell_width``."""
        return self.cells_h * self.cell_width_um / 1000.0

    @property
    def sensor_height_mm(self) -> float:
        """CCD active height, ``cells_v × cell_height``."""
        return self.cells_v * self.cell_height_um / 1000.0

    @property
    def sample_pitch_um(self) -> tuple[float, float]:
        """Sensor-plane µm per PAL sample (x) and per PAL line (y).

        x: a cell is read out every ``1 / pixel_clock``; the DVR takes a sample
        every ``1 / sampling_rate``, so a sample spans
        ``cell_width × pixel_clock / sampling_rate`` of the sensor.
        y: one PAL line is one cell row.
        """
        return (
            self.cell_width_um * self.pixel_clock_mhz / self.sampling_rate_mhz,
            self.cell_height_um,
        )

    @property
    def native_pixel_pitch_um(self) -> float:
        """Geometric-mean sensor-plane pitch of a PAL sample, for areas only.

        Per-axis lengths must use :attr:`sample_pitch_um` (x ≠ y).
        """
        x, y = self.sample_pitch_um
        return math.sqrt(x * y)


def load_camera(path: str | Path = DEFAULT_CONFIG_PATH) -> CameraConfig:
    """Load a ``configs/<camera>.toml`` file into a :class:`CameraConfig`."""
    path = Path(path)
    data = tomllib.loads(path.read_text())
    cam = data["camera"]
    dvr = data["dvr"]
    disp = data["display_1080p"]
    lens = data["lens"]
    glass = data["sight_glass"]
    focus = data["focus"]
    detection = data["detection"]
    return CameraConfig(
        name=cam.get("model", path.stem),
        cell_width_um=float(cam["cell_width_um"]),
        cell_height_um=float(cam["cell_height_um"]),
        cells_h=int(cam["cells_h"]),
        cells_v=int(cam["cells_v"]),
        pixel_clock_mhz=float(cam["pixel_clock_mhz"]),
        sampling_rate_mhz=float(dvr["sampling_rate_mhz"]),
        active_line_us=float(dvr["active_line_us"]),
        native_width_px=int(dvr["samples_per_line"]),
        native_height_px=int(dvr["lines"]),
        display_width_px=int(disp["width_px"]),
        display_height_px=int(disp["height_px"]),
        display_stretch=(float(disp["stretch_x"]), float(disp["stretch_y"])),
        body_length_mm=float(cam["body_length_mm"]),
        flange_distance_mm=float(cam["flange_distance_mm"]),
        focal_length_mm=float(lens["focal_length_mm"]),
        f_number=float(lens["f_number"]),
        iris_stops=tuple(float(n) for n in lens["iris_stops"]),
        extension_tube_mm=float(lens["extension_tube_mm"]),
        lens_body_length_mm=float(lens["body_length_mm"]),
        focus_travel_mm=float(lens.get("focus_travel_mm", 0.0)),
        air_gap_mm=float(lens["air_gap_mm"]),
        sight_glass_thickness_mm=float(glass["thickness_mm"]),
        sight_glass_index=float(glass["refractive_index"]),
        focus_object_distance_mm=float(focus["object_distance_mm"]),
        min_side_px=float(detection["min_side_px"]),
        max_size_um=float(detection["max_size_um"]),
        source_path=path,
    )


_SECTION = re.compile(r"^\[(\w+)\]")
_TAGGED = re.compile(r"^\s*(\w+)\s*=.*?#\s*([A-Z]+):")
# Strongest first; a derived quantity inherits the weakest class of its inputs.
SOURCE_RANK = (
    "MEASURED PHOTO DATASHEET CHOICE DERIVED PLANT ESTIMATE ASSUMED UNSOURCED"
).split()


def source_classes(path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, str]:
    """Map ``section.key`` to the ``# CLASS: source`` tag on its config line."""
    out: dict[str, str] = {}
    section = ""
    for line in Path(path).read_text().splitlines():
        if m := _SECTION.match(line):
            section = m[1]
        elif m := _TAGGED.match(line):
            out[f"{section}.{m[1]}"] = m[2]
    return out


def display_factors(
    cfg: CameraConfig,
    frame_width_px: int | None = None,
    frame_height_px: int | None = None,
) -> tuple[float, float]:
    """Frame pixels per PAL sample (x) and per PAL line (y) for a recording.

    * PAL recordings (``native_width_px`` wide, or ``None``): ``(1, 1)``.
    * 1080p clips: ``display_1080p.stretch_x/_y``, measured by registering
      the DVR's OSD glyphs between the two recordings
      (``python -m optics.scale_chain``).

    Any other frame geometry raises: its scale is unknown.
    """
    w = cfg.native_width_px if frame_width_px is None else frame_width_px
    if w == cfg.native_width_px and frame_height_px in (
        None,
        cfg.native_height_px,
    ):
        return 1.0, 1.0
    if w == cfg.display_width_px and frame_height_px in (
        None,
        cfg.display_height_px,
    ):
        return cfg.display_stretch
    raise ValueError(
        f"no scale chain for a {w}×{frame_height_px} frame: only PAL "
        f"{cfg.native_width_px}×{cfg.native_height_px} recordings and the "
        f"{cfg.display_width_px}×{cfg.display_height_px} DVR clips are known"
    )


def sensor_pitch_xy(
    cfg: CameraConfig,
    frame_width_px: int | None = None,
    frame_height_px: int | None = None,
) -> tuple[float, float]:
    """Sensor-plane µm per frame pixel, ``(x, y)``, for a recording type."""
    px, py = cfg.sample_pitch_um
    sx, sy = display_factors(cfg, frame_width_px, frame_height_px)
    return px / sx, py / sy


def lens_from_config(
    cfg: CameraConfig,
    frame_width_px: int | None = None,
    frame_height_px: int | None = None,
) -> LensSetup:
    """Build a :class:`LensSetup` whose pixel is a pixel of this recording.

    Without a frame size the pixel is a PAL sample. ``pixel_pitch_um`` is
    the geometric mean of the per-axis pitch (right for areas); per-axis
    lengths come from ``pixel_pitch_x_um`` / ``pixel_pitch_y_um``.
    """
    px, py = sensor_pitch_xy(cfg, frame_width_px, frame_height_px)
    return LensSetup(
        focal_length=cfg.focal_length_mm,
        f_number=cfg.f_number,
        extension_tube=cfg.extension_tube_mm,
        pixel_pitch_um=math.sqrt(px * py),
        sensor_width=cfg.sensor_width_mm,
        sensor_height=cfg.sensor_height_mm,
        pixel_aspect=px / py,
    )


def sight_glass_from_config(cfg: CameraConfig) -> SightGlass:
    """Build a :class:`SightGlass` from a config."""
    return SightGlass(
        thickness=cfg.sight_glass_thickness_mm,
        refractive_index=cfg.sight_glass_index,
    )


def probe_frame_size(video_path: str | Path) -> tuple[int, int]:
    """Metadata-only ``(width, height)`` probe — does NOT decode any frames."""
    cap = cv2.VideoCapture(str(video_path))
    try:
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    finally:
        cap.release()
    if w <= 0 or h <= 0:
        raise RuntimeError(f"Could not read frame size from {video_path}")
    return w, h


def probe_frame_width(video_path: str | Path) -> int:
    """Metadata-only frame-width probe — does NOT decode any frames."""
    return probe_frame_size(video_path)[0]


def lens_from_config_and_video(
    cfg: CameraConfig, video_path: str | Path
) -> LensSetup:
    """Build a :class:`LensSetup` for this video's recording type (frame size)."""
    w, h = probe_frame_size(video_path)
    return lens_from_config(cfg, w, h)


def um_per_px_xy_at_focus(
    cfg: CameraConfig, lens: LensSetup
) -> tuple[float, float]:
    """Object-plane µm per frame pixel ``(x, y)`` at the focused plane."""
    d_focus = cfg.focus_object_distance_mm
    gm = 1000.0 * float(mm_per_pixel_at(lens, d_focus, np.array([d_focus]))[0])
    root = math.sqrt(lens.pixel_aspect)
    return gm * root, gm / root


def detection_area_px(
    cfg: CameraConfig, lens: LensSetup
) -> tuple[float, float]:
    """Detector area window ``(min_area, max_area)`` in px² from ``[detection]``.

    The lower bound is the resolution limit (``min_side_px`` squared); the upper
    bound is the pixel count of a ``max_size_um`` square at the focused plane,
    ``max_size_um² / (µm_x · µm_y)``, so it follows the recording's per-axis
    scale.
    """
    ux, uy = um_per_px_xy_at_focus(cfg, lens)
    return cfg.min_side_px**2, cfg.max_size_um**2 / (ux * uy)
