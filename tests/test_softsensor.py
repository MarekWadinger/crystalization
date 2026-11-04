"""Soft sensor: scale symmetry, observability, EKF behaviour, growth fits."""

from __future__ import annotations

from dataclasses import astuple

import numpy as np
import pytest

from softsensor import ekf
from softsensor import evaluate as ev
from softsensor.data import Sample, microscope_samples, traced_frames
from softsensor.growth import bootstrap_window, fit_window

THETA_PRIOR_SD = 0.16


def _truth(x0: np.ndarray, times: np.ndarray) -> np.ndarray:
    """Noise-free states at ``times`` (min) from ``x0`` at t = 0."""
    out, x, t = [], x0.copy(), 0.0
    for tk in times:
        x, _ = ekf.propagate(x, tk - t)
        t = tk
        out.append(x.copy())
    return np.array(out)


def _filter(
    theta_true: float, anchor: bool, seed: int = 0
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """EKF with diffuse ln L and G priors on a linear-growth strike."""
    rng = np.random.default_rng(seed)
    x_true0 = np.array([np.log(40.0), np.log(4.0), theta_true])
    times = np.arange(1.0, 121.0)
    xt = _truth(x_true0, times)
    meas = [
        ekf.Measurement(
            t, ekf.CAMERA_H, xk[0] + xk[2] + rng.normal(0, 0.1), 0.01
        )
        for t, xk in zip(times, xt, strict=True)
    ]
    if anchor:
        meas.append(
            ekf.Measurement(60.0, ekf.ANCHOR_H, float(xt[59, 0]), 0.01)
        )
    x0 = np.array([np.log(40.0), np.log(4.0), 0.0])
    p0 = np.diag([10.0**2, 10.0**2, THETA_PRIOR_SD**2])
    xs, ps = ekf.run(x0, p0, times, meas, q_g=1e-3)
    return xt, xs, ps


# --- observability -------------------------------------------------------


@pytest.mark.parametrize("c", [0.5, 1.7, 3.0])
def test_scale_orbit_camera_outputs_identical_anchor_differs(c: float) -> None:
    # Arrange
    x = np.array([np.log(35.0), np.log(3.5), 0.1])
    times = np.arange(1.0, 90.0)
    # Act
    a, b = _truth(x, times), _truth(ekf.scale_orbit(x, c), times)
    # Assert: camera y = ln L + θ identical, anchor z = ln L shifted by ln c
    np.testing.assert_allclose(a @ ekf.CAMERA_H, b @ ekf.CAMERA_H, atol=1e-12)
    np.testing.assert_allclose(b @ ekf.ANCHOR_H - a @ ekf.ANCHOR_H, np.log(c))
    # ... and G/L is the same on both trajectories
    np.testing.assert_allclose(
        a[:, 1] - a[:, 0], b[:, 1] - b[:, 0], atol=1e-12
    )


def test_observability_camera_only_rank2_null_is_scale_direction() -> None:
    # Arrange
    x0 = np.array([np.log(40.0), np.log(4.0), 0.0])
    times = list(np.arange(1.0, 61.0))
    # Act
    o = ekf.observability_matrix(x0, times, [ekf.CAMERA_H] * len(times))
    sv = np.linalg.svd(o, compute_uv=False)
    null = np.linalg.svd(o)[2][-1]
    d = ekf.SYMMETRY
    # Assert
    assert np.linalg.matrix_rank(o, tol=1e-9 * sv[0]) == 2
    np.testing.assert_allclose(
        abs(null @ d) / np.linalg.norm(d), 1.0, atol=1e-9
    )


def test_observability_one_anchor_restores_full_rank() -> None:
    # Arrange
    x0 = np.array([np.log(40.0), np.log(4.0), 0.0])
    times = list(np.arange(1.0, 61.0)) + [30.0]
    hs = [ekf.CAMERA_H] * 60 + [ekf.ANCHOR_H]
    # Act
    o = ekf.observability_matrix(x0, times, hs)
    # Assert
    assert np.linalg.matrix_rank(o) == 3


def test_ekf_without_anchor_theta_stays_at_prior_but_g_over_l_learned() -> (
    None
):
    # Arrange / Act
    xt, xs, ps = _filter(theta_true=0.2, anchor=False)
    p0 = np.diag([100.0, 100.0, THETA_PRIOR_SD**2])
    # Assert: θ posterior SD at its prior (no information from the camera)
    assert np.sqrt(ps[-1, 2, 2]) == pytest.approx(THETA_PRIOR_SD, rel=1e-3)
    # ln(G/L) posterior SD far below its prior; estimate matches truth
    sd_rel_prior = ekf.log_relative_growth_sd(p0)
    sd_rel_post = ekf.log_relative_growth_sd(ps[-1])
    assert sd_rel_post < sd_rel_prior / 50
    assert xs[-1, 1] - xs[-1, 0] == pytest.approx(
        xt[-1, 1] - xt[-1, 0], abs=0.05
    )


def test_ekf_without_anchor_absolute_size_off_by_theta() -> None:
    # The camera fixes ln L + θ; with θ at its prior mean 0 the size
    # estimate carries the whole offset θ_true (scale symmetry).
    # Arrange / Act
    xt, xs, _ = _filter(theta_true=0.3, anchor=False)
    # Assert: L and G both carry the factor c = exp(θ_true)
    assert xs[-1, 0] - xt[-1, 0] == pytest.approx(0.3, abs=0.05)
    assert xs[-1, 1] - xt[-1, 1] == pytest.approx(0.3, abs=0.05)


def test_ekf_one_anchor_collapses_theta_and_fixes_size() -> None:
    # Arrange / Act
    xt, xs, ps = _filter(theta_true=0.3, anchor=True)
    sd_theta = np.sqrt(ps[-1, 2, 2])
    # Assert
    assert sd_theta < 0.6 * THETA_PRIOR_SD
    assert abs(xs[-1, 2] - 0.3) < 3 * sd_theta
    assert abs(xs[-1, 0] - xt[-1, 0]) < 0.1


# --- growth fits ---------------------------------------------------------


def _line_samples(g: float, t_lag: float, l0: float) -> list[Sample]:
    rng = np.random.default_rng(1)
    out = [Sample("s0", 0.0, l0 * np.exp(rng.normal(0, 0.05, 41)))]
    for i, t in enumerate([30.0, 45.0, 60.0, 80.0, 100.0]):
        size = l0 + g * (t - t_lag)
        out.append(
            Sample(f"s{i + 1}", t, size * np.exp(rng.normal(0, 0.05, 41)))
        )
    return out


def test_fit_window_recovers_growth_rate_and_lag() -> None:
    # Arrange
    s = _line_samples(g=4.0, t_lag=12.0, l0=30.0)
    # Act
    f = fit_window(s, 25.0, 105.0)
    boot = bootstrap_window(s, 25.0, 105.0, np.random.default_rng(2), 300)
    lo, hi = np.percentile(boot[:, 0], [2.5, 97.5])
    # Assert
    assert f.g == pytest.approx(4.0, rel=0.05)
    assert f.t_lag == pytest.approx(12.0, abs=3.0)
    assert f.g_ci[0] < 4.0 < f.g_ci[1]
    assert lo < 4.0 < hi


def test_curve_rate_is_slope_for_constant_relative_growth() -> None:
    # Arrange: ln L linear in t -> L' = L · k
    t = np.array([0.0, 50.0, 100.0])
    c = ev.Curve(t, np.log(20.0) + 0.02 * t)
    # Act
    g = c.rate(np.array([50.0]))
    # Assert (central difference of an exponential, ±10 min)
    expected = 20.0 * (np.exp(0.02 * 60) - np.exp(0.02 * 40)) / 20.0
    np.testing.assert_allclose(g, expected)


# --- decision rule -------------------------------------------------------


def test_first_flag_needs_persistence() -> None:
    # Arrange
    t = np.arange(30.0)
    cond = np.zeros(30, bool)
    cond[3:8] = True  # 5-min blip: not a flag
    cond[12:30] = True
    # Act
    tf = ev.first_flag(t, cond, persist=10)
    # Assert: decided at the 10th consecutive minute of the second run
    assert tf == 21.0
    assert np.isnan(ev.first_flag(t, np.zeros(30, bool)))


def test_truth_flags_ignore_samples_below_camera_floor() -> None:
    # Arrange: test strike tiny early (below floor), 50 % larger later
    nominal = ev.Curve(np.array([0.0, 100.0]), np.log([30.0, 300.0]))
    test = [
        Sample("a", 5.0, np.array([10.0])),
        Sample(
            "b", 60.0, np.array([1.5 * float(np.exp(nominal.ln_size(60.0)))])
        ),
    ]
    # Act
    slow, fast = ev.truth_flags(test, nominal)
    # Assert
    assert np.isnan(slow)
    assert fast == 60.0


# --- data ----------------------------------------------------------------


def test_microscope_samples_match_dataset_readme() -> None:
    # Act
    ms = microscope_samples()
    # Assert: README table (pre-seed sample excluded), times from the sidecar
    assert [s.sample_id for s in ms["b1"]][0] == "b1-s03"
    b1 = {s.sample_id: s for s in ms["b1"]}
    assert b1["b1-s05"].t_min == pytest.approx(37.45, abs=0.01)
    assert round(b1["b1-s10"].median_um) == 483
    assert len(ms["b2"]) == 8
    assert ms["b2"][0].t_min == 0.0


def test_real_camera_uses_only_early_b1_chord_frames() -> None:
    # Act
    meas = ev.real_camera(traced_frames("chord", "b1"), 0.18)
    # Assert: 2 readers x 3 frames x 2 sample times, all <= 62 min
    assert len(meas) == 12
    assert max(m.t for m in meas) <= ev.REAL_T_MAX_MIN


# --- round 2: scale-free flag, anchor-only reference, growth age ---------


def test_scale_free_flag_invariant_to_theta_but_size_flag_is_not() -> None:
    # Arrange: b2 as test strike, b1 as nominal; identical camera noise
    ms = microscope_samples()
    nominal, truth = (ev.Curve.from_samples(ms[b]) for b in ("b1", "b2"))
    test = ev.eval_samples(ms["b2"])
    runs = []
    # Act
    for theta in (-0.3, 0.0, 0.3):
        meas = ev.simulate_camera(truth, theta, 0.18, np.random.default_rng(3))
        runs.append(
            ev.run_estimator(meas, nominal, test, truth, 0.1, truth.t[-1])
        )
    rel = {(r.t_rel_slower, r.t_rel_faster) for r in runs}
    size = [(r.t_slower, r.t_faster) for r in runs]
    # Assert: one scale-free outcome, and it is a real flag (not vacuous)
    assert len({str(x) for x in rel}) == 1
    assert any(np.isfinite(v) for v in next(iter(rel)))
    # the size flag moves with θ_true (it depends on scale)
    assert len({str(x) for x in size}) > 1


@pytest.mark.parametrize("mode", ev.ANCHOR_MODES)
def test_anchor_reference_uses_no_camera_data(mode: str) -> None:
    # Arrange
    ms = microscope_samples()
    nominal, truth = (ev.Curve.from_samples(ms[b]) for b in ("b1", "b2"))
    a = ev.anchor_sample(ms["b2"])
    anchor = ev.anchor_measurement(a, 0.05)
    cam = ev.simulate_camera(truth, 0.2, 0.1, np.random.default_rng(0))
    cam2 = ev.simulate_camera(truth, -0.4, 0.3, np.random.default_rng(9))
    test = ev.eval_samples(ms["b2"])

    def ref(meas: list[ekf.Measurement]) -> ev.Scores:
        return ev.anchor_reference(
            meas, nominal, test, truth, truth.t[-1], mode
        )

    # Act
    alone, with_cam, with_other = (
        ref([anchor]),
        ref([*cam, anchor]),
        ref([anchor, *cam2]),
    )
    # Assert: camera rows change nothing (nan-aware equality)
    np.testing.assert_equal(astuple(alone), astuple(with_cam))
    np.testing.assert_equal(astuple(alone), astuple(with_other))
    # ... and the anchor does change it (it is not the nominal curve)
    base = ev.nominal_baseline(nominal, test, truth, truth.t[-1])
    assert alone.log_rmse != pytest.approx(base.log_rmse)


@pytest.mark.parametrize("mode", ev.ANCHOR_MODES)
def test_anchor_reference_passes_through_anchor(mode: str) -> None:
    # Arrange
    ms = microscope_samples()
    nominal, truth = (ev.Curve.from_samples(ms[b]) for b in ("b1", "b2"))
    a = ev.anchor_sample(ms["b2"])
    # Act: score at the anchor sample itself, noise-free anchor
    s = ev.anchor_reference(
        [ev.anchor_measurement(a)], nominal, [a], truth, truth.t[-1], mode
    )
    # Assert
    assert s.log_rmse == pytest.approx(0.0, abs=1e-9)


def test_growth_age_defined_on_monotone_part_only() -> None:
    # Arrange: grows to 400 µm at 100 min, then declines
    c = ev.Curve(
        np.array([0.0, 50.0, 100.0, 150.0]), np.log([20, 100, 400, 350])
    )
    # Act
    tau = c.growth_age(np.log([20.0, 100.0, 200.0, 400.0, 410.0, 10.0]))
    # Assert
    np.testing.assert_allclose(tau[:4], [0.0, 50.0, 75.0, 100.0])
    assert np.isnan(tau[4]) and np.isnan(tau[5])


def test_scenarios_bias_the_simulated_signal_as_specified() -> None:
    # Arrange
    truth = ev.Curve(np.array([0.0, 170.0]), np.log([20.0, 500.0]))

    def sim(scen: ev.Scenario = ev.MATCHED) -> list[ekf.Measurement]:
        return ev.simulate_camera(
            truth, 0.0, 0.1, np.random.default_rng(1), scen
        )

    base = sim()
    # Act
    beta = sim(ev.Scenario("b", kappa=0.3))
    ramp = sim(ev.Scenario("r", ramp=0.5))
    t = np.array([m.t for m in base])
    dy_beta = np.array([b.z - m.z for b, m in zip(beta, base, strict=True)])
    dy_ramp = np.array([r.z - m.z for r, m in zip(ramp, base, strict=True)])
    # Assert: β = κ ln(L/L_ref); ramp = 0 before, −0.5 after the packing span
    np.testing.assert_allclose(
        dy_beta, 0.3 * (truth.ln_size(t) - np.log(ev.L_REF_UM)), atol=1e-12
    )
    lo, hi = ev.PACKING_SPAN_MIN
    np.testing.assert_allclose(dy_ramp[t <= lo], 0.0, atol=1e-12)
    np.testing.assert_allclose(dy_ramp[t >= hi], -0.5, atol=1e-12)
