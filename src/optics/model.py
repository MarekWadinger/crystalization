"""Thin-lens geometry for a fixed lens + extension-tube + sight-glass setup.

The model is the standard Gaussian thin-lens model (Hecht, *Optics*, §5.2),
extended with two operationally-relevant corrections:

* a finite extension tube ``e`` placed between the lens flange and the
  sensor — the back focal distance becomes ``i = f + e`` at infinity focus,
  with the focus ring then trimming ``i`` further;
* a flat sight glass of thickness ``t`` and refractive index ``n_g`` that
  shifts the apparent object distance toward the lens by
  ``Δ = t · (1 − 1/n_g)`` (Hecht §5.6, refraction at a planar interface).

Sign convention: distances are positive on either side of the lens; ``d_o``
is measured from the lens principal plane to the object.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

ArrayLike = NDArray[np.float64] | float


@dataclass(frozen=True, slots=True)
class LensSetup:
    """Geometry of a thin lens + extension tube + sensor stack.

    All lengths in millimetres.
    """

    focal_length: float
    """Lens focal length f."""

    f_number: float
    """Working F-number N (= f / aperture_diameter)."""

    extension_tube: float
    """Extra distance e between the lens flange and the sensor."""

    pixel_pitch_um: float
    """Sensor pixel pitch in micrometres."""

    sensor_width: float
    """Sensor active-area width."""

    sensor_height: float
    """Sensor active-area height."""

    @property
    def aperture_diameter(self) -> float:
        """A = f / N."""
        return self.focal_length / self.f_number

    @property
    def back_focal_at_infinity(self) -> float:
        """Image distance when focus ring is at infinity, ``i = f + e``."""
        return self.focal_length + self.extension_tube


@dataclass(frozen=True, slots=True)
class SightGlass:
    """Flat sight glass between the lens and the object."""

    thickness: float
    """Glass thickness t."""

    refractive_index: float
    """Borosilicate n_g in the visible band."""

    @property
    def apparent_shift(self) -> float:
        """Δ = t · (1 − 1/n_g): how much closer the object appears."""
        return self.thickness * (1.0 - 1.0 / self.refractive_index)


def image_distance_for_focus(lens: LensSetup, d_focus: float) -> float:
    """Image distance ``i`` when the lens is focused at object distance ``d_focus``.

    From the thin-lens equation 1/f = 1/d_o + 1/i:

        i = f · d_focus / (d_focus − f)

    The extension tube does not change this formula — it changes which
    ``d_focus`` is reachable. The focus ring then shifts ``i`` by a few
    millimetres around this value; here we assume the focus ring is set so
    that ``i`` lands on the sensor.
    """
    if d_focus <= lens.focal_length:
        raise ValueError(
            f"d_focus={d_focus} must exceed f={lens.focal_length}"
        )
    return lens.focal_length * d_focus / (d_focus - lens.focal_length)


def object_distance(lens: LensSetup, i: float) -> float:
    """Inverse of :func:`image_distance_for_focus` — solve for ``d_o``.

    From 1/f = 1/d_o + 1/i:

        d_o = f · i / (i − f)
    """
    if i <= lens.focal_length:
        raise ValueError(f"i={i} must exceed f={lens.focal_length}")
    return lens.focal_length * i / (i - lens.focal_length)


def magnification(lens: LensSetup, d_focus: float) -> float:
    """Transverse magnification M = i / d_o at the focused plane.

    Equivalently M = f / (d_focus − f).
    """
    return lens.focal_length / (d_focus - lens.focal_length)


def image_distance(lens: LensSetup, d_o: ArrayLike) -> NDArray[np.float64]:
    """Image distance ``i(d_o)`` for an object at d_o (focus ignored).

    i(d_o) = f · d_o / (d_o − f)

    This is the distance at which the lens forms a sharp image of an object
    at d_o. If this does not equal the *fixed* sensor distance, defocus
    results — see :func:`circle_of_confusion`.
    """
    d = np.asarray(d_o, dtype=np.float64)
    return lens.focal_length * d / (d - lens.focal_length)


def mm_per_pixel_at(
    lens: LensSetup,
    d_focus: float,
    d_o: ArrayLike,
) -> NDArray[np.float64]:
    """Object-plane pixel size at distance ``d_o`` for a lens focused at d_focus.

    Once the focus ring is set, the lens-to-sensor distance ``i_fixed`` is
    fixed. The image of an object at d_o gets relayed to the sensor with
    transverse magnification ``M(d_o) = i_fixed / d_o`` — note this is the
    geometric scale even when the image is *defocused*. The object-plane
    pixel pitch is therefore::

        Δx(d_o) = pixel_pitch / M(d_o) = pixel_pitch · d_o / i_fixed

    which is **linear in d_o**: doubling the object distance doubles the
    millimetres-per-pixel.
    """
    i_fixed = image_distance_for_focus(lens, d_focus)
    d = np.asarray(d_o, dtype=np.float64)
    pitch_mm = lens.pixel_pitch_um * 1e-3
    return pitch_mm * d / i_fixed


def apparent_object_distance(
    real_d_o: ArrayLike, glass: SightGlass
) -> NDArray[np.float64]:
    """Reduce real object distance by the sight-glass thin-glass shift.

    For a flat glass of thickness ``t`` and index ``n_g``, an object behind
    the glass appears closer to the lens by ``Δ = t · (1 − 1/n_g)``. This
    is the small-angle limit of Snell's law for a parallel plate (Hecht
    §5.6.1) and is independent of object distance.
    """
    d = np.asarray(real_d_o, dtype=np.float64)
    return d - glass.apparent_shift


def circle_of_confusion(
    lens: LensSetup,
    d_focus: float,
    d_o: ArrayLike,
) -> NDArray[np.float64]:
    """Geometric circle-of-confusion diameter at the sensor.

    Standard textbook form (Wikipedia *Circle of confusion*, derived from
    similar triangles + thin-lens equation; reproduced verbatim in
    Jacobson, *Manual of Photography* and Conrad, *Depth of Field in
    Depth*)::

        c(d_o) = A · |d_o − d_focus| / d_o · f / (d_focus − f)
               = f² / (N · (d_focus − f)) · |d_o − d_focus| / d_o

    with A = f / N the aperture diameter. The behaviour is *asymmetric*
    in ``d_o``:

      - **Near side** (d_o < d_focus): c grows quickly because |d − d_f|/d
        increases when both numerator grows and denominator shrinks.
      - **Far side** (d_o > d_focus): c saturates at the hyperfocal limit
        c_∞ = A · f / (d_focus − f) as d_o → ∞.

    In the reciprocal variable u = 1/d_o the geometry is *symmetric* and
    *linear*::

        c(u) = (f² / N) · |u − u_focus|        with u_focus = 1/d_focus

    which is the cleanest form for fitting depth-from-defocus models.

    Returns the diameter in the same units as the lens parameters (mm).
    """
    d = np.asarray(d_o, dtype=np.float64)
    return (
        lens.focal_length**2
        / lens.f_number
        * np.abs(d - d_focus)
        / (d * (d_focus - lens.focal_length))
    )
