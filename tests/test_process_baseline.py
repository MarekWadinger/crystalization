"""Process-signal baseline: plant supersaturation, growth law, k_g fit."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

from softsensor import evaluate as ev
from softsensor import process as pr

ROOT = Path(__file__).resolve().parents[1]


def _script():
    path = ROOT / "scripts" / "softsensor_process_baseline.py"
    spec = importlib.util.spec_from_file_location("process_baseline", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------- supersaturation formula


def test_solubility_matches_sheet_value_at_65c() -> None:
    # notes_data_lab.md §3c: "At 65 °C this gives 75.32."
    assert float(pr.sucrose_solubility(65.0)) == pytest.approx(75.32, abs=5e-3)


def test_supersaturation_hand_computed_seed_example() -> None:
    # Arrange: sheet worked example P 93, T 65, Bx 75 (notes §3c) by hand
    bsat = 64.397 + 0.07251 * 65 + 0.0020569 * 65**2 - 9.035e-6 * 65**3
    nw = 75 * 7 / 100 / 25  # 0.21
    sc = 0.5 * nw + 0.95 + 0.05 * 2.72 * (-nw)  # 1.02644
    hand = 75 * 93 * (100 - bsat) / (25 * bsat * sc * 100)
    # Act
    kp = float(pr.supersaturation(75.0, 93.0, 65.0))
    # Assert: equals the hand computation and the sheet's printed 0.89
    assert kp == pytest.approx(hand, rel=1e-12)
    assert round(kp, 2) == 0.89


def test_supersaturation_reproduces_sheet_and_dcs_values() -> None:
    # sheet: Bx 83 → 1.385 (T-SEED); DCS live 15.11.2025: Viskozita 81.5,
    # 69.5 °C, recipe purity 93.4 % → KP_akt 1.210 (plant DCS Q&A §2.2)
    assert float(pr.supersaturation(83.0, 93.0, 65.0)) == pytest.approx(
        1.385, abs=5e-4
    )
    assert float(pr.supersaturation(81.5, 93.4, 69.5)) == pytest.approx(
        1.210, abs=5e-3
    )


def test_exp_form_is_the_textbook_variant_and_lower() -> None:
    # The DCS live value rules out the exp form (1.126 vs 1.210 shown).
    kp_exp = float(pr.supersaturation(81.5, 93.4, 69.5, "exp"))
    assert kp_exp == pytest.approx(1.126, abs=5e-3)
    assert kp_exp < float(pr.supersaturation(81.5, 93.4, 69.5))
    with pytest.raises(ValueError):
        pr.saturation_coefficient(0.2, "power")


def test_lab_brix_purity_from_diluted_readings() -> None:
    # b1-s03: refract 39.52, polari 18.5, dilutions 2 / 4
    bx, p = pr.lab_brix_purity(39.52, 18.5, 2, 4)
    assert bx == pytest.approx(79.04)
    assert p == pytest.approx(100 * 74.0 / 79.04)


# --------------------------------------------------------- growth law


def test_growth_rate_is_zero_when_undersaturated() -> None:
    g = pr.growth_rate(np.array([0.9, 1.0, 1.2]), k_g=10.0, g=1.0)
    np.testing.assert_allclose(g, [0.0, 0.0, 2.0])


def test_integrate_size_constant_supersaturation_is_linear() -> None:
    t = np.linspace(0.0, 100.0, 1001)
    size = pr.integrate_size(t, np.full_like(t, 1.2), 13.0, 15.0, g=2.0)
    np.testing.assert_allclose(size, 13.0 + 15.0 * 0.2**2 * t, rtol=1e-12)


def test_integrate_size_linear_ramp_matches_analytic() -> None:
    # S = 1 + a t, g = 1: L = L0 + k a t² / 2 (trapezoid exact for linear)
    a, k, l0 = 0.01, 12.0, 10.0
    t = np.linspace(0.0, 120.0, 241)
    size = pr.integrate_size(t, 1.0 + a * t, l0, k)
    np.testing.assert_allclose(size, l0 + k * a * t**2 / 2, rtol=1e-12)


def test_no_growth_before_supersaturation_crosses_one() -> None:
    t = np.linspace(0.0, 60.0, 601)
    s = 0.95 + 0.002 * t  # crosses 1 at 25 min
    size = pr.integrate_size(t, s, 13.0, 20.0)
    assert np.all(size[t <= 25.0] == 13.0)
    assert size[-1] > 13.0


# ------------------------------------------------------ k_g recovery


def _synthetic() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    t = np.arange(0.0, 170.0 + 1e-9, 0.1)
    s = np.interp(
        t, [0, 16, 50, 80, 122, 170], [1.04, 1.05, 1.2, 1.35, 1.65, 2.2]
    )
    t_obs = np.array([2.5, 16.4, 37.5, 49.5, 60.5, 79.5, 96.5, 122.5])
    return t, s, t_obs


@pytest.mark.parametrize("g", [1.0, 2.7])
def test_fit_kg_recovers_true_value_noise_free(g: float) -> None:
    t, s, t_obs = _synthetic()
    k_true = 9.0
    l_obs = np.interp(t_obs, t, pr.integrate_size(t, s, 13.0, k_true, g))
    assert pr.fit_kg(t, s, 13.0, t_obs, l_obs, g) == pytest.approx(
        k_true, rel=1e-5
    )


def test_fit_kg_recovers_true_value_under_log_noise() -> None:
    t, s, t_obs = _synthetic()
    k_true = 9.0
    clean = np.interp(t_obs, t, pr.integrate_size(t, s, 13.0, k_true))
    rng = np.random.default_rng(7)
    est = [
        pr.fit_kg(
            t, s, 13.0, t_obs, clean * np.exp(rng.normal(0, 0.05, len(t_obs)))
        )
        for _ in range(50)
    ]
    assert np.median(est) == pytest.approx(k_true, rel=0.03)


# ---------------------------------------------------- seeding detection


def _dcs(n: int = 400) -> tuple[np.ndarray, ...]:
    t = np.arange(n) * 0.5  # 30 s samples, min
    stir = np.where((t >= 5) & (t < 180), 10.0, 0.0)
    steam = np.where(t >= 10, 100.0, 0.0)
    bx = np.full(n, 80.0)
    steam[(t >= 40) & (t < 50)] = 30.0  # seeding cut at 40 min, Bx 80
    bx[t >= 120] = 90.0
    steam[(t >= 170) & (t < 180)] = 0.0  # end-of-strike cut, Bx 90
    return t, steam, stir, bx


def test_detect_seeding_finds_steam_cut_and_rejects_strike_end() -> None:
    t, steam, stir, bx = _dcs()
    assert pr.detect_seeding(t, steam, stir, bx) == [40.0]
    # a strike whose seeding is outside the export (as b1 on 2026-02-04):
    # only the end-of-strike cut is left; the Brix gate rejects it
    steam[(t >= 40) & (t < 50)] = 100.0
    assert pr.detect_seeding(t, steam, stir, bx) == []
    assert pr.detect_seeding(t, steam, stir, bx, bx_max=np.inf) == [170.0]


def test_detect_seeding_needs_steam_held_open_first() -> None:
    t, steam, stir, bx = _dcs()
    steam[(t >= 10) & (t < 40)] = 60.0  # never fully open before the cut
    assert pr.detect_seeding(t, steam, stir, bx) == []


# ------------------------------------------- interim driver on real data


def test_lab_points_are_massecuite_samples_with_plant_purity() -> None:
    mod = _script()
    lab = mod.lab_points()
    assert {b: len(v) for b, v in lab.items()} == {"b1": 8, "b2": 7}
    pur = [p.purity for v in lab.values() for p in v]
    assert 91.0 <= min(pur) and max(pur) <= 94.0  # plant: purity 91–94 %
    assert mod.slurry_l0() == pytest.approx(13.0)


def test_anchor_noise_draws_match_the_ekf_rows() -> None:
    mod = _script()
    for seed in (1000, 1001, 1199):
        assert mod._anchor_w(seed) == ev._draws(seed)[1]


def test_interim_baseline_scores_same_held_out_samples_as_ekf() -> None:
    mod = _script()
    ms = mod.microscope_samples()
    fit = mod.run_pair(ms, mod.lab_points(), "b1", "b2", mod.Config())
    assert fit.k_g > 0
    assert np.isfinite(fit.unanchored.log_rmse)
    assert len(fit.anchored) == len(mod.EVAL_SEEDS)
    assert fit.unanchored.tau_defined <= len(ev.eval_samples(ms["b2"]))
