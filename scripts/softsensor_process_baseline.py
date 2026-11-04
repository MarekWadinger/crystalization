"""Process-signal-only baseline of the crystal-growth soft sensor.

    uv run --with openpyxl python scripts/softsensor_process_baseline.py

Writes ``docs/softsensor/process_baseline.md``:

1. 2026-10-30 INTERIM driver: plant supersaturation KP from the lab Brix
   and purity (interpolated between samples) at an ASSUMED massecuite
   temperature, growth law ``G = k_g (S − 1)^g`` integrated from the seed
   slurry size; ``k_g`` fitted on one strike's microscope medians, tested
   on the other, with the metrics of ``docs/softsensor/results.md``.
2. 2026-02-04 pipeline check on the DCS export ``Paulen_data.xlsx``:
   seeding from the steam cut, KP trajectory, predicted L(t). No size
   truth exists for that day.
3. What changes once the 2026-10-30 DCS export arrives.

``openpyxl`` is needed only for part 2 (as ``scripts/check_anchors.py``);
without it, or without the Drive file, part 2 says it did not run. Every
number in the output comes from this run.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

from softsensor import evaluate as ev
from softsensor import process as pr
from softsensor.data import (
    MICROSCOPE,
    PRE_SEED,
    SIDECAR,
    Sample,
    microscope_samples,
    seeding_t_s,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "softsensor" / "process_baseline.md"
CMD = "uv run --with openpyxl python scripts/softsensor_process_baseline.py"
DCS = (
    Path.home()
    / "Library/CloudStorage/GoogleDrive-marek.wadinger@stuba.sk"
    / "My Drive/sugar_plant/sered/data/Paulen_data.xlsx"
)
EVAL_SEEDS = range(1000, 1200)
"""Same seeds and draw order as ``scripts/softsensor_results.py``, so the
anchor noise w of each seed equals the EKF rows' w (θ drawn first)."""
DT_MIN = 0.1
"""Integration grid step, min."""

# ASSUMED inputs (sources in the docstrings).
T_ASSUMED = 70.8
"""ASSUMED massecuite temperature on 2026-10-30, °C: median TI1006 of the
ZRA while boiling, STU_DATA 2025-10-26…11-01 (notes_data_lab.md §2b)."""
T_SWEEP = (68.0, 70.0, 70.8, 72.0, 74.0)
"""°C. Covers the per-strike TI1006 medians 68.4–72.9 (STU 2025,
notes_data_lab.md §2d) and the 2026-02-04 strike (part 2 of the output)."""
G_EXP = 1.0
"""Growth exponent g: Georgieva et al. 2003 Eq. 24 (linear in S − 1),
industrial fed-batch sugar pan (notes_literature_models.md §2)."""
G_ALT = 2.7
"""Alternative g: HYCON2 benchmark, Hernández 2011 Eq. 3.44."""
SLURRY_PHOTO = "MICRO.jpg"
"""Seed size L0: median of the 4 burned-in chords of the slurry reference
photo of 2026-10-30 (REAL microscope; 'likely seed slurry, unconfirmed',
sidecar ``photo_clock.unassigned_photos``)."""
L0_ALT_UM = 6.81
"""Alternative L0: Mastersizer Dv50 of the seed slurry sampled 2025-01-16
(REAL, other date; datasets/README.md)."""
PURITY_0204 = 93.4
"""ASSUMED purity on 2026-02-04, %: the ZRA recipe parameter 'Kvocient
čistoty SS' (notes_plant_dcs_qa_photos.md §2.2); no lab purity that day.
2026-10-30 lab purity was 91.1–93.6."""
KP_SEED_TARGET = 1.13
"""ZRA recipe 'Koeficient presýtenia' at seeding (notes_plant_dcs_qa_photos.md
§2.2)."""
TAGS = {
    "stirrer": "EI1004/AI1/PV.CV",
    "bx": "QI1003/AI1/PV.CV",
    "temp": "TI1006/AI1/PV.CV",
    "steam_out": "PIC1002_PID/AO1/OUT.CV",
    "bx_sp": "QIC1000_PID/PID1/SP.CV",
}
SIDECAR_0204 = ROOT / "datasets" / "2026-02-04 11-08-51.json"
GROWTH_SPAN = (16.0, 123.0)
"""min: b1 samples from the end of the seed-formation lag (16.4 min) to the
last sample before the plateau (122.5 min)."""
STRIKE_0204_SEED = "12:31:30"
"""Steam cut found by ``scripts/check_anchors.py`` (operator note 12:30)."""


# ---------------------------------------------------------------- data


@dataclass(frozen=True, slots=True)
class LabPoint:
    """One lab massecuite sample: minutes since seeding, Brix, purity."""

    sample_id: str
    t_min: float
    bx: float
    purity: float


def lab_points() -> dict[str, list[LabPoint]]:
    """Massecuite lab samples (polarimeter dilution 4) per strike.

    The standard-syrup samples (dilution 2, before filling) are dropped;
    the pre-seeding sample b1-s02 is kept (it bounds the interpolation).
    """
    side = json.loads(SIDECAR.read_text())
    seed = seeding_t_s()
    out: dict[str, list[LabPoint]] = {}
    for s in side["samples"]:
        if s.get("refract") is None or s.get("dilution_polari") != 4:
            continue
        b = s["id"].split("-")[0]
        bx, p = pr.lab_brix_purity(
            s["refract"], s["polari"], s["dilution_refract"],
            s["dilution_polari"],
        )  # fmt: skip
        t = (float(s["t"]) - seed[b]) / 60.0
        out.setdefault(b, []).append(LabPoint(s["id"], t, bx, p))
    return {b: sorted(v, key=lambda x: x.t_min) for b, v in out.items()}


def after_tightening() -> frozenset[str]:
    """Sample ids taken after tightening (sidecar comment 'po suš')."""
    side = json.loads(SIDECAR.read_text())
    return frozenset(
        s["id"]
        for s in side["samples"]
        if (s.get("comment") or "").startswith("po suš")
    )


def slurry_chords() -> list[float]:
    """Burned-in chords (µm) of the slurry reference photo."""
    return [
        1000.0 * float(r["value_mm"])
        for r in csv.DictReader(MICROSCOPE.open(newline=""))
        if r["photo"] == SLURRY_PHOTO
        and r["kind"] == "crystal"
        and r["value_mm"]
    ]


def slurry_l0() -> float:
    """Median chord of the slurry reference photo, µm."""
    return float(np.median(slurry_chords()))


@dataclass(frozen=True, slots=True)
class Config:
    """One baseline variant."""

    t_c: float = T_ASSUMED
    g: float = G_EXP
    form: str = "sheet"
    l0: float = 13.0
    boiling_only: bool = False
    """Fit k_g without the 'po sušení' (after tightening) samples."""

    def label(self, l0_src: str) -> str:
        return (
            f"T {self.t_c:.1f} °C, g {self.g:g}, SC {self.form}, "
            f"L0 {self.l0:.1f} µm ({l0_src})"
        )


def lab_driver(
    lab: Sequence[LabPoint], t_end: float, cfg: Config
) -> tuple[np.ndarray, np.ndarray]:
    """Grid 0…t_end (min) and KP on it from Bx, P interpolated linearly
    between lab samples (flat outside) at the constant temperature."""
    t = np.arange(0.0, t_end + DT_MIN, DT_MIN)
    tl = np.array([p.t_min for p in lab])
    bx = np.interp(t, tl, [p.bx for p in lab])
    pur = np.interp(t, tl, [p.purity for p in lab])
    return t, pr.supersaturation(bx, pur, cfg.t_c, cfg.form)


# --------------------------------------------------------- 2026-10-30


@dataclass(frozen=True, slots=True)
class Fit:
    train: str
    test: str
    cfg: Config
    k_g: float
    train_log_rmse: float
    unanchored: ev.Scores
    anchored: list[ev.Scores]


def _eval_times(
    held: Sequence[Sample], t_end: float
) -> tuple[np.ndarray, np.ndarray]:
    """1-min grid ∪ held-out times, and the grid mask (as evaluate.py)."""
    grid = np.arange(0.0, np.floor(t_end) + 1.0)
    times = np.unique(np.concatenate([grid, [s.t_min for s in held]]))
    return times, np.isin(times, grid)


def _anchor_w(seed: int) -> float:
    r = np.random.default_rng([seed, 0])
    r.normal(0.0, ev.THETA_SD)  # θ_0: drawn first, unused here
    return float(r.normal(0.0, ev.ANCHOR_SD))


def run_pair(
    ms: dict[str, list[Sample]],
    lab: dict[str, list[LabPoint]],
    train: str,
    test: str,
    cfg: Config,
) -> Fit:
    """Fit k_g on ``train`` (all post-seeding medians), score on ``test``."""
    tr = ms[train]
    if cfg.boiling_only:
        post = after_tightening()
        tr = [s for s in tr if s.sample_id not in post]
    t_tr, s_tr = lab_driver(lab[train], tr[-1].t_min, cfg)
    t_obs = [s.t_min for s in tr]
    l_obs = [s.median_um for s in tr]
    k = pr.fit_kg(t_tr, s_tr, cfg.l0, t_obs, l_obs, cfg.g)
    fit_l = np.interp(
        t_obs, t_tr, pr.integrate_size(t_tr, s_tr, cfg.l0, k, cfg.g)
    )
    train_rmse = float(np.sqrt(np.mean(np.log(fit_l / np.array(l_obs)) ** 2)))

    te = ms[test]
    truth = ev.Curve.from_samples(te)
    nominal = ev.Curve.from_samples(ms[train])
    held = ev.eval_samples(te)
    t_end = truth.t[-1]
    t, s = lab_driver(lab[test], t_end, cfg)
    integ = pr.growth_integral(t, s, cfg.g)
    times, mask = _eval_times(held, t_end)
    i_at = np.interp(times, t, integ)
    g_at = pr.growth_rate(np.interp(times, t, s), k, cfg.g)
    zero = np.zeros(len(times))

    def score(ln_l: np.ndarray, sd: np.ndarray) -> ev.Scores:
        return ev.assess(
            times, ln_l, g_at, sd, zero, held, truth, nominal, mask
        )

    unanch = score(np.log(cfg.l0 + k * i_at), zero)
    a = ev.anchor_sample(te)
    i_a = float(np.interp(a.t_min, t, integ))
    after = times >= a.t_min
    sd = np.where(after, ev.ANCHOR_SD, 0.0)
    anch = []
    for seed in EVAL_SEEDS:
        la = a.median_um * np.exp(_anchor_w(seed))
        size = np.where(after, la + k * (i_at - i_a), cfg.l0 + k * i_at)
        anch.append(score(np.log(size), sd))
    return Fit(train, test, cfg, k, train_rmse, unanch, anch)


# ------------------------------------------------------------ format


def _f(v: float, nd: int = 2) -> str:
    return "–" if not np.isfinite(v) else f"{v:.{nd}f}"


def _table(head: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


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


def _tau(r: Sequence[ev.Scores], n: int) -> str:
    v = np.array([s.tau_rmse for s in r], float)
    k = float(np.mean([s.tau_defined for s in r]))
    m = f"{np.nanmean(v):.1f}" if np.isfinite(v).any() else "–"
    return f"{m} ({k:.1f}/{n})"


def _cells(r: Sequence[ev.Scores], n: int) -> list[str]:
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


HEAD = [
    "test strike",
    "estimate",
    "anchor",
    "log-size RMSE",
    "G RMSE (µm/min)",
    "G/L RMSE (%/min)",
    "τ RMSE (min) (defined/total)",
    "size flag slower",
    "size flag faster",
    "G/L flag slower",
    "G/L flag faster",
]


# ---------------------------------------------------------- sections


def lab_section(
    lab: dict[str, list[LabPoint]], ms: dict[str, list[Sample]]
) -> str:
    med = {s.sample_id: s for b in ms.values() for s in b}
    rows = []
    for b, pts in lab.items():
        for p in pts:
            m = med.get(p.sample_id)
            kp = {
                tc: float(pr.supersaturation(p.bx, p.purity, tc))
                for tc in (68.0, T_ASSUMED, 74.0)
            }
            rows.append(
                [
                    b, p.sample_id, f"{p.t_min:.1f}", f"{p.bx:.2f}",
                    f"{p.purity:.1f}", f"{kp[68.0]:.3f}",
                    f"{kp[T_ASSUMED]:.3f}", f"{kp[74.0]:.3f}",
                    f"{float(pr.supersaturation(p.bx, p.purity, T_ASSUMED, 'exp')):.3f}",
                    f"{m.median_um:.1f}" if m else "–",
                ]
            )  # fmt: skip
    return "\n".join(
        [
            "## 1. Inputs on 2026-10-30",
            "",
            "Lab Brix and purity (REAL, `ZRA.xlsx` via the run sidecar: "
            "Bx = refract × 2, P = polari × 4 / Bx × 100) of the massecuite "
            "samples; t = min since that strike's seeding (sidecar, b1 "
            "11:29:33, b2 15:22:00). KP = plant supersaturation coefficient "
            "(`src/softsensor/process.py`, sheet form unless stated) at an "
            "ASSUMED constant temperature. Microscope median: REAL (AI "
            "transcription), as in `results.md` §1.",
            "",
            _table(
                [
                    "strike",
                    "sample",
                    "t (min)",
                    "Bx (REAL)",
                    "P % (REAL)",
                    "KP @ 68 °C (ASSUMED T)",
                    f"KP @ {T_ASSUMED} °C (ASSUMED T)",
                    "KP @ 74 °C (ASSUMED T)",
                    f"KP exp form @ {T_ASSUMED} °C",
                    "microscope median (µm, REAL)",
                ],
                rows,
            ),  # fmt: skip
            "",
            "Bx rises 79 → 91 over a strike while purity stays 91–94 %. "
            "The lab Brix of a diluted massecuite sample is whole-massecuite "
            "dry substance (crystals dissolve on dilution; interp.), so KP "
            "above is computed as the plant computes it from QI1003, on the "
            "whole massecuite: it equals the mother-liquor supersaturation "
            "only near seeding and overstates it as crystal content grows "
            "(KP > 2 at the end of b1 is not a physical supersaturation of "
            "the liquor).",
            "",
        ]
    )


def baseline_section(
    ms: dict[str, list[Sample]],
    lab: dict[str, list[LabPoint]],
    l0: float,
) -> tuple[str, dict[str, Fit]]:
    cfg = Config(l0=l0)
    fits = {
        test: run_pair(ms, lab, train, test, cfg)
        for train, test in (("b1", "b2"), ("b2", "b1"))
    }
    rows: list[list[object]] = []
    for test in ("b2", "b1"):
        f = fits[test]
        te = ms[test]
        truth = ev.Curve.from_samples(te)
        nominal = ev.Curve.from_samples(ms[f.train])
        held = ev.eval_samples(te)
        n = len(held)
        a = ev.anchor_sample(te).sample_id
        nom = ev.nominal_baseline(nominal, held, truth, truth.t[-1])
        rows += [
            [test, f"nominal curve ({f.train}), no data (REAL, as results.md)",
             "–", *_cells([nom], n)],
            [test, "process-signal baseline (INTERIM, lab-sample driver), "
             f"k_g {f.k_g:.2f} µm/min from {f.train}", "none",
             *_cells([f.unanchored], n)],
            [test, "process-signal baseline (INTERIM, lab-sample driver), "
             f"k_g {f.k_g:.2f} µm/min from {f.train}", a,
             *_cells(f.anchored, n)],
        ]  # fmt: skip
    tr_rows = []
    for test, f in fits.items():
        tr = ms[f.train]
        t, s = lab_driver(lab[f.train], tr[-1].t_min, cfg)
        size = pr.integrate_size(t, s, cfg.l0, f.k_g, cfg.g)
        for smp in tr:
            li = float(np.interp(smp.t_min, t, size))
            si = float(np.interp(smp.t_min, t, s))
            tr_rows.append(
                [
                    f.train, smp.sample_id, f"{smp.t_min:.1f}",
                    f"{smp.median_um:.1f}", f"{li:.1f}",
                    f"{np.log(li / smp.median_um):+.3f}", f"{si:.3f}",
                    f"{float(pr.growth_rate(si, f.k_g, cfg.g)):.2f}",
                ]
            )  # fmt: skip
    text = "\n".join(
        [
            "## 2. Leave-one-strike-out, process-signal baseline "
            "(INTERIM, lab-sample driver)",
            "",
            f"Configuration: KP from lab Bx/P (§1) at T = {T_ASSUMED} °C "
            "(ASSUMED: median TI1006 of the ZRA while boiling, STU_DATA "
            "2025-10-26…11-01, `docs/sered/notes_data_lab.md` §2b); growth "
            f"law G = k_g·max(KP − 1, 0)^g with g = {G_EXP:g} (ASSUMED: "
            "Georgieva et al. 2003 Eq. 24, `notes_literature_models.md` §2); "
            f"L(0) = {l0:.1f} µm (REAL microscope, median of the 4 chords on "
            f"the slurry reference photo `{SLURRY_PHOTO}`, n = 4) at the "
            "sidecar seeding time; L(t) = L(0) + k_g ∫ max(KP − 1, 0)^g dt "
            f"on a {DT_MIN} min grid. k_g (INTERIM) minimises the log-size "
            "residuals at all post-seeding microscope medians of the "
            "training strike (b1: 10, b2: 8 samples) and is applied to the "
            "test strike with the test strike's own lab driver. No camera, "
            "no θ.",
            "",
            "Metrics exactly as `results.md` §3 (`softsensor.evaluate."
            "assess`): held-out microscope times of the test strike (b1: 49, "
            "60, 79, 96, 122, 160, 170 min; b2: 52, 69, 96, 146, 162 min; "
            "the anchor sample excluded from both rows); G truth = ±10-min "
            "central difference of the test microscope curve; growth age "
            "against the training strike's curve. The anchored row restarts "
            "L at the anchor (first test sample at t ≥ 30 min) as "
            "L_a·e^w + k_g(I(t) − I(t_a)), w ~ N(0, 0.1²) with the same "
            f"draws as the EKF rows ({len(EVAL_SEEDS)} seeds; mean [5 %, "
            "95 %]). The baseline carries no posterior SD, so its size "
            "flags use SD 0 before the anchor and 0.1 after it, its G/L "
            "flags SD 0 (as the references in `results.md`). Cells: % of "
            "seeds flagged / median flag time (min since seeding).",
            "",
            _table(HEAD, rows),
            "",
            "The baseline has no uncertainty, so its flags fire whenever it "
            "differs from the nominal by more than 20 % for 10 min. Size "
            "flags in the first 15 min compare the slurry L(0) with the "
            "nominal's first median and say nothing about "
            "growth; G/L flags compare the model's KP-driven rate with the "
            "nominal's. They are reported for completeness, not as "
            "decisions.",
            "",
            "Training fit (INTERIM): microscope median vs fitted L at the "
            "training samples; KP and G of the fitted model there. "
            f"Training log-size RMSE: b1 {fits['b2'].train_log_rmse:.3f}, "
            f"b2 {fits['b1'].train_log_rmse:.3f}.",
            "",
            _table(
                [
                    "train",
                    "sample",
                    "t (min)",
                    "microscope median (µm, REAL)",
                    "fitted L (µm, INTERIM)",
                    "ln(fit/obs)",
                    f"KP @ {T_ASSUMED} °C",
                    "G (µm/min)",
                ],
                tr_rows,
            ),  # fmt: skip
            "",
        ]
    )
    return text, fits


def sweep_section(
    ms: dict[str, list[Sample]],
    lab: dict[str, list[LabPoint]],
    l0: float,
) -> str:
    variants: list[tuple[Config, str]] = [
        (Config(t_c=tc, l0=l0), "T sweep") for tc in T_SWEEP
    ]
    variants += [
        (Config(g=G_ALT, l0=l0), "g = 2.7 (HYCON2)"),
        (Config(form="exp", l0=l0), "SC exp form"),
        (Config(l0=L0_ALT_UM), "L0 = Mastersizer Dv50"),
        (Config(t_c=68.0, form="exp", l0=l0), "SC exp form, 68 °C"),
        (Config(l0=l0, boiling_only=True), "fit without 'po sušení'"),
        (Config(g=0.5, l0=l0), "g = 0.5 (CHOICE, diagnostic)"),
        (Config(g=0.25, l0=l0), "g = 0.25 (CHOICE, diagnostic)"),
    ]
    rows = []
    for cfg, what in variants:
        for train, test in (("b1", "b2"), ("b2", "b1")):
            f = run_pair(ms, lab, train, test, cfg)
            rows.append(
                [
                    what, f"{cfg.t_c:.1f}", f"{cfg.g:g}", cfg.form,
                    f"{cfg.l0:.2f}", f"{train} → {test}", f"{f.k_g:.2f}",
                    f"{f.train_log_rmse:.3f}",
                    f"{f.unanchored.log_rmse:.3f}",
                    f"{np.mean([s.log_rmse for s in f.anchored]):.3f}",
                    f"{f.unanchored.g_rmse:.2f}",
                    f"{f.unanchored.rel_g_rmse:.3f}",
                ]
            )  # fmt: skip
    return "\n".join(
        [
            "## 3. Sensitivity of the INTERIM baseline to its ASSUMED inputs",
            "",
            "Each row refits k_g on the training strike. g = 0.5 and 0.25 "
            "are not from the literature: they test whether a weaker "
            "dependence on the rising whole-massecuite KP fits better "
            "(diagnostic of the shape mismatch, not a proposed model). "
            "'fit without po sušení' drops the after-tightening sample "
            f"({', '.join(sorted(after_tightening()))}) from the training "
            "fit; the test samples are unchanged. Temperature "
            "enters only through Bsat(T) in KP (k_g absorbs the Arrhenius "
            "factor of the Georgieva law at constant T). Anchored = mean "
            f"over the {len(EVAL_SEEDS)} anchor-noise seeds.",
            "",
            _table(
                [
                    "variant",
                    "T (°C)",
                    "g",
                    "SC form",
                    "L0 (µm)",
                    "train → test",
                    "k_g (µm/min)",
                    "train log RMSE",
                    "test log RMSE, no anchor",
                    "test log RMSE, anchored",
                    "test G RMSE (µm/min), no anchor",
                    "test G/L RMSE (%/min), no anchor",
                ],
                rows,
            ),  # fmt: skip
            "",
        ]
    )


# ------------------------------------------------------------ 2026-02-04


def _dcs_rows() -> tuple[list[datetime], dict[str, np.ndarray]]:
    import openpyxl  # ty: ignore[unresolved-import]  # optional, see docstring

    wb = openpyxl.load_workbook(DCS, read_only=True, data_only=True)
    rows = list(wb.worksheets[0].iter_rows(values_only=True))
    head = list(rows[1])
    body = [r for r in rows[2:] if r[0] is not None]
    t = [r[0] for r in body]
    cols = {
        k: np.array([r[head.index(tag)] for r in body], float)
        for k, tag in TAGS.items()
    }
    return t, cols


def operator_seeding_0204() -> datetime:
    """Operator's seeding time on 2026-02-04 (sidecar seeding event)."""
    side = json.loads(SIDECAR_0204.read_text())
    ev0 = next(e for e in side["events"] if e.get("is_seeding"))
    return datetime.fromisoformat(ev0["wallclock"])


def dcs_section(fits: dict[str, Fit], l0: float) -> tuple[str, float | None]:
    """Section text and the steam-cut delay after the operator's seeding
    time (min), None when the DCS file could not be read."""
    title = "## 4. Pipeline check on the 2026-02-04 DCS export"
    try:
        stamps, c = _dcs_rows()
    except (ImportError, FileNotFoundError) as e:
        return f"{title}\n\nNot run: {e}.\n", None
    t0 = stamps[0]
    tm = np.array([(s - t0).total_seconds() / 60.0 for s in stamps])
    seeds = pr.detect_seeding(tm, c["steam_out"], c["stirrer"], c["bx"])
    ungated = pr.detect_seeding(
        tm, c["steam_out"], c["stirrer"], c["bx"], bx_max=np.inf
    )
    rejected = [m for m in ungated if m not in seeds]

    def clock(m: float) -> str:
        return (t0 + timedelta(minutes=m)).strftime("%H:%M:%S")

    def bx_at(m: float) -> float:
        return float(c["bx"][int(np.searchsorted(tm, m))])

    op = operator_seeding_0204()
    op_min = (op - t0).total_seconds() / 60.0

    seed_rows = []
    for m in seeds:
        k = int(np.searchsorted(tm, m))
        sp_before = float(c["bx_sp"][max(k - 2, 0)])
        sp_after = float(np.min(c["bx_sp"][k : k + 40]))
        kp = float(pr.supersaturation(c["bx"][k], PURITY_0204, c["temp"][k]))
        seed_rows.append(
            [
                clock(m), f"{c['bx'][k]:.2f}", f"{c['temp'][k]:.2f}",
                f"{kp:.3f}", f"{sp_before:.2f} → {sp_after:.2f}",
            ]
        )  # fmt: skip

    # the complete strike: seeded at the 12:31:30 cut, until the stirrer stops
    ts = next(m for m in seeds if clock(m) == STRIKE_0204_SEED)
    k0 = int(np.searchsorted(tm, ts))
    k1 = k0 + int(np.argmax(c["stirrer"][k0:] < 1.0))
    sl = slice(k0, k1)
    t = tm[sl] - ts
    bx, temp = c["bx"][sl], c["temp"][sl]
    kp = pr.supersaturation(bx, PURITY_0204, temp)
    kp_exp = pr.supersaturation(bx, PURITY_0204, temp, "exp")
    g = G_EXP
    size = {b: pr.integrate_size(t, kp, l0, f.k_g, g) for b, f in fits.items()}
    traj = []
    for m in np.arange(0.0, t[-1] + 1e-9, 15.0):
        i = int(np.searchsorted(t, m))
        traj.append(
            [
                clock(ts + t[i]), f"{t[i]:.1f}", f"{bx[i]:.2f}",
                f"{temp[i]:.2f}", f"{kp[i]:.3f}", f"{kp_exp[i]:.3f}",
                f"{float(pr.growth_rate(kp[i], fits['b2'].k_g, g)):.2f}",
                f"{size['b2'][i]:.0f}", f"{size['b1'][i]:.0f}",
            ]
        )  # fmt: skip
    k_b1, k_b2 = fits["b2"].k_g, fits["b1"].k_g
    text = "\n".join(
        [
            title,
            "",
            "Source: Drive `sugar_plant/sered/data/Paulen_data.xlsx` (REAL "
            "DCS, ZRA only, 30 s, 11:00–17:00, no LI1000 level). No size "
            "truth exists for this day, so nothing here is scored; this "
            "section shows the DCS path of the baseline runs and what it "
            "outputs.",
            "",
            "Seeding from the steam signature (`process.detect_seeding`): "
            "steam-flap output PIC1002_PID/AO1/OUT ≥ 95 % for ≥ 10 samples, "
            "then ≤ 50 %, stirrer EI1004 > 5 A, QI1003 ≤ 85. The Brix gate "
            "rejects "
            + (
                ", ".join(
                    f"the cut at {clock(m)} (QI1003 {bx_at(m):.1f}, end of "
                    "the previous strike)"
                    for m in rejected
                )
                or "nothing"
            )
            + ". KP at the cut "
            f"uses QI1003, TI1006 (REAL) and P = {PURITY_0204} % (ASSUMED: "
            "ZRA recipe purity of the standard syrup). The QIC1000 "
            "setpoint step (cooking curve starts) is an independent "
            "check of the seeding.",
            "",
            _table(
                [
                    "steam cut (REAL)",
                    "QI1003 (REAL)",
                    "TI1006 °C (REAL)",
                    "KP (ASSUMED P)",
                    "QIC1000 SP before → min after",
                ],
                seed_rows,
            ),  # fmt: skip
            "",
            f"The {STRIKE_0204_SEED} cut is {ts - op_min:.1f} min after the "
            f"operator's seeding time {op.strftime('%H:%M:%S')} (sidecar "
            "`2026-02-04 11-08-51.json`) and agrees with "
            "`scripts/check_anchors.py`. "
            + "".join(
                f"The {clock(m)} cut is the next strike (export ends "
                f"{clock(tm[-1])}). "
                for m in seeds
                if m > ts
            )
            + "KP at seeding is "
            f"{seed_rows[[r[0] for r in seed_rows].index(STRIKE_0204_SEED)][3]}"
            f" against the recipe seeding target {KP_SEED_TARGET} "
            "(ASSUMED purity; at seeding QI1003 is a valid mother-liquor "
            "Brix, plant expert).",
            "",
            f"Strike seeded {STRIKE_0204_SEED}, until the stirrer stops "
            f"({clock(ts + t[-1])}): TI1006 (REAL) median "
            f"{np.median(temp):.1f} °C, range {temp.min():.1f}–"
            f"{temp.max():.1f} °C; QI1003 {bx[0]:.1f} → {bx[-1]:.1f}. "
            f"Predicted L(t) from L(0) = {l0:.1f} µm with k_g fitted on "
            f"2026-10-30 b1 ({k_b1:.2f} µm/min) or b2 ({k_b2:.2f} µm/min) "
            "(INTERIM, lab-Brix driver at an ASSUMED temperature, "
            "transferred to a QI1003 driver: not validated), g = 1, sheet "
            "form. QI1003 reads the whole massecuite, so KP after the "
            "first minutes is an index, not the liquor supersaturation. "
            "The operator logged drying ('sušenie') at 15:41 (sidecar); "
            "the model has no tightening phase and keeps growing.",
            "",
            _table(
                [
                    "clock",
                    "t since cut (min)",
                    "QI1003 (REAL)",
                    "TI1006 °C (REAL)",
                    "KP sheet",
                    "KP exp",
                    "G (µm/min, k_g b1)",
                    "L (µm, k_g b1)",
                    "L (µm, k_g b2)",
                ],
                traj,
            ),  # fmt: skip
            "",
        ]
    )
    return text, ts - op_min


def when_dcs(n_lab: str, delay: float | None) -> str:
    cut = (
        f"on 2026-02-04 the cut was {delay:.1f} min after the operator's time"
        if delay is not None
        else "§4 did not run"
    )
    return f"""## 5. What changes when the 2026-10-30 DCS export arrives

The requested export (QI1003, TI1006, EI1004, PIC1001, PIC1002_PID OUT,
PIC1003_PID, QIC1000/1001, TIC1002, and LI1000 if it exists) replaces three
inputs of §2 and nothing else:

1. **Driver.** Bx(t) = QI1003 at 30 s instead of {n_lab} lab Brix per
   strike interpolated linearly; T(t) = TI1006 instead of the ASSUMED
   {T_ASSUMED} °C. The temperature sweep of §3 is then dropped. Purity stays
   the lab purity interpolated between samples (no online purity exists);
   the recipe value {PURITY_0204} % is the fallback.
2. **Seeding time.** t = 0 moves from the sidecar operator times (b1
   11:29:33, b2 15:22:00) to the steam cut found by
   `process.detect_seeding` ({cut}). Every microscope sample time
   since seeding shifts by that difference; the estimator and the
   baseline both use the DCS time.
3. **k_g** is refitted with the DCS driver, b1 → b2 and b2 → b1, and the
   rows of §2 are recomputed with the same metrics, held-out samples and
   anchor draws. The row label changes from "process-signal baseline
   (interim, lab-sample driver)" to "process-signal baseline (DCS)" and it
   replaces the interim row in tab:loso.

The export also gives the first measured comparison of QI1003 with the lab
Brix at the {n_lab} lab samples per strike (both whole-massecuite readings; an
offset there moves KP directly). It does not remove the main limitation:
neither signal is the mother-liquor Brix after the first minutes, so KP
stays an index. A mother-liquor measurement (a centrifuged or filtered lab
sample) or a crystal-content estimate would be needed to turn it into a
supersaturation. Unchanged: the growth law, g, L(0), the metrics and the
n = 2 strikes.

Code path: `_dcs_rows()` and §4 already run the DCS driver on
`Paulen_data.xlsx`; for 2026-10-30 it needs the export path, the same tag
names, and the lab purity interpolation of `lab_driver` in place of the
constant {PURITY_0204} %.
"""


def limits(
    ms: dict[str, list[Sample]], lab: dict[str, list[LabPoint]], n_lab: str
) -> str:
    post = [p for p in lab["b1"] if p.sample_id not in PRE_SEED]
    kp = [float(pr.supersaturation(p.bx, p.purity, T_ASSUMED)) for p in post]
    b1 = ms["b1"]
    span = [s for s in b1 if GROWTH_SPAN[0] <= s.t_min <= GROWTH_SPAN[1]]
    rates = [
        (b.median_um - a.median_um) / (b.t_min - a.t_min)
        for a, b in zip(span[:-1], span[1:], strict=True)
    ]
    drop = [
        1.0
        - float(
            pr.supersaturation(p.bx, p.purity, T_ASSUMED, "exp")
            / pr.supersaturation(p.bx, p.purity, T_ASSUMED)
        )
        for pts in lab.values()
        for p in pts
    ]
    chords = slurry_chords()
    post_dry = sorted(after_tightening())
    items = [
        "**Whole-massecuite Brix.** Lab Brix of a diluted massecuite sample "
        "and QI1003 both include the crystals; the plant formula wants the "
        "mother liquor. KP from them overstates the liquor supersaturation "
        f"as crystal content grows (KP {kp[0]:.2f} → {kp[-1]:.2f} over the "
        f"post-seeding b1 lab samples at {T_ASSUMED} °C), so the fitted "
        "G = k_g (KP − 1)^g rises over the strike where the microscope "
        f"growth rate between samples is {min(rates):.1f}–{max(rates):.1f} "
        f"µm/min from {span[0].t_min:.0f} to {span[-1].t_min:.0f} min in "
        "b1, then stops in tightening. k_g is a curve-fit constant of this "
        "index, not a kinetic constant. The diagnostic g < 1 rows of §3 fit "
        "better for that reason; they are not a literature growth law.",
        "**ASSUMED temperature** on 2026-10-30 (no DCS); §3 shows how much "
        f"the result moves over {min(T_SWEEP):.0f}–{max(T_SWEEP):.0f} °C.",
        "**n = 2 strikes**, one sampled run: one fit per direction, no "
        "estimate of between-strike or between-day variability. The interim "
        f"driver has {n_lab} lab points per strike, linearly interpolated.",
        "**No tightening or discharge model**: L keeps growing through "
        "tightening (between the 'pred sušením' and 'po sušení' samples, "
        f"{', '.join(post_dry)} being the latter), where the microscope "
        "medians plateau, fall or jump.",
        f"**Seed size**: L(0) = {np.median(chords):.0f} µm from "
        f"{len(chords)} chords on one slurry photo, the same for both "
        f"strikes; b1's first post-seeding median is already "
        f"{b1[0].median_um:.0f} µm at {b1[0].t_min:.1f} min (crystals "
        "before seeding: residual footing or nucleation, open), which a "
        "process model cannot know without a size measurement.",
        "**Purity**: lab purity of the whole massecuite (crystals raise it); "
        f"2026-02-04 uses the recipe value {PURITY_0204} % (ASSUMED).",
        "Microscope truth: one AI transcription of operator-chosen crystals "
        "(as in `results.md`).",
        "SC form: the plant sheet (2.72·(−c·NW)) reproduces the DCS live KP "
        "(unit test); the textbook exp form lowers KP by "
        f"{100 * min(drop):.0f}–{100 * max(drop):.0f} % on the lab points "
        "and is shown in §3.",
        "Lohani et al. (2026, ESCAPE 36), our group's supersaturation soft "
        "sensor from standard process measurements, was not found as code "
        "in this repo, its sibling worktrees or the Drive `sugar_plant` "
        "folder, so it is not reused here; this baseline uses the plant's "
        "own KP formula instead.",
    ]
    return "\n".join(["## 6. Limitations", "", *(f"- {i}" for i in items), ""])


def main() -> None:
    ms = microscope_samples()
    lab = lab_points()
    l0 = slurry_l0()
    n = sorted(len(v) for v in lab.values())
    n_lab = f"{n[0]}–{n[-1]}" if n[0] != n[-1] else str(n[0])
    s_lab = lab_section(lab, ms)
    s_base, fits = baseline_section(ms, lab, l0)
    s_dcs, delay = dcs_section(fits, l0)
    parts = [
        s_lab,
        s_base,
        sweep_section(ms, lab, l0),
        s_dcs,
        when_dcs(n_lab, delay),
        limits(ms, lab, n_lab),
    ]
    text = "\n".join(
        [
            "# Process-signal baseline (2026-10-30 interim, 2026-02-04 "
            "pipeline check)",
            "",
            f"Generated by `{CMD}`. Do not edit by hand. Labels: REAL = "
            "measured (microscope medians, lab Brix/purity, DCS signals); "
            "ASSUMED = an input not measured on that day (source given); "
            "INTERIM = computed with the interim lab-sample driver and "
            "ASSUMED inputs (fitted k_g, predicted sizes, metrics).",
            "",
            *parts,
        ]
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
