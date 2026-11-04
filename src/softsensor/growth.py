"""ΔL-law growth fits on the microscope medians.

Model on a time window: ``L(t) = L0 + G·(t − t_lag)``, with L0 the median of
the strike's first post-seeding sample and G, t_lag from ordinary least
squares of the window's medians on t. Uncertainty two ways:

- OLS: t-distribution CI on G from the residuals of the window medians;
- bootstrap: crystals resampled with replacement within every sample
  (L0 sample included), medians and fit recomputed. This covers the
  operator-chosen-crystal sampling only, not model error or clustering
  by photo.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy import stats

from softsensor.data import Sample


@dataclass(frozen=True, slots=True)
class LineFit:
    """ΔL-law fit on one window."""

    g: float
    """Growth rate, µm/min."""
    g_ci: tuple[float, float]
    """OLS 95 % CI on G (nan when n = 2)."""
    t_lag: float
    """Time (min since seeding) at which the fitted line equals L0."""
    l0: float
    n: int


def fit_line(t: np.ndarray, size: np.ndarray, l0: float) -> LineFit:
    """OLS ``size = a + G·t``; ``t_lag = (L0 − a) / G``."""
    n = len(t)
    g, a = np.polyfit(t, size, 1)
    if n > 2:
        resid = size - (a + g * t)
        se = np.sqrt(resid @ resid / (n - 2) / np.sum((t - t.mean()) ** 2))
        half = float(stats.t.ppf(0.975, n - 2) * se)
        ci = (float(g) - half, float(g) + half)
    else:
        ci = (float("nan"), float("nan"))
    return LineFit(float(g), ci, float((l0 - a) / g), l0, n)


def window(samples: Sequence[Sample], lo: float, hi: float) -> list[Sample]:
    """Samples with ``lo ≤ t ≤ hi`` (min since seeding)."""
    return [s for s in samples if lo <= s.t_min <= hi]


def fit_window(samples: Sequence[Sample], lo: float, hi: float) -> LineFit:
    """ΔL-law fit on the window medians; L0 = first sample's median."""
    w = window(samples, lo, hi)
    t = np.array([s.t_min for s in w])
    med = np.array([s.median_um for s in w])
    return fit_line(t, med, samples[0].median_um)


def bootstrap_window(
    samples: Sequence[Sample],
    lo: float,
    hi: float,
    rng: np.random.Generator,
    n_boot: int = 2000,
) -> np.ndarray:
    """Bootstrap draws ``(G, t_lag)`` of :func:`fit_window`, shape (n, 2)."""
    w = window(samples, lo, hi)
    t = np.array([s.t_min for s in w])
    out = np.empty((n_boot, 2))
    for i in range(n_boot):
        l0 = float(
            np.median(
                rng.choice(samples[0].sizes_um, len(samples[0].sizes_um))
            )
        )
        med = np.array(
            [np.median(rng.choice(s.sizes_um, len(s.sizes_um))) for s in w]
        )
        f = fit_line(t, med, l0)
        out[i] = f.g, f.t_lag
    return out
