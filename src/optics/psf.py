"""Sharpness-measure vs defocus, under two PSF models.

We compute the response of a generic edge/texture-energy sharpness measure
(Laplacian variance, Tenengrad, Brenner — all behave similarly because they
weight the OTF by a high-pass kernel) as a function of the defocus
circle-of-confusion ``c``.

Two models are provided:

* **Gaussian PSF** — the standard depth-from-defocus approximation
  (Pentland, *IEEE TPAMI* 9(4) 1987; Subbarao & Surya, *IJCV* 13(3) 1994;
  Pertuz, Puig & García, *Pattern Recognition* 46:1415–1432, 2013). The
  PSF is a 2-D Gaussian with σ ≈ ρ · c (Pentland's ρ-convention, ρ ≈ 1/2)
  giving the OTF ``|H(u)|² = exp(−4π² σ² u²)``. Integrating a Laplacian-
  variance measure against a flat texture spectrum yields ``S ∝ σ⁻⁵ ∝
  c⁻⁵`` — a sharply peaked power-law, NOT a Gaussian.

* **Diffraction-limited (Airy)** — at small apertures and small defocus
  the geometric c shrinks below the Airy spot diameter
  ``d_Airy = 2.44 · λ · N`` (Born & Wolf, *Principles of Optics* §8.5;
  Goodman, *Introduction to Fourier Optics* §6.4). A Gaussian fit to the
  Airy intensity profile has σ_diff in the range 0.42–0.45 · λ · N
  depending on which matching criterion is used (Smith, *Modern Optical
  Engineering*, 4th ed. §11). Adding the two PSFs in quadrature clamps
  the maximum sharpness at the focused plane.

Both models share the same ``c⁻⁵`` tail at large defocus — the
diffraction term only matters near the peak.

Sources cross-checked against the deep-research findings in
``docs/optics/README.md`` §12.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from optics.model import LensSetup, circle_of_confusion, magnification

# Reference wavelength for visible-band imaging — green channel weighted.
LAMBDA_GREEN_MM: float = 550e-6  # 550 nm in millimetres


def _power_law_sharpness(
    sigma: NDArray[np.float64], sigma_floor: float
) -> NDArray[np.float64]:
    """Truncated-band Laplacian-variance response.

    The integral

        S = ∫_0^{u_N} |OTF(u)|² · u⁴ · du

    with a Gaussian OTF |H(u)|² = exp(−4π² σ² u²) admits a closed form via
    the lower incomplete gamma function::

        S(σ) ∝ σ⁻⁵ · γ(5/2, 4π² σ² u_N²)

    where ``u_N`` is the Nyquist frequency (1/(2·pitch)). For σ → 0 the
    integrand cuts off at u_N and S saturates at u_N⁵/5 (finite); for
    σ → ∞ the gamma asymptote gives the textbook σ⁻⁵ tail. We replace
    the role of u_N with an equivalent ``σ_floor = 1/(2π · u_N)`` and the
    practical approximation::

        S ≈ (σ² + σ_floor²)⁻⁵ᐟ²

    which matches the limits at both ends within ~10 %. Quadrature-adding
    the floor is the operationally-relevant correction: σ_floor accounts
    for finite pixel pitch and the high-frequency cutoff imposed by the
    sensor's sample-and-hold response.
    """
    s2 = sigma**2 + sigma_floor**2
    out: NDArray[np.float64] = s2 ** (-2.5)
    return out / float(out.max())


def sharpness_gaussian(
    coc: NDArray[np.float64] | float,
    sigma_floor: float = 1.4e-3,
) -> NDArray[np.float64]:
    """Laplacian-variance sharpness vs geometric CoC, Gaussian-PSF model.

    Parameters
    ----------
    coc:
        Circle-of-confusion diameter, same length unit as ``sigma_floor``.
    sigma_floor:
        Sensor-imposed blur floor (default 1.4 µm = pixel_pitch/2 for the
        Hanwha HCB-6000) added in quadrature to σ. Without it the c⁻⁵
        power-law diverges at σ = 0.

    Returns
    -------
    Normalised sharpness in [0, 1] with peak at coc = 0.
    """
    c = np.asarray(coc, dtype=np.float64)
    sigma = c / 2.0
    return _power_law_sharpness(sigma, sigma_floor)


def working_f_number(f_number: float, magnification: float) -> float:
    """Image-side working F-number ``N_w = N (1 + M)``.

    At macro magnification the exit cone at the sensor is narrower than the
    nominal ``f/N`` suggests; the image-side NA is ``1 / (2 N_w)``. Pupil
    magnification is taken as 1 (not given in the lens datasheet).
    """
    return f_number * (1.0 + magnification)


def sharpness_diffraction(
    coc: NDArray[np.float64] | float,
    f_number: float,
    wavelength_mm: float = LAMBDA_GREEN_MM,
    sensor_floor_mm: float = 1.4e-3,
    *,
    magnification: float = 0.0,
) -> NDArray[np.float64]:
    """Same model with a diffraction *and* sensor floor.

    The Airy radius (first zero) is ``r_Airy = 1.22 · λ · N_w``; the Gaussian
    that best matches the Airy intensity has σ_diff ≈ 0.42 · λ · N_w
    (Goodman, *Introduction to Fourier Optics*, §6.2 — Gaussian fit to a
    circular-aperture PSF), with ``N_w`` the working F-number of
    :func:`working_f_number`. Pass the transverse ``magnification`` of the
    setup; ``0`` (the default) is the infinity-focus limit ``N_w = N`` and
    underestimates diffraction at macro distances. σ_diff adds in quadrature
    with the geometric blur (c/2) and with the sensor sampling floor
    (≈ pixel_pitch / 2).
    """
    c = np.asarray(coc, dtype=np.float64)
    sigma_geom = c / 2.0
    sigma_diff = (
        0.42 * wavelength_mm * working_f_number(f_number, magnification)
    )
    sigma_floor = float(np.hypot(sigma_diff, sensor_floor_mm))
    return _power_law_sharpness(sigma_geom, sigma_floor)


def sharpness_vs_object_distance(
    lens: LensSetup,
    d_focus: float,
    d_o: NDArray[np.float64],
    *,
    diffraction: bool = True,
) -> NDArray[np.float64]:
    """Sharpness as a function of object distance — full chain.

    Composes :func:`optics.model.circle_of_confusion` with either
    :func:`sharpness_gaussian` or :func:`sharpness_diffraction`.
    """
    c = circle_of_confusion(lens, d_focus, d_o)
    if diffraction:
        return sharpness_diffraction(
            c, lens.f_number, magnification=magnification(lens, d_focus)
        )
    return sharpness_gaussian(c)
