"""Process-signal growth model: plant supersaturation and a power growth law.

Supersaturation is the plant's own "koeficient presýtenia" KP from the
DCS formula sheets ``Vzorce A_seed.xlsx`` / ``Vzorce A_varostroj.xlsx``
(Drive ``sugar_plant/sered/``), transcribed in
``docs/sered/notes_data_lab.md`` §3c:

- ``Bsat(T) = 64.397 + 0.07251 T + 0.0020569 T² − 9.035e-6 T³`` (sucrose
  solubility, % dry substance, T in °C);
- ``NW = Bx (100 − P) / 100 / (100 − Bx)`` (non-sugars per water);
- ``SC = a NW + b + (1 − b) · 2.72 · (−c NW)``, a, b, c = 0.5, 0.95, 1;
- ``KP = Bx P (100 − Bsat) / ((100 − Bx) Bsat SC 100)``.

The sheet multiplies by 2.72 where the Wright/Vavrinecz form raises e to
the power (notes §8, "likely bug"). The sheet form reproduces the sheet's
worked examples (0.89 and 1.385) and, within 0.002, the DCS live value
KP_akt 1.210 at Viskozita 81.5, 69.5 °C and the recipe purity 93.4 %
(``docs/sered/notes_plant_dcs_qa_photos.md`` §2.2; which purity and
temperature the DCS feeds is not documented), so it is the default;
``form="exp"`` gives the textbook form.

Growth law ``G = k_g (S − 1)^g`` (``notes_literature_models.md`` §2:
g = 1 in Georgieva et al. 2003 Eq. 24, an industrial fed-batch sugar pan
seeded at ≈ 10 µm; g = 2.7 in the HYCON2 benchmark, Hernández 2011
Eq. 3.44). No dissolution: ``G = 0`` where ``S ≤ 1``. ``k_g`` (µm/min)
absorbs the temperature and purity factors of the Georgieva law; it is
fitted on microscope medians. Size ``L(t) = L0 + k_g ∫_0^t (S − 1)^g``.

Inputs Bx and P are the dry substance and purity of the mother liquor in
the formula. The plant feeds it QI1003, which reads the whole massecuite
(crystals included), and the lab Brix of a diluted massecuite sample is
also whole-massecuite dry substance. Both overstate the mother-liquor Bx
once the crystal content grows, so KP computed from them is an index, not
the mother-liquor supersaturation, after the first minutes of a strike.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from scipy.optimize import minimize_scalar

SC_A, SC_B, SC_C = 0.5, 0.95, 1.0
"""Impurity coefficients a, b, c of the plant sheet (source unknown, notes
§7 q. 9)."""
SC_FORMS = ("sheet", "exp")


def sucrose_solubility(t_c: np.ndarray | float) -> np.ndarray:
    """Saturation dry substance of pure sucrose solution (% DS), plant
    sheet polynomial; 75.32 at 65 °C."""
    t = np.asarray(t_c, float)
    return 64.397 + 0.07251 * t + 0.0020569 * t**2 - 9.035e-6 * t**3


def nonsugar_water(
    bx: np.ndarray | float, purity: np.ndarray | float
) -> np.ndarray:
    """Non-sugars per water ``NW = Bx (100 − P) / 100 / (100 − Bx)``."""
    bx, p = np.asarray(bx, float), np.asarray(purity, float)
    return bx * (100.0 - p) / 100.0 / (100.0 - bx)


def saturation_coefficient(
    nw: np.ndarray | float, form: str = "sheet"
) -> np.ndarray:
    """Impurity saturation coefficient SC(NW).

    ``sheet``: ``a NW + b + (1 − b)·2.72·(−c NW)`` as in the DCS sheet;
    ``exp``: ``a NW + b + (1 − b)·exp(−c NW)``.
    """
    nw = np.asarray(nw, float)
    if form == "sheet":
        tail = (1.0 - SC_B) * 2.72 * (-SC_C * nw)
    elif form == "exp":
        tail = (1.0 - SC_B) * np.exp(-SC_C * nw)
    else:
        raise ValueError(f"form must be one of {SC_FORMS}, not {form!r}")
    return SC_A * nw + SC_B + tail


def supersaturation(
    bx: np.ndarray | float,
    purity: np.ndarray | float,
    t_c: np.ndarray | float,
    form: str = "sheet",
) -> np.ndarray:
    """Plant supersaturation coefficient KP(Bx %, purity %, T °C)."""
    bx, p = np.asarray(bx, float), np.asarray(purity, float)
    bsat = sucrose_solubility(t_c)
    sc = saturation_coefficient(nonsugar_water(bx, p), form)
    return bx * p * (100.0 - bsat) / ((100.0 - bx) * bsat * sc * 100.0)


def lab_brix_purity(
    refract: float, polari: float, dil_refract: float, dil_polari: float
) -> tuple[float, float]:
    """Lab Brix and purity from the diluted readings (``ZRA.xlsx``):
    sacharizácia = refract × dilution, polarizácia = polari × dilution,
    purity = polarizácia / sacharizácia × 100."""
    bx = refract * dil_refract
    return bx, 100.0 * polari * dil_polari / bx


def growth_rate(
    s: np.ndarray | float, k_g: float, g: float = 1.0
) -> np.ndarray:
    """``G = k_g max(S − 1, 0)^g`` in the units of ``k_g``."""
    return k_g * np.maximum(np.asarray(s, float) - 1.0, 0.0) ** g


def growth_integral(
    t: np.ndarray, s: np.ndarray, g: float = 1.0
) -> np.ndarray:
    """``I(t) = ∫_{t_0}^t max(S − 1, 0)^g dt`` by the trapezoid rule on the
    grid ``t`` (I = 0 at ``t[0]``), so ``L = L0 + k_g I``."""
    f = growth_rate(s, 1.0, g)
    steps = 0.5 * (f[1:] + f[:-1]) * np.diff(t)
    return np.concatenate([[0.0], np.cumsum(steps)])


def integrate_size(
    t: np.ndarray, s: np.ndarray, l0: float, k_g: float, g: float = 1.0
) -> np.ndarray:
    """``L(t) = L0 + k_g I(t)`` on the grid ``t`` (L0 at ``t[0]``)."""
    return l0 + k_g * growth_integral(t, s, g)


def fit_kg(
    t: np.ndarray,
    s: np.ndarray,
    l0: float,
    t_obs: Sequence[float] | np.ndarray,
    l_obs: Sequence[float] | np.ndarray,
    g: float = 1.0,
    bounds: tuple[float, float] = (1e-3, 1e4),
) -> float:
    """``k_g`` minimising ``Σ (ln L(t_j) − ln L_j)²`` over observed sizes.

    ``L(t_j)`` is :func:`integrate_size` read at ``t_j`` (linear between
    grid points). Bounded scalar search on ``ln k_g``.
    """
    integ = np.interp(np.asarray(t_obs, float), t, growth_integral(t, s, g))
    ln_obs = np.log(np.asarray(l_obs, float))

    def cost(ln_k: float) -> float:
        r = np.log(l0 + np.exp(ln_k) * integ) - ln_obs
        return float(r @ r)

    lo, hi = np.log(bounds[0]), np.log(bounds[1])
    res = minimize_scalar(
        cost, bounds=(lo, hi), method="bounded", options={"xatol": 1e-8}
    )
    return float(np.exp(res.x))


def detect_seeding(
    t: np.ndarray,
    steam_out: np.ndarray,
    stirrer_a: np.ndarray,
    bx: np.ndarray,
    open_pct: float = 95.0,
    cut_pct: float = 50.0,
    hold: int = 10,
    stirrer_on_a: float = 5.0,
    bx_max: float = 85.0,
) -> list[float]:
    """Seeding times from the steam cut: the steam-flap output falls from
    ≥ ``open_pct`` (held for ``hold`` samples) to ≤ ``cut_pct`` while the
    stirrer runs and the Brix signal ``bx`` is at most ``bx_max``. One time
    per stirrer-on interval (the first cut).

    The Brix gate rejects the steam cut that ends a strike (tightening,
    Bx ≈ 90) before the stirrer stops: the ZRA recipe seeds near
    80.7 Bx ("Viskozita stabilizácia") and ends boiling at 90 Bx
    (``notes_plant_dcs_qa_photos.md`` §2.2); 85 is a CHOICE between them.
    """
    out: list[float] = []
    run, armed, found = 0, False, False
    for k in range(len(t)):
        on = stirrer_a[k] > stirrer_on_a
        if not on:
            run, armed, found = 0, False, False
            continue
        if steam_out[k] >= open_pct:
            run += 1
            armed = armed or run >= hold
        elif (
            armed and not found and steam_out[k] <= cut_pct and bx[k] <= bx_max
        ):
            out.append(float(t[k]))
            found = True
        else:
            run = 0
    return out
