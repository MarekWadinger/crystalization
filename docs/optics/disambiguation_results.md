# Depth disambiguation: pipeline and current results

**Updated:** 2026-11-05 (rerun with focus travel ξ = 0, lens at its FAR stop; author decision).
**Pipeline code:** [`../../src/optics/disambiguate.py`](../../src/optics/disambiguate.py),
[`../../src/optics/csd.py`](../../src/optics/csd.py).
**Reproduce:** `uv run python -m optics.disambiguate` (figs 09, 10 and the git-ignored
`crystal_observations.csv`); every number below, old vs new:
`uv run --frozen python scripts/rerun_paper_numbers.py` → [`rerun_results.md`](./rerun_results.md).

> **Read first.** None of the sizes on this page measures crystals. No hand-labelled annotations
> exist yet. The edge detector's size distribution follows its area window. The watershed tiles the
> frame, so its distribution follows its own seed spacing. The near/far split is a tie-break (below).

## What the pipeline does

1. Detect crystals on every 15th frame of `datasets/2026-02-05 10-36-32.mp4` (60 frames, auto crop
   1826 × 906 px) with the watershed (`optics.detect_watershed`) or the edge detector
   (`annotator.detection`). The area window is `detection_area_px` from `configs/camera_100.toml`:
   `[9, 345 389]` px² on the 1080p clips (3 px side up to a 1 mm square at 1.489 × 1.945 µm/px).
2. Score each detection by the mean Laplacian-variance inside its box; normalise to the 99.5th
   percentile.
3. The top 15 % in sharpness define the focal-plane size prior `P_w(w)`.
4. For the others, invert `S = (σ² + σ_floor²)^(−5/2)` to the CoC, then `c(d_o)` to the two
   candidate depths, and keep the side whose implied size is more probable under `P_w`.
5. Sizes are area-equivalent: `sqrt(w·h)` of the box times the geometric-mean µm/px (1.701 µm on
   the clips). That is exact for areas under the anisotropic pixel, but not a length along either axis.

## Current numbers (60 frames, watershed, current window)

| Quantity | Value |
|---|---:|
| Detections | 52 784 (focus 7 918, near 33 958, far 10 908) |
| Near / far split | 76 / 24 |
| Off-focus p_near within 0.500 ± 0.002 | 99.6 % (0.1–99.9 % quantiles 0.497–0.504) |
| Median / mean area-equivalent size | 0.076 / 0.083 mm (CV 0.43, log-normal s 0.41) |
| Mean depth correction | 0.006 % of the median |
| \|d − d_focus\| of near/far assignments, p50 / p99 | 3.0 / 6.0 µm |

All four detector × window runs are in [`rerun_results.md`](./rerun_results.md). With the legacy
`[80, 8000]` px² window, the old paper's numbers come back (2026-11-05, ξ = 0): edge 18 823 detections, median
0.037 mm, 70 / 30; watershed 52 302, median 0.076 mm (0.075 before ξ = 0), 72 / 28. The legacy window was tuned to a
guessed ~52 µm crystal, so it only matches those old numbers.

## The near/far split is a tie-break, not a finding

The assigned depths lie within ≈ 6 µm of focus. There the near and far hypotheses imply sizes that
differ by only ≈ 2δ/d_focus ≈ 0.02 %. For 99.6–99.9 % of the off-focus detections in every run,
their prior likelihoods are therefore equal to within ±0.002. `side = "near" if p_near > 0.5` then
decides on the sign of a rounding-level difference. The 70–80 % "near" shares (and the earlier
79 / 21) say nothing about where the slurry sits. The two interpretations once offered (slurry in
front of the focal plane, or a right-skewed prior) are both unsupported at this aperture.

## Why the size signal is so weak here

The thin-lens geometry is `d_focus = 55.42 mm`, `K = f²/(N(d_focus − f)) = 37.5 mm` at F/1.6. A
symmetric pair needs **δ ≈ 1.3 mm** for a 5 % size ratio. The detector loses edges once the CoC
reaches a few resolution elements. The resolution element is the CCD cell / PAL sample (6.5 µm
geometric mean at the sensor), not the upscaled clip pixel, so that happens at |δ| ≈ 48 µm (5 PAL
samples), where the ratio is 0.17 %. The in-focus half-slice (CoC ≤ 1 PAL sample) is ±9.7 µm at
F/1.6 and ±97 µm at F/16. The figures and the paper quoted ±4.2 µm, ±21 µm and 0.08 %, which use
the clip pixel (2.9 µm).

Which crystals are in front of the lens depends on the time since seeding, not on a fixed
population. On the seed pan (ZRA) the slurry is ≈ 10–19 µm (microscope, `MICRO.jpg`), 22–35 µm
two minutes after seeding, and 0.2–0.8 mm two hours later (A. Fedor's microscope run 2026-10-30,
values AI-transcribed from the photo overlays, [`../../datasets/README.md`](../../datasets/README.md)).
The Mastersizer of the slurry (Dv50 6.81 µm, `docs/Granulometry_Zuckerslurry Se 2025-01-16 A.pdf`)
describes only the seeding material. The clip's own time since seeding is unknown: its date is
disputed, and the "≈ 2 h after seeding" label was a batch-match prediction (`datasets/README.md`).

## What would make disambiguation work

1. Stop the lens down (F/16 widens the slice ≈ 10×; the recommendation stands).
2. A detector validated against hand labels (Cellpose, Phase 1 of `papers/cep/ROADMAP.md`) that
   finds blurred crystals, so detections reach |δ| of a millimetre.
3. Optical flow over consecutive frames (apparent speed ∝ 1/d_o) instead of a size prior.

## Superseded history

- 2026-06-13 run (e = 10 mm, then 45 mm, d_focus 62.2 mm, 2.18 µm/px, Hanwha 2.9 µm pitch): median
  0.052 mm, 79.2 / 20.8. Its reading as "seed magma, first hour of a 4-hour A-strike, operator
  confirmed" is **retracted**: the camera is on the seed pan, and no operator confirmation exists.
- 2026-09-07 note (e = 60 mm "measured on site"): the geometry values are the plant's approximations
  from the 2026-08-12 Q&A ("≈ 6 cm", "≈ 2 cm", "20 mm"), not site measurements.
- The DVR-overlay crop finding stands: the glyphs created thousands of false detections and pushed
  α from 4.57 to 5.36.

## CSV columns (`crystal_observations.csv`, git-ignored, rewritten by each run)

`frame_idx, x_px, y_px, apparent_size_px (sqrt(w·h) in frame px), sharpness_score, s_normalised,
coc_mm, d_near, d_far, w_near_mm, w_far_mm, p_near, side, physical_size_mm`.
