"""Leave-one-strike-out evaluation of the growth EKF on the 2026-10-30 run.

Truth is the microscope median per sample (AI transcription), interpolated
linearly in ln L between samples. Two camera signals:

- SIMULATED: ``y_k = ln L_micro(t_k) + β(L) + θ_k + v_k`` at 1/min while the
  true size is at least :data:`L_MIN_UM`; θ_0 ~ N(0, THETA_SD²); β = 0 and
  θ constant unless a :class:`Scenario` says otherwise.
- REAL: per (frame, reader) medians of the blind AI chord traces of b1.

References without camera: the nominal curve (the other strike's
interpolated medians) and the anchor-only reference (the nominal curve
shifted in ln L to pass through the microscope anchor).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from softsensor import ekf
from softsensor.data import Sample, TracedFrame

# Analysis constants. Sources: the reframe brief (measurement model, scratch
# estimates) unless stated; none is an optical value of the installation.
L_MIN_UM = 40.0
"""CHOICE: camera used only when L ≥ 40 µm (brief: resolution floor 3 px
≈ 11–12 µm, so use L ≳ 30–40 µm)."""
THETA_SD = 0.16
"""Prior SD of θ = ln(λ·b_sel) (brief, inference)."""
ANCHOR_SD = 0.10
"""SD of a microscope anchor in ln (brief: 0.06–0.13, bootstrap, scratch)."""
SIGMA_V = (0.10, 0.18)
"""Per-frame camera noise in ln (brief: outline 0.10, chord 0.18; scratch)."""
LNL0_SD = 1.0
"""CHOICE: prior SD of ln L at seeding (seeds 10–33 µm on this run)."""
LNG0_SD = 1.0
"""CHOICE: prior SD of ln G at seeding (a factor e around the nominal)."""
ANCHOR_AFTER_MIN = 30.0
"""CHOICE: the anchor is the first microscope sample at t ≥ 30 min."""
FLAG_DELTA = float(np.log(1.2))
"""CHOICE: off-nominal when size (or G/L) differs by > 20 %."""
FLAG_PERSIST_MIN = 10
"""CHOICE: the flag condition must hold on 10 consecutive 1-min points."""
Z95 = 1.96
RATE_HALF_MIN = 10.0
"""Half-width (min) of the central difference defining a growth rate."""
Q_GRID = tuple(float(q) for q in np.logspace(-5, 1, 13))
"""Candidate random-walk intensities of ln G, 1/min."""
REAL_T_MAX_MIN = 62.0
"""CHOICE: REAL traced chords used only up to the 60-min sample's frames
(brief: they track the microscope to ≈200 µm, ≤ 60 min, biased low after)."""

# Robustness scenarios (SIMULATED only).
L_REF_UM = 100.0
"""CHOICE: reference size of the size-dependent bias β(L) = κ ln(L/L_ref)."""
PACKING_RATIO = 1.75
"""Midpoint of the traced lab/camera ratio 1.5–2.0 at 122–170 min
(``scripts/traced_vs_lab.py``, chords and outlines, p50 and p90), up from
≈ 1.0 at 37–60 min."""
PACKING_SPAN_MIN = (60.0, 122.0)
"""Interval over which that ratio rose (last k ≈ 1 sample, first packed)."""
THETA_RW_Q = float(
    np.log(PACKING_RATIO) ** 2 / (PACKING_SPAN_MIN[1] - PACKING_SPAN_MIN[0])
)
"""θ random-walk intensity (1/min) whose SD over the packing span equals
ln 1.75."""
Q_THETA_SMALL = 1e-3
"""CHOICE: the 'small Q_θ > 0' of the filter variant, 1/min."""


@dataclass(frozen=True, slots=True)
class Scenario:
    """Deviation of the SIMULATED camera from the filter's model."""

    name: str
    kappa: float = 0.0
    """β(L) = κ ln(L / L_REF_UM)."""
    theta_q: float = 0.0
    """θ_true random walk, variance per minute."""
    ramp: float = 0.0
    """θ_true falls linearly by ``ramp`` over PACKING_SPAN_MIN."""


MATCHED = Scenario("matched model")


@dataclass(frozen=True, slots=True)
class Curve:
    """Piecewise-linear ln L(t) through a strike's microscope medians."""

    t: np.ndarray
    ln_l: np.ndarray

    @classmethod
    def from_samples(cls, samples: Sequence[Sample]) -> Curve:
        return cls(
            np.array([s.t_min for s in samples]),
            np.log([s.median_um for s in samples]),
        )

    def ln_size(self, t: np.ndarray | float) -> np.ndarray:
        """ln L at t (flat outside the sampled range)."""
        return np.interp(t, self.t, self.ln_l)

    def rate(self, t: np.ndarray | float) -> np.ndarray:
        """Growth rate (µm/min): central difference ± RATE_HALF_MIN, clipped;
        0 far outside the sampled range (flat extrapolation)."""
        t = np.asarray(t, float)
        lo = np.clip(t - RATE_HALF_MIN, self.t[0], self.t[-1])
        hi = np.clip(t + RATE_HALF_MIN, self.t[0], self.t[-1])
        span = np.where(hi > lo, hi - lo, 1.0)
        return (np.exp(self.ln_size(hi)) - np.exp(self.ln_size(lo))) / span

    def ln_rel_rate(self, t: np.ndarray | float) -> np.ndarray:
        """ln(G/L) at t; nan where the curve does not grow."""
        g = self.rate(t)
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where(g > 0, np.log(g), np.nan) - self.ln_size(t)

    @property
    def mean_rate(self) -> float:
        """(L_end − L_first) / duration, µm/min."""
        size = np.exp(self.ln_l)
        return float((size[-1] - size[0]) / (self.t[-1] - self.t[0]))

    def growth_age(self, ln_l: np.ndarray | float) -> np.ndarray:
        """Growth age: the t at which this curve reaches ln L.

        Defined on the curve's monotone part only (first sample up to its
        maximum, kept where strictly increasing); nan outside that range.
        """
        top = int(np.argmax(self.ln_l))
        t, v = self.t[: top + 1], self.ln_l[: top + 1]
        keep = np.concatenate([[True], v[1:] > np.maximum.accumulate(v)[:-1]])
        t, v = t[keep], v[keep]
        x = np.asarray(ln_l, float)
        tau = np.interp(x, v, t)
        return np.where((x >= v[0]) & (x <= v[-1]), tau, np.nan)


def prior(nominal: Curve) -> tuple[np.ndarray, np.ndarray]:
    """Prior at seeding from the nominal strike (G median = its mean rate)."""
    x0 = np.array([nominal.ln_l[0], np.log(nominal.mean_rate), 0.0])
    return x0, np.diag([LNL0_SD**2, LNG0_SD**2, THETA_SD**2])


def anchor_sample(samples: Sequence[Sample]) -> Sample:
    """First sample at t ≥ :data:`ANCHOR_AFTER_MIN`."""
    return next(s for s in samples if s.t_min >= ANCHOR_AFTER_MIN)


def eval_samples(samples: Sequence[Sample]) -> list[Sample]:
    """Held-out evaluation samples: t ≥ ANCHOR_AFTER_MIN, anchor excluded."""
    a = anchor_sample(samples)
    return [s for s in samples if s.t_min >= ANCHOR_AFTER_MIN and s is not a]


def simulate_camera(
    truth: Curve,
    theta: float,
    sigma_v: float,
    rng: np.random.Generator,
    scen: Scenario = MATCHED,
) -> list[ekf.Measurement]:
    """SIMULATED camera: one ln-median per minute while L ≥ L_MIN_UM."""
    t = np.arange(1.0, np.floor(truth.t[-1]) + 1.0)
    v = rng.normal(0.0, sigma_v, len(t))
    walk = np.cumsum(rng.normal(0.0, np.sqrt(scen.theta_q), len(t)))
    lo, hi = PACKING_SPAN_MIN
    ramp = scen.ramp * np.clip((t - lo) / (hi - lo), 0.0, 1.0)
    ln_l = truth.ln_size(t)
    y = ln_l + scen.kappa * (ln_l - np.log(L_REF_UM)) + theta + walk - ramp + v
    vis = ln_l >= np.log(L_MIN_UM)
    return [
        ekf.Measurement(float(tk), ekf.CAMERA_H, float(yk), sigma_v**2)
        for tk, yk in zip(t[vis], y[vis], strict=True)
    ]


def real_camera(
    frames: Sequence[TracedFrame], sigma_v: float
) -> list[ekf.Measurement]:
    """REAL camera: ln of each (frame, reader) median chord, t ≤ REAL_T_MAX_MIN."""
    return [
        ekf.Measurement(
            f.t_min, ekf.CAMERA_H, float(np.log(f.median_um)), sigma_v**2
        )
        for f in frames
        if f.t_min <= REAL_T_MAX_MIN
    ]


def anchor_measurement(s: Sample, noise: float = 0.0) -> ekf.Measurement:
    """Microscope anchor ``z = ln median + noise`` with R = ANCHOR_SD²."""
    return ekf.Measurement(
        s.t_min, ekf.ANCHOR_H, float(np.log(s.median_um)) + noise, ANCHOR_SD**2
    )


def first_flag(
    t: np.ndarray, cond: np.ndarray, persist: int = FLAG_PERSIST_MIN
) -> float:
    """Time at which ``cond`` has held on ``persist`` consecutive grid
    points (the online decision time); nan if never."""
    run = 0
    for tk, c in zip(t, cond, strict=True):
        run = run + 1 if c else 0
        if run >= persist:
            return float(tk)
    return float("nan")


def truth_flags(test: Sequence[Sample], nominal: Curve) -> tuple[float, float]:
    """First microscope sample where the test strike is > δ slower / faster.

    Only samples the camera could see (median ≥ L_MIN_UM) count, so seed
    size differences before growth are not called growth deviations.
    """
    vis = [s for s in test if s.median_um >= L_MIN_UM]
    d = np.array([np.log(s.median_um) - nominal.ln_size(s.t_min) for s in vis])
    t = np.array([s.t_min for s in vis])
    slow, fast = t[d < -FLAG_DELTA], t[d > FLAG_DELTA]
    nan = float("nan")
    return (
        float(slow[0]) if len(slow) else nan,
        float(fast[0]) if len(fast) else nan,
    )


def curve_flags(test: Curve, nominal: Curve) -> dict[str, float]:
    """Noise-free flags of the interpolated test curve (where ≥ L_MIN_UM)
    against the nominal, same rule as the estimator (δ, 10-point
    persistence on the 1-min grid, zero SD): the truth of the SIMULATED
    signal, for size and for ln(G/L)."""
    t = np.arange(np.ceil(test.t[0]), np.floor(test.t[-1]) + 1.0)
    vis = test.ln_size(t) >= np.log(L_MIN_UM)
    d = test.ln_size(t) - nominal.ln_size(t)
    dr = test.ln_rel_rate(t) - nominal.ln_rel_rate(t)
    with np.errstate(invalid="ignore"):
        return {
            "slower": first_flag(t, vis & (d < -FLAG_DELTA)),
            "faster": first_flag(t, vis & (d > FLAG_DELTA)),
            "rel_slower": first_flag(t, vis & (dr < -FLAG_DELTA)),
            "rel_faster": first_flag(t, vis & (dr > FLAG_DELTA)),
        }


@dataclass
class Scores:
    """Metrics of one estimate at the held-out microscope times, and flags."""

    log_rmse: float
    g_rmse: float
    """µm/min."""
    rel_g_rmse: float
    """Relative growth rate G/L, %/min."""
    t_slower: float
    t_faster: float
    """Size flags (min since seeding; nan = never)."""
    t_rel_slower: float
    t_rel_faster: float
    """Scale-free ln(G/L) flags."""
    tau_rmse: float
    """Growth-age RMSE (min) where τ̂ and τ are both defined."""
    tau_defined: int
    sd_theta_end: float = float("nan")


def assess(
    times: np.ndarray,
    ln_l: np.ndarray,
    g: np.ndarray,
    sd_ln_l: np.ndarray,
    sd_rel: np.ndarray,
    test: Sequence[Sample],
    truth: Curve,
    nominal: Curve,
    flag_mask: np.ndarray,
) -> Scores:
    """Score an estimate ``(ln L̂, Ĝ)`` on ``times``.

    Metrics at the test samples' times; flags on ``times[flag_mask]``
    (the 1-min grid, optionally truncated). Size flag:
    ``d = ln L̂ − ln L_nom``, slower when ``d + Z95·sd < −δ``. Scale-free
    flag: same rule on ``ln(Ĝ/L̂) − ln(G_nom/L_nom)``.
    """
    t = np.array([s.t_min for s in test])
    idx = np.searchsorted(times, t)
    ln_true = np.log([s.median_um for s in test])
    g_true = truth.rate(t)
    e_ln = ln_l[idx] - ln_true
    e_g = g[idx] - g_true
    e_rel = 100 * (g[idx] / np.exp(ln_l[idx]) - g_true / np.exp(ln_true))
    tau_hat = nominal.growth_age(ln_l[idx])
    tau_err = tau_hat - nominal.growth_age(ln_true)
    ok = np.isfinite(tau_err)

    tf = times[flag_mask]
    d = ln_l[flag_mask] - nominal.ln_size(tf)
    sd = sd_ln_l[flag_mask]
    with np.errstate(invalid="ignore", divide="ignore"):
        rel_hat = np.where(g > 0, np.log(g), np.nan) - ln_l
        dr = rel_hat[flag_mask] - nominal.ln_rel_rate(tf)
        sdr = sd_rel[flag_mask]
        rel_slow = dr + Z95 * sdr < -FLAG_DELTA
        rel_fast = dr - Z95 * sdr > FLAG_DELTA
    return Scores(
        log_rmse=float(np.sqrt(np.mean(e_ln**2))),
        g_rmse=float(np.sqrt(np.mean(e_g**2))),
        rel_g_rmse=float(np.sqrt(np.mean(e_rel**2))),
        t_slower=first_flag(tf, d + Z95 * sd < -FLAG_DELTA),
        t_faster=first_flag(tf, d - Z95 * sd > FLAG_DELTA),
        t_rel_slower=first_flag(tf, rel_slow),
        t_rel_faster=first_flag(tf, rel_fast),
        tau_rmse=float(np.sqrt(np.mean(tau_err[ok] ** 2)))
        if ok.any()
        else float("nan"),
        tau_defined=int(ok.sum()),
    )


def _times(
    test: Sequence[Sample], t_end: float, t_flag_max: float
) -> tuple[np.ndarray, np.ndarray]:
    grid = np.arange(0.0, np.floor(t_end) + 1.0)
    times = np.unique(np.concatenate([grid, [s.t_min for s in test]]))
    return times, np.isin(times, grid) & (times <= t_flag_max)


def run_estimator(
    meas: Sequence[ekf.Measurement],
    nominal: Curve,
    test: Sequence[Sample],
    truth: Curve,
    q_g: float,
    t_end: float,
    q_theta: float = 0.0,
    t_flag_max: float = np.inf,
) -> Scores:
    """Run the EKF on one strike and score it (held-out times = ``test``)."""
    times, mask = _times(test, t_end, t_flag_max)
    x0, p0 = prior(nominal)
    xs, ps = ekf.run(x0, p0, times, meas, q_g, q_theta=q_theta)
    sd_rel = np.sqrt(ps[:, 0, 0] + ps[:, 1, 1] - 2 * ps[:, 0, 1])
    s = assess(
        times,
        xs[:, 0],
        np.exp(xs[:, 1]),
        np.sqrt(ps[:, 0, 0]),
        sd_rel,
        test,
        truth,
        nominal,
        mask,
    )
    s.sd_theta_end = float(np.sqrt(ps[-1, 2, 2]))
    return s


def nominal_baseline(
    nominal: Curve,
    test: Sequence[Sample],
    truth: Curve,
    t_end: float,
    t_flag_max: float = np.inf,
) -> Scores:
    """Operator expectation: the nominal curve, no data (never flags)."""
    times, mask = _times(test, t_end, t_flag_max)
    zero = np.zeros(len(times))
    return assess(
        times,
        nominal.ln_size(times),
        nominal.rate(times),
        zero,
        zero,
        test,
        truth,
        nominal,
        mask,
    )


ANCHOR_MODES = ("scale", "age")


def anchor_reference(
    meas: Sequence[ekf.Measurement],
    nominal: Curve,
    test: Sequence[Sample],
    truth: Curve,
    t_end: float,
    mode: str = "scale",
    t_flag_max: float = np.inf,
) -> Scores:
    """Anchor-only reference: the nominal curve made to pass through the
    microscope anchor. Camera rows of ``meas`` are ignored.

    - ``scale``: shifted in ln L by ``z − ln L_nom(t_a)`` (G scaled by the
      same factor, so G/L is the nominal one);
    - ``age``: shifted in time, ``L_nom(t − t_a + τ_a)`` with τ_a the
      nominal's growth age at the anchor (falls back to ``scale`` where τ_a
      is undefined).

    Before the (latest) anchor it is the nominal curve. Size flags use the
    anchor SD √R; the reference carries no other uncertainty.
    """
    if mode not in ANCHOR_MODES:
        raise ValueError(mode)
    anchors = [m for m in meas if np.array_equal(m.h, ekf.ANCHOR_H)]
    times, mask = _times(test, t_end, t_flag_max)
    t_eff, shift = times.copy(), np.zeros(len(times))
    sd = np.zeros(len(times))
    for m in sorted(anchors, key=lambda m: m.t):  # latest anchor wins
        after = times >= m.t
        tau_a = float(nominal.growth_age(m.z))
        if mode == "age" and np.isfinite(tau_a):
            t_eff[after], shift[after] = times[after] - m.t + tau_a, 0.0
        else:
            t_eff[after] = times[after]
            shift[after] = m.z - float(nominal.ln_size(m.t))
        sd[after] = np.sqrt(m.r)
    return assess(
        times,
        nominal.ln_size(t_eff) + shift,
        nominal.rate(t_eff) * np.exp(shift),
        sd,
        np.zeros(len(times)),
        test,
        truth,
        nominal,
        mask,
    )


def _draws(seed: int) -> tuple[float, float, np.random.Generator]:
    """θ_0, anchor noise w and the camera-noise stream of one seed.

    θ_0 and w come from their own stream, so every camera variant (σ_v,
    scenario) of a seed shares them.
    """
    r = np.random.default_rng([seed, 0])
    theta, w = r.normal(0.0, THETA_SD), r.normal(0.0, ANCHOR_SD)
    return theta, w, np.random.default_rng([seed, 1])


def simulated_measurements(
    test_samples: Sequence[Sample],
    sigma_v: float,
    anchored: bool,
    seed: int,
    scen: Scenario = MATCHED,
) -> list[ekf.Measurement]:
    """SIMULATED camera (+ anchor) measurements of one seed."""
    theta, w, rng = _draws(seed)
    meas = simulate_camera(
        Curve.from_samples(test_samples), theta, sigma_v, rng, scen
    )
    if anchored:
        meas.append(anchor_measurement(anchor_sample(test_samples), w))
    return meas


def simulated_runs(
    test_samples: Sequence[Sample],
    nominal: Curve,
    q_g: float,
    sigma_v: float,
    anchored: bool,
    seeds: Sequence[int],
    scen: Scenario = MATCHED,
    q_theta: float = 0.0,
) -> list[Scores]:
    """EKF on the SIMULATED camera of the test strike, one run per seed."""
    truth = Curve.from_samples(test_samples)
    test = eval_samples(test_samples)
    return [
        run_estimator(
            simulated_measurements(
                test_samples, sigma_v, anchored, seed, scen
            ),
            nominal,
            test,
            truth,
            q_g,
            truth.t[-1],
            q_theta,
        )
        for seed in seeds
    ]


def anchor_reference_runs(
    test_samples: Sequence[Sample],
    nominal: Curve,
    seeds: Sequence[int],
    mode: str = "scale",
) -> list[Scores]:
    """Anchor-only reference with each seed's anchor noise (as the EKF)."""
    truth = Curve.from_samples(test_samples)
    test = eval_samples(test_samples)
    a = anchor_sample(test_samples)
    return [
        anchor_reference(
            [anchor_measurement(a, _draws(seed)[1])],
            nominal,
            test,
            truth,
            truth.t[-1],
            mode,
        )
        for seed in seeds
    ]


def tune_q(
    train_samples: Sequence[Sample], sigma_v: float, seeds: Sequence[int]
) -> tuple[float, dict[float, float]]:
    """Q_G minimising mean anchored log-RMSE on the training strike
    (SIMULATED camera; the training strike is its own nominal)."""
    nominal = Curve.from_samples(train_samples)
    cost = {
        q: float(
            np.mean(
                [
                    s.log_rmse
                    for s in simulated_runs(
                        train_samples, nominal, q, sigma_v, True, seeds
                    )
                ]
            )
        )
        for q in Q_GRID
    }
    return min(cost, key=cost.__getitem__), cost
