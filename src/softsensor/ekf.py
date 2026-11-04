"""Discrete EKF for seed-pan crystal growth from a camera size signal.

State ``x = [ln L, ln G, θ]``: log median crystal size (L in µm), log
growth rate (G in µm/min, random walk in ln G) and the camera log offset
θ = ln(λ·b_sel) (constant, Q_θ = 0). Process ``L⁺ = L + G·Δt``.
Measurements are linear:

- camera ``y = ln L + θ + v``, ``h = [1, 0, 1]``;
- microscope anchor ``z = ln L + w``, ``h = [1, 0, 0]``.

Scale symmetry: ``(L, G, θ) → (cL, cG, θ − ln c)`` leaves every camera
output unchanged (:func:`scale_orbit`), so without an anchor the direction
``[1, 1, −1]`` in state space is unobservable (:func:`observability_matrix`).

Why ln G and not G: in ``[ln L, G, θ]`` coordinates the unobservable
direction is ``[1, G, −1]`` and moves with the estimate of G, so an EKF
linearised at noisy estimates gains spurious information on θ (the EKF
inconsistency known from SLAM). In ``[ln L, ln G, θ]`` the direction is the
constant ``[1, 1, −1]``, invariant under every Jacobian F and orthogonal to
the camera row h, so the EKF cannot learn θ from the camera alone.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

CAMERA_H = np.array([1.0, 0.0, 1.0])
ANCHOR_H = np.array([1.0, 0.0, 0.0])
MAX_STEP_MIN = 1.0
"""Longest propagation sub-step (min) between linearisations."""


@dataclass(frozen=True, slots=True)
class Measurement:
    """One scalar measurement ``z = h·x + noise`` at time ``t`` (min)."""

    t: float
    h: np.ndarray
    z: float
    r: float
    """Noise variance."""


def propagate(x: np.ndarray, dt: float) -> tuple[np.ndarray, np.ndarray]:
    """Process step ``L⁺ = L + G·Δt``; return ``x⁺`` and the Jacobian F."""
    size, rate = float(np.exp(x[0])), float(np.exp(x[1]))
    nxt = size + rate * dt
    f = np.array(
        [[size / nxt, rate * dt / nxt, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    )
    return np.array([np.log(nxt), x[1], x[2]]), f


def predict(
    x: np.ndarray, p: np.ndarray, dt: float, q_g: float, q_theta: float = 0.0
) -> tuple[np.ndarray, np.ndarray]:
    """EKF time update; ln G (and, if ``q_theta > 0``, θ) are random walks
    with variances ``q_g·Δt`` and ``q_theta·Δt``."""
    xn, f = propagate(x, dt)
    q = np.diag([0.0, q_g * dt, q_theta * dt])
    return xn, f @ p @ f.T + q


def update(
    x: np.ndarray, p: np.ndarray, m: Measurement
) -> tuple[np.ndarray, np.ndarray]:
    """EKF measurement update (Joseph form)."""
    s = float(m.h @ p @ m.h) + m.r
    k = p @ m.h / s
    x = x + k * (m.z - float(m.h @ x))
    a = np.eye(3) - np.outer(k, m.h)
    return x, a @ p @ a.T + m.r * np.outer(k, k)


def run(
    x0: np.ndarray,
    p0: np.ndarray,
    t_out: Sequence[float] | np.ndarray,
    meas: Sequence[Measurement],
    q_g: float,
    t0: float = 0.0,
    q_theta: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Filter from ``t0``; return states and covariances at ``t_out``.

    Measurements at a time are applied before the state is recorded there.
    """
    by_t: dict[float, list[Measurement]] = {}
    for m in meas:
        by_t.setdefault(float(m.t), []).append(m)
    times = sorted({float(t) for t in t_out} | set(by_t))
    want = {float(t) for t in t_out}
    x, p, t = np.asarray(x0, float).copy(), np.asarray(p0, float).copy(), t0
    xs: dict[float, np.ndarray] = {}
    ps: dict[float, np.ndarray] = {}
    for tk in times:
        while tk - t > 1e-9:
            dt = min(MAX_STEP_MIN, tk - t)
            x, p = predict(x, p, dt, q_g, q_theta)
            t += dt
        for m in by_t.get(tk, []):
            x, p = update(x, p, m)
        if tk in want:
            xs[tk], ps[tk] = x.copy(), p.copy()
    keys = [float(t) for t in t_out]
    return np.array([xs[k] for k in keys]), np.array([ps[k] for k in keys])


def scale_orbit(x: np.ndarray, c: float) -> np.ndarray:
    """Map ``(L, G, θ) → (cL, cG, θ − ln c)`` in state coordinates."""
    lc = np.log(c)
    return np.array([x[0] + lc, x[1] + lc, x[2] - lc])


def observability_matrix(
    x0: np.ndarray,
    times: Sequence[float] | np.ndarray,
    hs: Sequence[np.ndarray],
) -> np.ndarray:
    """Rows ``h_j Φ(t_j, 0)`` of the noise-free linearisation along ``x0``.

    ``Φ`` is the state-transition matrix of the linearised process model,
    accumulated in sub-steps of at most :data:`MAX_STEP_MIN`.
    """
    order = np.argsort(times)
    x, phi, t = np.asarray(x0, float).copy(), np.eye(3), 0.0
    rows: list[np.ndarray] = [np.zeros(3)] * len(times)
    for j in order:
        while times[j] - t > 1e-9:
            dt = min(MAX_STEP_MIN, times[j] - t)
            x, f = propagate(x, dt)
            phi = f @ phi
            t += dt
        rows[j] = hs[j] @ phi
    return np.array(rows)


SYMMETRY = np.array([1.0, 1.0, -1.0])
"""Tangent of the scale orbit (the same at every state)."""


def log_relative_growth_sd(p: np.ndarray) -> float:
    """Posterior SD of ``ln(G/L) = x[1] − x[0]``; scale-invariant."""
    g = np.array([-1.0, 1.0, 0.0])
    return float(np.sqrt(g @ p @ g))
