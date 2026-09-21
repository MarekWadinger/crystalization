"""Measurement-error budget for the Camera 100 optical chain.

First-order (linear) propagation plus a Monte-Carlo check, from the input
uncertainties in ``INPUTS`` to the derived quantities used in the paper.

    uv run python -m optics.error_budget
"""

from __future__ import annotations

import numpy as np

from optics.config import load_camera

# (value, 1-sigma, provenance)
_cfg = load_camera()
INPUTS: dict[str, tuple[float, float, str]] = {
    "f": (
        _cfg.focal_length_mm,
        0.7,
        "datasheet 35 mm; ±2 % typical CCTV tolerance (ASSUMED)",
    ),
    "e": (_cfg.extension_tube_mm, 0.5, "operator tape/caliper 2026-09-07"),
    "x": (
        _cfg.focus_travel_mm,
        1.0,
        "~3 exposed helicoid turns ≈ 1 mm (operator estimate)",
    ),
    "p": (
        _cfg.native_pixel_pitch_um,
        0.02,
        "Sony IMX307/IMX327 unit cell 2.9 µm (datasheet)",
    ),
    "t": (_cfg.sight_glass_thickness_mm, 0.5, "operator 2026-09-07"),
    "a": (_cfg.air_gap_mm, 1.0, "operator 2026-09-07"),
    "n": (
        _cfg.sight_glass_index,
        0.03,
        "borosilicate 1.47 assumed; soda-lime would be 1.52",
    ),
}


def derived(
    f: float, e: float, x: float, p: float, t: float, a: float, n: float
) -> dict[str, float]:
    i = f + e + x
    d = f * i / (i - f)
    delta = t * (1 - 1 / n)
    return {
        "um_per_px": p * f / (e + x),
        "d_focus_mm": d,
        "H_to_inner_face_mm": d + delta,
        "H_behind_front_mm": d - (t - delta) - a,
        "H2_behind_front_mm": _cfg.flange_distance_mm
        + e
        + _cfg.lens_body_length_mm
        + x
        - i,
    }


def main() -> None:
    names = list(INPUTS)
    x0 = np.array([INPUTS[k][0] for k in names])
    sig = np.array([INPUTS[k][1] for k in names])
    base = derived(*x0)

    # linear sensitivities by central differences
    contrib: dict[str, dict[str, float]] = {q: {} for q in base}
    for j, k in enumerate(names):
        h = np.zeros_like(x0)
        h[j] = 1e-4 * max(abs(x0[j]), 1.0)
        up, dn = derived(*(x0 + h)), derived(*(x0 - h))
        for q in base:
            contrib[q][k] = (up[q] - dn[q]) / (2 * h[j]) * sig[j]

    rng = np.random.default_rng(0)
    samples = rng.normal(x0, sig, size=(200_000, len(names)))
    mc = {q: np.std([derived(*s)[q] for s in samples[:20_000]]) for q in base}

    print("## Inputs (1 σ)\n")
    print("| Symbol | Value | σ | Source |\n|---|---:|---:|---|")
    for k in names:
        v, s, src = INPUTS[k]
        print(f"| {k} | {v:g} | ±{s:g} | {src} |")
    print(
        "\n## Propagated 1 σ per derived quantity (linear; MC check in last column)\n"
    )
    hdr = (
        "| Quantity | Value | "
        + " | ".join(f"σ from {k}" for k in names)
        + " | total σ (lin) | total σ (MC) | rel. |"
    )
    print(hdr)
    print("|---|---:|" + "---:|" * (len(names) + 3))
    for q, v in base.items():
        parts = contrib[q]
        tot = float(np.sqrt(sum(c * c for c in parts.values())))
        cells = " | ".join(f"{abs(parts[k]):.3f}" for k in names)
        print(
            f"| {q} | {v:.3f} | {cells} | **{tot:.3f}** | {mc[q]:.3f} | {100 * tot / abs(v):.1f} % |"
        )
    print(
        "\nNot in the table (discrete, not Gaussian): the C-mount flange depth. "
        "If the measured 60 mm already includes the 5 mm C-mount adapter ring, "
        "e is 55 mm: µm/px +9 %, d_focus +2.0 mm, H′ shifts −5 mm."
    )


if __name__ == "__main__":
    main()
