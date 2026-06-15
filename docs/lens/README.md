# Camera 100 — Optical Chain Inventory

Plant: **Slovenské cukrovary, s.r.o., Sereď**. Camera designation: Camera 100.
Purpose: post-hoc calibration of px → µm at the object plane from historical
video.

> Every entry is tagged as **FACT** (directly observed in a photo/PDF or
> stated by the operator), **DATASHEET** (manufacturer spec sheet with URL),
> **DERIVED** (computed from FACT/DATASHEET — formula shown), or **ESTIMATE**
> (informed guess with stated assumption and uncertainty). No other category
> is allowed in this document.

---

## 1. FACTS

### 1.1 Camera body

| Item | Value | Source |
|---|---|---|
| Make / model | Hanwha Vision HCB-6000 | Polz quote `P5PI-100`, 6 Oct 2025 |
| Lens not included | "Cena bez objetivu: 125 EUR" on the quote | Polz quote |

### 1.2 Camera body — from manufacturer datasheet

| Item | Value | Source |
|---|---|---|
| Sensor | 1/2.8" progressive-scan CMOS | [hanwhavision.com](https://www.hanwhavision.com/en/products/camera/analog/analog-box/hcb-6000/) |
| Native resolution | 1920 × 1080 | same |
| Output formats | AHD / TVI / CVI / CVBS-PAL | same |
| Lens mount | C / CS | same |
| Frame rate | 30 fps | same |

### 1.3 Lens

| Item | Value | Source |
|---|---|---|
| Brand on barrel | `FUJINON` | engraving in [`122620.jpg`](./20260205_122620.jpg) |
| Focal length / max aperture engraved | `1:1.6 / 35` | engraving in [`122620.jpg`](./20260205_122620.jpg) |
| Model | `HF35HA-1B` | operator (confirmed `B` suffix) |
| Focus ring current position | **4 m** (the `4` tick is aligned with the body index when looking down at the top of the horizontally mounted lens) | operator, read from [`122532.jpg`](./20260205_122532.jpg) |

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
| Standard mark | `DIN 8902` | engraving on glass, photos [`122524.jpg`](./20260205_122524.jpg), [`122532.jpg`](./20260205_122532.jpg) |
| Flange bolt count | **8** | operator, from [`122524.jpg`](./20260205_122524.jpg) |
| Material | borosilicate (the only material specified by DIN 8902) | DIN standard |

### 1.6 Installation

| Item | Value | Source |
|---|---|---|
| Camera mount orientation | horizontal | operator |
| Illumination | transmitted (LED inside vessel, opposite the lens) | green/yellow spot visible in [`122524.jpg`](./20260205_122524.jpg), [`122532.jpg`](./20260205_122532.jpg), [`122537.jpg`](./20260205_122537.jpg), [`122620.jpg`](./20260205_122620.jpg) |

---

## 2. DERIVED

### 2.1 Sensor active area and pixel pitch

| Item | Value | Formula |
|---|---|---|
| Sensor active area | ≈ 5.37 × 3.02 mm | 1/2.8" optical-format convention × 16:9 |
| Pixel pitch at sensor | ≈ **2.8 µm/px** | 5.37 mm ÷ 1920 |

### 2.2 Forward optical scale at the user-reported focus reading

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

> **Estimate: DN100, Ø100 mm clear, 15 mm thick borosilicate.**
> Uncertainty: ±25 % on diameter (could be DN80 or DN125), ±5 mm on
> thickness (could be 20 mm at higher PN class).
> Refractive index assumed n_g ≈ 1.47 (borosilicate, visible band).
> **Verify by tape-measuring the flange OD or the bolt-circle diameter.**

### 3.2 Extension tube length

Assumptions:

- Focus ring reading 4 m is accurate (FACT).
- The visible horizontal FOV in [`snapshot 1.png`](../../datasets/snapshot%201.png) is **~20 mm** (visual
  estimate based on the crystal sizes appearing to be roughly 0.5–1.5 mm,
  which is normal for industrial massecuite). **This is the dominant
  assumption — confirm it before trusting the tube length.**

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
| Lens-front → outside face of sight glass | tape measure, ±5 mm |
| Sight-glass clear diameter | tape-measure flange OD or bolt-circle Ø |
| Sight-glass thickness | vendor sheet, callipers at maintenance window |
| Inside of glass → typical crystal plane | tape measure or process-flow diagram |
| Iris (F-stop) currently locked at | read the iris ring against the body index dot in person |
| Extension tube length, exact | callipers between lens C-mount and camera body |
| Camera-side capture chain (DVR model, AHD/CVBS, codec, rescaling) | check the recorder rack |
| DIP-switch state on the external control box | sharp photo of the switch row in [`122519.jpg`](./20260205_122519.jpg) |
| °Brix and temperature of the liquor over the video archive period | DCS historian export |
| Lab MA / CV sieve results over the same period | lab archive |
| Maintenance log entries for Camera 100 | plant MaR records |

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

---

*Last updated: 2026-06-03. Maintained by Marek Wadinger.*
