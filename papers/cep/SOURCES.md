# Sources: literature and background claims → source

Audit of every literature or background claim in `main.tex`, `sections/*.tex`, `highlights.txt` and
`cover_letter.md`, 2026-11-03. Bibliography checked by DOI against Crossref, with abstracts from OpenAlex where
available, ISBNs from Open Library, and vendor and standard pages. Bib keys refer to `references.bib`.
Results from our own data or code (µm/px, α, DoF, CSD) are out of scope here: they must come from a script.

**Verdicts.** *KEEP* = the source supports the claim as worded. *REPHRASE* = a source exists for a weaker or
corrected claim (wording given). *REMOVE* = no verifiable source found. *SCRIPT* = not a literature claim; it needs
a script in this repo or must go. Confidence: H = checked against the abstract or full text, M = checked against
title and metadata only, L = not checkable (book without a copy, paywall).

Text edits below are **proposals for author approval**. The citation audit of 2026-11-03 changed `references.bib` and
swapped or added citation keys in the sections (Huo2020, Manee2019, ITUBT656, GeblerHotovy2020); it changed no claim wording.

## 1. Bibliography fixes (references.bib)

| Key | Problem found | Fix |
|---|---|---|
| Czapla2010 | Checked 2026-11-03: DOI 10.1016/j.cherd.2010.03.004 resolves to Czapla, Kail, Öncül, Lorenz, Briesen, Seidel-Morgenstern, *CHERD* 88(11) 1494–1504 (2010). Applies an FBRM probe model (PSD → CLD) to dl-threonine and models chord splitting by modifying the particle geometry (TUM portal abstract). | OK. Supports the probe-model and particle-shape clause of §1.2 together with Wynn2003 and Kail2009 (M–H). |
| Borissova2009 | Checked 2026-11-03: DOI 10.1021/cg7010265 resolves to Borissova, Khan, Mahmud, Roberts, Andrews, Dallin, Chen, Morris, *Cryst. Growth Des.* 9(2) 692–706 (2009). In situ ATR-FTIR measurement of l-glutamic acid concentration and supersaturation; "fouling of the ATR crystal prevents its routine use for unseeded crystallization studies" (abstract). | OK. Supports the spectroscopy sentence of §1.2 (H); see I-8 for a proposed qualifier. |
| Eggers2008 | Wrong DOI (another paper) and wrong issue (24 → 22). | DOI 10.1016/j.ces.2008.08.007; full title. |
| Larsen2007 | Title belongs to a different Larsen paper (CES 61, 2006). | Title set to the DOI's paper: "Model-based object recognition …". |
| McCabe1929 | Wrong DOI (Forrest et al., corrosion) and wrong title. | "Crystal growth in aqueous solutions. I—Theory", DOI 10.1021/ie50229a008. |
| Worlitschek2003 | Wrong DOI (Hentschel & Page). | DOI 10.1002/ppsc.200390000. |
| Wynn2003 | DOI check digit wrong (-9). Title truncated. | DOI 10.1016/S0032-5910(03)00084-6; full title. |
| Zhou2011 | Wrong DOI (Arias et al., inpainting). | DOI 10.1007/s11263-010-0409-8; issue 1. |
| Heath2002, Vincent1991, BeucherMeyer1993 | DOI missing. | DOIs added (Crossref match). |
| Simon2015 | "and others" | All 46 authors from Crossref. |
| Borchert2014, Salami2021 | Titles shortened. | Full titles. |
| Asadi2006 | No DOI or ISBN. | Wiley DOI 10.1002/0471790990; ISBN 978-0-471-76347-5 (print 2006). |
| Bubnik1995 | "9th edition" and ISBN 978-3870403324 not verifiable. | Both dropped. Authors, title, publisher and year confirmed (Bartens, Berlin 1995). |
| Hecht2017, Smith2008, Goodman2017, RandolphLarson1988 | ISBN missing or unverified. | ISBNs confirmed via Open Library. |
| PhotonsToPhotos2024 | Year and author wrong. | Bill Claff, 2007-02-02 (page checked). Key kept so the draft builds. |
| Mastersizer2025 | Attributed to the plant. Measurement date missing. | AGRANA Sugar Technology report, sample 2025-01-16, measured 2025-03-04 (PDF checked). |
| Bennar2010 | – | Title page checked on the local PDF (SPU Nitra, FBP, dissertation 2010). |
| GeblerHotovy2021, GeblerHotovy2020 | Checked 2026-11-03 on the journal's open PDFs (cukr-listy.cz): parts 14–16 are LCaŘ 137, nos. 5–6, 7–8, 9–10 (2021), pp. 229–231, 292–294, 353–354, entries U–Ž. "Cukrovina" (massecuite), cited [GH] in the glossary, is in part 2, LCaŘ 136(2) 89–91 (2020). | Full names, issues and URLs added; GeblerHotovy2020 added and cited with GeblerHotovy2021 for [GH]. |
| Daniels2017 | Volume and issue missing. | Vol. 142, no. 9 (publisher page sugarindustry.info/paper/18737). |
| SimonNagy2009 → Huo2020 | SimonNagy2009 is real, but its external bulk video imaging detects the metastable zone, not a CSD; it does not support "image-based CSD monitoring … through the wall of a crystallizer". | Cite swapped to Huo et al. 2020, *Ind. Eng. Chem. Res.* 59(10) 4646–4658, DOI 10.1021/acs.iecr.9b05828: 3D CSD from "two microscopic cameras fixed at different angles outside the crystallizer" (abstract, H). SimonNagy2009 stays in the bib, uncited. |
| Salami2021 → Manee2019 | Salami2021 is real, but it classifies sliding-window crops with a CNN to detect an impurity phase; it is not segmentation and reports no CSD. | Cite swapped to Manee, Zhu, Romagnoli 2019, *Ind. Eng. Chem. Res.* 58(51) 23175–23186, DOI 10.1021/acs.iecr.9b02450: deep-learning segmentation (RetinaNet-based) that generates the CSD (abstract, H). Salami2021 stays in the bib, uncited. |
| ITUBT656 | BT.601-7 gives 13.5 MHz, 720 active samples and the 5.75 MHz luma passband, but not the 576 active lines cited to it in §2. | Added ITU-R BT.656-5 (2007), Table 1: 625-line active lines 23–310 and 336–623 = 576; cited with ITUBT601. |

Entries in the bib but not cited in the current draft (so not printed): Asadi2006, BornWolf1999, Bubnik1995,
Goodman2017, NayarNakagawa1994, Smith2008, Zhou2011, SimonNagy2009 and Salami2021. Standards, datasheets and plant documents carry a URL or a repo path in place of a DOI.

## 2. Introduction and abstract

| # | Claim (location) | Verdict | Source / proposed wording | Conf. |
|---|---|---|---|---|
| I-1 | "typical white-sugar plant operates a three-massecuite scheme A/B/C" (§1.1) | REPHRASE (Sereď-specific) | Sereď runs an A/B/C three-product scheme with pans A1–A3, ZRA, B1–B2, C1–C2: `docs/sered/notes_plant_dcs_qa_photos.md` (flow sheet [SCHEME]; DeltaV [S:Varna_all]) → cite SlovenskeCukrovary2026. Generic statement: Asadi2006 (page not checked). | H (plant) / L (book) |
| I-2 | Strike "run for three to four hours" (Bubnik1995, Asadi2006) (§1.1) | REPHRASE | Book pages not checkable. Sereď seed pan: fill-to-discharge 2.8–4.0 h (typically 3.0–3.6 h), 47 strikes, SCADA 2025-10-26…11-01 (`docs/sered/notes_data_lab.md` §2d). That segmentation was done by hand by an agent, so it needs a script before the number goes into the paper. | M |
| I-3 | MA and CV are the plant's target parameters (§1.1) | KEEP with a source | Sereď white sugar MA 0.76–0.95 mm, CV by the Rens method (Bennar2010, Tab. 5–13, pp. 81–85). Industry use of MA/CV: Daniels2017 (abstract). | H |
| I-4 | "MA drives downstream classification, CV controls centrifuge efficiency and the recoverable molasses fraction"; "must be reworked at substantial energy and yield cost" (§1.1) | REMOVE | No source checked. Keep only "MA and CV are the quality specification" (I-3). | – |
| I-5 | Operators rely on indirect proxies: conductivity, refractive index, boiling-point elevation (§1.1) | REPHRASE | End of concentration is judged "by eye, by touch, or conductometrically" (Bennar2010 p. 42). Towards the end of drying "the massecuite peels off the pan's sight glasses" (p. 44). Sereď DCS trends °Bx (QI1003 "Viskozita"), vacuum and stirrer current (`notes_data_lab.md`). Name what Sereď uses; drop "boiling-point elevation" unless sourced. | H |
| I-6 | "among the most-requested unsolved sensor problems in industrial crystallization" (Nagy2013, Simon2015) (§1.1) | REPHRASE | The reviews cover in-line CSD monitoring as an active PAT topic. They do not rank it "most requested". Proposed: "In-line CSD measurement remains an active topic of process analytical technology (Nagy2013; Simon2015)." | M |
| I-7 | FBRM: "recovering a size distribution from it is an ill-posed inversion that needs a model of the probe optics and the particle shape" (Wynn2003, Kail2009, Czapla2010) (§1.2) | KEEP | Wynn2003: direct CLD→PSD inversion is stable only in some cases (Birmingham repository abstract). Kail2009: PSD estimated from the CLD with an optical probe model (TUM portal abstract). Czapla2010: probe model with a particle-geometry modification for chord splitting. | M–H |
| I-8 | "fouling of the probe crystal hinders routine use" (Borissova2009) (§1.2) | KEEP, qualifier proposed | Abstract: fouling of the ATR crystal "prevents its routine use for unseeded crystallization studies"; seeded runs gave good predictions. Proposed: "… and fouling of the probe crystal can prevent routine use (in unseeded crystallization, Borissova2009)". | H |
| I-9 | "each FBRM probe costs 50–150 kEUR" (§1.2) | **REMOVE** | Vendor prices are not published. No peer-reviewed figure found. Alternative: a written Mettler-Toledo quote archived in `docs/`. | – |
| I-10 | PVM "produces real in-line images but no calibrated size — sizes must be hand-measured"; "very shallow depth of field" (Wynn2003, Eggers2008) (§1.2) | REPHRASE | Wynn2003 is about FBRM, not PVM. Eggers2008 is image analysis in a flow-through cell. In situ microscopy sizes are extracted by image analysis and modelled (Kempkes2008, title/abstract summary). Drop "no calibrated size". The DoF statement needs a PVM source or must go. | M |
| I-11 | "Spectroscopic probes such as ATR-FTIR track solute concentration and supersaturation rather than size" (Borissova2009) (§1.2) | KEEP | In situ ATR-FTIR with PLS calibration measures l-glutamic acid concentration and supersaturation (abstract). | H |
| I-12 | "acoustic-emission methods correlate ultrasonic absorption with loading" (§1.2) | REMOVE or cite a review | No citation given and none checked. | – |
| I-13 | Off-line laser diffraction/sieving: "shortest practical cycle is 30–60 minutes" (§1.2); abstract "cycle times longer than the operator decision interval" | REPHRASE (Sereď-specific) | No source for 30–60 min. Sereď: the seed-slurry sample of 2025-01-16 was measured on 2025-03-04 by AGRANA Sugar Technology (Mastersizer2025, PDF header), so laser diffraction there is a central-lab measurement, not a per-strike one. The pan operator's lab sheet for ZRA on 2026-10-30 has 17 samples at irregular 2–50 min intervals (`notes_data_lab.md` [ZRA-X]). | H |
| I-14 | Camera retrofit "hardware investment is a few hundred Euro" (§1.2) | REPHRASE | Only source: a quote of 125 EUR without lens for an analogue box camera (Polz quote P5PI-100, 2025-10-06; PolzQuote2025). That model (HCB-6000) is **not** the installed body. Lens price unsourced. Proposed: "an analogue box camera was quoted at 125 EUR without lens". | H |
| I-15 | Through-sight-glass imaging "demonstrated for pharmaceutical crystallization (Larsen2007, Borchert2014)" (§1.2) | REPHRASE | Borchert2014 is KDP (inorganic) with online microscopy, not pharmaceutical (H). Larsen2007 is in situ video of α-glycine (M). Through-the-wall CSD imaging: Huo2020 (two cameras outside the crystallizer, H, abstract); SimonNagy2009's bulk video imaging detects the metastable zone, not a CSD. Sugar: lab online image analysis of sucrose (Ferreira2011, H) and off-line massecuite image analysis reporting MA/CV (Daniels2017, H). **No peer-reviewed in-line sight-glass CSD measurement on an industrial sugar pan was found** in this search. Say so instead. | H/M |
| I-16 | "with deep-learning segmentation in recent work" (Gao2018, Manee2019) (§1.2) | KEEP | Gao2018: deep-learning segmentation and classification, in-line, l-glutamic acid (H, abstract). Manee2019: deep-learning segmentation generating the CSD, NaCl antisolvent crystallization (H, abstract). Salami2021 (CNN crop classification, no CSD) no longer cited here. | H |
| I-17 | Published approaches treat calibration as a prerequisite using a scale target, and ignore depth of field ("universally ignored") (§1.2, abstract) | REPHRASE | No survey supports "universally". Proposed: "the methods cited above calibrate with a reference target and apply one scale to all detections". The authors must check each cited paper before keeping even that. | L |
| I-18 | Thin-lens model (Hecht2017 Ch. 5; BornWolf1999 Ch. 4) (§1.3, §3.1) | KEEP | Standard. Hecht section numbers (§5.2) not checked against a copy. | L |
| I-19 | Flat-plate shift Δ = t(1 − 1/n) (Hecht2017 §5.6) (§1.3, §3.2) | KEEP the formula, **check the section** | Paraxial result, standard. §5.6 of Hecht 5th ed. is not confirmed to contain it (5.6 may be fibre optics); check a copy or cite BornWolf1999. | L |
| I-20 | Exact flat-port projection is a 12th-degree polynomial (Agrawal2012) (§1.3, §3.2, §8) | KEEP with qualifier | Abstract: "For two refractions, AFP is either 4th or 12th degree equation depending on the refractive indices." Air→glass→massecuite = two refractions with distinct indices → 12th degree. | H |
| I-21 | Geometric CoC (Pentland1987, Pertuz2013); Gaussian-PSF fall-off (SubbaraoSurya1994); SML focus measure (NayarNakagawa1994) (§1.3, §4) | KEEP | Metadata H. Pertuz2013 is a focus-measure comparison and only secondary for the CoC. | M |
| I-22 | "Zhou2011 establish that circular-aperture defocus is symmetric in reciprocal object distance, breaking sign disambiguation" (§1.3, §6, §7.1) | REPHRASE / re-cite | Zhou2011's abstract does not establish this (it shows circular apertures limit DFD accuracy). Direct source: SellentFavaro2014 abstract: "given a single input image from a conventional camera one cannot distinguish between blurred objects lying in front or behind the focal plane, as they may be subject to exactly the same amount of blur." The 1/d symmetry follows from the CoC formula (Pentland1987), and the paper derives it. | H |
| I-23 | McCabe ΔL law predicts linear-in-time growth at fixed supersaturation (McCabe1929, RandolphLarson1988) (§1.3, §8) | KEEP | ΔL law: size-independent growth (McCabe1929, title H). "Linear in time" holds only at constant supersaturation. That qualifier is already in the text. | M |

## 3. Optics, defocus and detection sections

| # | Claim (location) | Verdict | Source / proposed wording | Conf. |
|---|---|---|---|---|
| O-1 | Extension tube fixes i∞ = f + e; focus ring trims i (PhotonsToPhotos2024) (§3.1) | KEEP | Claff 2007: v = (1 + m)f; adding extension x raises m by x/f (page checked). Focus-ring travel is not on that page (config: focus_travel 1 mm = ESTIMATE). | H |
| O-2 | Defocused point's centroid sits where geometric optics places it (Pertuz2013) (§3.1) | REPHRASE | Pertuz2013 does not state this. It is the chief-ray property of a symmetric blur with no vignetting. State it as a geometric-optics argument without the cite. | – |
| O-3 | "DIN 8902 borosilicate", n_g = 1.47 (§2.1, §3.2, Fig. 5, Fig. 18) | **REPHRASE (contradiction)** | DIN 8902:2020-08 is "Pressure resistant circular sight glasses of **soda-lime-glass**" (DIN8902; borosilicate is DIN 7080). n = 1.4714 is borosilicate (SchottBorofloat33). Either the glass is soda-lime (n ≈ 1.52, source needed) or the stamp is misread. config tags n_g ASSUMED and the stamp ESTIMATE. | H |
| O-4 | "paraxial form adequate for sub-percent pixel-pitch budgeting"; "residual refractive distortion < 1 %" for 0.05 mm crystals (§3.2, §8) | SCRIPT | Not a literature claim, and no script computes it. Either add an exact two-interface ray trace (Agrawal2012 forward projection) to `src/optics/` or delete both phrases. | – |
| O-5 | Gaussian PSF σ ≈ c/2 (Pentland1987, SubbaraoSurya1994, Pertuz2013) (§4.2; `src/optics/psf.py`) | REPHRASE / open | In Pentland's model σ is proportional to the blur radius, with a camera constant. A uniform disk of diameter c has per-axis σ = c/4, or c/(2√2) as radial RMS; c/2 equals the blur radius. The c⁻⁵ tail exponent does not depend on the constant. The FWHM, the ±4.2 µm DoF and the F/16 numbers do. The constant needs a page-checked source or a fit. | L |
| O-6 | σ_diff ≈ 0.42 λN, "Goodman §6.4 Gaussian fit to Airy; Smith §11" (§4.2; psf.py) | RE-CITE | Neither book was checked. Peer-reviewed source for Gaussian fits to the 2-D paraxial Airy PSF: ZhangZerubia2007 (abstract H). Its σ ≈ 0.21 λ/NA (coefficient from memory, check eq./table) with NA ≈ 1/(2N) gives 0.42 λN. Curvature matching gives 0.225 λ/NA → 0.45 λN (own Taylor expansion), consistent with psf.py's "0.42–0.45". | M |
| O-7 | Airy diameter 2.44 λN (BornWolf1999 §8.5; psf.py) | KEEP | Standard Fraunhofer result. Section not page-checked. | L |
| O-8 | Laplacian-variance, Tenengrad, Brenner are high-pass focus measures (§4.2) | KEEP | Pertuz2013 (focus-measure survey). | M |
| O-9 | Fujinon HF35HA-1B: f = 35 mm, F1.6–F22, MOD 0.25 m, BFD 15.03 mm, length 29.5 mm, C mount, 2/3" (§2.2, §3.5) | KEEP | Datasheet `docs/lens/fujinon-hf35ha-1b.pdf` (checked) → FujinonHF35HA1B. "Ø 11 mm image circle" is not on the datasheet: derive it from the 2/3" format or drop it. | H |
| O-10 | Hanwha HCB-6000, 1/2.8" CMOS, IMX307/327, 2.9 µm, 1920×1080 (abstract, §2.2) | **REMOVE** | The installed body is "ADEMCO VIDEO" (photos). HCB-6000 came only from PolzQuote2025. Candidate manual: AdemcoACM380E. It lists 510×492 / 768×494 effective pixels (EIA-type counts, not the 500×582 / 752×582 PAL counts in the audit) and "CS or C (C mount adapter supplied)". Pixel geometry must come from the confirmed model's PAL datasheet. | H |
| O-11 | Standard C-mount flange focal distance 17.53 mm (§3.5) | KEEP, cite | Standard value (17.526 mm). Needs a citable reference (e.g. a lens maker's C-mount note). config tags it DATASHEET. | M |
| O-12 | DVR samples PAL at 13.5 MHz into 720 samples and keeps 576 lines (§2.3); BT.601 luma passband 5.75 MHz (§4) | KEEP | ITU-R BT.601-7 (ITUBT601): 13.5 MHz, 720 active samples, Fig. 3 luma filter template to 5.75 MHz. 576 active lines: ITU-R BT.656-5 Table 1 (ITUBT656). | H |
| O-13 | Marker-controlled watershed is "the standard treatment in cell-biology image analysis" (Vincent1991, BeucherMeyer1993) (§7.4) | REPHRASE | The sources are general image-segmentation papers, not cell biology. Proposed: "a standard image-segmentation method". | H |

## 4. Sereď-specific facts (must cite plant documents)

| # | Claim (location) | Verdict | Source | Conf. |
|---|---|---|---|---|
| P-1 | Camera 100 is on the seed pan, DCS tag ZRA (§2.1) | KEEP | Plant Q&A 2026-08-12 + DeltaV "Udaje ZRA" (SlovenskeCukrovary2026); `docs/sered/README.md` "Settled" | H |
| P-2 | Seed pan seeded with slurry; seed massecuite dosed into A pans (§2.1) | KEEP | Fedor 2026-11-03 (pers. comm.), DCS seed route (`notes_plant_dcs_qa_photos.md`) | H |
| P-3 | Seed-slurry Mastersizer D[3;2] 3.95, D[4;3] 8.71, Dv10/50/90 1.56/6.81/18.5 µm (§2.1, §4.4, §7, §8) | KEEP | Mastersizer2025 (PDF checked; run 1; 3-run mean 1.57/6.77/18.6) | H |
| P-4 | Seed pan mechanically stirred, stirrer current tag EI1004 (§2.1) | KEEP | DCS tag list and SCADA (`notes_data_lab.md`, EI1004 10–18 A) | H |
| P-5 | Sight glass Ø150 / DN150, 20 mm, "both measured on site 2026-09-07"; e = 60 mm "operator caliper"; F/1.6 "verified" (§2.1, §2.2, §3, abstract) | REPHRASE | Plant Q&A item 8–9: "≈ 6 cm", "≈ 2 cm", "20 mm", "Ø 150 mm", "F = 1.6, if I read it correctly". config: no site measurement on 2026-09-07. Use "plant estimate". | H |
| P-6 | Glossary terms [GH], [P] and [Be] (Appendix B) | KEEP | GeblerHotovy2020 (part 2: Cukrovina) and GeblerHotovy2021 (parts 14–16: Var, Varna, Varostroj, Záděl, Zrnění varu očkováním with mikroočko 5–10 µm, Zrnič), checked on the journal PDFs; SlovenskeCukrovary2026; Bennar2010 (local PDF). | H |
| P-7 | "crystals stay ≈ 9 µm", "9 µm crystal population" (abstract, highlights, §3, §7, §8) | REMOVE | Contradicted by plant ground truth: microscope 2026-10-30, 22–35 µm about 1 min after seeding, 0.23–0.82 mm about 2 h after (`datasets/README.md`). The 6.8 µm Dv50 is the slurry before seeding only. | H |

## 5. Highlights and cover letter

- `highlights.txt` contains no literature claims. Its last bullet repeats P-7 ("9 µm crystals") and the stale
  "20–200 µm", so it must go.
- `cover_letter.md` is a skeleton with no claims yet.
