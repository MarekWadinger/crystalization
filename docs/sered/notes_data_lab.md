# Sereď sugar plant: plant-data knowledge notes (B)

Scope: SCADA and lab exports, translations, formula sheets, the ZRA lab run, and the video-folder documents.
BASE = `My Drive/sugar_plant`. Source keys used in citations:

| Key | Path (under BASE) |
|---|---|
| [VARNA-dd] | sered/data/Varna_dd_10_2025.xlsx / Varna_01_11_2025.xlsx |
| [STU] | sered/data/STU_DATA.xlsx |
| [SUR] | sered/data/Sur_Hodinovy.xlsx |
| [PAULEN] | sered/data/Paulen_data.xlsx |
| [MAP] | sered/data/varna_lab_variables_research_map_EN.xlsx |
| [T-VARNA] / [T-STU] / [T-SEED] | translated/Varna_31_10_2025_translated.xlsx / STU_DATA_translated.xlsx / Vzorce A_seed_translated_checked.xlsx |
| [SEED-F] / [VARO-F] | sered/Vzorce A_seed.xlsx / sered/Vzorce A_varostroj.xlsx |
| [ZRA-X] / [ZRA-D] | Data2026/ZRA.xlsx / Data2026/ZRA.docx |
| [KRYSTAL] | video/Krystal_260204_161114.pdf (4 scanned phone pages, no text layer; read as images) |
| [CAM] | video/Camera_100_Slovenske_cukrovary.pdf |
| [GRAN] | video/Granulometry_Zuckerslurry Se 2025-01-16 A.pdf |
| [GAB-R] / [GAB-P] | video/processing/gaborcik/GaborčíkSP3final.pdf / GaborčíkSP3presentfinal.pdf |

"(interp.)" marks my inference. Everything else is read directly from the cited file.

---

## 1. Data inventory

| File | Content | Time range | Sampling | Rows × cols |
|---|---|---|---|---|
| [VARNA-26..01] (7 files) | Boiling-house **lab** report ("procesné hodnoty"), not SCADA. Each file has one sheet `Hárok1`. Columns: tag name, low–high limit, unit, then 24 hourly columns | Each file covers 06:00 to 05:00 the next day. Together they span 2025-10-26 06:00 → 2025-11-02 05:00 | Hourly grid. Most products are sampled every 3 h (07,10,13,16,19,22,01,04); massecuites about twice a day; seeds about once a day | 380 tag rows × 24 h. About 81–89 rows per day contain data (about 530–545 cells) |
| [STU] | SCADA process tags for every pan in the boiling house plus dryer, CSB heating and receivers. Data is in `Sheet1` only; 5 other sheets are empty | 2025-10-26 00:01 → 2025-11-01 23:00 | 1 min, **no gaps** | 10 020 × 213 tags (header rows: TAG / SK name / unit / tag path) |
| [T-STU] | Same as [STU] with an added English name row and the column order changed (LI1000 moved to col 5). Extra sheets: `C-stage` (C1/C2 subset, 10 024 rows), `Hárok3` (QI1603 + QIC1600 PV), `Hárok2` (C1 subset, 508 rows, ends 2025-10-26 09:05) | same | 1 min | — |
| [SUR] | Hourly SCADA for the **beet end only**. Sheets: `Difuzia+Majcka` (74 tags), `Bicov+Vapenka` (54), `Odparka` (139), `Saturacia` (58). **No crystallization / ZRA sheet** | One row at 2025-08-21 10:00, then 2025-09-09 16:00 → 2025-11-11 09:00 | 1 h. One 19-day gap after the first row; one duplicated timestamp | 1 508 rows per sheet. Some cells contain "Tag '…' does not exist" (e.g. LIC216, SI007, SI38) |
| [PAULEN] | ZRA-only SCADA: 18 tags (PIDs included) | **2026-02-04 11:00:00 → 17:00:00** (same day as the Camera 100 video) | 30 s | 721 data rows (rows to 1000 are blank) |
| [MAP] | English research map of the lab variables. Sheets: README, Varna_variables (21), Varna_samples (18), Other_lab_results, Sources. Prepared 2026-07-08 | — | — | — |
| [T-VARNA] | Varna_31_10 with an EN column prepended. The translation is machine-like (see §7) | 2025-10-31 06:00 → 11-01 05:00 | 1 h | 380 rows |
| [SEED-F], [VARO-F], [T-SEED] | **Formula sheets, not lab sample sheets**: supersaturation ("KP") calculation and the Brix-vs-level cooking curve. Each has 1 chart | — | — | ~72 rows |
| [ZRA-X] | Fedor's manual lab sheet for ZRA on 30.10.2026: 17 samples, 11:00–18:04 | 2026-10-30 | Irregular, 2–50 min apart | 17 × 10 |
| [ZRA-D] | Operator time log for the same run, with video timecodes | 2026-10-30 | — | 21 lines |

## 2. Tag dictionary

### 2a. Area numbering in [STU] (interp., from the tag descriptions)
- 10xx = **ZRA, the seed pan** ("očkovací varostroj").
- 11xx/12xx/13xx = A1/A2/A3 pans. 14xx/15xx = B1/B2. 16xx/17xx = C1/C2.
- 18xx = common equipment: vacuum headers (PIC1802 "Vakuum A", PIC1803 "Vakuum B"), refrigerant receivers ("refrižeranty"), feed tanks, brüden (PIC1800/1801).
- 19xx = sugar dryer drum. 20xx = CSB filter/heater.
- **Tag numbers are not unique across [SUR]**: TI1000 = outdoor temperature (Difuzia sheet) and LIS1002 = molasses level (Odparka sheet). Always qualify a tag by its source file.

### 2b. ZRA (seed pan) tags

| Tag | SK name (source) | EN meaning | Unit | Typical range |
|---|---|---|---|---|
| LI1000 | Hladina očkovací varostroj [STU]; "Hladina" [KRYSTAL trend legend] | Seed-pan massecuite level | % | Median 79.2. Strike cycle runs ~45 % at fill → 99–106 % at end; about −0.7 when empty [STU] |
| PIC1001 | Tlak vykurovacej pary očkovací varostroj [STU] | Heating-steam pressure, seed pan (gauge) | kPa | While boiling: median 11–17 per strike, p99 22.8, max 27.7. **≈ −50.7 when steam is off** [STU]. [PAULEN] 2026-02-04: −50.7 … 25.5, median 6.5 |
| PIC1002 | Podtlak očkovací varostroj [STU]; "Podtlak" [KRYSTAL legend] | Pan vacuum (PV) | kPa | −76 … −80 while boiling; ~0 when the vacuum is broken; min −82 [STU] |
| PIC1002_PID/AO1/OUT | Otvorenie klapky pary ZRA [PAULEN]; "Otvorenie klapky pary" [KRYSTAL] | Steam-flap opening | % | 0 or 100 for most of the time; ramps up after filling [PAULEN] |
| PIC1003_PID PV/SP/OUT | Podtlak do ZRA [STU, PAULEN] | Vacuum controller | kPa / % | PV ≈ PIC1002 (corr 0.9998). SP −81 (−75 at times). OUT 0/100 [STU] |
| QI1003 | Viskozita ZRA, unit **°Bx** [STU]; "Viskozita", unit "°" [KRYSTAL] | Online "viscosity" signal that is really on a Brix/DS scale (interp.: density/Brix meter) | °Bx | Floor 64.99 = sensor minimum when empty. Strike start ~72–77 → end 90–92; median 84.5 [STU] |
| QIC1000_PID PV/SP/OUT | Sirup do ZRA aktuálna/nastavená/poloha [STU] | Syrup feed controller on the QI1003 signal | °Bx / % | PV ≈ QI1003 (corr 0.9995). SP climbs with level, 80 → 91 (cooking curve, §3c). OUT 0–100, median 26 [STU] |
| QIC1001_PID | Voda do ZRA [STU] | Water addition controller on the same Brix signal | °Bx / % | SP ~80.7–91.5. OUT mostly 0 [STU] |
| TI1006 | Teplota varostroj ZRA [STU] | Massecuite temperature | °C | 69–73 while boiling (median 70.8). Spikes to 90–103 when empty (interp.: steaming out; [KRYSTAL] logs "čistenie" 11:48–11:52) |
| TIC1002_PID | "Tlak pary ZRA" kPa [STU]; "Teplota ZRA" [PAULEN] | **Actually a temperature loop**: PV ≈ TI1006 (corr 0.997) | °C | SP fixed at 80. OUT 0/100 |
| EI1004 | Prúd miešadla ZRA [STU] | Stirrer motor current | A | ~10 A after the start → 14–16 A at the end of the strike (max 19.8). ~0.04 when stopped [STU] |
| S_ZRAVZORCE/VISKOZITA.CV | "Sekvencia ZRA" [KRYSTAL legend, trend "Trend100"] | Sequence/formula value on the Brix scale (interp.: Brix target computed from the "Vzorce" curve) | ° | 89.42 at 04-Feb-26 03:52:47, while QI1003 = 92.4 and LI1000 = 100.4. **Not present in any xlsx** |
| LI1005 | Hladina ZRA refrižerant ultrazvuk [STU] | ZRA receiver level (ultrasonic) | % | **Always 0: dead signal** [STU] |
| LI1009 | Hladina v očkovacom refrižerante [STU]; "Hladina ZRA refrižerant" [PAULEN] | Seed receiver level below ZRA | % | Jumps to ~106 at discharge, then drains over ~4 h (interp.: seed drawn off to the A pans) [PAULEN] |
| LI1010 / TI1008 | Hladina / Teplota seed horný (refrižerant) [STU] | Upper seed receiver | % / °C | 13–87 % / 60–66 °C |
| TI1007 | Teplota seed v refrižerante [STU] | Seed temperature in the receiver | °C | 54–65 |
| TI1011 / TIC1012 | Teplota pred / po nahreve SEED [STU] | Seed heater inlet / outlet | °C | TI1011 is dead (0). TIC1012 80–87 (median 83) |

### 2c. Other pans (same pattern of tags, from [STU])
- A pans (n = 1/2/3):
  - EI1n04 stirrer: median 38–42 A
  - LI1n00 level
  - PIC1n01 steam pressure
  - PIC1n02 vacuum: about −79
  - QI1n03 "Viskozita" °Bx: median 84.6–86.5
  - TI1n05 temperature: median 67.6–70.1
- B pans (QI14 03 / QI15 03) and C pans (QI1603 / QI1703): the same signal is called "**Hustota**" (density) in °Bx. Medians: B 88.4 / 87.8, C 90.4 / 92.6.
- C pans run hotter: TI1605 median 80.6 °C.
- PID SP examples:
  - Vacuum: A −85…−89, B −90, C −95 kPa.
  - TIC1x02 "tlak pary" SPs: A 80–91, B 78–90, C 15–38 (C2 up to 195). Unit is written as kPa, but for A and B the PV equals temperature (interp.).
- Flat or dead signals: FI2018/FI2019 ≈ −4.99, FI1846 −37.46, LI1806 = 0, PI1906 = 0, TI1841 = −200, PI2013/PI2015/PIC2014 ≈ −0.249.

### 2d. ZRA strike statistics from [STU] (2025-10-26…11-01, my segmentation at LI1000 ≥ 5 %)
- 47 strikes in 7 days (about 6.7 per day).
- Fill-to-discharge time 2.8–4.0 h (typically 3.0–3.6 h). Empty/turnaround time ~10–30 min. The pan is empty 7.4 % of the time.
- Per strike:
  - QI1003: start 71.7–76.9, end 89.9–91.9
  - EI1004: end-of-strike 13.7–17.9 A
  - TI1006: median 68.4–72.9 °C
- Example (2025-10-30 08:00–11:15):
  - Level 45 → 99 %
  - QIC1000 SP 81.6 → 89.7 rises with level
  - QI1003 74.4 → 89.8
  - EI1004 10.0 → 14.3 A
  - Then empty at 11:15 (TI1006 89 °C)

## 3. Lab variables and formulas

### 3a. Varna report ([VARNA-*], checked on every filled row in all 7 files)
- **sacharizácia = údaj refraktometra × 2**: exactly 2.000 for every product (example: 45.22 → 90.44).
- **polarizácia = údaj polarimetra × 4**: exactly 4.000 for every product, syrups and massecuites alike (example: 21.07 → 84.28). The unit of the raw reading is °Z.
- **kvocient čistoty = polarizácia / sacharizácia × 100**: residual 0.00 on every row.
- **necukry/voda = S·(1 − Q/100)/(100 − S)**. Example: Zadinová 93.98 / 71.76 → 4.41. C-seed 92.96 / 76.12 → 3.15.
- Interpretation (interp.): ×2 implies a 1 : 1 dilution before the refractometer. ×4 is consistent with the polarimeter run at a quarter of the normal weight. [MAP] treats "sacharizácia" as RDS/Brix-like dry substance and "Symas" as the value reported by the SYMAS lab system.
- Colour chain per product: sacharizácia zriedenej vzorky → hustota z tabuľky → absorbancia → farba (IU) [VARNA-30], method per [MAP]. The cell values are mangled (e.g. density 76 700); see §7.
- Tag prefixes: H = entered/measured, C = calculated, HP = note (interp.).
- Products and limits:

| Product (SK) | EN [MAP] | Limits S / Pol / Q (%) | Observed 26.10–01.11.2025 |
|---|---|---|---|
| A-SEED | A seed massecuite | 87–95 / 84–90 / 92–98.5 | Filled **once**, 29.10 19:00: S 95.62, Pol 71.00, Q **74.25**, pH 7.484 |
| Kryštálová cukrovina | A massecuite | 87–95 / 84–90 / 92–98.5 | S ~90.4–90.7, Q ~93–94.6 |
| Kryštálový sirup biely / zelený | A white / green runoff | Q 88–98 / 86–95 | Q (Symas) 92–94 / 84–90 |
| Náťah | pan feed syrup | 86–95 / 75–86 / 85–93 | Symas S 79–81, Q 84–89 |
| Medziproduktová cukrovina, sirupy | B massecuite, B runoffs | — | Q ~85–88; runoffs Q 71–85 |
| Zadinová cukrovina | C massecuite | 88–96 / 66–79 / 75–88 | Strike nos. 179–183. S ~94–95, Q ~72–74, N/W 4.2–5.2 |
| C-seed | C seed | 88–94.5 | Strikes 35 (26.10), 36 (28.10), 38 (30.10). S 92.1–94.3, Q 72.4–76.1, N/W 2.8–4.5 |
| Melasa | molasses | 80–92 / 46–57 / 54–72 | S 77–82, Q 58.6–60.2 |

- Header constants: Sn (feed S, campaign average) = 79.33. Qn = 86.00.
- Q_KSZ "koeficient spätného zvarovania": limit 0–0.3, observed −0.13…0.49 every 3 h. [MAP] says it has no public definition (internal KPI).

### 3b. ZRA lab run 30.10.2026 ([ZRA-X] formulas read with data_only=False)
- D = refract × 2. F = E/D × 100.
- **E = polari × 2 for "štandardný syrup"** (rows 11:00 and 14:55; Bx ~70.5–70.9).
- **E = polari × 4 for all massecuite samples.**
- So the polarimeter factor depends on the sample type: 2 for the thin standard syrup, 4 for massecuite (interp.: different sample weights).

### 3c. "Vzorce" formula sheets ([SEED-F], [VARO-F], translations in [T-SEED])
**"KP pre očko / pre A varostroj" (supersaturation coefficient):**
- Inputs: P = purity ("Q čistoty"), T, Bx = "Q aktuálna" (the same quantity the QI signal measures, interp.).
- Bsat(T) = 64.397 + 0.07251·T + 0.0020569·T² − 9.035e-6·T³ (sucrose solubility, DS %). At 65 °C this gives 75.32.
- NW = Bx·(100 − P)/100/(100 − Bx).
- SC = a·NW + b + (1 − b)·2.72·(−c·NW), with a = 0.5, b = 0.95, c = 1.
- **KP = Bx·P·(100 − Bsat) / ((100 − Bx)·Bsat·SC·100)**.
- Setpoint: **KP_SP = 1.3 (seed pan)**, **1.1 (A pan)**.
- Worked examples: seed P 93, T 65, Bx 75 → 0.89 [SEED-F]. [T-SEED] uses Bx 83 → 1.385. A pan P 94.5 → 0.92 [VARO-F].

**"Varenie krivka" (cooking curve: required Brix as a function of level):**
- Q(L) = Qs + (2 − k)x / (1 + x(1 − k)) · (Qe − Qs), with x = (L − Ls)/(Le − Ls).
- Seed: Qs 83, Qe 93, Ls 40, Le 100 %, k 1.6.
- A pan: Qs 83, Qe 94, Ls 60, Le 100, k 1.5.
- This matches the level-dependent QIC1000 SP behaviour in [STU] (interp.). The STU SP stays below the sheet values (max 90.99 vs 93).
- KP check on the [ZRA-X] seeding sample (Bx 79.04, P 93.62), my calculation (interp.):
  - 70 °C: KP_sheet 1.05
  - 65 °C: KP_sheet 1.12
  - Both are below the 1.3 setpoint. TI1006 for 30.10.2026 is not in any file in my scope.

## 4. Granulometry, camera hardware, operator logs
- [GRAN] Seed slurry measurement:
  - Instrument: Malvern Mastersizer Xplorer v5.20, S/N MAL1085194, AGRANA "Sugar Technology intern".
  - Sample "Zuckerslurry Se 2025-01-16" ("Se" = Sereď, interp.), measured 04.03.2025.
  - Method: Mie model, 2-propanol dispersant, RI 1.510 / 1.390.
  - 3 runs. Average **Dv10 1.57, Dv50 6.77, Dv90 18.6 µm** (run 1: 1.56 / 6.81 / 18.5).
  - D[3;2] 3.95, D[4;3] 8.71 µm. Span 2.489. Specific surface area 1520 m²/kg. Concentration 0.0081 %.
- [CAM] **Price quote only.** Quote number "P5PI – 100", Polz Instruments → Slovenské cukrovary s.r.o., Sereď (attn. Roman Gála, head of MaR), dated 6.10.2025.
  - Camera: Hanwha Vision (ex-Samsung) **HCB-6000** box camera, 1/2.8" CMOS, 2 MP.
  - Output: 1920×1080 (AHD/TVI/CVI) **or PAL CVBS**. WDR 120 dB, 12 V DC / 24 V AC, −10…55 °C.
  - Price 125 EUR without lens. No optics, magnification or µm/px are given.
- [KRYSTAL] Operator log for 2026-02-04 (PDF stamp 16:11:24):
  - ~11:48 discharge ("vyprázdnenie"); cleaning until filling at 11:52
  - 12:03 filling, bubbles at the camera; 12:05 many bubbles
  - 12:10 concentrating
  - 12:30 stabilisation, bubbles again, **seeding**, boiling-in with limited steam, "first crystals visible (very small inclusions)"
  - 12:39 boiling-up
  - 15:41 drying ("sušenie"); 15:58 vacuum break; 15:59 discharge; 16:07 new strike, vacuum
  - Note on page 1: "campaign ends 10.2–11.2, ideally collect by 10.2"
  - Pages 2–3: photos of the SCADA trend "Varostroj ZRA" (Trend100) with the 8-tag legend in §2b, covering 3.2 21:00 → 4.2 ~16:10, ~3.5–4 h cycles
- [ZRA-D] Operator log for 2026-10-30. Video start 08:45:33; the stated video offsets agree to within 1 min:

| Event | Clock time | Video offset |
|---|---|---|
| "Očko pustené" | 10:57 | ~2:12:00 |
| Camera flooded ("kamera zaplavená") at level 43.4 % | ~11:12:53 (computed) | 2:27:20 |
| Seeding ("očkovanie") | ~11:30 | 2:44:00 |

  - After seeding: samples at 11:32, 11:46 (10× zoom), 12:07 (no lab, 4×), 12:19, 12:30, 12:49, 13:06, 13:32
  - 14:10 before drying, 14:20 after drying
  - Strike 2: new batch ~14:50, seeding 15:22 (10× and 40×), 15:33 after seeding, then 15:54–17:48, 18:04 after drying
- [ZRA-X] lab values:
  - Strike 1: Bx 77.64 (before seeding) → 79.04 (after seeding) → 79.96 (after crystals are visible, 11:46) → 81.8 → 84.4 → 87.1 → 89.0 (before drying) → 90.78 (after drying)
  - Strike 2: 79.86 (seeding) → 90.24 (after drying)
  - **Purity is flat at 91.1–93.6** (mean ≈ 92.1)
  - Standard feed syrup: Bx 70.5–70.9, Q 91.8–91.9
  - Data2026 also holds microscope photos named by sample time (11-46.jpg … 17-48-4.jpg, PREDOCKOM, POOCKU, POSUS-18-04, MICRO)

## 5. Date coverage vs the video recordings

| Video | Overlapping data | Non-overlapping data |
|---|---|---|
| **2026-02-04 11:08:51**, Camera 100, 13.4 GB | [PAULEN] 11:00–17:00 at 30 s (ZRA only, **no LI1000**: use LI1009 + EI1004 + QI1003). [KRYSTAL] events 11:48–16:07 | [STU] / [VARNA] / [SUR] are all in the 2025 campaign |
| **2026-10-30 08:45:33**, ZRA lab run, 9.9 GB LQ | [ZRA-X] / [ZRA-D] only (11:00–18:04 lab) | No SCADA for 2026-10-30 in my scope. [STU] and [VARNA] cover **2025**-10-30, the same day and month one year earlier: **do not join them** |

Phase alignment for 2026-02-04 from [PAULEN] (my event detection: stirrer < 2 A or QI1003 at floor) plus [KRYSTAL]:
- 11:00–11:45: end of the previous strike. QI1003 87.7 → 90.8, EI1004 10.8 → 15.7 A, PIC1001 14 → 25 kPa. So **the video opens about 37 min before discharge**.
- 11:45:30: stirrer off. 11:48: LI1009 jumps to 106 % (discharge). 11:51: TI1006 96.6 °C (steam-out).
- 12:03: stirrer on, QI1003 74.9. Fill and concentrate. Seeding ~12:30 [KRYSTAL].
- 15:59:30: stirrer off (log: 15:58 vacuum break, 15:59 discharge). 16:13: next strike running.
- So the video holds about 1 complete strike (12:03–15:59, ~4 h) **if the recording runs past 16:00** (interp.; duration not checked).

## 6. Gaborčík project ([GAB-R], [GAB-P])
- Title: "Process Variable Monitoring Using Camera Data". Semestral project, Bc. Jakub Gaborčík, FCHPT STU, 2026 (PDF dated 2026-01-11). Supervisor doc. Ing. Radoslav Paulen, PhD.
- **It has nothing to do with sugar or crystals.** Content:
  - Trained YOLO12n (Ultralytics, 100 epochs, imgsz 640) to detect a glass and the water in it.
  - Hardware: Genius FaceCam 2000X2 1080p webcam, Acer Nitro laptop with RTX 4060.
  - Dataset: 87 photos, split 60/14/13; augmented in Roboflow to 180/14/13. The slides say "207 images available".
  - Water volume is estimated from the water-height / glass-height ratio, assuming a linear map with bias.
  - Confusion matrices: 13/14 glass and 13/14 water correct (validation); 12/13 and 11/13 (test).
  - Planned next steps: water drops in a lab distillation column (volumetric flow), then deployment on a microcontroller.
- **No crystal sizes, µm values, or plant results are claimed anywhere.** It sits in video/processing/ probably only as a related camera-sensing precedent (interp.).

## 7. Open questions
1. What does S_ZRAVZORCE/VISKOZITA ("Sekvencia ZRA") compute? Is it the "Vzorce" cooking-curve target? It is not exported in any xlsx. [KRYSTAL]
2. Duration of the 2026-02-04 video: does it cover the full 12:03–15:59 strike? Is there SCADA after 17:00?
3. Is there SCADA (LI1000, PIC1001/2, QI1003, EI1004, TI1006) for 2026-10-30? Not in my scope; [ZRA-D] gives the level only once (43.4 % at camera flooding).
4. What does "Očko pustené 10:57" mean: seed pan filling started, or slurry admitted? Seeding itself is logged at 11:30 [ZRA-D].
5. The meaning of "Camera 100" is unclear. Options: the quote number P5PI-100 [CAM], the 100x ZRA tag block, or "Trend100" [KRYSTAL]. Lens and optics are not documented.
6. Why does the polarimeter factor change (×2 for standard syrup vs ×4 for massecuite, [ZRA-X])? Sample weights and dilution should be confirmed with the lab.
7. What is the formula for Q_KSZ (koeficient spätného zvarovania), and what do Sn = 79.33 / Qn = 86 represent? [MAP] says "internal".
8. Is QI1003 a Brix/density meter (labelled "Viskozita", unit °Bx)? Its type and calibration are unknown; it is clipped at 65.
9. What is the source of the KP coefficients a/b/c = 0.5/0.95/1, and which T feeds KP in the DCS (TI1006?) [SEED-F]?
10. Video_link.gdoc is only a stub: doc id 1ciQLHIjnVrW2r6vjZpymLmrFbVB6to8rzlqOGwK7Qbs. Reading it through the Drive connector failed with "insufficient scope", so its contents are unknown.

## 8. Contradictions and data-quality flags
- **The brief assumed "Vzorce A_seed / A_varostroj" are lab sample sheets.** They are DCS formula sheets (KP and cooking curve). The refract/polari formulas are in [VARNA-*] and [ZRA-X] instead. [SEED-F], [VARO-F]
- **The brief says Varna files are "daily SCADA exports".** They are lab reports with hourly columns. The ZRA SCADA tags (LI1000, PIC1001…) are in [STU] and [PAULEN], not in Varna or [SUR].
- **Likely bug in the KP sheet:** `(1-E3)*2.72*K3` multiplies by 2.72 instead of raising e^K (Wright/Vavrinecz form). With e^K, KP drops by about 6–9 % (seeding sample at 70 °C: 1.05 → 0.98) (interp.). [SEED-F], [VARO-F]
- **Tag naming mismatches:**
  - TIC1002/TIC1x02 "Tlak pary … kPa" [STU] is really temperature (PV = TI1006; [PAULEN] calls it "Teplota ZRA").
  - LI1009 is called "Hladina ZRA refrižerant" in [PAULEN] but "Hladina v očkovacom refrižerante" in [STU], while LI1005 is the "ZRA refrižerant ultrazvuk" (dead).
  - PIC1002 is the vacuum PV, but PIC1002_PID/AO1 output is the "steam flap opening".
- **A-SEED purity:** the only A-SEED lab row (29.10.2025) has Q 74.25 against a 92–98.5 limit and Pol 71.00 against an 84–90 limit. That looks like C-seed-type material or a mis-entry. The ZRA purity measured in 2026 is ~92. [VARNA-29], [ZRA-X]
- **Lost decimal points:** pH and some colour cells are stored as integers with the decimal separator stripped (pH 8701 = 8.701; Symas colour 2 378 000; density 76 700). Most other values are comma-decimal strings. Parse both. [VARNA-*]
- **Varna_26 was edited later** (file mtime 3 Sep 2026; the other Varna files are dated Dec 2025): the header is partly translated in place and the sheet has 1000 rows instead of 381 elsewhere. [VARNA-26]
- **Translation errors:**
  - "varostroj" rendered as "evaporator" ("Seeding evaporator level") [T-STU]
  - "Kryštálová cukrovina" as "Crystal candy", "číslo varu" as "boiling point" (it means strike number), "spätné zvarovanie" as "back welding" [T-VARNA]
  - [MAP] gives the correct terms
- **[MAP] "Other_lab_results" names the plant "Sládkovičovo"**, but every other source says Sereď ([CAM] address Cukrovarská 726, Sereď).
- **[GAB-R] internal inconsistencies:** the Acer spec table is captioned as the webcam table, and "87 photos" (report) differs from "207 images" (slides, post-augmentation).
- **[STU] has 7 pans × the same signal under different names** ("Viskozita" for ZRA/A, "Hustota" for B/C), all in °Bx. Do not treat them as different physical quantities without confirmation.
