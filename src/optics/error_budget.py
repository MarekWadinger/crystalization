"""Measurement-error budget for the Camera 100 optical chain.

First-order (linear) propagation plus a Monte-Carlo check, from the input
uncertainties in ``INPUTS`` to the derived quantities used in the paper.

    uv run python -m optics.error_budget
"""

from __future__ import annotations

import numpy as np

from optics.config import load_camera

# (value, 1-sigma, provenance). A uniform ±h spread enters as σ = h/√3.
_cfg = load_camera()
_PX, _PY = _cfg.sample_pitch_um
_U = 3**-0.5
INPUTS: dict[str, tuple[float, float, str]] = {
    "f": (
        _cfg.focal_length_mm,
        0.7,
        "lens engraving 35 mm (PHOTO); ±2 % CCTV tolerance (ASSUMED)",
    ),
    "e": (
        _cfg.extension_tube_mm,
        5.0 * _U,
        'Q&A 8(A) "≈ 6 cm" (PLANT), uniform ±5 mm',
    ),
    "x": (
        _cfg.focus_travel_mm,
        0.0,
        "focus travel 0 mm, lens at its FAR stop (author decision 2026-11-05)",
    ),
    "px": (
        _PX,
        0.02 * _PX * _U,
        "µm per PAL sample, CCD cell × clock / 13.5 MHz (ESTIMATE), "
        "line mapping uniform ±2 % (optics.scale_chain)",
    ),
    "py": (
        _PY,
        0.0,
        "µm per PAL line = CCD row (ESTIMATE); one cell for all 752 × 582 candidates",
    ),
    "t": (
        _cfg.sight_glass_thickness_mm,
        0.5,
        'Q&A 8(C) "20 mm" (PLANT)',
    ),
    "a": (
        _cfg.air_gap_mm,
        5.0 * _U,
        'Q&A 8(B) "≈ 2 cm" (PLANT), uniform ±5 mm',
    ),
    "n": (
        _cfg.sight_glass_index,
        0.03,
        "soda-lime 1.52, DIN 8902 stamp (ESTIMATE); borosilicate would be 1.47",
    ),
}


def derived(
    f: float,
    e: float,
    x: float,
    px: float,
    py: float,
    t: float,
    a: float,
    n: float,
) -> dict[str, float]:
    i = f + e + x
    d = f * i / (i - f)
    delta = t * (1 - 1 / n)
    return {
        "um_per_px_x_PAL": px * f / (e + x),
        "um_per_px_y_PAL": py * f / (e + x),
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
        "If the plant's ≈ 60 mm already includes the 5 mm CS→C adapter ring, "
        "e is 55 mm: µm/px +9 %, d_focus +2.0 mm, H′ shifts −5 mm. "
        "Per-recording µm/px with 95 % intervals (PAL and 1080p, x and y): "
        "uv run python -m optics.scale_chain."
    )


if __name__ == "__main__":
    main()
