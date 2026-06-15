"""Geometric optics for the Camera 100 sight-glass installation.

All length units are millimetres unless otherwise noted.

See ``docs/optics/README.md`` for derivations and the FACT/DERIVED/ESTIMATE
audit trail of the physical numbers used here.
"""

from __future__ import annotations

from optics.model import (
    LensSetup,
    SightGlass,
    apparent_object_distance,
    circle_of_confusion,
    image_distance,
    image_distance_for_focus,
    magnification,
    mm_per_pixel_at,
    object_distance,
)
from optics.psf import (
    sharpness_diffraction,
    sharpness_gaussian,
    sharpness_vs_object_distance,
)
from optics.video_io import (
    DEFAULT_CROP,
    CropBox,
    open_and_crop,
    read_frame_cropped,
)

__all__ = [
    "DEFAULT_CROP",
    "CropBox",
    "LensSetup",
    "SightGlass",
    "apparent_object_distance",
    "circle_of_confusion",
    "image_distance",
    "image_distance_for_focus",
    "magnification",
    "mm_per_pixel_at",
    "object_distance",
    "open_and_crop",
    "read_frame_cropped",
    "sharpness_diffraction",
    "sharpness_gaussian",
    "sharpness_vs_object_distance",
]
