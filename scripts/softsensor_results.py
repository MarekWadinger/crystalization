"""Soft-sensor prototype results on the 2026-10-30 sampled run.

    uv run python scripts/softsensor_results.py

Writes ``docs/softsensor/results.md``: (1) microscope growth per strike
(ΔL-law fits, b1 vs b2), (2) observability and practical identifiability of
the growth EKF, (3) leave-one-strike-out evaluation with a SIMULATED camera
signal against camera-free references, (4) robustness to model mismatch,
(5) the REAL blind AI chord traces of b1. Every number in the file comes
from this run.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np

from softsensor import ekf
from softsensor import evaluate as ev
from softsensor.data import Sample, microscope_samples, traced_frames
from softsensor.growth import bootstrap_window, fit_window, window

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "softsensor" / "results.md"
CMD = "uv run python scripts/softsensor_results.py"
N_BOOT = 4000
TUNE_SEEDS = range(0, 50)
EVAL_SEEDS = range(1000, 1200)
WINDOWS = {
    # name: {strike: (lo, hi)} in min since seeding (inclusive)
    "supervisor window 37–122 min": {"b1": (36.0, 123.0)},
    "common window 30–97 min": {"b1": (29.0, 97.0), "b2": (29.0, 97.0)},
    "early 30–70 min": {"b1": (29.0, 70.0), "b2": (29.0, 70.0)},
    "late, ≥ 69 min, before tightening": {
        "b1": (69.0, 161.0),
        "b2": (68.0, 147.0),
    },
}


def _f(v: float, nd: int = 2) -> str:
    return "–" if not np.isfinite(v) else f"{v:.{nd}f}"


def _table(head: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def growth_section(
    ms: dict[str, list[Sample]], rng: np.random.Generator
) -> str:
    out = [
        "## 1. Microscope growth per strike (REAL microscope, AI transcription)",
        "",
        "Medians of the operator-chosen microscope chords per sample "
        "(`datasets/microscope_annotations.csv`, one AI reading; pre-seeding "
        "sample b1-s02 excluded). t = minutes since that strike's seeding "
        "(sidecar video seconds; b1 11:29:33, b2 15:22:00).",
        "",
    ]
    rows = []
    for b, ss in ms.items():
        for i, s in enumerate(ss):
            slope = (
                (s.median_um - ss[i - 1].median_um)
                / (s.t_min - ss[i - 1].t_min)
                if i
                else float("nan")
            )
            rows.append(
                [b, s.sample_id, _f(s.t_min, 1), len(s.sizes_um),
                 _f(s.median_um, 1), _f(slope)]
            )  # fmt: skip
    out += [
        _table(
            [
                "strike",
                "sample",
                "t (min)",
                "n",
                "median (µm)",
                "ΔL/Δt from previous sample (µm/min)",
            ],
            rows,
        ),  # fmt: skip
        "",
        "ΔL-law fit `L = L0 + G·(t − t_lag)` on a window; L0 = median of the "
        "strike's first post-seeding sample (b1-s03 at 2.5 min, b2-s02 at "
        "0 min); G and t_lag by OLS on the window medians. OLS CI: t-dist on "
        f"the residuals. Bootstrap: {N_BOOT} resamples of crystals within "
        "every sample (L0 sample included); percentile 95 % CI.",
        "",
    ]
    rows, draws = [], {}
    for name, per in WINDOWS.items():
        for b, (lo, hi) in per.items():
            f = fit_window(ms[b], lo, hi)
            bs = bootstrap_window(ms[b], lo, hi, rng, N_BOOT)
            draws[(name, b)] = bs[:, 0]
            g_lo, g_hi = np.percentile(bs[:, 0], [2.5, 97.5])
            l_lo, l_hi = np.percentile(bs[:, 1], [2.5, 97.5])
            ts = ", ".join(f"{s.t_min:.0f}" for s in window(ms[b], lo, hi))
            rows.append(
                [name, b, ts, _f(f.g), f"[{_f(f.g_ci[0])}, {_f(f.g_ci[1])}]",
                 f"[{_f(g_lo)}, {_f(g_hi)}]", _f(f.t_lag, 1),
                 f"[{_f(l_lo, 1)}, {_f(l_hi, 1)}]"]
            )  # fmt: skip
    out += [
        _table(
            [
                "window",
                "strike",
                "sample t (min)",
                "G (µm/min)",
                "G OLS 95 % CI",
                "G bootstrap 95 % CI",
                "t_lag (min)",
                "t_lag bootstrap 95 % CI",
            ],
            rows,
        ),  # fmt: skip
        "",
        "b1 − b2 difference of G, bootstrap (independent resamples):",
        "",
    ]
    rows = []
    for name in WINDOWS:
        if ("b2" in WINDOWS[name]) and ("b1" in WINDOWS[name]):
            d = draws[(name, "b1")] - draws[(name, "b2")]
            lo, hi = np.percentile(d, [2.5, 97.5])
            rows.append(
                [name, _f(float(np.median(d))), f"[{_f(lo)}, {_f(hi)}]",
                 _f(float(np.mean(d > 0)), 3)]
            )  # fmt: skip
    out += [
        _table(
            [
                "window",
                "median G_b1 − G_b2 (µm/min)",
                "95 % CI",
                "P(G_b1 > G_b2)",
            ],
            rows,
        ),  # fmt: skip
        "",
        "Same time since seeding: b2 median vs b1 interpolated (ln-linear "
        "between b1 samples) at b2's sample times.",
        "",
    ]
    b1 = ev.Curve.from_samples(ms["b1"])
    rows = [
        [_f(s.t_min, 1), _f(s.median_um, 1),
         _f(float(np.exp(b1.ln_size(s.t_min))), 1),
         _f(s.median_um / float(np.exp(b1.ln_size(s.t_min))))]
        for s in ms["b2"]
    ]  # fmt: skip
    out += [
        _table(
            ["t (min)", "b2 median (µm)", "b1 interpolated (µm)", "b2 / b1"],
            rows,
        ),  # fmt: skip
        "",
    ]
    return "\n".join(out)


def growth_age_note(ms: dict[str, list[Sample]]) -> str:
    b1, b2 = (ev.Curve.from_samples(ms[b]) for b in ("b1", "b2"))
    tau = b1.growth_age(np.log([483.0, 484.0, 485.5]))
    top1, top2 = np.exp(b1.ln_l.max()), np.exp(b2.ln_l.max())
    return "\n".join(
        [
            "Growth age τ̂ = the time at which the nominal curve reaches L̂, "
            "defined on the nominal's monotone part (first sample up to its "
            "maximum; the b1 decline 486 → 452 µm is cut). It is ill-"
            "conditioned on the b1 plateau: on the b1 curve τ(483 µm) = "
            f"{tau[0]:.1f} min, τ(484 µm) = {tau[1]:.1f} min, τ(485.5 µm) = "
            f"{tau[2]:.1f} min, so 1 % in size moves τ by tens of minutes. It "
            f"is undefined above the nominal's maximum (b1 {top1:.1f} µm, b2 "
            f"{top2:.1f} µm): with b2 as nominal, the b1 samples at 122–170 "
            "min have no growth age. τ RMSE is over the times where both τ̂ "
            "and τ are defined; the count is given.",
            "",
        ]
    )


def observability_section(
    ms: dict[str, list[Sample]], q: dict[tuple[str, float], float]
) -> str:
    x0 = np.array([np.log(40.0), np.log(4.0), 0.0])
    times = [float(t) for t in range(1, 61)]
    o_cam = ekf.observability_matrix(x0, times, [ekf.CAMERA_H] * 60)
    o_anc = ekf.observability_matrix(
        x0, [*times, 30.0], [ekf.CAMERA_H] * 60 + [ekf.ANCHOR_H]
    )
    sv_cam = np.linalg.svd(o_cam, compute_uv=False)
    sv_anc = np.linalg.svd(o_anc, compute_uv=False)
    null = np.linalg.svd(o_cam)[2][-1]
    null = null / null[0]

    nominal_b2 = ev.Curve.from_samples(ms["b2"])
    x_0, p_eval = ev.prior(nominal_b2)
    q_b1 = q[("b2", 0.10)]
    t_end = ms["b1"][-1].t_min
    rows = []
    for label, p0 in [
        ("diffuse ln L, ln G (SD 10)", np.diag([100.0, 100.0, ev.THETA_SD**2])),
        ("evaluation prior", p_eval),
    ]:  # fmt: skip
        for anchored in (False, True):
            sds = [
                np.sqrt(
                    ekf.run(
                        x_0,
                        p0,
                        [t_end],
                        ev.simulated_measurements(ms["b1"], 0.10, anchored, s),
                        q_b1,
                    )[1][-1, 2, 2]
                )
                for s in OBS_SEEDS
            ]
            rows.append(
                [label, "one (b1-s05)" if anchored else "none",
                 _f(ev.THETA_SD, 3), _f(float(np.mean(sds)), 4)]
            )  # fmt: skip

    # Practical identifiability: SD of ln(G/L) over time (LOSO priors/Q).
    grid = [20.0, 30.0, 40.0, 50.0, 60.0, 80.0, 100.0, 120.0, 140.0, 160.0]
    cols, diffs = {}, []
    for test, train in (("b1", "b2"), ("b2", "b1")):
        nominal = ev.Curve.from_samples(ms[train])
        t_out = [*grid, ms[test][-1].t_min]
        for sv in ev.SIGMA_V:
            sd = {}
            for anchored in (False, True):
                sd[anchored] = np.mean(
                    [
                        [
                            ekf.log_relative_growth_sd(pk)
                            for pk in ekf.run(
                                *ev.prior(nominal),
                                t_out,
                                ev.simulated_measurements(
                                    ms[test], sv, anchored, s
                                ),
                                q[(train, sv)],
                            )[1]
                        ]
                        for s in OBS_SEEDS
                    ],
                    axis=0,
                )
            diffs.append(float(np.max(np.abs(sd[True] - sd[False]))))
            cols[f"{test} (SIMULATED, σ_v {sv})"] = sd[False]
    labels = [f"{t:.0f}" for t in grid] + ["end (b1 170 / b2 162)"]
    rows_t = [
        [lab, *[_f(float(v[i]), 3) for v in cols.values()]]
        for i, lab in enumerate(labels)
    ]
    return "\n".join(
        [
            "## 2. Observability and practical identifiability (SIMULATED)",
            "",
            "State `x = [ln L, ln G, θ]`, process `L⁺ = L + G·Δt`, camera "
            "`y = ln L + θ + v`, anchor `z = ln L + w`. The map "
            "`(L, G, θ) → (cL, cG, θ − ln c)` leaves every camera output "
            "unchanged (unit test, exact to 1e-12), so its tangent "
            "`[1, 1, −1]` is unobservable.",
            "",
            "Linearised observability matrix along L(0) = 40 µm, G = 4 µm/min, "
            "camera every minute for 60 min (SIMULATED, noise-free):",
            "",
            f"- camera only: singular values {', '.join(f'{v:.3g}' for v in sv_cam)}; "
            f"rank {np.linalg.matrix_rank(o_cam, tol=1e-9 * sv_cam[0])}; "
            f"null vector (scaled to first entry 1) "
            f"[{', '.join(f'{v:.4f}' for v in null)}].",
            f"- plus one anchor at 30 min: singular values "
            f"{', '.join(f'{v:.3g}' for v in sv_anc)}; rank "
            f"{np.linalg.matrix_rank(o_anc)}.",
            "",
            "σ_θ after the b1 strike, SIMULATED camera (σ_v 0.10, truth = b1 "
            f"microscope curve), Q_G = {q_b1:.3g} /min, mean over "
            f"{len(OBS_SEEDS)} seeds; anchor = b1-s05 median + w "
            f"(R = {ev.ANCHOR_SD}²):",
            "",
            _table(
                ["prior", "anchor", "σ_θ prior", "σ_θ posterior (end)"], rows
            ),  # fmt: skip
            "",
            "With the evaluation prior (ln L(0) SD 1.0, ln G(0) SD 1.0) σ_θ "
            "drops a little without an anchor: information from the priors "
            "on seed size and growth rate, not from the camera (with diffuse "
            "priors σ_θ stays at its prior).",
            "",
            "Practical identifiability: posterior SD of ln(G/L) over time, "
            "leave-one-strike-out priors and Q_G, no anchor, mean over "
            f"{len(OBS_SEEDS)} seeds (prior SD "
            f"{ekf.log_relative_growth_sd(p_eval):.3f}). The anchor changes "
            f"these by at most {max(diffs):.1e}: it informs only the scale "
            "direction. ln(G/L) is structurally observable from the camera "
            "but weakly estimated: an SD of 0.4 in ln is a factor 1.5 at "
            "1σ. It widens again when the medians stop growing (b1 after "
            "122 min).",
            "",
            _table(["t (min)", *cols], rows_t),
            "",
            "Design note: the brief specified G as a random walk. In "
            "`[ln L, G, θ]` coordinates the unobservable direction is "
            "`[1, G, −1]` and moves with the estimate of G, so the EKF "
            "linearised at noisy estimates gains spurious θ information "
            "(the EKF inconsistency known from SLAM). With `ln G` the "
            "direction is constant and the EKF keeps σ_θ at its prior (unit "
            "test, diffuse priors, tolerance 0.1 %).",
            "",
        ]
    )


def _summ(xs: Sequence[float], nd: int = 3) -> str:
    a = np.array(xs, float)
    lo, hi = np.percentile(a, [5, 95])
    return f"{np.mean(a):.{nd}f} [{lo:.{nd}f}, {hi:.{nd}f}]"


def _flag(xs: Sequence[float]) -> str:
    a = np.array(xs, float)
    ok = np.isfinite(a)
    if not ok.any():
        return "0 %"
    return f"{100 * ok.mean():.0f} % / {np.median(a[ok]):.0f}"


def _flagt(t: float) -> str:
    return f"{t:.0f}" if np.isfinite(t) else "never"


def _tau(r: Sequence[ev.Scores], n: int) -> str:
    v = np.array([s.tau_rmse for s in r], float)
    k = float(np.mean([s.tau_defined for s in r]))
    m = f"{np.nanmean(v):.1f}" if np.isfinite(v).any() else "–"
    return f"{m} ({k:.1f}/{n})"


def _row(r: Sequence[ev.Scores], n: int) -> list[str]:
    """Metric and flag cells for a list of per-seed scores."""
    one = len(r) == 1
    return [
        _f(r[0].log_rmse, 3) if one else _summ([s.log_rmse for s in r]),
        _f(r[0].g_rmse) if one else _summ([s.g_rmse for s in r], 2),
        _f(r[0].rel_g_rmse, 3) if one else _summ([s.rel_g_rmse for s in r]),
        _tau(r, n),
        _flag([s.t_slower for s in r]),
        _flag([s.t_faster for s in r]),
        _flag([s.t_rel_slower for s in r]),
        _flag([s.t_rel_faster for s in r]),
    ]


METRIC_HEAD = [
    "log-size RMSE",
    "G RMSE (µm/min)",
    "G/L RMSE (%/min)",
    "τ RMSE (min) (defined/total)",
    "size flag slower",
    "size flag faster",
    "G/L flag slower",
    "G/L flag faster",
]


def _truth_text(test: list[Sample], nominal: ev.Curve) -> tuple[str, str]:
    slow, fast = ev.truth_flags(test, nominal)
    ts = [s.t_min for s in test]

    def br(t: float) -> str:
        if not np.isfinite(t):
            return "never"
        i = ts.index(t)
        return f"({ts[i - 1]:.0f}, {t:.0f}]" if i else f"≤ {t:.0f}"

    return br(slow), br(fast)


def _references(
    test_samples: list[Sample], nominal: ev.Curve, train: str
) -> list[list[object]]:
    truth = ev.Curve.from_samples(test_samples)
    held = ev.eval_samples(test_samples)
    n = len(held)
    a = ev.anchor_sample(test_samples).sample_id
    rows: list[list[object]] = [
        [f"nominal curve ({train}), no data", "–", "–",
         *_row([ev.nominal_baseline(nominal, held, truth, truth.t[-1])], n),
         "–"]
    ]  # fmt: skip
    for mode in ev.ANCHOR_MODES:
        r = ev.anchor_reference_runs(test_samples, nominal, EVAL_SEEDS, mode)
        rows.append(
            [f"anchor only ({mode}-shifted nominal)", "–", a, *_row(r, n), "–"]
        )
    return rows


def loso_section(
    ms: dict[str, list[Sample]], q: dict[tuple[str, float], float]
) -> str:
    rows, truth_rows = [], []
    for train, test in (("b1", "b2"), ("b2", "b1")):
        nominal = ev.Curve.from_samples(ms[train])
        truth = ev.Curve.from_samples(ms[test])
        n = len(ev.eval_samples(ms[test]))
        rows += [[test, *r] for r in _references(ms[test], nominal, train)]
        for sv in ev.SIGMA_V:
            for anchored in (False, True):
                r = ev.simulated_runs(
                    ms[test], nominal, q[(train, sv)], sv, anchored, EVAL_SEEDS
                )
                rows.append(
                    [test, f"EKF, SIMULATED camera, Q_G {q[(train, sv)]:.3g}",
                     sv,
                     ev.anchor_sample(ms[test]).sample_id if anchored
                     else "none",
                     *_row(r, n),
                     _f(float(np.mean([s.sd_theta_end for s in r])), 3)]
                )  # fmt: skip
        slow, fast = _truth_text(ms[test], nominal)
        c = ev.curve_flags(truth, nominal)
        truth_rows.append(
            [test, train, slow, fast, _flagt(c["slower"]),
             _flagt(c["faster"]), _flagt(c["rel_slower"]),
             _flagt(c["rel_faster"])]
        )  # fmt: skip
    evt = {
        b: ", ".join(f"{s.t_min:.0f}" for s in ev.eval_samples(ms[b]))
        for b in ms
    }
    return "\n".join(
        [
            "## 3. Leave-one-strike-out, SIMULATED camera signal",
            "",
            "Signal: `y_k = ln L_micro(t_k) + θ_true + v_k` once per minute "
            f"while L_micro ≥ {ev.L_MIN_UM:.0f} µm; L_micro = test strike's "
            "microscope medians, ln-linear between samples; "
            f"θ_true ~ N(0, {ev.THETA_SD}²) per seed; v_k ~ N(0, σ_v²); "
            f"{len(EVAL_SEEDS)} seeds per row. Anchor (where used) = the "
            f"first test sample at t ≥ {ev.ANCHOR_AFTER_MIN:.0f} min, "
            f"z = ln median + w, w ~ N(0, {ev.ANCHOR_SD}²); the anchor-only "
            "references get the same w per seed. EKF prior from the training "
            f"strike (ln L(0) = its first median, SD {ev.LNL0_SD}; ln G(0) = "
            f"ln of its mean growth rate, SD {ev.LNG0_SD}; "
            f"θ ~ N(0, {ev.THETA_SD}²)); Q_G tuned on the training strike "
            "(table at the end).",
            "",
            "References without camera: (i) the nominal curve = training "
            "strike's interpolated medians; (ii) anchor only, scale: nominal "
            "shifted in ln L to pass through the anchor; (iii) anchor only, "
            "age: nominal shifted in time to pass through the anchor (growth "
            "age at the anchor). Before the anchor (ii) and (iii) equal (i). "
            "A DCS process-signal baseline cannot run: no DCS data exist for "
            "2026-10-30.",
            "",
            "Metrics at the held-out microscope times of the test strike "
            f"(b1: {evt['b1']} min; b2: {evt['b2']} min; anchor excluded): "
            "log-size RMSE; growth-rate RMSE against a ±"
            f"{ev.RATE_HALF_MIN:.0f}-min central difference of the "
            "microscope curve; G/L RMSE; growth-age RMSE. Mean [5 %, 95 %] "
            "over seeds.",
            "",
            "Flags (rule, both kinds): on the 1-min grid, flag slower when "
            f"d + {ev.Z95}·σ_d < −ln 1.2 (faster: d − {ev.Z95}·σ_d > ln 1.2) on "
            f"{ev.FLAG_PERSIST_MIN} consecutive points; the flag time is the "
            "last of them (the online decision time). Size flag: "
            "d = ln L̂ − ln L_nom(t), σ_d = posterior SD of ln L. G/L flag "
            "(scale-free): d = ln(Ĝ/L̂) − ln(G_nom/L_nom)(t), σ_d = posterior "
            "SD of ln G − ln L; θ cancels. References carry only the anchor's "
            "SD. Cells: % of seeds flagged / median flag time (min since "
            "seeding).",
            "",
            "Circularity: the SIMULATED signal is built from the same "
            "microscope medians it is scored against. These rows test the "
            "estimator's mechanics against a known truth; they do not test "
            "the camera.",
            "",
            growth_age_note(ms),
            _table(
                [
                    "test strike",
                    "estimate",
                    "σ_v",
                    "anchor",
                    *METRIC_HEAD,
                    "σ_θ end",
                ],
                rows,
            ),  # fmt: skip
            "",
            "Flag reference. Samples (REAL microscope): first test sample "
            f"(median ≥ {ev.L_MIN_UM:.0f} µm) > 20 % below / above the "
            "nominal, as (previous sample, flagged sample]. Curves (the "
            "SIMULATED truth): the same rule as the estimator applied to the "
            "noise-free interpolated curves (zero SD, 10-point persistence). "
            "With two strikes the nominal of one is the other, so signs flip "
            "between rows.",
            "",
            _table(
                [
                    "test strike",
                    "nominal",
                    "size slower (samples)",
                    "size faster (samples)",
                    "size slower (curves)",
                    "size faster (curves)",
                    "G/L slower (curves)",
                    "G/L faster (curves)",
                ],
                truth_rows,
            ),  # fmt: skip
            "",
        ]
    )


SCENARIOS = (
    ev.MATCHED,
    ev.Scenario("β(L), κ = 0.1", kappa=0.1),
    ev.Scenario("β(L), κ = 0.3", kappa=0.3),
    ev.Scenario("β(L), κ = −0.3", kappa=-0.3),
    ev.Scenario("θ random walk", theta_q=ev.THETA_RW_Q),
    ev.Scenario("θ packing ramp", ramp=float(np.log(ev.PACKING_RATIO))),
)


def robustness_section(
    ms: dict[str, list[Sample]], q: dict[tuple[str, float], float]
) -> str:
    sv = 0.18
    rows = []
    for train, test in (("b1", "b2"), ("b2", "b1")):
        nominal = ev.Curve.from_samples(ms[train])
        n = len(ev.eval_samples(ms[test]))
        for scen in SCENARIOS:
            for q_theta in (0.0, ev.Q_THETA_SMALL):
                for anchored in (False, True):
                    r = ev.simulated_runs(
                        ms[test], nominal, q[(train, sv)], sv, anchored,
                        ROBUST_SEEDS, scen, q_theta,
                    )  # fmt: skip
                    cells = _row(r, n)
                    rows.append(
                        [test, scen.name, f"{q_theta:g}",
                         "one" if anchored else "none",
                         *[c.split(" [")[0] for c in cells]]
                    )  # fmt: skip
    lo, hi = ev.PACKING_SPAN_MIN
    return "\n".join(
        [
            "## 4. Robustness of the SIMULATED evaluation",
            "",
            "Same leave-one-strike-out set-up, σ_v = 0.18, "
            f"{len(ROBUST_SEEDS)} seeds per row, means only. The camera "
            "signal deviates from the filter's model:",
            "",
            "- β(L) = κ ln(L / L_ref), L_ref = "
            f"{ev.L_REF_UM:.0f} µm (CHOICE), κ ∈ {{0.1, 0.3, −0.3}}. κ < 0 is "
            "a compressed camera signal, as the traced p90 vs lab p90 "
            "log-log slope below 1 in `scripts/traced_vs_lab.py`.",
            "- θ random walk from seeding with intensity "
            f"{ev.THETA_RW_Q:.4f} /min: its SD over {lo:.0f}–{hi:.0f} min "
            f"equals ln {ev.PACKING_RATIO} (the traced lab/camera ratio rose "
            f"from ≈ 1.0 to 1.5–2.0, midpoint {ev.PACKING_RATIO}, "
            "`scripts/traced_vs_lab.py`). Zero-mean, so it does not mimic "
            "the direction of the packing bias;",
            f"- θ packing ramp: θ falls linearly by ln {ev.PACKING_RATIO} "
            f"between {lo:.0f} and {hi:.0f} min (camera reads low, as the "
            "traces), constant after.",
            "",
            f"Filter: Q_θ = 0 (model) or Q_θ = {ev.Q_THETA_SMALL:g} /min "
            "(CHOICE). References without camera are unaffected by these "
            "scenarios (section 3).",
            "",
            _table(
                [
                    "test strike",
                    "camera scenario",
                    "filter Q_θ",
                    "anchor",
                    *METRIC_HEAD,
                ],
                rows,
            ),  # fmt: skip
            "",
        ]
    )


def real_section(ms: dict[str, list[Sample]], q_g: float) -> str:
    frames = [
        f for f in traced_frames("chord", "b1") if f.t_min <= ev.REAL_T_MAX_MIN
    ]
    meas_cam = ev.real_camera(frames, 0.18)
    nominal = ev.Curve.from_samples(ms["b2"])
    truth = ev.Curve.from_samples(ms["b1"])
    t_end = truth.t[-1]
    held = ev.eval_samples(ms["b1"])
    covered = [s for s in held if s.t_min <= ev.REAL_T_MAX_MIN]
    anchor = ev.anchor_sample(ms["b1"])
    am = ev.anchor_measurement(anchor)
    variants = {"none": meas_cam, anchor.sample_id: [*meas_cam, am]}
    t_cam = max(f.t_min for f in frames)

    def table(subset: list[Sample], t_flag_max: float) -> list[list[object]]:
        n = len(subset)
        rows: list[list[object]] = [
            ["nominal curve (b2), no data", "–",
             *_row([ev.nominal_baseline(nominal, subset, truth, t_end,
                                        t_flag_max)], n)]
        ]  # fmt: skip
        for mode in ev.ANCHOR_MODES:
            s = ev.anchor_reference(
                [am], nominal, subset, truth, t_end, mode, t_flag_max
            )
            rows.append(
                [f"anchor only ({mode}-shifted nominal)", anchor.sample_id,
                 *_row([s], n)]
            )  # fmt: skip
        for name, meas in variants.items():
            s = ev.run_estimator(
                meas, nominal, subset, truth, q_g, t_end, t_flag_max=t_flag_max
            )
            rows.append(["EKF, REAL camera", name, *_row([s], n)])
        return rows

    frame_rows = [
        [f.frame, f.reader, _f(f.t_min, 2), f.n, _f(f.median_um, 1)]
        for f in frames
    ]
    t_out = np.array([s.t_min for s in held])
    per_t = [[_f(s.t_min, 1), "covered" if s.t_min <= ev.REAL_T_MAX_MIN
              else "EXTRAPOLATION", _f(s.median_um, 0)] for s in held]  # fmt: skip
    for meas in variants.values():
        xs, ps = ekf.run(*ev.prior(nominal), t_out, meas, q_g)
        for i, r in enumerate(per_t):
            r.append(f"{np.exp(xs[i, 0]):.0f} ± {np.sqrt(ps[i, 0, 0]):.2f}")
            r.append(_f(ekf.log_relative_growth_sd(ps[i]), 3))
    for i, s in enumerate(held):
        per_t[i].append(_f(float(np.exp(nominal.ln_size(s.t_min))), 0))
    slow, fast = _truth_text(ms["b1"], nominal)
    c = ev.curve_flags(truth, nominal)
    head = ["reference / estimator", "anchor", *METRIC_HEAD]
    return "\n".join(
        [
            "## 5. REAL camera points: blind AI chord traces, b1",
            "",
            "Signal: per (raw PAL frame, reader) median of the chord traces "
            "(`datasets/camera_traced_chords.csv`, method `chord`, readers "
            "AI-A and AI-B), converted per axis at the modelled PAL scale "
            "from `configs/camera_100.toml`; y = ln median. Used only up to "
            f"{ev.REAL_T_MAX_MIN:.0f} min (frames at 122 and 170 min are "
            f"biased low, see brief). n = {len(meas_cam)} camera measurements "
            f"from {len({f.frame for f in frames})} frames at 2 sample times; "
            "σ_v = 0.18 (chord traces). Nominal = b2, Q_G = "
            f"{q_g:.3g} /min tuned on b2 (SIMULATED, σ_v 0.18). Anchor = "
            f"{anchor.sample_id} median (no added noise, R = "
            f"{ev.ANCHOR_SD}²).",
            "",
            _table(
                ["frame", "reader", "t (min)", "n chords", "median (µm)"],
                frame_rows,
            ),  # fmt: skip
            "",
            "### 5a. Main result: camera-covered window only (REAL)",
            "",
            "Held-out times ≤ "
            f"{ev.REAL_T_MAX_MIN:.0f} min ("
            + ", ".join(f"{s.t_min:.0f}" for s in covered)
            + f" min, n = {len(covered)}); flags only up to "
            f"{ev.REAL_T_MAX_MIN:.0f} min.",
            "",
            _table(head, table(covered, ev.REAL_T_MAX_MIN)),
            "",
            "### 5b. EXTRAPOLATION beyond the camera data (REAL, open loop)",
            "",
            f"After {t_cam:.1f} min the EKF has no camera data and predicts "
            "open loop. All held-out times ("
            + ", ".join(f"{s.t_min:.0f}" for s in held)
            + " min); flags over the whole strike. These rows are "
            "extrapolation, not camera-aided estimation.",
            "",
            _table(head, table(held, np.inf)),
            "",
            "Flag reference for b1 vs nominal b2 (REAL microscope): samples "
            f"size slower {slow}, faster {fast}; curves size slower "
            f"{_flagt(c['slower'])}, faster {_flagt(c['faster'])}, G/L "
            f"slower {_flagt(c['rel_slower'])}, faster "
            f"{_flagt(c['rel_faster'])} (min).",
            "",
            "Per held-out time (REAL camera; estimate = exp(ln L̂) ± posterior "
            "SD of ln L; SD ln(G/L) = posterior SD of ln G − ln L):",
            "",
            _table(
                [
                    "t (min)",
                    "window",
                    "microscope median (µm)",
                    *[
                        c
                        for k in variants
                        for c in (
                            f"EKF, anchor {k} (µm)",
                            f"SD ln(G/L), anchor {k}",
                        )
                    ],
                    "nominal b2 (µm)",
                ],
                per_t,
            ),  # fmt: skip
            "",
        ]
    )


LIMITS = """## 6. Limitations

- n = 2 strikes, one sampled run (2026-10-30). Leave-one-strike-out tunes on
  one strike and tests on the other; nothing here estimates between-strike
  or between-day variability. With two strikes, "slower than nominal" for
  one is "faster" for the other by construction.
- Microscope truth is one AI transcription of burned-in overlay values
  (no second reading), of operator-chosen crystals (not a size
  distribution); photo clock ±47 s.
- SIMULATED camera: built from the microscope curve itself, with the
  brief's scratch noise levels (σ_v 0.10 / 0.18, not from a repo script).
  Section 3 has no bias β(L), no outliers and a constant θ; section 4
  probes β(L) and a drifting θ with chosen magnitudes. It tests the
  estimator, not the camera.
- REAL camera: 12 (frame, reader) medians from 6 frames at 2 sample times
  of one strike, traced by AI annotators (not a detector); the Cellpose
  detector that would give a 1/min signal is not trained yet.
- No DCS data for 2026-10-30, so the process-signal baseline cannot run.
- Growth rates (truth and nominal) are ±10-min central differences of
  interpolated medians; G/L flags inherit their noise.
- Decision-rule constants (20 %, 1.96 σ, 10 points), the 40 µm floor, the
  priors, the anchor time, L_ref and Q_θ are analysis choices, not tuned.
"""

OBS_SEEDS = range(0, 20)
ROBUST_SEEDS = range(2000, 2100)


def main() -> None:
    rng = np.random.default_rng(20261030)
    ms = microscope_samples()
    q: dict[tuple[str, float], float] = {}
    tune_rows = []
    for train in ("b1", "b2"):
        for sv in ev.SIGMA_V:
            best, cost = ev.tune_q(ms[train], sv, TUNE_SEEDS)
            q[(train, sv)] = best
            edge = best in (ev.Q_GRID[0], ev.Q_GRID[-1])
            tune_rows.append(
                [train, sv, f"{best:.3g}", "yes" if edge else "no",
                 _f(cost[best], 3), _f(max(cost.values()), 3)]
            )  # fmt: skip
    parts = [
        growth_section(ms, rng),
        observability_section(ms, q),
        loso_section(ms, q),
        robustness_section(ms, q),
        real_section(ms, q[("b2", 0.18)]),
    ]
    text = "\n".join(
        [
            "# Soft-sensor prototype: results (2026-10-30 sampled run)",
            "",
            f"Generated by `{CMD}`. Do not edit by hand. Every number is "
            "labelled REAL (microscope or traced camera data) or SIMULATED "
            "(synthetic camera signal).",
            "",
            *parts,
            "## Q_G tuning (SIMULATED)",
            "",
            "Anchored, training strike as its own nominal, mean log-size RMSE "
            f"over {len(TUNE_SEEDS)} seeds; grid "
            f"{', '.join(f'{v:.0e}' for v in ev.Q_GRID)} /min.",
            "",
            _table(
                [
                    "train",
                    "σ_v",
                    "Q_G (/min)",
                    "at grid edge",
                    "best RMSE",
                    "worst RMSE on grid",
                ],
                tune_rows,
            ),  # fmt: skip
            "",
            LIMITS,
        ]
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
