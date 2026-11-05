# Camera 100 — Optical Chain Inventory

Plant: **Slovenské cukrovary, s.r.o., Sereď**. Camera designation: Camera 100.
Purpose: post-hoc calibration of px → µm at the object plane from historical
video.

> Every entry is tagged as **FACT** (directly observed in a photo/PDF or
> stated by the operator), **DATASHEET** (manufacturer spec sheet with URL),
> **DERIVED** (computed from FACT/DATASHEET — formula shown), or **ESTIMATE**
> (informed guess with stated assumption and uncertainty). No other category
> is allowed in this document.
>
> **Single source of the numbers:** [`configs/camera_100.toml`](../../configs/camera_100.toml),
> where every value carries its source class (MEASURED, PHOTO, DATASHEET, PLANT,
> ESTIMATE, ASSUMED, CHOICE, DERIVED, UNSOURCED). Where this page and the
> config disagree, the config wins. Pixel-scale derivation and its budget:
> [`../optics/scale_chain.md`](../optics/scale_chain.md).
>
> **2026-11-03 audit.** This page used to describe a Hanwha HCB-6000 (colour
> CMOS, 1920 × 1080, 2.9 µm pitch). That model appears only in the Polz price
> quote; every photo of the installed camera shows an analog B/W **"ADEMCO
> VIDEO"** box camera (§1.1). The geometry values once tagged "measured
> 2026-09-07" are the plant's approximate answers of 2026-08-12 (Q&A below);
> no site measurement was made on 2026-09-07.
>
> Sources cited by short name: **Q&A** = "Potrebné dáta a otázky -
> Zodpovedane.docx", A. Fedor, 2026-08-12 (Drive `sugar_plant/sered/`; English
> in [`../sered/notes_plant_dcs_qa_photos.md`](../sered/notes_plant_dcs_qa_photos.md)
> §3 items 8–10, §4); **Aug-photos** = Drive [`sugar_plant/sered/photos/20260810_*.jpg`][ph-dir]; **Q&A** = [Fedor's answers, 2026-08-12][qa] (English: [notes](../sered/notes_plant_dcs_qa_photos.md)).

---

## 1. FACTS

### 1.1 Camera body

| Item | Value | Source |
|---|---|---|
| Label on the body | **"ADEMCO VIDEO"**, white analog box camera | PHOTO: [20260810_111738][ph-side], [20260810_111741][ph-side2], [20260205_122519](20260205_122519.jpg) |
| Rear panel | DIP switches L/L–INT, AI–AES, VIDEO/D.D., AGC, BLC, NC; V-PHASE and ALC pots; BNC video out; 12 VDC / 24 VAC terminal | PHOTO: [20260810_111636][ph-rear], [20260205_122519](20260205_122519.jpg) |
| Output | analog monochrome PAL (CVBS) | DERIVED from the rear panel and the 720 × 576 grey recordings (ffprobe, [config `[dvr]`](../../configs/camera_100.toml)) |
| Model | **unread** (sticker not photographed; no photo shows the underside) | — |
| Sensor | **752 × 582 pixels** (plant). The same e-mail gives "44 µm/px" and a "32 × 24 mm" field of view: that is the Fujinon datasheet's 1/3" object field at its 0.25 m minimum object distance (§1.4), i.e. the bare lens **without** the 60 mm tube; with the tube the scale is ≈ 11× finer (3.92 × 3.59 µm, [scale_chain.md](../optics/scale_chain.md)) | PLANT: R. Gála (head of MaR) e-mail, [screenshot](../sered/plant_email_gala_camera.jpg); date to be supplied |
| Best-match class | Ademco ACM570-family body with a PAL 1/3" 752 × 582 Sony CCD; see §1.1.1 | ESTIMATE ([config `[camera]`](../../configs/camera_100.toml)) |
| Body mount | **CS**: the rear panel matches the ACM570E, whose manual gives "CS or C (C mount adapter supplied)" ([p. 12][m570-12]), i.e. a CS body that takes C lenses through a 5 mm ring. The ACM574TPX "adjustable back focus" option ([p. 15][m574-15]) is excluded: its panel has a back-focus adjuster and lock ([p. 5][m574-5]), ours has neither ([rear photo][ph-rear]). The C adapter is presumably the thin part (≈ 3 mm visible) between tube and body ([20260205_122510](20260205_122510.jpg)); to confirm with a side photo. Author decision (2026-11-04, [CLAIM_CHANGES 75](../../papers/cep/CLAIM_CHANGES.md)): that ring is not part of the ≈ 6 cm; if it were, µm/px would be +8.9 % | DATASHEET (ACM570E family), PHOTO, author decision |
| Hanwha HCB-6000 | **not the installed camera**: it appears only in the [Polz quote `P5PI-100`](../Camera_100_Slovenske_cukrovary.pdf) (6 Oct 2025, "Cena bez objetivu: 125 EUR"); it is a colour CMOS camera without DIP switches | quote vs photos ([Q&A notes §7 item 1](../sered/notes_plant_dcs_qa_photos.md)) |

#### 1.1.1 Camera candidates

No document describes this exact camera. Two Ademco manuals each match part of it, so the model is a combination:

| Property | Our camera | ACM570E | ACM574TPX / ACM575X | Taken from |
|---|---|---|---|---|
| Brand, type | "ADEMCO VIDEO", B/W box ([photo][ph-side]) | Ademco, B/W ([p. 11][m570-11]) | Ademco, B/W ([p. 4][m574-4]) | both |
| Rear panel | 6-way DIP L/L–INT, AI–AES, VIDEO–D.D., BLC, AGC, NC; V-PHASE, ALC pots ([photo][ph-rear]) | AES/AI, Video/DD, line-lock, BLC, AGC ([p. 12][m570-12]) | ≈ 13 lettered switches (gamma, peak white, DCT, BLC windows…), back-focus adjust and lock, Y/C and twisted-pair outputs ([p. 5][m574-5]) | ACM570E |
| TV system | PAL, 720 × 576 recorded ([config `[dvr]`](../../configs/camera_100.toml)) | 768 × 494, 1/60 s shutter: NTSC ([p. 12][m570-12]); listed as "60 HZ" ([eBay][ebay570]) | **PAL: 752 × 582**, 1/50 s ([p. 15][m574-15]) | ACM574TPX |
| Sensor | – | 1/3" interline CCD ([p. 12][m570-12]) | 1/3" Sony HyperHAD CCD ([p. 4][m574-4]) | ACM574TPX |
| Sync | – | internal / line-lock ([p. 12][m570-12]) | AC line lock / internal ([p. 15][m574-15]) | both |
| Mount | – | CS, C adapter supplied ([p. 12][m570-12]) | C/CS, adjustable back focus ([p. 15][m574-15]) | ACM570E (see Body mount) |
| **Supply** | **12 VDC / 24 VAC** ([photo][ph-rear]) | **24 VAC only** ([p. 12][m570-12]), conflict | 11–28 VDC / 20–29 VAC ([p. 15][m574-15]) | ACM574TPX |

The supply conflict means it is either a European dual-supply ACM570 variant or another model with the same panel; no PAL ACM570 is documented online (searched 2026-11-04: ACM570X/EX/P, CCIR/50 Hz, Honeywell HCM successors, [2006 Honeywell catalogue](https://www.mirekkon.pl/HoneywellCCTV.pdf)).

Plausible Sony 1/3" CCIR B/W CCDs (all third-party datasheet mirrors; no Sony-hosted copy found):

| CCD | Generation | Effective pixels | Unit cell | CCD clock | Datasheet | Fit |
|---|---|---|---|---|---|---|
| ICX059CL | Hyper HAD era | 752 × 582 | 6.50 × 6.25 µm | – | [datasheetspdf](https://www.datasheetspdf.com/pdf/635780/SonyCorporation/ICX059CL/1) | plausible ("HyperHAD" in the ACM574 manual, [p. 4][m574-4]) |
| ICX409AL | Super HAD | 752 × 582 | 6.50 × 6.25 µm | 14.1875 MHz | [electronicsdatasheets](https://www.electronicsdatasheets.com/download/51ed4945e34e247a48795e46.pdf?format=pdf) | plausible; config nominal |
| ICX259AL | EXview HAD | 752 × 582 | 6.50 × 6.25 µm | 14.1875 MHz | [datasheetspdf](https://www.datasheetspdf.com/pdf/670591/SonyCorporation/ICX259AL/1), [Oxford table](https://users.ox.ac.uk/~atdgroup/referencematerial/Sony%20CCD%20and%20CMOS%202D%20imaging%20sensors.pdf) | plausible |
| ICX405AL | HAD | 500 × 582 | 9.8 × 6.3 µm | 9.46875 MHz | [electronicsdatasheets](https://electronicsdatasheets.com/download/51ed4945e34e247a48795e3c.pdf?format=pdf) | unlikely (low-res; the ACM570E is 580 TVL, [p. 12][m570-12]); error budget's `cand` row |

The three 752 × 582 chips share one cell size, so the choice does not change µm/px; the 500-cell chip moves it by < 1 % ([scale_chain.md](../optics/scale_chain.md)). The sticker (likely on the underside, which no photo shows) would settle the model.

[ph-rear]: https://drive.google.com/file/d/1fhHPQ9Laxp2ctcztOOm1k5Ne4F88HHCl/view
[ph-side]: https://drive.google.com/file/d/1RxxgmGLPGWU_Pv804bgTLWdzYb8k2YQR/view
[ph-side2]: https://drive.google.com/file/d/1aWfsUM9iMf6P8XLvKYFqC2JyxTqqyLPM/view
[m570-11]: https://www.manualslib.com/manual/892194/Ademco-Acm380e.html?page=11
[m570-12]: https://www.manualslib.com/manual/892194/Ademco-Acm380e.html?page=12
[m574-4]: https://www.manualslib.com/manual/1181686/Ademco-Acm574tp.html?page=4
[m574-5]: https://www.manualslib.com/manual/1181686/Ademco-Acm574tp.html?page=5
[m574-15]: https://www.manualslib.com/manual/1181686/Ademco-Acm574tp.html?page=15
[ebay570]: https://www.ebay.com/itm/294920318808

### 1.2 Signal chain to the recordings

The camera's analog line is digitised by a DVR. The plant says it does not
record, it only has "a signal-processing device" ([Q&A item 10][qa]); the DVR make is
unknown.

| Item | Value | Source |
|---|---|---|
| PAL recordings (e.g. `2026-02-04 11-08-51.mp4`) | 720 × 576, one sample = one BT.601 13.5 MHz sample, one line = one CCD row | MEASURED (ffprobe); sampling rate ESTIMATE |
| Sensor-plane size of a PAL sample | **6.831 µm (x) × 6.250 µm (y)** (cell × 14.1875 / 13.5 MHz; one row) | ESTIMATE, `python -m optics.scale_chain` |
| 1080p clips (`2026-02-05 *.mp4`) | screen recordings of the DVR monitor output: the PAL picture stretched **2.677 × (x) and 1.875 × (y)** in a black pillarbox. They add no resolution | MEASURED from the DVR's own OSD glyphs, [`../optics/scale_chain.md`](../optics/scale_chain.md) |

### 1.3 Lens

| Item | Value | Source |
|---|---|---|
| Brand on barrel | `FUJINON` | engraving in [`122620.jpg`](./20260205_122620.jpg) |
| Focal length / max aperture engraved | `1:1.6 / 35` | engraving in [`122620.jpg`](./20260205_122620.jpg) |
| Model | `HF35HA-1B` | operator (confirmed `B` suffix) |
| Focus ring current position | **not readable**: the ring carries only NEAR … FAR, no distance scale ([Q&A item 9][qa]; Aug-photos [20260810_112149][ph-focus1]–[112202][ph-focus2]). so the earlier "4 m" reading of [`122532.jpg`](./20260205_122532.jpg) cannot be a distance; which `4` mark was read is unclear. Retracted (§6) | PLANT + PHOTO |
| Iris setting | **F/1.6**, "if I read it correctly"; ring between 1.6 and 2 on the photos | PLANT ([Q&A item 9][qa]), PHOTO [20260810_112120][ph-iris] |

### 1.4 Lens — from manufacturer datasheet

| Item | Value | Source |
|---|---|---|
| Focal length (mm) | 35 | [Graftek HF35HA-1B](https://graftek.com/product/hf35ha-1b/), [Stemmer Imaging](https://www.stemmer-imagingusa.com/lenses/fujinon-lenses/c-mount-lenses/hf35ha-1b) |
| Iris range | F1.6 ~ F22 | same |
| Image format | 2/3" (Ø 11 mm circle) | same |
| Mount | C | same |
| Filter thread (mm) | M25.5 x 0.5 | same |
| Minimum object distance (from front of lens) (m) | ~0.25 | same |
| Focusing range (from front of lens) (m) | ~0.25 to ∞ | same |
| Focus | Manual | same |
| Iris | Manual | same |
| Iris / focus mechanism | with lock screws | same |
| Back focal distance (in air) (mm) | 15.03 | [Machine Vision Direct](https://machinevisiondirect.com/products/fujinon-hf35ha-1b) |
| Exit pupil position (from image plane) (mm) | -26.6 | [Stemmer Imaging](https://www.stemmer-imagingusa.com/lenses/fujinon-lenses/c-mount-lenses/hf35ha-1b) |
| Mass (g) | 45 | same |
| Angle of view (H x V) | 2/3": 14°20' x 10°46'<br>1/2": 10°27' x 7°51'<br>1/3": 7°51' x 5°53' | [Graftek HF35HA-1B](https://graftek.com/product/hf35ha-1b/) |
| Object dimensions at M.O.D. (H x V) (mm) | 2/3": 59 x 44<br>1/2": 43 x 32<br>1/3": 32 x 24 | same |

### 1.5 Sight glass

| Item | Value | Source |
|---|---|---|
| Standard mark | `DIN 89..` (last digit worn; `DIN 8902` most likely — see below) | engraving on glass, photos [`122524.jpg`](./20260205_122524.jpg), [`122532.jpg`](./20260205_122532.jpg) |
| Flange bolt count | **8** | operator, from [`122524.jpg`](./20260205_122524.jpg) |
| Material | tempered soda-lime (DIN 8902 disc, ≤ 150 °C, Ø 10–350 mm, 3–25 mm thick) | DIN standard |
| Thickness / diameter | **20 mm / Ø150 mm** | PLANT: [Q&A item 8(C)][qa] |
| Refractive index used | 1.47 (borosilicate) | ASSUMED; contradicts the soda-lime reading of the stamp (1.52 → Δ = 6.84 mm instead of 6.39 mm). The pixel scale at focus does not depend on it |

DIN 89xx candidates: **8902** (round soda-lime, ≤ 150 °C) is the fit for a round
disc on a ~70–80 °C vessel. **8901** is withdrawn; **8903** is rectangular. If
the temperature margin is tight or the disc is quartz, cross-check against
**DIN 7080** (round borosilicate, ≤ 280 °C).

### 1.6 Illuminator

| Item | Value | Source |
|---|---|---|
| Location | **inside the vessel** | operator |
| Type | **optical fibre** light guide, "very close to the glass", est. 1–2 mm from the inner face | PLANT: [Q&A item 8(D)][qa]; blue armoured cable into the flange on [Aug-photos 20260810_111738][ph-side] |
| Fixing screws (visible on the module) | 3 × **A2-70** stainless (ISO 3506, ~304 SS, 700 MPa) | engraving on bolt heads, operator |
| Power feed | two cables (blue + brown — European mains colours) crossing the 8-bolt flange itself | operator |
| Blue cable | 90° knee → straight run → taped joint after the knee; no other bends | operator |
| Brown cable | red collar/bushing at the bolt where it crosses the flange | operator |
| Manufacturer / model | **not identified** | — |

### 1.7 Installation

The vessel is the **seed pan** (ZRA, *očkovací varostroj*): it is seeded with
milled-sugar slurry (*mikroočko*) and makes the seed massecuite for the A pans
(Q&A; A. Fedor 2026-11-03; [`../sered/README.md`](../sered/README.md)). Crystal sizes
there run from ≈ 10–19 µm (slurry) through 22–35 µm one to two minutes after
seeding to 0.2–0.8 mm about two hours later (microscope, 2026-10-30,
[`../../datasets/README.md`](../../datasets/README.md)); there is no single
"≈ 9 µm" population in front of the lens.

Camera outside the vessel, looking through the sight glass. Lamp inside the
vessel, on the sight-glass side, facing the glass. Mains cables run through
the 8-bolt flange to power the lamp. What the camera sees is a **thin layer
of massecuite between the lamp face and the inner glass surface**,
backlit by the lamp. Crystals in that thin layer appear as **dark
silhouettes against the bright lamp**; the green-yellow spot in the video
is the lamp itself seen through the lit slab.

Only this geometry is consistent with all of: lamp inside, camera outside,
a bright direct spot in the image, and the fact that massecuite is opaque
over any longer path.

| Item | Value | Source |
|---|---|---|
| Camera mount orientation | horizontal | operator |
| Illumination | transmitted / backlit — lamp inside vessel, facing the sight glass | operator + green-yellow spot in [`122524.jpg`](./20260205_122524.jpg), [`122532.jpg`](./20260205_122532.jpg), [`122537.jpg`](./20260205_122537.jpg), [`122620.jpg`](./20260205_122620.jpg) |

---

## 2. DERIVED

### 2.1 Sensor active area and pixel pitch (ESTIMATE, candidate datasheet)

| Item | Value | Formula |
|---|---|---|
| Sensor active area | 4.89 × 3.64 mm | 752 × 6.50 µm by 582 × 6.25 µm (ACM570E-class candidate) |
| Sensor-plane µm per PAL sample / line | **6.831 × 6.250 µm** | cell × CCD clock / DVR rate; one row per line |
| Sensor-plane µm per 1080p clip pixel | **2.552 × 3.333 µm** | PAL sample / (2.677, 1.875) |
| Slurry-plane µm/px at focus, PAL | **3.92 × 3.59 µm** (95 %: ±≈ 10 %) | pitch · f / (e + x); `python -m optics.scale_chain` |
| Slurry-plane µm/px at focus, 1080p clip | **1.464 × 1.913 µm** (95 %: ±≈ 10 %; +8.9 % if the ring is in the tube) | same |

Superseded: 5.57 × 3.13 mm and 2.9 µm/px (Hanwha HCB-6000 / Sony IMX307, an AI
inference from the quote, commit b997e2f), which gave an isotropic 1.66 µm/px.

### 2.2 Forward optical scale at the user-reported focus reading (superseded)

> Historical. It rests on the retracted "4 m" focus reading and the Hanwha
> sensor; kept as the record of why an extension tube was suspected.

Bare lens (no extension tube), focus ring at 4 m → using the thin-lens
magnification M = f / (d − f):

- M = 35 / (4000 − 35) ≈ **0.0088 ×**
- Object-plane pixel size = 2.8 µm / 0.0088 ≈ **320 µm/px**
- Horizontal FOV at object plane = 5.37 mm / 0.0088 ≈ **610 mm**

This bare-lens FOV is **much wider than what [`datasets/snapshot 1.png`](../../datasets/snapshot%201.png)
shows**. The crystals in the snapshot are clearly sub-millimetre in detail
and fill a 600 px wide frame at obvious sharpness — incompatible with
~320 µm/px.

Two possible reconciliations: (a) an extension tube is fitted between the
lens and the camera body, raising the effective magnification, or (b) the
focus ring has slipped / been moved since the snapshot was recorded. (a)
is more likely because the focus lock screw is present and intact in the
photos.

---

## 3. ESTIMATES (clearly tagged — verify before relying on)

### 3.1 Sight-glass disc diameter and thickness

DIN 8902 covers Ø50–Ø200 mm discs; common DIN 28120 / DIN 8902 flanged
sight-glass fittings have these bolt-circle counts:

| DN | Typical bolt count (PN6 / PN10) |
|---|---|
| DN50 | 4 |
| DN80 | 4 (some PN10: 8) |
| DN100 | 8 |
| DN125 | 8 |
| DN150 | 8 |
| DN200 | 12 |

With **8 bolts confirmed**, the candidate sizes are **DN80 (PN10), DN100,
DN125, or DN150**. Using the lens body (29 × 29.5 mm per the Fujinon
datasheet) as a known scale in photo [`122524.jpg`](./20260205_122524.jpg),
the clear viewing aperture looks roughly 3–4× the lens width.

> **Plant answer ([Q&A item 8(C)][qa], 2026-08-12): Ø150 mm (DN150), 20 mm thick.** Index still assumed borosilicate.
> Superseded estimate: DN100, Ø100 mm clear, 15 mm thick.
> Refractive index assumed n_g ≈ 1.47 (borosilicate, visible band).
> **Verify by tape-measuring the flange OD or the bolt-circle diameter.**

### 3.2 Extension tube length

Assumptions:

- Focus ring reading 4 m is accurate (FACT).
- The visible horizontal FOV in [`snapshot 1.png`](../../datasets/snapshot%201.png) is **~20 mm** (visual
  estimate based on the crystal sizes appearing to be roughly 0.5–1.5 mm,
  which is normal for industrial massecuite). **This is the dominant
  assumption — confirm it before trusting the tube length.** (Superseded:
  the camera is on the seed pan, not an A pan, and the plant states the
  spacer as ≈ 6 cm, [Q&A item 8(A)][qa]. The calculation below is kept only as the
  record of how in-scene anchoring went wrong by ≈ 6×.)

Calculation:

- Required magnification M = 5.37 mm / 20 mm = 0.27 ×
- True subject distance d′ = f(1 + 1/M) = 35 × (1 + 1/0.27) = **165 mm**
- Required image distance i′ = f·d′ / (d′ − f) = 35 × 165 / 130 = **44.4 mm**
- Bare-lens image distance at focus = 4 m: i = 35 × 4000/3965 = **35.3 mm**
- Extension tube length e = i′ − i ≈ **9 mm**

Sensitivity to the FOV assumption:

| Assumed FOV in snapshot | Tube length |
|---|---|
| 15 mm | 12 mm |
| 20 mm | 9 mm |
| 25 mm | 7 mm |
| 30 mm | 5 mm |

> **Estimate: ~10 mm extension tube** (most common stock size in
> machine-vision toolkits). Range 5–12 mm depending on the true FOV.
> **Verify by callipering the silver collar between the lens C-mount
> thread and the camera body.**

---

## 4. UNKNOWN — needs measurement, document, or process data

| Item | How to close |
|---|---|
| Lens-front → outside face of sight glass | plant **≈ 2 cm** ([Q&A item 8(B)][qa]); a caliper reading is still missing |
| Sight-glass clear diameter | plant Ø150 mm ([Q&A item 8(C)][qa]); clear aperture not measured |
| Sight-glass thickness | plant **20 mm** ([Q&A item 8(C)][qa]) |
| Inside of glass → typical crystal plane | plant: focus on the inner glass face; fibre lamp 1–2 mm behind it ([Q&A item 8(D)][qa]) |
| Iris (F-stop) currently locked at | plant **F/1.6** "if I read it correctly" ([Q&A item 9][qa]) |
| Extension tube length, exact | plant **≈ 6 cm** ([Q&A item 8(A)][qa]). **Dominant term of the scale budget** (±5 mm → −7.6 / +8.9 % worst case); a caliper reading and a photo of the mount would cut the 95 % budget from ±10 % to ±3 % |
| Is a 5 mm CS→C ring inside the ≈ 6 cm? | photo of the body mount; +8.9 % in µm/px if yes |
| Camera model sticker | photo of the sticker; removes the 752- vs 500-cell CCD term (0.6–0.8 %) |
| Focus-helicoid travel | 1 mm is an AI guess (no record); ±1 mm → ∓1.6 % in µm/px; caliper the lens body length |
| Camera-side capture chain (DVR model, codec, rescaling) | plant: "will be supplied" ([Q&A item 10][qa]). The 1080p display stretch is measured (§1.2); the DVR's 13.5 MHz sampling is assumed |
| °Brix and temperature of the liquor over the video archive period | DCS historian export |
| Lab MA / CV sieve results over the same period | lab archive |
| Maintenance log entries for Camera 100 | plant MaR records |
| Illuminator manufacturer / model | photo of any nameplate on the module; measure module OD |
| Gap between lamp face and inner sight-glass surface (= imaging slab thickness) | direct measurement at maintenance window; sets depth of field for µm/px |
| Last visible digit of the sight-glass `DIN 89..` engraving | clean the disc rim, photograph obliquely |

---

## 5. File inventory

| File | Content |
|---|---|
| [`20260205_122510.jpg`](./20260205_122510.jpg) | Wide view: lens, sight-glass flange, plant context |
| [`20260205_122519.jpg`](./20260205_122519.jpg) | Camera external control unit (DIP switches, terminals) |
| [`20260205_122524.jpg`](./20260205_122524.jpg) | Sight-glass flange, bolt circle (8 bolts), internal LED |
| [`20260205_122532.jpg`](./20260205_122532.jpg) | Lens — operator's perpendicular view (focus = 4 m read here) |
| [`20260205_122537.jpg`](./20260205_122537.jpg) | Lens above sight glass + glass rim engraving partial |
| [`20260205_122542.jpg`](./20260205_122542.jpg) | Lens close-up: `1.6 / 2 / 4 / FAR` marks |
| [`20260205_122552.jpg`](./20260205_122552.jpg) | Lens close-up + lock screw + ring markings |
| [`20260205_122600.jpg`](./20260205_122600.jpg) | Lens close-up: `NEAR / 16 / 8 / 4 / FAR / 2 / 1.6` |
| [`20260205_122620.jpg`](./20260205_122620.jpg) | Model nameplate: `FUJINON 1:1.6/35 HF35HA-1B` |

---

## 6. Errata — claims previously made by the assistant and now retracted

| Earlier claim | Status |
|---|---|
| `-F` suffix means DC/auto-iris | retracted — operator confirms `-B`, manual iris |
| Iris range stops at F/16 | retracted — verified F/1.6 – F/22 |
| MOD = 0.2 m | retracted — verified MOD = 0.25 m |
| MOD = 0.3 m | retracted — verified MOD = 0.25 m |
| Focus ring scale = `0.2 – 0.3 – 0.5 – 1 – 2 – ∞` | retracted — no verified source for tick positions |
| Distortion ≤ −0.1 % | retracted — no verified source |
| Two rings, one focus and one iris (with NEAR/FAR on focus ring) | unverified — operator reports `NEAR/FAR` shares visual field with the f-stop marks |
| Iris currently F/4 | retracted — was wrong interpretation; operator says the `4` reading is the focus position |
| Focus ring at 4 m | retracted 2026-11-03 — the ring has no distance scale ([Q&A item 9][qa]; Aug-photos [20260810_112149][ph-focus1]–[112202][ph-focus2]) |
| Camera = Hanwha HCB-6000, 1/2.8" CMOS, 2.9 µm pitch | retracted 2026-11-03 — quote only; the installed body is an "ADEMCO VIDEO" analog B/W PAL CCD (§1.1) |
| e = 60 mm, a = 20 mm, t = 20 mm "measured on site 2026-09-07" | corrected 2026-11-03 — plant approximations "≈ 6 cm", "≈ 2 cm", "20 mm" from the 2026-08-12 Q&A; 2026-09-07 is the date they were relayed in chat |
| The imaged population is the ≈ 9 µm Mastersizer slurry | retracted 2026-11-03 — the Mastersizer (Dv50 6.81 µm) describes the seed slurry before seeding; crystals in the seed pan grow to 0.2–0.8 mm within ≈ 2 h (microscope 2026-10-30) |

---

*Last updated: 2026-11-03 (camera, scale and geometry sources). Maintained by Marek Wadinger.*

[ph-dir]: https://drive.google.com/drive/folders/1uJTXGOnoWwBXfCj1Nv_FOQvw8-3Lcyaq
[qa]: https://drive.google.com/file/d/1cgfbt5J_RybBpDL5REj8ZUavK_UI-tuw/view
[ph-focus1]: https://drive.google.com/file/d/1ycLWYYtZgs-J23J1q9wOopz35r4Ikeqq/view
[ph-focus2]: https://drive.google.com/file/d/1vMolwuoEuK8AvDv-3gaaG4t-xm7y2g6g/view
[ph-iris]: https://drive.google.com/file/d/16XnIHE_P67oym-UcbYJx3Vvs5NAh1Mbv/view
