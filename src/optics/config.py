"""Versioned camera configuration loader.

Hardware constants live in ``configs/<camera>.toml`` (sensor size, lens
focal length, F-number, extension tube, sight-glass geometry, nominal
focus distance). They are *not* secrets and do not belong in ``.env``:
every figure and KPI snapshot is invalidated if a constant changes, so
they must be versioned with the code.

The DVR-sampled rate (``pixel_pitch_um``) is **not** in the TOML — it is
derived from the actual video frame width because the analogue chain may
downsample (e.g. the 13 GB Sereď batch is 720×576 PAL on a 1920×1080
native sensor, so the *effective* µm/px is sensor_width / frame_width).

Typical use::

    from optics.config import load_camera, lens_from_config_and_video

    cfg = load_camera("configs/camera_100.toml")
    lens = lens_from_config_and_video(cfg, "datasets/2026-02-04 11-08-51.mp4")
    # lens.pixel_pitch_um = 5568 / 720 ≈ 7.73 µm (PAL-downsampled feed)
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

import cv2

from optics.model import LensSetup, SightGlass


@dataclass(frozen=True, slots=True)
class CameraConfig:
    """Hardware constants for one camera+lens+sight-glass installation."""

    name: str
    sensor_width_mm: float
    sensor_height_mm: float
    native_width_px: int
    native_height_px: int
    focal_length_mm: float
    f_number: float
    extension_tube_mm: float
    lens_body_length_mm: float
    focus_travel_mm: float
    air_gap_mm: float
    sight_glass_thickness_mm: float
    sight_glass_index: float
    focus_object_distance_mm: float
    source_path: Path

    @property
    def native_pixel_pitch_um(self) -> float:
        """µm/px at the sensor's native resolution."""
        return self.sensor_width_mm * 1000.0 / self.native_width_px


def load_camera(path: str | Path) -> CameraConfig:
    """Load a ``configs/<camera>.toml`` file into a :class:`CameraConfig`."""
    path = Path(path)
    data = tomllib.loads(path.read_text())
    cam = data["camera"]
    lens = data["lens"]
    glass = data["sight_glass"]
    focus = data["focus"]
    return CameraConfig(
        name=cam.get("model", path.stem),
        sensor_width_mm=float(cam["sensor_width_mm"]),
        sensor_height_mm=float(cam["sensor_height_mm"]),
        native_width_px=int(cam["native_width_px"]),
        native_height_px=int(cam["native_height_px"]),
        focal_length_mm=float(lens["focal_length_mm"]),
        f_number=float(lens["f_number"]),
        extension_tube_mm=float(lens["extension_tube_mm"]),
        lens_body_length_mm=float(lens["body_length_mm"]),
        focus_travel_mm=float(lens.get("focus_travel_mm", 0.0)),
        air_gap_mm=float(lens["air_gap_mm"]),
        sight_glass_thickness_mm=float(glass["thickness_mm"]),
        sight_glass_index=float(glass["refractive_index"]),
        focus_object_distance_mm=float(focus["object_distance_mm"]),
        source_path=path,
    )


def lens_from_config(
    cfg: CameraConfig, frame_width_px: int | None = None
) -> LensSetup:
    """Build a :class:`LensSetup` from a config, optionally rescaling pixel pitch.

    If ``frame_width_px`` is given and differs from the camera's native width,
    the pixel pitch is rescaled so ``µm/px = sensor_width / frame_width``.
    Use this whenever an analogue/DVR chain downsamples below sensor native.
    """
    pitch_um = cfg.native_pixel_pitch_um
    if frame_width_px is not None and frame_width_px > 0:
        pitch_um = cfg.sensor_width_mm * 1000.0 / frame_width_px
    return LensSetup(
        focal_length=cfg.focal_length_mm,
        f_number=cfg.f_number,
        extension_tube=cfg.extension_tube_mm,
        pixel_pitch_um=pitch_um,
        sensor_width=cfg.sensor_width_mm,
        sensor_height=cfg.sensor_height_mm,
    )


def sight_glass_from_config(cfg: CameraConfig) -> SightGlass:
    """Build a :class:`SightGlass` from a config."""
    return SightGlass(
        thickness=cfg.sight_glass_thickness_mm,
        refractive_index=cfg.sight_glass_index,
    )


def probe_frame_width(video_path: str | Path) -> int:
    """Metadata-only frame-width probe — does NOT decode any frames."""
    cap = cv2.VideoCapture(str(video_path))
    try:
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    finally:
        cap.release()
    if w <= 0:
        raise RuntimeError(f"Could not read frame width from {video_path}")
    return w


def lens_from_config_and_video(
    cfg: CameraConfig, video_path: str | Path
) -> LensSetup:
    """Build a :class:`LensSetup` with pixel pitch derived from the video stream."""
    return lens_from_config(cfg, frame_width_px=probe_frame_width(video_path))
