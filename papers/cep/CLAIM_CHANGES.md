Proposed claim changes for author approval (branch docs/cep-grounded-draft)

## §5–§8: detection.tex, sizing.tex, csd.tex, growth.tex (draft-detection)

Each line: old → new. Evidence in brackets. Nothing here depends on hand-labelled crystals; those results are `\pending{}`.

1. §5 layers: "min-max-normalised quantile binning" of sharpness → uniform quantisation of a score 0.7·(1 − sharpness) + 0.3·Farnebäck flow; layers are not depth measurements. [`annotator.depth.segment_layers`, `optics.csd.main` LayerConfig]
2. §5 edge filter: "80–8000 px², aspect ≤ 3" → window from config `[9, 356 474]` px² on 1080p (PAL `[9, 71 020]`), aspect ≤ 3. [`optics.config.detection_area_px`; rerun rows 32–33]
3. §5 / fig 11: "55 features", "bandpasses ≈ 15–150 µm", "well above the ≈ 9 µm crystal population" → 840 detections (292 with the legacy window); legacy window = area-eq 15–150 µm (13–131 µm x, 17–171 µm y); the ≈ 9 µm population claim is removed. [rerun rows 32, 52–53; datasets/README.md microscope]
4. §5 selectivity / fig 10: "CoC 5 px at δ ≈ ±21 µm, 0.08 %" → ±47 µm, 0.17 % with the PAL sample (6.53 µm) as resolution element (±21 µm / 0.08 % stated as the clip-pixel value); the 5-element cutoff is labelled an assumption. Caption now says the plotted 0–50 mm range hides both values. [rerun rows 19–20, 24–26]
5. §5 size: µm sizes now use the geometric-mean scale 1.673 µm/px (was 1.66 isotropic); chords differ −12 % / +14 % per axis. [rerun rows 3–5]
6. §6 ambiguity: cite SellentFavaro2014 instead of Zhou2011. [SOURCES.md I-22]
7. §6 homog: "Earlier framings (Wadinger, internal working notes) …" revision history removed.
8. §6 implementation: now states the code's choices (85th-percentile focal subset, 99.5 % normalisation, 60-bin prior, σ_floor = half a clip pixel, tie-break p_near > 0.5). [`optics.disambiguate.disambiguate`]
9. §6 / fig 09: "79 % near; slurry sits slightly closer than focus, or right-skewed prior" → near/far is uninformative at F/1.6: 99.6–99.9 % of p_near within 0.500 ± 0.002; splits (76/24, 72/28, 70/30, 80/20) are tie-break outcomes; near wins above the prior mode, far below. Depth offsets 3.1 / 5.6 µm (p50/p99), size ratio ≤ 2 × 10⁻⁴. [rerun rows 66–67, 78–79, 90–93, 102–103; fig 14 right panel]
10. §6 fig 09 caption: "±0.005 mm", "0.01 %" → clusters at 55.097 / 55.103 mm, n 52 784 (33 957 / 10 909 / 7 918), mean correction 0.005 %. [rerun rows 92–93; docs/optics/rerun_results.md figure table]
11. §6 fig 07: 1.659 / 1.665 / 1.671 µm/px → 1.460×1.907 / 1.465×1.914 / 1.471×1.921 µm/px; window 48× → 21× the ±9.4 µm half-slice; generator `scripts/rerun_paper_numbers.py --fig07` (not `scale-overlay-demos`, which draws the wrong scale). "Sharpness maps indistinguishable because no pixel changes category" → the map is computed from the image and is identical by construction. [rerun rows 27–31]
12. §6 sharpness+motion "deterministic per-crystal assignment, near-certain once flow is reliable" → removed: apparent velocity scales with the same d_far/d_near ratio (≤ 2 × 10⁻⁴ at F/1.6), so motion does not help at this aperture. [derivation from eq. (ratio) and rerun rows 93]
13. §7 preface and §7.2 "Process interpretation — retracted": retraction/revision-history passages removed; section reframed as a failure analysis.
14. §7 "population in front of the lens is the ≈ 9 µm Mastersizer distribution" → seed slurry 1.56/6.81/18.5 µm before seeding; in the pan the microscope (2026-10-30) gives 29 µm median at 2 min, > 0.1 mm from 30–40 min, 0.48 mm (0.22–1.14) at 122 min. Table of 11 of 20 samples added. [`scripts/microscope_summary.py`, `datasets/microscope_annotations.csv`]. Note: the task text quoted "0.23–0.82 mm at ~2 h" from the first 4-photo reading; the full transcription of the same 13:32 sample gives 0.220–1.137 mm (n = 26), so the table uses the script output.
15. §7 new: the configured 1 mm max size excludes the 1.137 mm chord at 122 min (bound was set from the 0.821 mm first reading). For the config owner: revisit `max_size_um` (CHOICE). [configs/camera_100.toml; microscope_summary.py]
16. §7 new: case-study clip has no matched reference (date contradicted; 1 h 41–1 h 48 min even on 02-04, not "≈ 2 h"). [datasets/README.md; scripts/check_clip_overlap.py, scripts/check_anchors.py]
17. §7 edge CSD table "18 823 / 0.037 / CV 0.83 / s 0.57" → kept as the legacy-window column beside the configured window (47 414 / 0.018 / CV 2.16 / s 0.80); conclusion: the edge distribution follows the area window. [rerun rows 58–81]
18. §7 watershed: "median 0.074, CV 0.40, s 0.40, 52 302", "verified Camera 100 hardware configuration" → 0.075 / 0.43 / 0.41 / 52 784 (configured) and 0.075 / 0.40 / 0.40 / 52 302 (legacy); the watershed output follows its seed constants, not the window. Evidence in repo: window insensitivity (rerun rows 82–105) and the 12 px seed floor (code). Supporting evidence NOT in repo: a scratch sweep of `_PEAK_MIN_DISTANCE`/`_PEAK_THRESHOLD_ABS` on frames 300/750/1200 (median basin 36 → 53 → 90 px for constants 6/3 → 12/6 → 24/12). Paper text is qualitative ("largely reflect"); a sweep script should be added before submission. [Round 4, 2026-11-04: the committed `scripts/watershed_seed_sweep.py` (frames 300/750/1200, layers pooled) gives median basins 36.5 / 45.2 / 90.3 px for 6/3, 12/6, 24/12; the scratch value 53 px for 12/6 is not reproduced; App B cites the committed numbers.]
19. §7 fig 17 / §watershed: "102 / 740, legacy found ≈ 14 %", "order of magnitude consistent with a visual count" → 441 / 981 in the figure (code default window 50–50 000 px², aspect 4), 840 / 966 under the configured window; visual-count claim removed. [rerun rows 54–57]
20. §7 "three things move as a better detector should" (median doubles, CV halves, near/far toward 50/50) → removed; a narrower CV is not evidence of a narrower crystal distribution; near/far is a tie-break. [rerun rows 82–105]
21. §7 edge failure mechanisms (closing merges clusters rejected by max_area; facets invent crystals; peripheral bias) → removed: under the configured window max_area no longer rejects merged blobs; the other two were visual impressions without labels.
22. §7 homogeneous-slurry check "close agreement … consistent with homogeneity" → the subsets differ (near empty below ≈ 0.05 mm), explained by the tie-break; agreement would not have proven homogeneity anyway. [fig 14 right panel, regenerated]
23. §7 depth correction "0.00001 mm (0.01 %)", "DoF ±4.2 µm, a slab the size of a median seed crystal" → 0.005–0.013 % across four runs; half-slice ±9.4 µm (PAL sample). [rerun rows 16, 68, 80, 92, 104]
24. §7 watershed "standard treatment in cell-biology image analysis", "~50-line drop-in" → "a standard image-segmentation method". [SOURCES.md O-13]
25. §7 new subsection: validation protocol against hand-labelled crystals (label set from `crystal-detector-annotate export`, IoU ≥ 0.5 matching, P/R/F1, Cellpose AP@0.5 on held-out frames, inter-annotator ceiling, matched-pair size bias, camera vs microscope medians at matched times on 2026-10-30, ROADMAP Phase 1 acceptance). All results `\pending{}`.
26. §8 "growth-curve fit implemented as scaffolding in src/optics/csd.py" → no fit exists; `scripts/rq4_*.py` exploratory, no result reported. [grep of src/optics/csd.py]
27. §8 "Δx identifiable from data alone — no caliper, no scale target, no plant intervention" → not identifiable from the camera alone ((λΔx, λG, λo_b) fit equally); the scale needs G anchored by an independent size reference, e.g. the 2026-10-30 microscope series. [derivation from eq. growth]
28. §8 "breaks the 79/21 near-side split explanations" → removed (split is a tie-break). "v0.3 revision … closes RQ1–RQ3 fully" → removed.
29. §8 new: microscope growth medians b1 29 → 483 µm (2 → 122 min), b2 10 → 399 µm (0 → 162 min); at 96 min 355 vs 225 µm. [`scripts/microscope_summary.py`]

Cross-section notes for other writers (not edited here): fig 13 pipeline diagram still claims Stage F growth calibration is implemented (intro); discussion.tex still states s = 0.39, "~9 %", "≈ 9 µm population", "close agreement" of depth subsets; defocus.tex should use the same "one pixel" as §5–§7 (PAL sample). `\pending` needs `\newcommand` in main.tex (detection.tex has a `\providecommand` fallback). Captions use `\texttt` because `\code` (url) breaks in moving arguments.

## §2 Hardware, §3 Optics, §4 Defocus (hardware.tex, optics.tex, defocus.tex; writer: draft-optics)

Scripts: `uv run python -m optics.scale_chain` (docs/optics/scale_chain.md), `uv run --frozen python
scripts/rerun_paper_numbers.py [--no-video]` (docs/optics/rerun_results.md, row numbers below),
`uv run python -m optics.error_budget`, `uv run python scripts/check_clip_overlap.py`,
`uv run python scripts/microscope_summary.py`; config `configs/camera_100.toml`.

| # | Old claim | New claim | Evidence |
|---:|---|---|---|
| H1 | Camera is a Hanwha HCB-6000, 1/2.8" CMOS, 2.9 µm, 5.57 × 3.13 mm, 1920 × 1080 | Analogue monochrome PAL CCD labelled "ADEMCO VIDEO"; best-matching model ACM570E-class (752 × 582, 6.50 × 6.25 µm), alternative ACM380E-class (500 × 582, 9.8 × 6.3 µm), to be confirmed; HCB-6000 ruled out | photos 2026-08-10 (rear DIP panel); config `[camera]` (ESTIMATE); PolzQuote2025 is the only HCB-6000 source; AdemcoACM380E manual (NTSC-type counts only) |
| H2 | e = 60 mm, a = 20 mm, F/1.6 "operator measurement 2026-06-15, corrected 2026-09-07", "camera side operator-verified" | e ≈ 60, a ≈ 20, t 20 mm, F/1.6 are plant statements (Q&A 2026-08-12); focus travel 1 mm is our estimate; CS→C ring open | config `[lens]`, `[sight_glass]` classes; Q&A items 8–9 |
| H3 | "borosilicate sight glass marked DIN 8902", Ø150, 20 mm "measured on site 2026-09-07", PN10 flange | stamp reads "DIN 890…"; DIN 8902 would be soda-lime, model assumes n_g = 1.47 (borosilicate); Ø ≈ 150 / 20 mm plant; 8-bolt flange (photo); PN10 dropped | config `[sight_glass]`; DIN8902, SchottBorofloat33 (SOURCES.md) |
| H4 | (none) | Signal chain: DVR samples PAL at 13.5 MHz → 6.831 × 6.250 µm per sample/line at the sensor; 1080p clips are DVR screen recordings stretched 2.6773 × 1.8755 (OSD lever arm, 27 fits 2.6752–2.6795), clip px 2.552 × 3.333 µm, 1.306 anisotropy; clips add no resolution | `python -m optics.scale_chain`; config `[dvr]`, `[display_1080p]` (MEASURED stretch) |
| H5 | (none) | Spectral-isotropy check 1.002 / 1.065 / 1.132 vs predicted 1.093: ±10 % consistency only | `python -m optics.scale_chain` |
| H6 | Case-study clip implicitly dated 02-04 / growth stage implied elsewhere | Date uncertain (operator 02-04 vs file times and no shared frames with the 02-04 PAL recording → 02-05); strike phase and time since seeding unknown | `scripts/check_clip_overlap.py`; datasets/README.md |
| H7 | Black bars "leftmost ~40, rightmost ~55 columns", "analogue capture pads 4:3 into 16:9", Laplacian² ~110 vs ~10 | Picture spans columns 42.4 to 1869.5–1878.0 (left = DVR mask, right = analogue line end, moves ~8 px); Laplacian² numbers dropped (no script) | `python -m optics.scale_chain` (picture edges) |
| H8 | Crop 1800 × 905 ≈ 78 % | Automatic crop 1826 × 906 (80 %) is what the pipeline uses; fixed crop 1800 × 905 (79 %) | rerun rows 46–47 |
| H9 | Revision note 2026-09-07 (geometry rerun) | Removed (revision history) | — |
| H10 | (none) | Size references: Mastersizer sampled 2025-01-16, measured 2025-03-04 (AGRANA); microscope 2026-10-30 slurry 10–19 µm, b1 median chord 29 µm @ 2 min → 483 µm @ 122 min (operator-picked, single AI transcription) | Mastersizer2025; `scripts/microscope_summary.py` |
| O1 | Isotropic 1.66 µm/px at focus (1080p) | 1080p x 1.464 [95 % 1.336–1.624], y 1.913 [1.752–2.116]; PAL x 3.919 [3.576–4.347], y 3.586 [3.285–3.967]; +8.9 % if the 5 mm ring is in the tube; geometric mean 1.673 (1080p) / 3.749 (PAL) for areas only; all ESTIMATE | `python -m optics.scale_chain`; rerun rows 3–6 |
| O2 | (none) | Budget ±9.8 % x / ±9.5 % y (95 %, MC 200 000); e ±5 mm −7.6/+8.9 %, f ±2 %, line ±2 % (x), x 0–2 mm −1.6/+1.7 %, candidate < 1 %; n, t, a do not enter at focus | docs/optics/scale_chain.md |
| O3 | Fig 01 "1.66 µm/px, verified by operator caliper 2026-06-15" | 3.75 µm/px = geometric-mean PAL sample (6.53 µm at the sensor); per-axis values in Table 2 | `python -m optics.plots` (fig 01); rerun row 16 pitch 6.534 |
| O4 | "defocus centroid sits exactly where geometric optics places it (Pertuz2013)" | chief-ray argument, no cite | SOURCES.md (Pertuz2013 does not support it) |
| O5 | Paraxial shift "adequate for sub-percent pixel-pitch budgeting" | Shift moves the plane, not the scale; residual distortion not computed; n_g = 1.52 would give Δ = 6.84 mm | rerun row 10; SOURCES.md (no script for "< 1 %") |
| O6 | "factor-of-6 revision shrinks 10.4 → 1.66 µm/px", "e = 10 was 4.5× too short", "median 4.8× too large", 0.25 → 0.037 mm history, retraction text | e = 10 vs 60 mm: 5.55× in µm/px (8.12 × 10.61 µm/px on a clip pixel); revision history removed; tube must be measured because in-scene crystal size changes > 10× per strike (microscope 29 → 483 µm) | rerun rows 12–14; `scripts/microscope_summary.py` |
| O7 | Fig 06 "e = 10 mm (blue)" | e = 10 is orange; curves drawn without focus travel | fig 06 as regenerated |
| O8 | §3.5 autocorrelation 42.5 px → 0.14 mm, "≈ 9 µm seed-magma population" | Subsection removed: 42.5 px has no script (0.125 mm at µm_x if kept); ≈ 9 µm claim contradicted by the microscope | rerun rows 35–36; datasets/README.md |
| O9 | Dent analysis (medians 11 664 / 12 996, c = 5.8 µm, d_dent 55.074 mm, focal plane "8 µm past the inner face", face table, fig 17 dents) | Removed: c and the medians have no generating script, fig 17 dents has no generator and is drawn for d_focus = 62.2 mm. Replaced by a conditional consistency check: if focus is at the inner face, H is 21.5 ± 3.4 mm (1σ) behind the front element and H′ 12.0 mm, both inside the 30.5 mm body; not a measurement | rerun rows 37–43; `python -m optics.error_budget` |
| O10 | Fig 18 caption "focal-plane offset δ ≈ 8 µm recovered in situ" | Layout to scale; focus-at-inner-face and H → focus 61.5 mm marked as assumption | `python -m optics.optical_layout` |
| O11 | Focal slab "~8 µm into the slurry", "±21 µm detector cutoff", "FWHM 4.9 µm" in §3 | In-focus slice ±9.4 µm (PAL sample), conditional on focus at the inner face | rerun row 16 |
| D1 | In-focus slice ±4.2 µm (F/1.6), ±42 µm (F/16), "about the size of a median seed crystal" | ±9.4 / ±94 µm with the PAL sample (6.53 µm) as resolution element; clip-pixel values ±4.2 / ±42 shown only for comparison; seed-crystal comparison removed | rerun rows 16–17, 21–22 |
| D2 | Sharpness FWHM 4.9 µm | 10.5 µm (PAL floor; 4.5 µm with a clip pixel) | rerun rows 18, 23 |
| D3 | Fig 04 apertures F/1.6, F/2.8, F/4, F/8, F/16 | F/1.6, 2, 4, 8, 16 (engraved stops, as drawn) | config `lens.iris_stops` (PHOTO) |
| D4 | σ_diff ≈ 0.42 λN cited to Goodman §6.4 / Smith §11 | cited to ZhangZerubia2007 (0.21 λ/NA, NA ≈ 1/(2N)) | SOURCES.md |
| D5 | σ ≈ c/2 as an established result | σ = k c with a camera constant; k = 1/2 is our choice (uniform disk: c/4 per axis); it sets the FWHM, not the exponent | SOURCES.md (no page-checked source) |
| D6 | S ∝ (σ² + σ0²)^(−5/2) "the analytical prediction"; fig 03 "visual proof" of δ^−5 | Exponent 5 holds for a 1-D integral over a flat texture spectrum; 2-D with spectrum ∝ |ν|^−β gives (6 − β); fig 03 right panel restates the model's asymptote | derivation in defocus.tex §4.2 |
| D7 | α = 4.88 "matches theory α = 5 within 2.4 %", "quantitatively confirming the Gaussian-PSF + diffraction-floor model"; v0.1/v0.2 "false positive" history | α is an empirical slope of the per-pixel log1p(G * Lap²) density over its 50–95 % band; crop sensitivity 5.36 / 4.57 / 4.88 / 4.90 (auto crop, fig 08); no relation between α and the c^−5 law has been derived (uniform depth would give p(S) ∝ S^−6/5, exponential in log S); closeness to 5 is not evidence for the model | rerun rows 48–51; fit band = mode to just past it (diagnostic: `collect_sharpness_histogram` CDF 50/95 % at log1p 2.13 / 3.09, mode 2.13; not in a repo script) |
| D8 | Fig 08 caption "fit superimposed on the upper-half tail", "theoretical density… expected cusp shape" | Fit line extends the fit beyond its band and does not describe the upper bins; right panel (uniform depth ±5 mm) degenerate at this depth of field | fig 08 as generated by `python -m optics.measure`; rerun_results.md figure table |

## Title, abstract, highlights, keywords, §1, §9, §10, Appendix A (main.tex, highlights.txt, introduction.tex, discussion.tex, conclusions.tex, appendix_reproduction.tex; writer: draft-main)

Each line: old → new. Evidence in brackets (scripts as in §2–§8 above; literature verdicts by row of `SOURCES.md`). Nothing here depends on hand-labelled crystals; those results are `\pending{}`.

1. Title "Depth-aware crystal-size-distribution measurement from a single sight-glass camera, with growth-curve self-validation" → "Towards in-line crystal sizing through the sight glass of an industrial sugar seed pan: pixel scale, depth of field and detector failure modes". [no size measurement exists (§7); no growth fit exists (§8, `src/optics/csd.py`)]
2. Abstract framing "dominant instruments are expensive probes or off-line with cycle times longer than the operator decision interval"; "published approaches treat calibration as a prerequisite and DoF as nuisance" → "we found no reported in-line size measurement through the sight glass of an industrial sugar pan". [SOURCES I-13, I-15, I-17]
3. Abstract hardware "Fujinon HF35HA-1B + Hanwha HCB-6000 … 60 mm extension tube (verified by operator caliper measurement)" → analogue monochrome PAL CCD camera, 35 mm lens, extension tube of about 60 mm (plant statement). [hardware H1, H2]
4. Abstract result "median 0.074 mm, s = 0.39, CV ≈ 0.40, internally self-consistent distribution" and "(prior version 0.037 mm / CV 0.83)" → not reported as a result; "two classical detectors return size distributions set by their area window or seed spacing, not by the crystals". [rerun rows 58–105]
5. Abstract "1.66 µm/px; area filter bandpasses ≈ 20–200 µm and excludes the ≈ 9 µm crystal population" → removed; "median crystal chords growing from 29 µm to 483 µm within two hours of seeding" (b1, 2 → 122 min). [`scripts/microscope_summary.py`]
6. Abstract "geometric, defocus and disambiguation stages are validated against textbook optics and the sharpness statistics" → removed. New: 1080p clips are screen recordings stretched 2.677 × 1.875 and add no resolution; scale 1.464 × 1.913 µm (clip px) and 3.92 × 3.59 µm (PAL sample), about ±10 % at 95 %, dominated by the tube; ±9.4 µm in-focus slice at F/1.6; mean depth correction ≤ 0.013 %; 99.6–99.9 % of off-focus detections at p_near = 0.500 ± 0.002. [`optics.scale_chain`; rerun rows 16, 68–104]
7. Abstract "growth-curve self-validation promotes the pipeline to a soft sensor … removing residual dependence on hardware calibration" → "a growth-curve calibration of the scale needs an independent size reference". [growth.tex: (λΔx, λG, λo_b) fit equally]
8. Highlights (all five replaced): "Thin-lens model fixes the scale at 1.66 µm/px" → "Analogue PAL chain gives 1.46 × 1.91 µm per clip pixel, about ±10 % at 95 %"; "tail exponent 4.88 matches 5.0 within 2.4 %" → removed (α is not a test of the model, defocus D7); new "1080p screen recordings of the PAL camera add no resolution"; "A focal-plane size prior can break the front/back ambiguity" → "a size prior cannot tell front from back"; "±4.2 µm; F/16 ±42 µm" → "±9.4 µm"; "detector sees 20–200 µm features, not the 9 µm crystals" → "Classical detector size distributions follow detector settings, not crystals" and "seed-pan crystals grow from 29 to 483 µm in two hours". Highlights are no longer typeset in the PDF; `highlights.txt` is the CEP submission file (saves the extra page against the 20-page limit).
9. Keywords 8 → 6: dropped "depth from defocus", "Bayesian prior", "homogeneous-slurry", "open-source pipeline"; added "depth of field", "measurement uncertainty"; "through-sight-glass imaging" → "sight-glass imaging".
10. §1.1 "three-massecuite scheme … run for three to four hours (Bubnik1995, Asadi2006)" → Sereď three-product scheme with A, B, C pans and the seed pan ZRA (SlovenskeCukrovary2026); strike duration removed (the Sereď 2.8–4.0 h needs a script). [SOURCES I-1, I-2]
11. §1.1 "MA drives classification, CV controls centrifuge efficiency; rework at energy and yield cost" → MA/CV as the product specification, Sereď MA 0.76–0.95 mm. [Bennar2010, Daniels2017; SOURCES I-3, I-4]
12. §1.1 proxies "conductivity, refractive index, boiling-point elevation" → end of concentration judged by eye, touch or conductometrically; DCS trends brix, vacuum and stirrer current. [Bennar2010 p. 42; SOURCES I-5]
13. §1.1 "among the most-requested unsolved sensor problems" → "remains an active topic of process analytical technology". [SOURCES I-6]
14. §1.2 FBRM "biases the CSD by 15–40 %", "50–150 kEUR", "window fouling a heavy maintenance burden" → removed; ill-posed chord-to-size inversion needing a probe and shape model (Wynn2003, Kail2009, Czapla2010); fouling stated only for ATR probes (Borissova2009). [SOURCES I-7, I-8, I-9]
15. §1.2 PVM "no calibrated size, very shallow DoF (Wynn2003, Eggers2008)" → in situ microscopy and flow-cell imaging with image analysis (Eggers2008, Kempkes2008). [SOURCES I-10]
16. §1.2 "NIR and Raman" → ATR-FTIR (Borissova2009); acoustic-emission sentence removed. [SOURCES I-11, I-12]
17. §1.2 off-line "shortest practical cycle 30–60 minutes" → Sereď seed-slurry sample taken 2025-01-16, measured 2025-03-04 by a central laboratory. [Mastersizer2025; SOURCES I-13]
18. §1.2 "hardware investment is a few hundred Euro" → "a replacement box camera was quoted at 125 EUR without lens". [PolzQuote2025; SOURCES I-14]
19. §1.2 "demonstrated for pharmaceutical crystallization (Larsen2007, Borchert2014)" → now Ferreira2011 (lab sucrose), Daniels2017 (off-line massecuite), SimonNagy2009 (through the wall), Larsen2007 (glycine), Borchert2014 (KDP), Gao2018 and Salami2021 (deep learning); "We found no peer-reviewed in-line CSD measurement through the sight glass of an industrial sugar pan". [SOURCES I-15, I-16]
20. §1.2 "two persistent weaknesses: calibration as prerequisite; DoF universally ignored" → removed; replaced by three properties of the installed setting (plant-stated geometry without a scale target, analogue chain sets the pixel grid, thin in-focus slice with front/back ambiguity). [SOURCES I-17]
21. §1.3 front/back ambiguity Zhou2011 → SellentFavaro2014; the building-block list removed (each tool is cited where it is used). [SOURCES I-22]
22. §1.4 problem statement "deliver a per-frame CSD accounting for DoF, UQ on every output, soft-sensor read-out of time-since-graining validated against the wall clock" → removed (not delivered).
23. RQ1 "bounded by in-scene evidence alone" → scale per axis from documented and plant-stated inputs; RQ2 "agree with the Gaussian-PSF prediction, to what precision" → slice thickness and crop robustness of sharpness statistics; RQ3 "can the ambiguity be broken" kept as a question, answered no at F/1.6; RQ4 "per-batch median collapses to one curve and identifies lens-stack parameters" → do classical detectors measure size, and what is needed. [§3–§8 as rewritten]
24. §1.5 fig 13 pipeline diagram ("every block implemented", Stage F "growth-curve self-calibration identifies extension tube + F-number") → figure removed from the paper; the pipeline is one sentence. [no growth code in `src/optics/csd.py`; rerun_results.md figure table]. If the figure returns, `src/optics/pipeline_diagram.py` must drop Stage F and the "all blocks implemented" footer.
25. Contributions "complete pipeline delivering calibrated CSD … growth-curve self-validation", "framework that breaks the front/back ambiguity", "validated industrial case study" → source-classed signal-chain model and per-axis scale; DoF with the PAL sample and crop sensitivity; negative result for size-prior disambiguation; detector failure analysis with microscope reference, pending validation protocol and growth identifiability condition; reproducible audit trail.
26. §9 "geometric optics chain closed end-to-end … self-consistent mm/px to ~10 % with in-scene anchoring" → scale modelled per axis, about ±10 % at 95 %, +8.9 % if the CS→C ring is in the tube; no in-image anchoring; "not measured in the image" stated as the first limitation. [`optics.scale_chain`]
27. §9 "Defocus structure matches theory to ~9 %", "α = 4.88 within 2.4 % of 5.0" → α 5.36 → 4.88–4.90 with cropping, not a test of the model. [rerun rows 48–51; defocus D7]
28. §9 "homogeneous-slurry self-consistency check passes" → homogeneity untested; subsets differ because of the tie-break. [§7.4]
29. §9 "median 0.074 mm, CV 0.40, s = 0.39 … verified Camera 100 hardware configuration" → removed; neither detector measures size; resolution is not the obstacle from ~30 min after seeding (medians > 0.1 mm = tens of PAL samples). [rerun rows 82–105; microscope_summary.py]
30. §9 "±4.2 µm window … 79/21 split could reflect the prior's right-skew" → ±9.4 µm; splits are tie-breaks (99.6–99.9 % at 0.500 ± 0.002). [rerun rows 16, 67, 79, 91, 103]
31. §9 "residual refractive distortion < 1 % at 1.66 µm/px" → not computed (limitation). [SOURCES O-4]
32. §9 "Without cropping the apparent agreement with theory (α = 5.36, +7 %) was spurious" → crop sensitivity only; right picture edge moves ~8 clip px, crops need a margin. [rerun rows 48–51; `optics.scale_chain`]
33. §9 "v0.1 anchored e ≈ 10 mm … 4.5× off the true e = 60 mm"; "caliper measurement or growth-curve self-calibration the only robust route" → revision history removed; geometry to be measured at the next shutdown.
34. §9 recommendation "stop down 4 stops; F/16 widens 10× to ±42 µm, letting disambiguation see the 3-D distribution" → F/16 gives ±94 µm; because the size ratio depends only on δ/d_focus and the admitted range grows ∝ N, even F/16 stays below δ ≈ 1.3 mm (5 % ratio); treat the camera as a thin-slice sensor at F/1.6. [rerun rows 17, 19, 26; Eqs. coc and ratio]
35. §9 recommendation "time-dependent detector parameters scheduled against the growth curve" → removed (no growth curve); replaced by a validated segmentation (fine-tuned Cellpose) with a window above 1 mm (1.137 mm chord observed). [microscope_summary.py]
36. §9 new recommendations: read camera sticker, caliper the tube/spacer, photograph the mount, read DVR model and glass stamp, image a ruler/graticule at the inner glass face; record the PAL stream; log DVR vs SCADA clock (agree to about ±30 s on 2026-02-04). [`scripts/check_anchors.py`]
37. §9 "Generalisation: pharmaceutical crystallisation, mineral flotation, polymer particulation; homogeneity check reports validity directly" → removed (not shown); replaced by a soft-sensor outlook ending in `\pending{validated camera size against time, 2026-10-30}`.
38. §10 conclusions "complete pipeline delivers calibrated depth-aware CSD", "optical model matches sharpness statistics to ~9 %", "disambiguation chains validated", "what is retracted is the size interpretation" → rewritten to the RQ1–RQ4 answers above.
39. Appendix A "10 tests" (tests/test_optics.py) → 28 optics tests (test_optics 17, test_scale_chain, test_provenance), suite collects 140; generator table now lists `optics.scale_chain`, `optics.error_budget`, `scripts/rerun_paper_numbers.py` (`--no-video`, `--fig07`), `check_clip_overlap.py`, `check_anchors.py`, `microscope_summary.py`, `optics.optical_layout`, `optics.detect_watershed`; `scale-overlay-app` dropped as fig 7 generator (it draws the wrong scale); audit trail `docs/optics/README.md` §§11–13 → `docs/optics/rerun_results.md` and `docs/optics/scale_chain.md`; fig 00 stated as having no generator. [`uv run pytest --collect-only`; rerun_results.md figure table]

Cross-section note (not edited here): optics.tex §3.2 says a column length is "15 % longer than with the geometric-mean pixel of 1.673 µm"; 1.913/1.673 = 1.143, so +14 % (as detection.tex says). The 15 % is relative to the old 1.66 µm.

## Fix pass on the validated review issues (writer: fix, 2026-11-03)

Each line: old → new [evidence]. All are proposed for author approval. New analysis numbers come from
`scripts/detector_checks.py` (`docs/optics/detector_checks.md`) and the diffraction rows appended to
`scripts/rerun_paper_numbers.py`.

40. Abstract novelty "we found no reported in-line size measurement" → "no peer-reviewed report"; intro adds that the sugar-trade literature and vendor pan cameras were not searched (`\pending`). [SOURCES I-15 covers peer-reviewed literature only]
41. Abstract / Table 2 / §3.2 / discussion / conclusions "±10 % at 95 %" → interval conditional on a 1/3" sensor and 13.5 MHz sampling; the +8.9 % ring case stated next to it; §3.2 adds that the scale ∝ cell width and ∝ 13.5 MHz / r, so a 1/2" CCD with the same cell count would be ≈ 33 % coarser (6.4 vs 4.8 mm format width), and that nothing checks the absolute scale. [configs/camera_100.toml sensor_format, sampling_rate_mhz = ESTIMATE; scale_chain.md]
42. Abstract "in-focus slice ±9.4 µm" → "with the PAL sample as resolution element, the air-equivalent in-focus slice"; §4.3 new paragraph: the PAL sample is an optimistic assumption (BT.601 luma passband 5.75 MHz ≈ 600 points per 52 µs line, interlace, H.264), measurement `\pending`. [ITUBT601; defocus.tex]
43. §4.2 diffraction σ = 0.42 λ N → 0.42 λ N_w with the working F-number N_w = N(1 + M) = 2.74 N (code fixed in `optics.psf`). Diffraction FWHM 0.37 / 1.83 / 3.65 PAL samples at F/1.6 / F/8 / F/16; reaches one sample at F/4.4. F/1.6 PAL FWHM unchanged (10.5 µm); clip-pixel FWHM 4.5 → 5.5 µm (tab:dof). [rerun_paper_numbers.py diffraction rows]
44. §4.3 / tab:dof / fig 04 / discussion / recommendation 4 "stopping down to F/16 widens the slice tenfold to ±94 µm" → ±94 µm is a geometric bound only; beyond ≈ F/4 no depth meets the one-sample criterion; recommendation: diffraction exceeds one PAL sample beyond ≈ F/4.4. Discussion keeps "stopping down does not reach δ ≈ 1.3 mm" (5-sample cutoff at F/16 ≈ ±0.47 mm). [as 43; Eq. coc]
45. Discussion "k = 1/2 sets the slice" → k sets the sharpness FWHM and the inverted CoC, not the in-focus slice or the exponent. [Eq. coc has no k]
46. §6.4 RQ3 negative result rested on the inverted depths (3.1 / 5.6 µm) → rests on the bound: δ ≤ ±47 µm (assumed cutoff) gives ≤ 0.17 % size difference, below a prior bin (≈ 2.5 % of the 99th percentile); inverted depths reported as model outputs set by the normalisation, k, the exponent 5 and σ_floor; a PAL-sample σ_floor would multiply them by 2.24 (≈ 7 / 12.5 µm); the gap in fig 09 is the focal subset by construction. [Eq. ratio; `optics.disambiguate._sharpness_to_coc` (c ∝ σ_floor)]
47. §6.2 new: the point-object depth model applies to objects thinner than the slice; crystals of 0.1–0.5 mm are 5–25× the 19 µm slice, so for them the model describes edge elements, and per-crystal near/far is undefined; RQ3 restricted to objects smaller than the slice. §7.6 "detections lie within a few micrometres of focus" → bound-based statement plus this restriction. [tab:microscope; tab:dof]
48. §6.2 new: static marks / adhered crystals as a confounder of the focal subset and of homogeneity (`\pending` temporal-median test). [optics.tex §slab; growth.tex rq4 scripts]
49. Contribution 3 "negative result for size-prior disambiguation" → "an analytic bound on size-prior disambiguation (≤ 0.17 %)".
50. Contribution 4 (blocker) "failure analysis … against a seed-pan size reference from 54 microscope photographs" → "label-free failure analysis on plant data: outputs over a full PAL strike, a watershed seed-constant sweep, the microscope size range a measurement must cover, and a pending validation protocol". [§7 has no camera-vs-microscope comparison]
51. NEW RESULT §7.5 / fig 19 / abstract / highlights / conclusions: over strike b2 of the 2026-02-04 PAL recording (−40 to +200 min, 13 times × 10 frames, configured PAL window), edge median 31–36 µm and watershed median 180–216 µm, flat, including before seeding; microscope medians of 2026-10-30 (another day) grow ≈ 17× (29 → 483 µm). [`scripts/detector_checks.py time`; seeding = sidecar b2-e06 12:30, SCADA steam cut 12:31:30]
52. §7.3 title / abstract / conclusions "watershed follows its seed constants … the count and median largely reflect the tiling" (no script) → "tiles the frame and follows its seed clearance": kept basins cover 86 % of the crop; median 87–89 µm for spacing 6–16 px, 63 / 88 / 108 µm for clearance 3 / 6 / 9 px, 60 → 148 µm jointly (6/3 → 24/12); new tab:ws-sweep. The scratch-sweep note of item 18 is replaced by this committed sweep. [`scripts/detector_checks.py sweep`, six single frames, so the configured median is 88, not 75 µm]
53. §7.2 / abstract "edge distribution set by the area window, not by the crystals"; "from outline fragments", "rectangles around blurred regions" → "depends on the area window"; fragment and blur readings marked visual, not checked against labels; whether in-window detections are crystals needs labels. Same for fig 11 caption.
54. Abstract / highlights / conclusions / §3.4 "29 to 483 µm within (in) two hours" → "in 122 min", "operator-picked chords"; §2.1 / §7.1 add single AI transcription with a `\pending` human second reading.
55. Table 3 adds the pre-seeding b1 11:30 row (18 / 33 / 42 µm, 27 s before seeding) with the open question (footing or nucleation); the b2 15:22 row is flagged for 2–3 µm sub-resolution chords; growth.tex flags the same. [datasets/README.md]
56. §7.1 / recommendation 3 "the 1 mm window excludes the 1.14 mm chord" → "may exclude crystals like" (area-equivalent bound vs single chord).
57. §7.7 acceptance "camera distribution inside the microscope range" → (a) median ratio within a factor 1.25 from 30 min, (b) slope of log median over 30–120 min within ±25 % (both analysis CHOICES for author approval); selection bias of the two methods discussed; 2026-10-30 capture chain unknown (`\pending`). [tab:microscope ranges are ≈ 5× wide]
58. Mastersizer Dv 1.56 / 6.81 / 18.5 (run 1) → mean of three runs 1.57 / 6.77 / 18.6 µm (D[3;2], D[4;3] stated as run 1); "sampled 2025-01-16" → "sample labelled 2025-01-16" (hardware, intro, csd, bib note). [docs/Granulometry_Zuckerslurry Se 2025-01-16 A.pdf, "Mittel"]
59. §2.4 now carries the "1 h 41–1 h 48 min under the operator's date" estimate with its source (trend photo, Krystal PDF p. 3; scripts/check_anchors.py; datasets/README.md); §7.1 points there. §2.4 also states why the clip stays the frame-level case study and introduces the PAL strike. Scale references `sec:camera` → `sec:chain` / `sec:budget`.
60. §2.2 adds the Honeywell HCC334/484 alternative from the plant notes and states that the 1/3" format is unconfirmed; docs/sered/README.md reconciled with the config candidate and the retired 2.9 µm / 1.66 µm/px.
61. §2.3 adds the picture-edge check (684.8 PAL samples vs 1827–1836 clip px → 2.668–2.681) and the OSD-before-scaling assumption; datasets/README.md stale sx = 2.553 paragraph replaced. [docs/optics/scale_chain.md picture edges]
62. §3.2 "15 % longer" → "14 %" (1.913 / 1.673 = 1.143); same in docs/optics/rerun_results.md.
63. Fig 07: three panels → one panel at focus (page limit); caption states 55.1 mm is the rounded config value, scales 0.07 % above the exact 1.464 × 1.913, HUD 1.47; near/far scales moved to the text.
64. Config `camera.body_length_mm` ESTIMATE → ASSUMED (drawing only); fig 18 shows "(assumed)" in red; caption updated.
65. Figures regenerated with neutral on-image text: fig 08 (one panel, fit drawn over the shaded 50–95 % band, suptitle and degenerate model panel removed), fig 09 / 14 ("not a crystal-size measurement", "tie-break", "inverted depths, model output", "area-equivalent detection size"), fig 10 (log δ 1 µm–5 mm, PAL sample, cutoff labelled assumed), fig 02 (log CoC axis, "c at d_o → ∞", no overlap), fig 05 (no "DIN 8902", n assumed), fig 17 (neutral titles).
66. Removed from the paper for the 20-page limit: figs 01 (µm/px vs d_o), 05 (sight-glass shift), 06 (tube sweep), 12 (sharpness layers), 17 (watershed vs edge, which also used a third area window). Their numbers remain in the text; generators unchanged.
67. Intro "a replacement box camera was quoted at 125 EUR" → "a supplier quoted 125 EUR … for a replacement box camera of a different type"; acknowledgement "camera-and-lens datasheet support" → "a supplier quotation"; CRediT carries a `\pending` that annotation and Cryst_CNN roles refer to work not in this version. [SOURCES I-14: HCB-6000 is not the installed body]
68. Overfull tab:inputs and tab:dof fixed (p{} column; shorter headers).

Not done (needs data or an author decision):
- Rerun on the 2026-10-30 recording (the strongest case study): the 123 GB FFV1 file is on the NAS, not mounted here; the 02-04 PAL strike (item 51) is used instead.
- Human second reading of the microscope overlays; effective-resolution measurement of the PAL chain; temporal-median static-mark test; sugar-trade / vendor literature search: all `\pending`.
- Journal fit (CEP vs a sensors / measurement venue): `cover_letter.md` no longer pitches a soft sensor validated on plant data; the author decides the venue.
- σ_floor in `optics.disambiguate` stays half a clip pixel (code unchanged so that tab:ws-compare reproduces); its effect is stated (item 46).

## Author-approved claim edits (writer: thesis-writer, 2026-11-03)

69. Camera scale is modelled, not validated; no absolute camera size. Approved by author 2026-11-03. Abstract, highlight 1, contribution 1, tab:scale caption, §3.2, §3.4, §5.1, fig 07 caption, §7 preamble, §7.1, §7.5 and fig 19 caption, §7.7 acceptance (a), §9.1, §9.2, §9.4, §10: "±10 % at 95 %" (stated as if bounding the scale) → the model's input-uncertainty budget, conditional on a 1/3" sensor, 13.5 MHz and the plant's "≈ 6 cm" being the tube alone (e = 60 ± 5 mm), not validated in the image; detector sizes in µm qualified as "at the modelled scale", detector outputs, not crystal sizes. Abstract and conclusions add: no absolute crystal size from the camera is reported; camera growth is treated in pixels (scale identified only via the microscope anchor, §8). Abstract trimmed to 249 words ("from the seed pan", "report of an", "camera … of about 60 mm" moved into the budget clause). New §7.7 paragraph "First matched-time reading" (`\pending{matched-time comparison script and figure}`): camera crystals at the modelled 3.92 µm/px ≈ 3× smaller than the microscope chords late in b1 (13:32: ≈ 230 crystals, largest ≈ 300 µm, vs single crystals 0.3–1.1 mm); not clumping or the detector; candidate causes (i) scale (tube), (ii) different population at the glass, (iii) orientation, 20–30 % only; a ≈ 30 mm tube (6 cm including the 29.5 mm lens body) gives M = 31/35 instead of 61/35, ≈ 2× coarser by itself (61/31 = 1.97); ruler/graticule at the inner glass face decides (i) vs (ii). [Parallel session: Cellpose outlines on 2026-10-30 camera frames vs microscope photos, single visual reading, no repo script yet; magnification (e + x)/f from Eq. thinlens]
70. Introduction citation wording. Approved by author 2026-11-03. (a) Borissova2009: "fouling of the probe crystal hinders routine use" → "can prevent routine use in unseeded crystallization" [the paper reports seeded runs worked]. (b) Daniels2017: "MA and CV are the usual specification in the industry" → "MA and CV are used to characterise sugar crystal size in the industry" [one company, Suiker Unie]. (c) Ferreira2011: "Image-based CSD monitoring has been shown for sucrose in the laboratory" → "… includes online image analysis of sucrose crystal size and morphology in the laboratory"; the rest of the list recast to noun phrases for grammar (off-line analysis of massecuite samples, imaging through the wall, in situ imaging of glycine and KDP), citations unchanged. [paper is mainly morphology and agglomeration, laboratory]

## Corrections after the 2026-11-03 discrepancy analysis (writer: subagent, 2026-11-03)

71. Correction after the 2026-11-03 discrepancy analysis; author-requested fixes. §7.7 "First matched-time reading" (item 69) and §9.1: "camera crystals ≈ 3× smaller than the microscope chords … neither clumping nor the detector explains the gap", causes (i) scale / (ii) wall layer or settled crystals / (iii) orientation, and the "≈ 30 mm tube → ≈ 2× coarser" reading → the camera p90 levels off against the microscope p90 (log-log slope 0.2–0.45) and its level follows the Cellpose diameter setting, so the time-varying gap is a detector failure: late raw frames show crystals ≈ 90–190 PAL samples across, comparable to the microscope at the modelled scale, which flat-field (201 px Gaussian divide) + CLAHE (8 × 8 tiles) split into 30–50-sample facets (220–290 outlines per frame where ≈ 37 microscope-size crystals fit); frames 60 s apart are uncorrelated (no static layer); up to 11:46 the crystals are 3–9 samples and the outlines texture. A residual constant factor ≈ 1.3–1.6 is undecided between the tube (site photos ≈ 40 mm, ×1.5) and operator selection; hand-traced whole-crystal outlines at matched times plus a bench stage micrometer through the locked lens decide it. `\pending{matched-time comparison script and figure}` kept. Orientation cause (iii) dropped with the old cause list. §9.1: "≈ 3× … a ≈ 30 mm tube alone ≈ 2×" → "residual ≈ 1.3–1.6 once fragmentation is set aside; photos read the tube ≈ 37–42 mm, alone ≈ 1.5× coarser". [scratchpad research/backward_data, backward_images (main session, 2026-11-03); M = (e + x)/f, 61/41 = 1.49]
72. Correction after the 2026-11-03 discrepancy analysis; author-requested fixes. §2.1: "8-bolt flange" → "bolted flange" (no photo shows the full bolt circle; plant notes said ~12, docs/lens/README.md 8); lamp added as an optical fibre "very close to the glass", est. 1–2 mm from the inner face (Q&A 8(D), not measured). §2.2: site photos read the tube ≈ 37–42 mm (tape measure, lens body as ruler) and the lens–glass gap ≈ 35–46 mm, contradicting "≈ 6 cm" / "≈ 2 cm"; the model keeps the plant values. §3.4: same photo reading; ≈ 40 mm → ≈ 1.5× coarser, so the ±5 mm tube spread of the budget is too narrow; the budget stays conditional on 60 mm. §3.6 "the camera samples the slurry layer pressed against the glass" → "a backlit projection through the ≈ 1–2 mm slurry slab between glass and lamp, sharp plane at the glass" (still conditional on the assumed focal plane, which is our drawing's, not a plant statement). [Aug-photos 20260810_111738/111741, sered/photos/1786375479369/391; scratchpad research/forward_optics; Q&A 8(D)]
73. Author-requested matched-time tracing (2026-11-03). §7.7: "a residual factor ≈ 1.3–1.6 undecided between a ≈ 40 mm tube and operator selection" → four blind AI annotators (two longest-chord, two full-outline following the team protocol) on 12 raw frames at 12:07/12:30/13:32/14:20: traced sizes grow with the microscope (p90 log-log slope 0.64 / 0.78); on the separate-crystal frames lab ÷ traced at the modelled scale is 0.86–1.02 (chords) and 1.14–1.32 (outlines); selection can only raise it, so the true scale is ≤ ≈ 1.3× the modelled one and the ≈ 40 mm tube (×1.49) is excluded for these frames; late packed frames 1.4–2.0 are not a measurement (outlines not closed, field partly tiled). `\pending{human annotation of the twelve frames}`. §3.4 and §9.1 updated to the bound. [scripts/traced_vs_lab.py; datasets/camera_traced_chords.csv, camera_traced_outlines.json, camera_traced_frames/]
74. Author decision 2026-11-04: the tube is Fedor's ≈ 6 cm (spacer ring alone), settled. The AI reading of the site photos (tube ≈ 37–42 mm, gap ≈ 35–46 mm; items 71–73) was never a measurement and is withdrawn. §2.2 and §3.4: photo reading and "contradicting the plant's ≈ 6 cm / ≈ 2 cm" removed. §7.7: "the 1.49 times of a ≈ 40 mm tube is excluded" → "the two methods differ by about 30 %, so the tracing cannot resolve the ±10 % budget". §9.1: "which excludes the ≈ 37–42 mm tube read from site photographs" removed. Config comments on tube and air gap likewise. [docs/sered/notes_plant_dcs_qa_photos.md:267; author 2026-11-04]
75. Author decision 2026-11-04: no CS-to-C adapter ring in the 6 cm. The ring alternative (+8.9 %) is removed: abstract, tab:scale caption and "With ring" column, §3.2, §2.2 ("is open … \citep{AdemcoACM380E}" → "taken as the spacer alone, without a 5 mm CS-to-C adapter ring"), §9.1, §9.3 rec 1 ("(CS-to-C ring)"), config comment. The matched-time tracing cannot distinguish the two cases (1.00 vs 1.09 against a 30 % spread between methods), so this is an author decision, not a fit. [author 2026-11-04]
76. Author request 2026-11-04: fig 19 and §7.5 in PAL samples, not µm (no absolute camera size, item 69). Edge median 31–36 µm → 8.4–9.7 PAL samples, watershed 180–216 µm → 48–58 (same detections, unit only; within 16 % and 20 %). Microscope triangles removed from fig 19 (placing them on a pixel axis needs the unvalidated scale); caption cites their 17-fold growth instead. [scripts/detector_checks.py time; docs/optics/detector_checks.md]

## Soft-sensor reframe (branch docs/cep-soft-sensor-frame)

Writer: thesis-writer, 2026-11-04. Brief: scratchpad `brief_reframe.md` (supervisor, plant-expert and optics-expert
round). Each line: old → new [evidence]. Everything is proposed for author approval; item 85 is a NEW scientific
claim. Estimator numbers come only from `docs/softsensor/results.md` (`uv run python scripts/softsensor_results.py`)
and keep its REAL / SIMULATED label.

77. Structure (pure moves, one line): section map applied. §1 Intro → §2 Process and data (`process.tex`: old sec:plant,
    csd sec:expected → sec:microscope, tab:microscope) → §3 Camera measurement model (`measurement.tex`: optics
    sec:budget PAL rows, sec:tube sensitivity, defocus sec:dof and csd sec:depthsmall as two sentences, sizing sec:homog
    projection and static-mark text, matched-time tracing) → §4 Growth model and observability (`growth.tex`) → §5
    Estimator and baseline (`estimator.tex`, with csd sec:validation) → §6 Results (`results.tex`, csd sec:csd-time and
    fig 19) → §7 Discussion → §8 Conclusions; App A optics (`appendix_optics.tex`: sec:camera, tab:inputs, sec:chain,
    crop paragraph, thinlens, shift one sentence, sec:slab, fig:layout, CoC/PSF short, sec:dof, tab:dof, fig:dof); App B
    classical detectors and near/far (`appendix_detectors.tex`: sec:recording clip, edge/watershed, tab:ws-constants,
    window, selectivity, fig:discrim, ambiguity/impl/result in one subsection, tab:ws-compare, tab:ws-sweep, first
    Cellpose reading); App C reproduction; App D glossary. Files hardware/optics/defocus/detection/sizing/csd.tex
    deleted from the working tree (content moved). Labels kept where the text moved; `\secref` on appendix labels
    replaced by `\ref` (elsarticle prints "Appendix A.x"); `Appendix~\ref` → `\ref` (it printed "Appendix Appendix").
78. Cut from the paper (one line): figs 00 (frames), 02 (CoC), 03 (sharpness), 07 (overlay), 08 (sharpness density),
    09 (disambiguation), 11 (detection overlay), 14 (detector distribution); tab:crop; sec:empirical except one crop
    sentence (α 5.36 vs 4.88–4.90, App A); sec:selfcheck; sec:overlay; sec:status; sec:softsensor outlook; the 10 mm
    tube "5.55× coarser" sentence; layer details; the 1080p clip from the main text (App B only). Numbers of cut
    passages remain in `docs/optics/rerun_results.md`.
79. Terminology (one line): seed pan (ZRA at first mention) for graining vacuum pan / vessel; seed slurry only for the
    input seed, massecuite (syrup before seeding) for pan contents, "homogeneous slurry" → well-mixed massecuite
    (all plant-expert misuse lines: hardware 14, 28, 32, 104, 107, 154; sizing 23, 25, 31; introduction 57; detection 17;
    defocus 83; optics 66, 111, 120; csd 166; discussion 48); strike for batch; sampled run of 2026-10-30 for
    laboratory run; DCS for SCADA / control system (DeltaV once); focal plane for focused plane; slab only for the
    1–2 mm glass–lamp gap; near/far for front/back, App B only; measurement gain λ and µm per PAL sample for pixel scale
    and µm/px in the main text; tightening for drying; detections / camera size signal y_k for detector "CSD".
80. Notation (one line): optics focus travel x → ξ, glass thickness t → t_g, refractive shift Δ → z_g, pixel extent
    Δ_k / Δx → scale μ_x, μ_y, CoC c → b and K → b_∞, PSF σ = k c → ρ = κ b, floors σ_0 / σ_floor → ρ_0, wavelength λ →
    λ_w, sharpness S → Φ, reciprocal distance u dropped, OTF H dropped, Gaussian kernel G → words, layers L → n_ℓ,
    h-maxima h → h_max, log-normal shape s → σ_ln, p_near → π_near, crystal width w → ℓ (P_w → P_ℓ), δ = signed
    defocus only (eq:ratio uses |δ|), spectral slope β → β_ν. Main text: x_k, L, G, θ, λ, b_sel, β(L), v_k / R, z_j /
    w_j, Q_G, F_k, C, C^z, n_f, τ_b, o_b, τ, u_k, c (scale factor of Proposition 1 only).
81. Title "Towards in-line crystal sizing through the sight glass … detector failure modes" → "Estimating crystal growth
    in an industrial sugar seed pan from an installed sight-glass camera" (brief option 2). Option 1 ("… soft sensor …:
    measurement model, observability and plant validation") is not used because no real-camera estimator result exists
    yet (item 99). Author decision.
82. Abstract rewritten around the operator decisions, the measurement model, the observability result, the negative
    control and the SIMULATED estimator result (log-size RMSE 0.31–0.32 → 0.09–0.11 with one anchor, slower strike
    flagged); removed: 1080p stretch, clip-pixel scale, front/back sentence, "report no absolute camera size"
    (superseded by the anchor result); 249 words. [results.md §3; abstract check]
83. Keywords → state estimation, Kalman filter, observability, soft sensor, sugar crystallization, sight-glass imaging.
84. Highlights, all five → soft sensor of seed-pan growth; log size plus constant offset and noise; camera alone
    observes relative growth rate and curve shape, not absolute size; one microscope sample makes absolute size
    observable; classical detector medians flat over a strike as a negative control.
85. NEW CLAIM, needs author approval. §4.2 Proposition 1 (scale symmetry) with proof: under L⁺ = L + GΔt (any G
    sequence, random walk in ln G) and y = ln L + θ + v, (L, G, θ) → (cL, cG, θ − ln c) leaves y unchanged, so L, G, θ
    are not observable from the camera; G/L, L/L_0 and, for constant G, L/G = t + o_b/G are; growth-rate and τ_b ratios
    between strikes sharing θ are; one anchor z_j fixes θ and with it L and G in every strike sharing θ. Local version:
    in (ln L, ln G, θ) the direction q = (1, 1, −1) satisfies F_k q = q and C q = 0, C^z q = 1. Promotes growth.tex
    lines 17–24 ("(λΔx, λG, λo_b) fit equally"). The brief's "y/ẏ = t + o_b/G" is written as 1/ẏ = L/G = t + o_b/G
    (y/ẏ was a typo). [derivation in the paper; SIMULATED check: rank 2, null vector [1, 1, −1], rank 3 with one anchor;
    σ_θ 0.160 → 0.160 without and 0.0875 with an anchor (diffuse priors); SD ln(G/L) at 60 min 0.449 either way;
    results.md §2; unit test tests/test_softsensor.py]. HermannKrener1977 cited for the rank condition only; the scale
    result is stated as our derivation.
86. §4.1 growth model: G random walk → random walk in ln G, state (ln L, ln G, θ) (author decision; the estimator
    agent's design: keeps the unobservable direction fixed and G > 0; with G the direction (1, G, −1) moves and the EKF
    gains spurious θ information). Nominal curve L(t; b) = L̄(τ_b t) + o_b, growth age τ = τ_b t, τ̂ < t flags a slow
    strike; time since seeding is not an estimand (DCS steam cut 12:31:30 vs note 12:30). [src/softsensor/ekf.py
    docstring and unit test; datasets/README.md anchor table]
87. §4.1 citations: size-independent growth with the Martins2007 caveat (growth per volume size-independent, per surface
    area size-dependent; M confidence, abstract only); growth driven by supersaturation (QuintanaHernandez2004). §4.2
    multirate fusion (Gudi1995, FatehiHuang2017) and bias augmentation (Friedland1969). [citation-finder list]
88. §4 "Status: no fit implemented; rq4 scripts no result" → cut; the estimator now exists in src/softsensor (§5).
    The tube-length argument (optics lines 89–93: size changes > 10× per strike, a wrong gain rescales the curve without
    inconsistency) moved into §4.1 as the motivation for Proposition 1.
89. §1.1 "operators judge the end of concentration by eye, by touch or conductometrically (Bennar2010)" → removed
    (unverified for Sereď, plant expert); "control system trends brix, vacuum and stirrer current" → "DCS trends level,
    vacuum, massecuite temperature, stirrer current and a signal on a Brix scale"; new: three operator decisions (draw
    into the A pans, boil-up feed / KP when growth is slow, end of tightening); "we know of no plant specification for
    the size of the seed massecuite"; crystal size only from samples. "grains the seed massecuite" → "grains each strike
    with seed slurry and produces the seed massecuite". [brief decision 6; docs/sered/README.md]
90. §1.2 condensed to one instruments paragraph (citations unchanged) plus a new soft-sensor lineage paragraph:
    Kadlec2009 (soft sensors predict low-rate / off-line quality variables), Damour2010 (CEP sugar soft sensor: crystal
    mass, concentration, purity, not size or growth), Morales2023 (supersaturation from level, Brix, temperature; M
    confidence, abstract only), Lohani2026 (supersaturation from standard process measurements; SELF-CITATION: Lohani
    and Paulen are co-authors), Mesbah2011 (EKF/UKF on a semi-industrial fed-batch crystallizer), Borsos2017 (imaging in
    a nucleation-control loop), Ochsenbein2014 (growth rates fitted off-line to imaging data). New novelty sentence: "to
    our knowledge, no in situ camera size has been fused in a recursive estimator for an industrial sugar pan"
    [citation-finder gap search, not a proof]. Not cited: Paz Suárez 2011, Ma & Wang 2012 (unverified).
91. §1.3 three installation properties → the three measurement-model elements (gain, sampled layer, detector).
    §1.4 RQ1–RQ4 (scale; slice and crop; near/far; classical detectors) → RQ1–RQ3 of the brief; old RQ3 near/far → App B.
    Contributions 1–5 → 1–4: measurement model; observability condition; estimator "with a per-strike validation
    protocol, tested leave-one-strike-out on simulated signals and first real points; process baseline waits on DCS"
    (not "validated"); open dataset. Old contributions 2 (DoF) and 3 (0.17 % bound) are now supporting results in §3.2
    and App B.
92. §2 data, new facts: 2026-10-30 seedings 11:29:33 / 15:22:00 (sidecar); per-sample refractometric dry substance and
    polarisation (sidecar); no DCS for 2026-10-30 (`\pending`); DCS export 2026-02-04 at 30 s with PIC1001, PIC1002,
    QI1003, QIC1000, TI1006, EI1004, LI1009 and no LI1000; QI1003 labelled viscosity, Brix scale, reads the whole
    massecuite, not a true Brix; new tab:data. tab:microscope adds b1 13:06 and b2 16:58 rows. New definition: crystal
    size L := median microscope chord (laboratory definition). [datasets/README.md; docs/sered/notes_data_lab.md §2b, §5
    (QI1003 meaning is marked interp. there); scripts/microscope_summary.py]
93. §3 new measurement equation y_k = ln L_k + θ + β(L_k) + v_k, θ = ln(λ b_sel), λ = μ̂/μ dimensionless, with new
    tab:terms (term, meaning, value, source). Per-frame σ 0.10 / 0.18 and σ_w 0.06–0.13 of the brief are not in the
    paper as measured values (scratch, no repo script): `\pending`. [brief decision 2]
94. §3.1 new derived number: σ_lnλ = ln(1.098)/1.96 ≈ 0.05 (normal reading of the ±9.8 % budget); λ treated as one
    factor for both axes because the dominant tube term is common. [tab:scale; optics.scale_chain]
95. §3.2 "a single focal-plane scale suffices" → "and the estimator needs no depth state" (same evidence: ≤ 0.17 %,
    mean correction 0.005–0.013 %). "That this slab represents the bulk of the stirred pan is the homogeneity
    assumption" → "the layer next to the glass represents the well-mixed massecuite: an assumption". [rerun rows]
96. §3.3 new: the y_k detector is a fine-tuned Cellpose model (`\pending` version, fine-tuning set, AP); classical
    detectors only as negative control; window must admit chords above 1 mm. Old recommendation 3 folded in here.
97. §3.4 matched-time tracing: "the true scale is at most about 1.3 times the modelled one" (item 73) → removed; the
    microscope-over-traced ratio is read as e^(−θ) for the tracings (gain and selection combined), method-dependent
    (≈ 30 % between methods), so θ belongs to the detector used. Packed-frame ratio 1.4–2.0 → negative β(L). New:
    β = 0 inside the valid range, update skipped outside; floor 40 µm in the estimator (analysis choice). [scripts/
    traced_vs_lab.py: chords k p50 0.98–0.99, p90 0.86–1.02; outlines 1.14–1.32; packed 1.42–2.01]
98. §3.4 new formula R = Var(ln median) ≈ (π/2) σ_ln²/n (asymptotic variance of a sample median, derived in text);
    §3.5 new anchor equation z_j = ln L(t_j) + w_j; photo clock ±47 s. [derivation; sidecar photo_clock]
99. §5 estimator design (new, analysis choices for author approval): discrete EKF in (ln L, ln G, θ), steps ≤ 1 min;
    priors from the training strike (ln L_0, ln G_0 SD 1.0), θ ~ N(0, 0.16²) (the brief's "σ_θ ≈ 0.16 (inference)" is
    now a stated prior); Q_G grid 1e-5…1e-1 /min tuned on the training strike; camera once per minute while L ≥ 40 µm;
    flag rule 20 % band, 1.96 σ, 10 consecutive min; anchor = first test sample at t ≥ 30 min, anchor SD 0.1 assumed.
    Mesbah2011, HaseltineRawlings2005 cited for the filter choice. [src/softsensor; results.md §3]
100. §5.2 process-signal baseline: defined (DCS inputs, kinetics calibrated on anchors; Lohani2026 predecessor,
    self-citation) but cannot run on 2026-10-30 (`\pending`, needs DCS). New: the nominal-curve prediction (the other
    strike's microscope curve) is reported as a reference, explicitly not a substitute. [results.md §3]
101. §5.3 validation protocol moved; detector level and acceptance (a), (b) unchanged; estimator level → leave one
    strike out with log-size RMSE, G RMSE vs ±10 min central difference, G/L RMSE and flag share/time vs the 20 %
    crossing; acceptance margins and θ carried b1 → b2 `\pending`. [src/softsensor/evaluate.py]
102. §6.1 negative control moved unchanged in numbers; adds "these detectors define the floor the camera signal must
    clear".
103. §6.2 NEW RESULT (REAL microscope, single AI transcription): b1 G = 4.35 µm/min over 37–122 min (OLS 95 % 3.98–4.72,
    bootstrap 3.49–6.11), lag 20.4 min, plateau after 122 min (483 / 486 / 452 µm); b2/b1 1.35 at 30 min, 1.03 at 52,
    0.64 at 96; b2 G = 1.21 µm/min from 69 min (bootstrap 0.65–1.84); G_b1 − G_b2 = 2.23 µm/min over 30–97 min
    (bootstrap 1.23–3.20); interpolated b2 > 20 % below b1 at 75 min, > 20 % above from 13 min. [results.md §1, §3]
104. §6.3 NEW RESULT (SIMULATED, tab:loso): leave-one-strike-out log-size RMSE 0.09–0.11 with anchor, 0.15–0.16
    without, nominal curve 0.31–0.32; σ_θ end 0.157 without, 0.087–0.092 with anchor; b2 flagged slower in 96–98 % of
    seeds at median 103–107 min (28–32 min after the 75 min crossing), 60–62 % without anchor; early b2 lead flagged in
    2–9 % at 24–29 min. Stated as a test of the filter, not the camera (signal built from the scored medians; σ_v 0.10 /
    0.18 are scratch values; no β, no outliers). [results.md §3]
105. §6.4 NEW RESULT (REAL camera points, 12 AI chord-trace medians, b1, ≤ 62 min): RMSE 0.060 (anchor) / 0.075 (none)
    vs nominal 0.046 inside the window; open loop to 122 min 494 vs 483 µm (nominal 262), overshoot at 160 min 673 vs
    486 µm; all held-out 0.22 vs 0.32; never flags. Stated as thin evidence; camera-aided claim `\pending` fine-tuned
    detector and DCS. [results.md §4]
106. §7 discussion rewritten: what the operator gets with and without an anchor; limitations condensed (α, crop, κ,
    paraxial distortion, case-study clip dropped) and extended (two strikes of one run, AI-transcribed truth, simulated
    circularity, twelve real points, priors / ln G / floor / flag rule as choices, no DCS for the sampled run);
    recommendations 4 → 2 (site geometry; PAL stream with clock logging against the DCS); soft-sensor outlook deleted.
107. §8 conclusions rewritten to RQ1–RQ3; RQ3 "not yet answered", with the SIMULATED and REAL estimator numbers above.
108. App B first matched-time reading: "the time-varying gap is therefore a detector failure" dropped (the reading now
    only motivates the fine-tuning); "frames 60 s apart are uncorrelated, no static layer" moved to §3.2; the rest
    condensed, `\pending` kept.
109. App D glossary: "Seed pan (graining pan)" → "Seed pan"; "Seeding (graining)" split into Seeding (očkovanie) and
    Graining = seeding followed by formation ((cz) zrnění varu očkováním); "Seed massecuite (seed magma, footing)" →
    "Seed massecuite"; "Tightening (drying)" → "Tightening"; Strike = one batch cycle and its massecuite (b1, b2);
    Massecuite adds "pan contents after seeding (syrup before)". [plant expert via brief]
110. Bibliography: 14 entries appended from the citation-finder list (Crossref-verified): Kadlec2009, Damour2010,
    Morales2023 (M), Lohani2026 (self-citation), Mesbah2011, HaseltineRawlings2005, Borsos2017, Ochsenbein2014,
    Martins2007 (M), QuintanaHernandez2004, HermannKrener1977, Friedland1969, Gudi1995, FatehiHuang2017; each used only
    for its "supports" line. Not added: Sinopoli2004, Sun2023, Georgieva2003,
    Simoglou2005, MuskeBadgwell2002, Patience2001, Jiang2021.
111. Cover letter Problem / Contribution / Fit rewritten (SIMULATED result only, real-camera and baseline results as
    bracketed placeholders). CRediT "Resources (plant data, SCADA)" → "(plant data, DCS)" (terminology only).
112. App C table: generators of cut figures removed; rows for `scripts/traced_vs_lab.py` and `scripts/softsensor_*.py`
    (`\pending`) added; fig 00 "no generator" note removed with the figure.

Review round 2 (referee BLOCKERs, bridging review, notation audit; conservative option applied, all proposals):

113. A1 framing: "We turn the camera … into a soft sensor" → "We design a soft sensor of crystal growth around the
    sight-glass camera … and test its estimator in simulation and on first real camera points" (abstract, intro §1.3,
    conclusions opener, highlight 1, cover letter). Abstract adds the negative real result: on 12 AI-traced real camera
    points the estimator does no better than the nominal curve. Cover letter: "sets out its validation on plant data" →
    "defines a validation protocol …; the validation itself is pending". [results.md §4]
114. A2 "flags the slower strike" removed from abstract, highlights and cover letter; §6.3 adds: with two strikes the
    nominal of each is the other, so a strike flagged slower makes the other faster by construction; the flags show
    mechanics, not a detection rate. (Conclusions sentence still carries it until the results.md rerun.)
115. A3 Proposition 1 → Lemma 1 (label prop:scale → lem:scale). Proof gaps fixed: G_N affects no output and is
    undetermined (statement restricted to k < N); L_0 = o_s holds only if L̄(0) = 0 (stated as a condition); for a
    linear nominal curve the τ ratio restates the G ratio (stated). HermannKrener1977 cited as the structural rank
    condition. NEW CLAIM, needs author approval: Corollary 1, β(L) = γ ln L gives y = (1+γ) ln L + θ, so the inferred
    G/L is biased by (1+γ) while the scale symmetry persists with θ − (1+γ) ln c; a packing ratio growing with size acts
    as γ < 0. Symbol γ instead of the suggested κ (κ is the PSF constant in App A). [derivation in the paper]
116. A3 practical identifiability next to the structural result: new tab:ident (SIMULATED, b1, σ_v 0.10, diffuse
    priors): SD θ end 0.160 / 0.0875 without / with anchor; SD ln(G/L) 0.449 at 60 min and 0.872 at 170 min either way;
    text: ln(G/L) known only to about a factor e^0.45 at 60 min. [results.md §2; to recheck after the rerun]
117. A4 RQ3 wording "better and earlier than an estimator using process signals only" → "than references without the
    camera"; added: comparison with anchor-only and nominal-curve references, the process-signal baseline waits on
    DCS data, real-data answer after the 2026-11-23 freeze. Contribution 1: "matched-time comparison with the
    microscope" → "AI tracings of twelve frames matched in time to the microscope; R and w_j pending". Contribution 2
    adds "that share the offset" and the β distortion. Contribution 3: "with classical detectors as a negative control"
    → "as a failed baseline", references named.
118. A5 intro "None of these estimates crystal size or growth rate" → "None of these reports crystal size or growth
    rate directly, although a crystal mass with a known crystal count implies a mean size". New §7.1 paragraph: mass-
    balance route L ∝ (m_c/N_c)^(1/3) from a crystal-mass soft sensor (Damour2010) plus seed count and constant shape
    factor escapes the camera's scale symmetry; alternative and candidate future baseline, not built. [Damour2010
    supports the crystal-mass estimate only; the scaling is our reasoning]
119. A5 new §7.1 paragraph on why strike-to-strike growth differences matter (seed massecuite drawn into the A pans; KP
    of the boil-up as the lever; "we know of no plant specification" → the sensor reports deviation from earlier
    strikes, not from a target). [plant facts already in §2, §1.1]
120. A6 "negative control" → "failed classical-detector baseline" (§3.3, §6.1 title and text, tab:data, App B intro,
    conclusions RQ3, highlight 5); §6.1 adds that only the pre-seeding frames are a true negative control.
121. A7 gain budget: §3.1 cut to one paragraph; tab:scale and the Monte Carlo term list moved to new App A
    sec:budget-detail (numbers unchanged). Depth-of-field numbers removed from abstract and conclusions ("thin enough
    for one scale"). App B: near/far implementation paragraph, inverted depths, prior-bin argument and the near/far
    split and π_near rows of tab:ws-compare cut; the near/far conclusion is one sentence (99.6–99.9 % within
    0.500 ± 0.002, tie-breaks); clip paragraph cut to one sentence (date-dispute details and the 1 h 41–48 min
    estimate dropped).
122. B flow: two-line opening and one-line handover added to §2–§6; conclusion openers use the RQ wording of §1, RQ2
    adds "provided θ is shared"; §7 keeps the operator view (the "measurement model is simple" RQ1 recap removed).
    ±47 µm stays in App B only; 0.17 % once in §3.2 (plus tab:terms). Discussion cross-reference tab:inputs →
    \ref{app:optics}. R derivation to a footnote; local-rank block split into structural / design / numerical
    paragraphs; b_sel paragraph now leads "θ belongs to the detector, so it is fitted from the anchor". Terms: "slurry
    reference" → "seed slurry" (text and tab:microscope); "residual footing" → "residual massecuite"; DeltaV only at
    first mention (glossary intro "DeltaV screens" → "DCS screens").
123. C1 correctness: tab:terms quoted "microscope over traced" as b_sel; by Eq. meas that ratio is e^(−θ). Row relabelled
    θ = ln(λ b_sel) with value "e^(−θ) (microscope over traced median) 0.86–1.02 / 1.14–1.32"; packed-field value also
    labelled e^(−θ).
124. C2 notation: growth age τ → a (â); strike index b → s (τ_s, o_s, L(t; s), G_s), names b1/b2 kept; ΔL-law intercept
    L_0 → L_init in §6.2; Euler e → \mathrm{e} or \exp; axis subscripts upright (μ_x, μ_y, p_x, p_y); crystal width ℓ
    → w_c (App B); spectral slope β_ν → α (App A; α is free since the sharpness slope symbol was cut); median density
    f(m) → g(m); h(x_k) dropped from Eq. meas, L_k pointed to §4.1; n (outlines per update) defined against n_f
    (frames per update); Ḡ defined as the nominal growth rate of a linear nominal curve; R = σ_v² defined at first use;
    §6.3 states the simulation uses the per-frame σ as per-update noise (an upper bound when an update pools frames).
125. C3 Δt: the filter propagates in sub-steps of ≤ 1 min (§5.1). 40 µm floor justified as a choice just above the
    3–9-sample texture range of the untuned detector (9 samples ≈ 35 µm; derived from 3.919 µm per sample). θ prior
    0.16 written as an inference, (0.05² + 0.15²)^(1/2), with 0.15 a judgement of the selection-bias spread across
    detectors. [brief "σ_θ ≈ 0.16 (inference)"]
126. §5.2 retitled "Process-signal baseline and references"; new anchor-only reference (same filter, anchors and priors,
    no camera updates) described for the coordinator's rerun; acceptance requires beating anchor-only, nominal curve
    and process-signal baseline on both strikes. [to confirm against results.md after the rerun]

Round 3, after the results.md rerun (estimator agent, `uv run python scripts/softsensor_results.py`; labels SIMULATED /
REAL / EXTRAPOLATION kept as in results.md):

127. tab:loso rebuilt from results.md §3: rows per test strike = nominal curve, two anchor-only references, EKF at
    σ_v 0.10 / 0.18 with and without anchor; columns log-size RMSE [5 %, 95 %], G/L RMSE, growth-age RMSE, G/L flags.
    Old numbers (0.088 / 0.094 / 0.107 / 0.113 anchored, size-flag columns, σ_θ column) → b2 0.085 / 0.104, b1 0.092 /
    0.109 anchored; 0.144 / 0.154 / 0.150 / 0.158 without; nominal 0.310 / 0.319. [results.md §3]
128. §5.2 anchor-only reference: "same filter, same anchors and priors, no camera updates" (round 2, my definition) →
    withdrawn; replaced by the implemented two camera-free references, the nominal curve shifted in ln L through the
    anchor and shifted in time to the growth age at the anchor. Result §6.3: neither beats the plain nominal curve
    (0.337–0.570 vs 0.310–0.319) because the strikes cross after the 30–37 min anchor; the anchor pays off only with the
    camera (b2, σ_v 0.10: 0.085 vs 0.144). [results.md §3]
129. Evaluated flag: size flag → scale-free G/L flag (d = ln(Ĝ/L̂) − ln(Ḡ/L̄), θ cancels, no anchor needed); size flag
    kept as a one-sentence definition. Results: identical with and without anchor; b2 relatively faster at 141 min in
    90–100 % (noise-free curves 134), b1 relatively slower at 157–162 min in 66–100 % (134); early divergence at 34 min
    missed (b2) or flagged late at 84–85 min (b1). n = 2 caveat kept. Flag truth changed from "interpolated curves first
    differ by 20 % (75 / 13 min)" to the same flag rule on the noise-free curves (G/L 34 / 134 min, size 84 / 23 min).
    The round-1/2 size-flag claims (b2 slower in 96–98 % at 103–107 min, 28–32 min late) are withdrawn. [results.md §3]
130. Growth age: a = τ_s t → defined by L̄(a) = L(t; s) (equal to τ_s t if o_s = 0), on the rising part of the nominal
    curve only. New: RMSE 5.4–12.3 min with camera and anchor vs 31.0–39.5 min nominal; limits stated (b1 plateau:
    483 / 484 / 485.5 µm → 122.5 / 137.7 / 160.4 min; undefined above 485.5 µm (b1) and 399.0 µm (b2)). [results.md §3]
131. NEW CLAIM, needs author approval: key design requirement "the camera adds value only if its bias θ stays constant
    within a strike". New §6.4 and tab:robust (SIMULATED, σ_v 0.18, one anchor, 100 seeds): γ = 0.1 tolerable (0.152 /
    0.194); |γ| = 0.3 log-size close to or worse than nominal (0.324 / 0.419; 0.273 / 0.306) while G/L stays below every
    reference; θ random walk (spread ln 1.75 over 60–122 min) and packing ramp (θ falls ln 1.75 over 60–122 min) worse
    than nominal (0.512 / 0.485; 0.447 / 0.343), ramp flags b2 slower in 69 % (wrong direction); Q_θ = 0.001 removes the
    false flags and the true ones (b2 faster 94 % → 25 %). results.md's κ is written γ (Corollary 1 notation). §5.3 new
    acceptance criterion (c): camera-to-microscope ratios at all matched times from 30 min within a factor 1.25 (an
    analysis choice), i.e. θ constant, no packing bias. Abstract, conclusions, discussion and cover letter state the
    requirement. ln 1.75 is described as "inside the 1.4–2.0 of the packed traced frames" (traced_vs_lab.py gives
    1.42–2.01; results.md's "1.5–2.0, midpoint 1.75" not repeated). [results.md §4]
132. §6.5 REAL rows: main result = covered window only (held-out 49 and 60 min): log-size RMSE nominal 0.046, anchor-only
    0.095 (ln shift) / 0.073 (time shift), EKF 0.075 (no anchor) / 0.060 (anchor); G/L RMSE EKF 0.54, nominal 0.66,
    time-shifted reference 0.46; no flags. Open-loop rows reduced to one sentence labelled EXTRAPOLATION (494 vs 483 µm
    at 122 min; 673 vs 486 µm at 160 min); "over all held-out times 0.22 vs 0.32" removed. [results.md §5a, §5b]
133. tab:ident replaced: σ_θ 0.0875 → 0.0876 (diffuse priors, text); table now SD ln(G/L) under leave-one-strike-out
    priors and Q_G, no anchor, at 30 / 60 / 120 min / end for b1 and b2, σ_v 0.10 / 0.18 (b1 0.450 at 60 min, 0.863 at
    the end); "anchor changes these by at most 0.025"; "0.45 is a factor of about 1.5 at one sigma". [results.md §2]
134. Q_G grid 1e-5…1e-1 /min → 1e-5…10 /min; optimum interior: 0.1 trained on b1, 0.0316 trained on b2. [results.md
    Q_G tuning]
135. Abstract: "0.09–0.11" → "0.085–0.109 … provided the camera bias stays constant within a strike"; "fail as a
    baseline" → "fail" (word limit); "operator-picked" dropped from the microscope clause, "of the seed pan of" → "of
    the seed pan at". Conclusions RQ3: "flags the slower strike in 96–98 %" removed; adds anchor-only references no
    better than nominal, G/L flag late-divergence result and the constant-bias condition. Cover letter numbers likewise.
136. §6.2: "b2 falls more than 20 % below b1 at 75 min" → flag rule on the noise-free curves: b2 G/L slower from 34 min,
    faster from 134 min, size > 20 % below b1 from 84 min. [results.md §3 flag reference]
137. App C: "full suite collects 142 tests" → 160 passed, 1 failed, 2 skipped; the failing `test_crystal_rules`
    frame-scale test is pre-existing (fails on the base branch). Adds `uv run pytest -q tests/test_softsensor.py # 21`
    and `uv run python scripts/softsensor_results.py`; generator row `scripts/softsensor_*.py` (pending) →
    `scripts/softsensor_results.py` for §§4–6, tab:ident, tab:loso, tab:robust. [estimator agent's run]
138. App D glossary: table* → single-column table, source column merged into "Meaning [source]" (21 → 20 pages). No
    content change.
139. §7.1 adds the requirement sentence (a packing drift of θ produces false flags, §6.4).

Round 4, final integration except Cellpose (2026-11-04; branch committed at 51641fa, these edits uncommitted). The author
agreed to the round 1–3 decisions (title, Lemma 1, ln G state, estimand, constant-θ requirement).

140. §5.2 / §6: process-signal baseline `\pending` → interim baseline (INTERIM, `scripts/softsensor_process_baseline.py`,
    `docs/softsensor/process_baseline.md`, `src/softsensor/process.py`): G = k_g max(KP − 1, 0) (g = 1 assumed); KP as
    the plant's DCS formula sheet writes it (reproduces the live KP_akt 1.208 vs 1.210; source
    docs/sered/notes_plant_dcs_qa_photos.md §2.2, notes_data_lab.md §3c); driver = lab Brix and purity, T assumed
    70.8 °C (median TI1006 while boiling, 2025 DCS); L_0 = 13.0 µm (four chords of the seed-slurry photo); k_g 16.26
    (from b1) / 9.88 µm/min (from b2). tab:loso rows "process-signal baseline (interim)": b2 0.836 / 0.891 [0.872,
    0.910], G/L 1.427 / 1.049, age 30.2 / 15.0 min; b1 0.637 / 0.321 [0.300, 0.353], 1.413 / 1.176, 66.4 / 28.7 min;
    flags as in the file, marked "not decisions". The DCS export replaces the lab driver, T and the seeding time but not
    the structural limitation. 2026-02-04 pipeline check: seeding detected at 12:31:30 vs the 12:30 note. The
    g < 1 diagnostic rows are not mentioned (author decision pending). Remaining `\pending` pinned to the DCS export.
141. New §6.4 "Interim process-signal baseline": it does worse than the nominal curve (and fits its own training strike
    with log RMSE 0.591 / 0.652) because the Brix input reads the whole massecuite (lab sample and QI1003 alike; crystal
    dissolution on dilution is our interpretation): KP rises 1.04 → 2.27 over the post-seeding b1 samples while the
    microscope growth rate stays 3.5–4.9 µm/min from 16 to 122 min; argument for a direct size measurement. One
    sentence each in §7.1 and §8 RQ3. [process_baseline.md §1, §2, §6; results.md §1]
142. σ_w `\pending` → bootstrap median 0.071, range 0.031–0.157 over 18 post-seeding samples, sampling noise only (not
    operator choice, transcription or clock) (§3.5, tab:terms). [scripts/microscope_anchor_noise.py,
    docs/softsensor/anchor_noise.md]. The evaluation's assumed anchor SD 0.1 is unchanged.
143. App B: committed watershed seed sweep added (median basin 36.5 / 45.2 / 90.3 clip px for 6/3, 12/6, 24/12);
    item 18 annotated (scratch 53 px not reproduced). [scripts/watershed_seed_sweep.py,
    docs/optics/watershed_seed_sweep.md]
144. Fig 18 caption "sharp-focus plane", "H → focus" → "focal plane", "H → focal plane" (generator relabelled); tab:dof
    caption "CoC b". Regenerated figs 04, 10, 18 checked against captions (CoC b, signed δ, PAL sample, massecuite).
    Fig 18 still prints "glass t = 20 mm" where the text uses t_g (generator, out of scope).
145. Intro novelty sentence "We found no peer-reviewed in-line CSD measurement through the sight glass of one; the
    sugar-technology trade literature and commercial pan-camera systems were not covered by this search \pending" →
    "Commercial pan microscopes report MA and CV in-line, behind a dedicated sight glass (BoucheGaillac2015, Selby2024)
    or as an insertion probe (Honkanen2023, Honkanen2024); the latter takes the growth rate as the time derivative of
    the volumetric mean size, without an estimator (Honkanen2023). We found no report of size measurement from an
    existing operator sight-glass camera, and no recursive estimator that fuses an in situ camera size for an
    industrial sugar pan." [refs_round2.md §1; BoucheGaillac2015 vendor-authored trade journal, no DOI; Honkanen2023
    peer-reviewed proceedings, no DOI]. Selby2024 pages: bib uses the publisher's 46–54; Crossref gives 42–50 (bib
    comment; check the print copy).
146. §3.3 Cellpose `\pending{citation for Cellpose-SAM}` → Pachitariu2025 (Cellpose-SAM, bioRxiv preprint),
    Stringer2021 (Cellpose), PachitariuStringer2022 (fine-tuning); "Cellpose 4.2.1.1 with the base model cpsam" (uv.lock
    pin). NEEDS Marian Choma's confirmation: the base model `cpsam` is inferred from the checkpoint date
    (cpsam_20260517_223507 predates cpsam_v2 of cellpose 4.2.0). Fine-tuning set and AP stay `\pending` (Cellpose agent).
147. §4.2 Lemma 1: adds CastroDeBoer2020 and MassonisVillaverde2020 (scaling symmetry → structural unidentifiability;
    breaking it restores observability) as the same mechanism, Villaverde2019 for θ as a constant state; "the lemma and
    its corollary are our derivation" kept (the cited results are continuous-time).
148. §5.1 adds that Mesbah2011 also compared a moving-horizon estimator, the alternative if the EKF proves fragile.
149. Bibliography: 10 entries appended from refs_round2.md (Stringer2021, PachitariuStringer2022, Pachitariu2025,
    CastroDeBoer2020, MassonisVillaverde2020, Villaverde2019, BoucheGaillac2015, Selby2024, Honkanen2023,
    Honkanen2024). Not added: BellmanAstrom1970 (M), MartinsRochaRein2005 (optional), Kwon2015 (M).
150. AI_USE.md: five log rows for 2026-11-04 (analysis agents, reframe writing, estimator and baseline code, DOI-checked
    citation search, review agents) and a drafted declaration; declarations.tex carries the same text, marked "draft
    from AI_USE.md; each author confirms".
151. Page budget (21–22 → 20 pages): cut from the appendices fig 04 (dof envelope; tab:dof keeps the numbers), the
    spectral-isotropy check paragraph (1.002 / 1.065 / 1.132), the PSF / sharpness-model paragraph and Eq. sharpness
    (the 10.5 µm sharpness FWHM row of tab:dof goes with it; diffraction FWHM kept in one sentence), tab:ws-compare
    (key numbers stay in the App B text; log-normal shape, percentiles and near/far rows dropped), tab:ws-constants
    (values in the text), fig 10 (discriminability; 0.17 % / 1.3 mm in the text). App D: intro paragraph folded into
    the caption, five unused rows dropped (boiling house, vacuum break, vapour, pan operator, standard syrup) and
    meanings shortened (no definitional change). App C generator table updated. Generators unchanged.
152. Conclusions `\pending` "estimator on the detector signal and the process-signal baseline" → "estimator on the
    fine-tuned detector signal; process-signal baseline on the DCS export".

Not done here (out of scope or needs the author):
- On-image text of generated figures still uses old terms: fig 18 ("sugar slurry (inside the vessel)", "1 PAL pixel =
  …", "Camera 100"), fig 04 (title "Depth of field shrinks dramatically", axis "c"), fig 10 (axis "δ = d_focus − d_near",
  sign differs from App A's signed δ). Generators are in src/optics (not edited).
- Page budget (round 2): still 20 of 20. The App D glossary `table*` floats to its own page and leaves page 19 nearly empty; moving it
  or shrinking it recovers about one page for the pending y_k-vs-z_j figure.
