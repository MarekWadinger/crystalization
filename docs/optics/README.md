# Camera 100 — Optics, Scale, and Defocus

**Author:** Marek Wadinger. **Last updated:** 2026-11-03 (analog-PAL scale, plant-sourced geometry, rerun of every number).
**Companion code:** `src/optics/`, `src/scale_overlay/`, tests in
`tests/test_optics.py`. **Companion hardware doc:** [`../lens/README.md`](../lens/README.md).

This chapter answers four questions for the Camera 100 installation in
the Sereď sugar plant:

1. **What is a pixel worth in millimetres at the focused plane?**
2. **How does mm/px change as crystals drift away from that plane?**
3. **What is the defocus-blur (sharpness) distribution along depth — is it Gaussian, gamma, or something else?**
4. **Can the depth-defocus relationship be paired with the in-frame sharpness map to read true crystal size per pixel?**

Every numerical claim is tagged **FACT** (observed in hardware photos / a
datasheet), **DERIVED** (computed from facts via the equations below),
**ESTIMATE** (informed guess with a stated assumption and uncertainty),
or **MEASURED** (extracted from the actual video frames). No other
category appears.

> **2026-11-03.** The single source of every physical input is
> [`configs/camera_100.toml`](../../configs/camera_100.toml), whose lines carry the finer classes
> MEASURED, PHOTO, DATASHEET, PLANT, ESTIMATE, ASSUMED, CHOICE, DERIVED, UNSOURCED
> (`tests/test_provenance.py`). Where this chapter and the config disagree, the config wins. The
> pixel scale is derived in [`scale_chain.md`](./scale_chain.md). Every number of the paper, old vs
> new, is in [`rerun_results.md`](./rerun_results.md) (`scripts/rerun_paper_numbers.py`). The camera
> is an analog B/W PAL CCD ("ADEMCO VIDEO"), not the Hanwha HCB-6000 of earlier versions. The
> geometry once tagged "FACT, operator measurement 2026-09-07" is the plant's approximate answer of
> 2026-08-12 (PLANT).

---

## 0. The video this chapter is calibrated against

| Item | Value |
|---|---|
| File | `datasets/2026-02-05 10-36-32.mp4` |
| Resolution | 1920 × 1080, 30 fps, 1568 frames: a **screen recording of the DVR monitor output**. It is the 720 × 576 PAL picture stretched 2.677 × (x) and 1.875 × (y) in a pillarbox ([`scale_chain.md`](./scale_chain.md)) |
| In-frame DVR timestamp | `2018-11-09 10:33:38` (the DVR clock is not set; the overlay date is not the recording date) |
| Recording date | **disputed**: the file birth time and name say 2026-02-05; the clip sidecar says 2026-02-04 (operator statement, June 2026). Time since seeding unknown ([`../../datasets/README.md`](../../datasets/README.md)) |
| First frame | [`figures/00_first_frame.png`](./figures/00_first_frame.png) |

![first frame](./figures/00_first_frame.png)

---

## 1. Hardware givens (FACT / DATASHEET)

These come from [`../lens/README.md`](../lens/README.md) and are repeated
here so this chapter stands alone numerically.

| Symbol | Meaning | Value | Source |
|---|---|---|---|
| f | Lens focal length | **35.00 mm** | Fujinon HF35HA-1B datasheet |
| N_max | Max aperture | **F/1.6** (full open) | Fujinon datasheet |
| N_min | Min aperture | **F/22** | Fujinon datasheet |
| MOD | Minimum object distance | **0.25 m** (≈ MOD relative to front element) | Fujinon datasheet |
| camera | Camera body | analog B/W PAL CCD, label **"ADEMCO VIDEO"** (PHOTO); model ESTIMATE: Ademco ACM570E-class | Aug-photos 20260810_111738, rear 111636; config `[camera]` |
| p_x × p_y | Sensor-plane size of one PAL sample × line | **6.831 × 6.250 µm** (ESTIMATE) | CCD cell 6.50 × 6.25 µm × 14.1875 MHz / 13.5 MHz (candidate datasheet); `optics.scale_chain` |
| W × H | CCD active area | **4.89 × 3.64 mm** (ESTIMATE) | 752 × 6.50 µm, 582 × 6.25 µm |
| stretch | 1080p clip px per PAL sample (x) / line (y) | **2.677 / 1.875** (MEASURED) | DVR OSD glyphs registered between the recordings |
| t_glass | Sight-glass thickness | **20 mm** (PLANT) | Q&A item 8(C), A. Fedor 2026-08-12; DIN 8902 disc, Ø150 mm (DN150), 8-bolt flange |
| a | Lens front → outer glass face (air gap) | **≈ 20 mm** (PLANT, "≈ 2 cm") | Q&A item 8(B) |
| n_g | Sight-glass refractive index | **1.47** (ASSUMED — borosilicate; the DIN 8902 stamp suggests soda-lime 1.52) | does not enter the scale at focus |
| e | Extension tube length | **≈ 60 mm** (PLANT, "≈ 6 cm"; the 45 mm was our own estimate sent with the questions). Whether a 5 mm CS→C ring is inside it is open (+8.9 % in µm/px) | Q&A item 8(A) |
| x | Focus-helicoid travel | **1 mm** (ESTIMATE, AI guess, no record) | ±1 mm → ∓1.6 % in µm/px |
| N_op | F-number in service | **F/1.6** (PLANT, "if I read it correctly"; ring between 1.6 and 2 on the photos) | Q&A item 9, Aug-photos 20260810_112120 |

The old rows (Hanwha HCB-6000, 2.9 µm IMX307 pitch, 5.57 × 3.13 mm; "FACT, operator measurement
2026-09-07") are superseded: the Hanwha appears only in a price quote, and no site measurement was
made on 2026-09-07.

---

## 2. Thin-lens model (DERIVED)

We use the standard Gaussian thin-lens approximation
(Hecht, *Optics*, 5th ed. §5.2):

$$ \frac{1}{f} = \frac{1}{d_o} + \frac{1}{i} $$

with **transverse magnification**

$$ M = \frac{i}{d_o} = \frac{f}{d_o - f}. $$

The extension tube ``e`` enters not as a separate term in the equation
but by *fixing* the image distance ``i = f + e`` whenever the lens
focus ring is wound to infinity. With the focus ring at any other
setting the ring trims ``i`` by a few mm around ``f + e``. This is
captured in the standard close-up identity
``m_x = (v + x)/f − 1 = m + x/f`` ([Photons-to-Photos, *Close-up
formulas*](https://photonstophotos.net/GeneralTopics/Close-up/How_Extension_Tubes_Affect_Magnification.htm) — derived from the
thin-lens equation in Hecht §5.2), giving ``m = e/f`` at infinity focus.

For the verified Camera 100 setup (`LensSetup` in
[`../../src/optics/model.py`](../../src/optics/model.py)):
``f = 35 mm``, ``e = 60 mm``, focus-ring travel ``x ≈ 1 mm`` → image distance
``i = f + e + x = 96 mm`` → focused object distance at that ring setting

$$ d_{\text{focus}} = \frac{f\,i}{i - f} = \frac{35 \cdot 96}{61} = \mathbf{55.1\ mm}. $$

This is a **macro setup** — working distance of about 6 cm, near 1:1
magnification. The focus ring may be off the infinity tick, but the
40 mm-plus extension tube fixes the regime: ``d_focus`` cannot exceed
55 mm at infinity ring nor fall much below ~52 mm at MOD ring (where
the lens adds ~5–6 mm of internal extension). For all calculations
below we use the central value ``d_focus = 55.1 mm``.

> **Historical note.** Earlier drafts of this document used
> ``e = 10 mm`` (an estimate from snapshot FOV) and inferred
> ``d_focus = 165 mm``. A 2026-06-15 revision (recorded then as an
> operator caliper reading; per the config it was our own estimate sent with
> the plant questions) gave ``e = 45 mm``, ``d_focus = 62.2 mm``;
> the plant's Q&A answer (2026-08-12, relayed 2026-09-07) gave ``e ≈ 60 mm``,
> ``d_focus = 55.1 mm`` and ``t = 20 mm``, ``a ≈ 20 mm``. With the
> superseded isotropic 2.9 µm pitch this was 1.66 µm/px; with the analog
> chain it is 1.464 × 1.913 µm/px on the 1080p clips (§3). The detector
> medians that moved with these revisions (0.25 → 0.037 mm) are detector
> artefacts, not crystal sizes, and no strike stage can be read from them
> ([`rerun_results.md`](./rerun_results.md)).

> **Compound-lens caveat.** The Fujinon HF35HA-1B is a multi-element
> design, not a thin lens. The thin-lens identity ``M = i/d_o`` holds
> for *effective* focal length and *effective* image distance measured
> from the rear principal plane, but the principal plane position is
> not the front mounting flange. For FOV / pixel-pitch budgeting at
> the few-percent level this is fine; for sub-pixel metric
> reconstruction the lens has to be empirically calibrated (Mannan &
> Langer, CRV 2016 — see §11.2).

### 2.1 Sight-glass refractive shift

A parallel glass slab of thickness ``t`` and index ``n_g`` shifts the
*apparent* object distance toward the lens by

$$ \Delta = t\left(1 - \frac{1}{n_g}\right) $$

(Hecht §5.6.1, paraxial limit; same formula in any introductory optics
text — see [Concepts of Physics, "Refraction from a glass slab"](https://www.concepts-of-physics.com/optics/refraction-from-a-glass-slab.php)
for a step-by-step derivation). With t = 20 mm and n_g = 1.47,
**Δ = 6.39 mm**, independent of the object distance. The optical
calculations are with **apparent** object distance; the real distance
to a crystal is the apparent value plus Δ. (Caveat: this is the
*first-order* paraxial form — see §6.3.3 for the exact 12th-degree
polynomial result of [Agrawal et al., CVPR 2012](https://www.umiacs.umd.edu/~aagrawal/cvpr12flatport/index.html).)

![sight glass shift](./figures/05_sight_glass_shift.png)

---

## 3. Pixel → millimetre at the focused plane (DERIVED + MEASURED)

The object-plane pixel size at the focused plane is, per axis,

$$ \Delta x = \frac{p_x}{M} = p_x\,\frac{d_{\text{focus}} - f}{f}, \qquad \Delta y = \frac{p_y}{M}, $$

with p_x, p_y the sensor-plane size of one frame pixel (§1). The pixel is **not square**.

| Quantity | Value (d_focus = 55.1 mm, e ≈ 60 mm); class ESTIMATE |
|---|---|
| M = f / (d_focus − f) | **1.743 ×** |
| PAL sample at focus, x × y | **3.919 × 3.586 µm** (95 %: ±9.8 / ±9.5 %) |
| 1080p clip pixel at focus, x × y | **1.464 × 1.913 µm** (95 %: 1.331–1.618 / 1.746–2.107); geometric mean 1.673 µm, for areas only |
| … if the 5 mm CS→C ring is inside the ≈ 6 cm | +8.9 %: clip 1.600 × 2.092 µm |
| FOV at focus = CCD area / M | **2.80 × 2.09 mm** |
| px/mm at focus, 1080p | **683 (x), 523 (y)** |

Budget, Monte Carlo and the empirical checks: [`scale_chain.md`](./scale_chain.md). The tube
length dominates; glass index, thickness and air gap do not change the scale at focus.

### 3.1 In-scene anchoring (MEASURED)

Autocorrelation of mid-frame rows gave a first-decorrelation length
of **~42.5 px (median over 18 rows)** in `frame 0` (UNSOURCED: the
script is not in the repo). This corresponds to roughly half the spacing
between adjacent crystal edges, so the dominant texture period is
**~85 px**. Along a row of the 1080p clip (1.464 µm/px) this is
**~0.125 mm** (0.14 mm at the superseded 1.66 µm/px). It is not used as
a scale anchor or a crystal size. Strike stage is not inferred from this size: the
camera sits on the **ZRA seed pan** (seeded with slurry, "mikroočko";
plant Q&A *Potrebné dáta a otázky – Zodpovedané*, 2026-08-12, and the
DeltaV "Udaje ZRA" screen; see `docs/sered/notes_plant_dcs_qa_photos.md`),
and frame 0 (11:08:39) lies ~37 min before the 11:46 discharge of the
previous ZRA strike (`datasets/2026-02-04 11-08-51.json`, event b1-e00). That timing holds only
for the PAL recording; for the `10-36-32` clip of §0 the date is disputed and the time since
seeding is unknown.
An earlier version of this section cited an unsourced "operator
confirmation" of an A-strike first hour; that claim is withdrawn.

### 3.2 Extension-tube sweep (historical sensitivity)

This figure was decisive in the 2026-06-15 revision: at the (then-
estimated) e = 10 mm the predicted µm/px ≈ 10 µm/px landed in the
mid-strike crystal-size range and looked "self-consistent"; only the
estimate of e = 45 mm (then the plant's ≈ 60 mm) revealed that we were a
factor of ≈ 5.5 off in the scale ((60 + 1)/(10 + 1)). The figure now uses the PAL-sample geometric
mean (6.53 µm), so its curves are per PAL sample, not per clip pixel.

![extension tube sweep](./figures/06_extension_tube_sweep.png)

A 1 mm error in e gives a 1.6 % error in µm/px at the focused plane
(1/(e + x)) and a 0.33 mm error in d_focus (f²/(e + x)²).

---

## 4. mm/px as the subject moves away from focus (DERIVED)

Once the focus ring is set the lens–sensor distance ``i_fixed`` is
constant. The image of an object at arbitrary depth ``d_o`` is
projected onto the sensor with transverse magnification

$$ M(d_o) = \frac{i_{\text{fixed}}}{d_o}, $$

so the object-plane pixel size

$$ \Delta x(d_o) = \text{pitch}\,\frac{d_o}{i_{\text{fixed}}} $$

is **strictly linear in ``d_o``**. Doubling the distance doubles
the mm/px. The defocus blur (§5) does *not* change this geometric
mapping — defocus spreads each point across many pixels but the
*centroid* of the spread sits exactly where geometric optics says.

![mm per pixel vs distance](./figures/01_mm_per_pixel.png)

### Numerical answers around the focused plane

| d_o (mm) | 1080p µm/px x × y | PAL µm/px x × y |
|---:|---:|---:|
| 50 | 1.330 × 1.737 | 3.56 × 3.26 |
| **55.1 (focus)** | **1.465 × 1.914** | **3.92 × 3.59** |
| 60 | 1.596 × 2.085 | 4.27 × 3.91 |
| 65 | 1.729 × 2.258 | 4.63 × 4.23 |
| 80 | 2.128 × 2.779 | 5.70 × 5.21 |

(`optics.config.um_per_px_xy_at_focus` × d_o/d_focus; ESTIMATE.)

---

## 5. Defocus blur — circle of confusion (DERIVED)

For a lens focused at ``d_focus`` with aperture ``A = f/N``, the
**circle of confusion** diameter at the sensor for an object at
``d_o`` is

$$ c(d_o) = \frac{f^2}{N (d_{\text{focus}} - f)} \cdot \frac{|d_o - d_{\text{focus}}|}{d_o}. $$

This is the standard textbook form — verified verbatim against the
[Wikipedia *Circle of confusion* article](https://en.wikipedia.org/wiki/Circle_of_confusion#Determining_a_circle_of_confusion_diameter_from_the_object_field)
("c = A |S₂ − S₁| / S₂ · f / (S₁ − f)") and against [Pertuz, Puig &
García (2013), Pattern Recognition 46:1415–1432](https://doi.org/10.1016/j.patcog.2012.11.011)
which cites it back to Pentland 1987. See
[`model.py:circle_of_confusion`](../../src/optics/model.py).

The behaviour is **asymmetric in object space**:

- **near side** ``d_o < d_focus``: c grows fast (|d − d_f| grows *and* the 1/d term grows);
- **far side** ``d_o > d_focus``: c saturates at the hyperfocal limit ``c_∞ = A f / (d_focus − f)`` as ``d_o → ∞``.

In the reciprocal-distance variable ``u = 1/d_o`` the geometry is
**linear and symmetric** around ``u_focus = 1/d_focus``:

$$ c(u) = \frac{f^2}{N}\,|u - u_{\text{focus}}|. $$

This is the natural variable for fitting depth-from-defocus models.

![CoC vs distance](./figures/02_coc_vs_distance.png)

### 5.1 Depth of field is *extraordinarily* tiny here

DoF for F-numbers from 1.6 (the verified current setting) to 16, with
focus at d_focus = 55.1 mm:

![depth of field envelope](./figures/04_dof_envelope.png)

The blur threshold is one **PAL sample** (CCD cell, 6.53 µm geometric mean at the
sensor): the 1080p clip pixels are upscaled PAL samples and carry no extra
resolution. Total DoF (near + far):

| F-number | DoF at 1-sample blur (6.5 µm) | DoF at 2-sample blur (13.1 µm) |
|---|---:|---:|
| **F/1.6 (CURRENT)** | **≈ 0.019 mm** | **≈ 0.038 mm** |
| F/2.0 | ≈ 0.024 mm | ≈ 0.047 mm |
| F/4.0 | ≈ 0.047 mm | ≈ 0.094 mm |
| F/8.0 | ≈ 0.094 mm | ≈ 0.189 mm |
| F/16 | ≈ 0.189 mm | ≈ 0.378 mm |

**The current operating point is extreme.** At F/1.6 the in-focus
slice is only **±9.4 µm** at 1-sample blur (±4.2 µm if one counts the 2.9 µm
clip pixel, as the paper did). That is thinner than the crystals minutes after
seeding (22–35 µm, microscope 2026-10-30). Detected crystals are essentially **all at one depth**, which
makes the depth-aware machinery of §§5–6 of the manuscript
*demonstrated but not load-bearing* at this aperture. The principal
plant-side recommendation remains: **stop the lens down**. Going from
F/1.6 to F/16 multiplies the in-focus depth by 10×, finally admitting
3-D structure into the data.

---

## 6. Sharpness vs depth — power-law, NOT Gaussian (DERIVED + MEASURED)

### 6.1 Theory

Approximate the defocus PSF as a Gaussian with ``σ ≈ c/2`` (Pentland
1987; Subbarao & Surya 1994). Its OTF is

$$ |H(u)|^2 = \exp(-4 \pi^2 \sigma^2 u^2). $$

A Laplacian-variance sharpness measure (and Tenengrad, Brenner, etc.)
weights the OTF by ``u^4`` and integrates:

$$ S(\sigma) \propto \int_0^{u_N} |H(u)|^2 u^4\, du \approx (\sigma^2 + \sigma_0^2)^{-5/2}, $$

with a finite floor ``σ_0`` coming from the Nyquist limit
``u_N = 1/(2\,\text{pitch})`` and diffraction
``σ_{\text{diff}} = 0.42 \lambda N`` (Goodman, *Introduction to Fourier
Optics*, §6.2 — Gaussian fit to the Airy PSF). Combined with the c(d_o)
formula above:

- in **d_o** space, sharpness has a **power-law cusp**: very tall, very
  narrow at the focused plane, asymmetric (sharper falloff to the
  near side);
- in **u = 1/d_o** space, the cusp is **symmetric**;
- it is **not a Gaussian** — the wings fall as ``c^{-5}``, much heavier
  than a Gaussian's exponential decay;
- a gamma distribution does not fit it either — the asymmetry is in
  the *position* (mapped via ``d_o → 1/d_o``), not in the *shape*.

![sharpness vs distance](./figures/03_sharpness_vs_distance.png)

The red dashed reference Gaussian (FWHM-matched to the diffraction-floor
model) shows how dramatically different the actual shape is from a
Gaussian — it has a sharper peak and much heavier tails.

### 6.2 Measurement on the plant video

Code in [`src/optics/measure.py`](../../src/optics/measure.py)
aggregates a Laplacian-variance histogram across 120 sampled frames of
`datasets/2026-02-05 10-36-32.mp4` (every 5th frame, subsampled per
frame, **overlay-cropped**) and fits a power law to the upper tail
(50–95 % quantile band):

| Crop | α (MEASURED) | vs 5.00 |
|---|---:|---:|
| none (contaminated) | 5.36 | +7.2 % |
| top 55 + bottom 120 (DVR overlay only) | 4.57 | −8.6 % |
| `DEFAULT_CROP` (+ left 50, right 70) | 4.88 | −2.5 % |
| **auto crop, `resolve_crop` (what `optics.measure` runs; fig 08)** | **4.90** | **−2.0 %** |

(`scripts/rerun_paper_numbers.py`, rows 48–51; scale-free.) The paragraph below
discusses the overlay-only crop, before the side bars were removed.

![measured vs theory](./figures/08_measured_vs_theory.png)

The cropped α = 4.57 sits *below* the theoretical 5.00. This is the
direction predicted by the **diffraction + sensor floor** on the
sharpness model: the very-sharpest pixels are softened by the
σ_floor term, which gently *flattens* the upper tail rather than
sharpening it. The pre-crop α = 5.36 had it the other way — too
steep — because perfect digital glyph edges in the DVR datetime
overlay (see §13 of [`disambiguation_results.md`](./disambiguation_results.md))
were extending the tail past where any physical crystal could
contribute, producing a tail that looked artificially fat.

> **Honest framing.** Neither 5.36 (overlay-contaminated) nor 4.57
> (cropped) is a clean 1-to-1 measurement of the theoretical c⁻⁵
> exponent — the histogram x-axis is ``log1p(Laplacian²)`` and the
> change-of-variable from CoC c to that axis is non-trivial. The
> qualitative conclusion is what matters: **the sharpness distribution
> is heavy-tailed power-law, not Gaussian or gamma**, and the
> *quantitative* tail slope after crop is consistent (within ~10 %) with
> the Gaussian-PSF + diffraction-floor model.

**Bottom line on Q3 of the brief:**

> The sharpness distribution along depth is *NOT* Gaussian and *NOT* a
> gamma. It is a Cauchy-like power-law cusp with exponent ≈ 5, sharply
> peaked at the focused plane, asymmetric in object distance but
> symmetric in *reciprocal* object distance. This is consistent with
> the depth-from-defocus literature (Pentland 1987; Subbarao & Surya
> 1994; Pertuz, Puig & García 2013; Favaro & Soatto tutorial) and
> matches the present video to within 2 % on the tail exponent (α = 4.90,
> fully cropped).

### 6.3 Caveats verified by the literature

1. **The σ⁻⁵ exponent depends on the Gaussian-PSF assumption.** Under
   the *true* geometric pillbox PSF the MTF is a `jinc²` function
   (Nayar & Nakagawa, IEEE TPAMI 16(8) 824–831, 1994) and oscillates
   past its first zero — the qualitative monotonic decrease holds, the
   exact exponent shifts. The 4.90 measured value (fully cropped; 5.36
   was overlay contamination) is consistent with the Gaussian approximation; if the
   operator stops the lens down to F/16 the diffraction floor takes
   over and the exponent will flatten further. See Mannan & Langer
   (IEEE CRV 2016) for the model-error growth with defocus magnitude.

2. **Circular apertures cannot distinguish near from far.** The
   reciprocal-distance symmetry of c(u) shown in
   [`02_coc_vs_distance.png`](./figures/02_coc_vs_distance.png) is
   *also* the famous front/back ambiguity of depth-from-defocus
   (Zhou, Lin & Nayar, IJCV 2011): two crystals at distances
   ``d_f - δ`` and ``d_f + δ`` (in u-space, ``u_f ± Δu``) produce
   identical blur kernels. For sugar slurry imaging this is benign as
   long as the geometry constrains crystals to one side of focus
   (mechanical mounting + sight-glass clear aperture); if not, a
   coded-aperture trick or two-focus measurement would be needed.

3. **The sight-glass shift Δ = t·(1 − 1/n_g) is first-order only.**
   Exact projection through a thick flat port requires a 12th-degree
   polynomial (Agrawal et al., *A Theory of Multi-Layer Flat
   Refractive Geometry*, CVPR 2012; Chadebecq et al., IJCV 2020). The
   paraxial form here is adequate for FOV and pixel-pitch budgeting
   (Δ = 6.39 mm), but a refractive-aware calibration would be needed
   for sub-pixel metric reconstruction — e.g. PMC10781309 reports
   pinhole-model RMSE of 2.28–2.42 mm vs 0.26–0.39 mm with explicit
   refraction. Not a concern at our 1.5–1.9 µm/px (1080p) scale, where
   the ±10 % scale budget dominates, but flag it before publishing.

4. **The 1/3 in-front, 2/3 behind DoF heuristic is wrong** and was
   refuted in the research verification round. The DoF formula in
   §5.1 is correct; the 1/3–2/3 ratio is a hyperfocal-near-infinity
   approximation that fails at close focus distances. Do not quote
   the heuristic.

---

## 7. Pairing with the sharpness map — what the app does

`src/scale_overlay/app.py` builds a Gradio interface that:

1. Loads any video matching this hardware (defaults are the Camera 100 numbers).
2. Lets the user override `f`, N, e, pitch, d_focus.
3. For a chosen frame and a chosen object distance ``d_o``:
   - draws a **scale grid** at the correct mm/px(d_o) on the frame;
   - draws a labelled **ruler** with µm/px and px/mm read-outs;
   - shows the **Laplacian-variance sharpness map** side-by-side so the
     user can see *which pixels are at the focused plane* and *which
     are upstream/downstream*;
   - reports the current circle of confusion, the in-focus depth
     window (CoC ≤ 1 pixel), and the image distance.

Launch with `uv run scale-overlay-app`.

Demo snapshots (same frame, grid centred at three different depths):

| d_o = 54.9 mm (near) | d_o = 55.1 mm (focus) | d_o = 55.3 mm (far) |
|---|---|---|
| ![near](./figures/07_overlay_near.png) | ![focus](./figures/07_overlay_at_focus.png) | ![far](./figures/07_overlay_far.png) |
| 1.460 × 1.907 µm/px | 1.465 × 1.914 µm/px | 1.471 × 1.921 µm/px |

The demos are drawn by `scripts/rerun_paper_numbers.py --fig07`: the frame rows are resampled
×1.306 so that a displayed pixel is 1.465 µm on both axes, and the square grid is then true. The
module `scale_overlay.render_demos` and the app still draw an isotropic grid, and the demo module
uses the PAL-sample scale on the 1080p frame (2.3× too coarse; [`rerun_results.md`](./rerun_results.md),
code issue 1). The scale shift across the ±0.2 mm window is **±0.36 %**, far below the ±10 % scale
budget. For crystal counting at a fixed depth a single scale per axis is good enough.

---

## 8. What the answer to the original four questions is

| Question | Answer |
|---|---|
| 1. mm/px at the focused plane | **1.464 × 1.913 µm/px** on the 1080p clips, **3.92 × 3.59 µm/px** per PAL sample (ESTIMATE, ±≈ 10 % at 95 %, +8.9 % if the CS→C ring is in the tube). The pixel is anisotropic. |
| 2. How does mm/px change with depth? | **Strictly linear in d_o**: Δx(d_o) = p_x · d_o / i_fixed, same for y. Within the in-focus slice (±9.4 µm at F/1.6) the variation is ≈ 0.02 %. |
| 3. Sharpness distribution vs depth? | **Power-law cusp** ``S ∝ c^{-5}``, asymmetric in d_o, symmetric in 1/d_o. NOT Gaussian, NOT gamma. The measured tail exponent on the fully cropped clip is 4.90, within 2 % of 5.0. |
| 4. Can sharpness be paired with mm/px? | **Yes** — the scale-overlay app does exactly this. The sharpness map identifies which pixels are at the focused plane; the geometric model maps those pixels to mm at that depth. |

---

## 9. UNKNOWN / verify before publishing

| Item | How to close | Impact |
|---|---|---|
| Real extension-tube length (plant "≈ 6 cm") and whether a 5 mm CS→C ring is inside it | Caliper and a photo of the body mount | dominant term: ±5 mm → ±8 % in µm/px; ring +8.9 %. Would cut the 95 % budget from ±10 % to ±3 % |
| Camera model (sticker unread) | Photo of the sticker | 752- vs 500-cell CCD: 0.6–0.8 % in µm/px |
| Focus-helicoid travel (1 mm, AI guess) | Caliper the lens body length | ±1 mm → ∓1.6 % in µm/px |
| F-number set on the lens (plant: F/1.6 "if I read it correctly") | Read the iris ring in person | DoF ∝ N |
| Real sight-glass thickness (plant: 20 mm) | Vendor sheet or callipers at maintenance | moves the plane, not the scale |
| Lens-front to outside-glass distance (plant: ≈ 2 cm) | Caliper | Sets the *absolute* d_focus in plant coordinates |
| Inside-of-glass to typical crystal plane | Process diagram or tape measure | Sets which crystals are in focus |
| DVR make, sampling rate (13.5 MHz assumed), codec | Plant: "will be supplied" (Q&A item 10) | ±2 % line-mapping term in x; the 1080p stretch is measured |

---

## 10. Strike annotation (sidecar pipeline)

Every video analysed in this chapter has a paired sidecar JSON that records
operator-observed events on the strike timeline. The sidecar for the
canonical Sereď batch is `datasets/2026-02-04 11-08-51.json`.

The `optics-sidecar` CLI manages these files:

```bash
# Create a sidecar for a new video
uv run optics-sidecar wizard "datasets/<stem>.mp4"

# Validate a sidecar (also runs automatically on git commit)
uv run optics-sidecar check "datasets/<stem>.json"

# See what is still missing
uv run optics-sidecar next "datasets/<stem>.json"
```

Full operator documentation is in
[`../operator_notes/sidecar_guide.md`](../operator_notes/sidecar_guide.md).

Schema source of truth: `src/optics/observations_schema.py` (`Phase` enum,
`ObservationsFile` Pydantic model). Lightweight loader for hot-path code:
`src/optics/observations.py` (`Observations.from_video(path)`).

---

## 10.5 High-pass preprocessing (illumination + glass-rupture removal)

The sight-glass carries a fixed pattern of cracks/ruptures and a slow LED
illumination gradient that contaminate sharpness and detection. The high-pass
filter removes both in one step — `residual = |image − GaussianBlur(image, σ)|`
— with no reference frame or temporal window, so it works on a single image as
well as a video. This is the reusable form of `scripts/rq4_rupture_removal_methods.py`
Method 3 (σ = 25 px default).

```bash
# Image in, <name>_highpass.png out
uv run optics-highpass datasets/frame.png

# Video (apply the sight-glass crop first, custom sigma)
uv run optics-highpass "datasets/2026-02-04 11-08-51.mp4" --crop --sigma 25 -o /tmp/hp.mp4
```

As a function for use in other pipelines (e.g. before crystal detection):

```python
from optics.highpass import highpass
residual = highpass(frame, sigma_px=25.0)   # float32, same shape
```

Source: `src/optics/highpass.py` (`highpass`, `highpass_image`, `highpass_video`).

---

## 11. Reproducing the figures

```bash
# Type-check + tests
uv run pytest tests/test_optics.py

# Every paper number, old vs new (writes nothing); fig 07 at the per-axis scale
uv run --frozen python scripts/rerun_paper_numbers.py
uv run --frozen python scripts/rerun_paper_numbers.py --fig07

# Pixel scale and its budget
uv run python -m optics.scale_chain

# Render all theoretical plots
uv run python -m optics.plots

# Render measured-vs-theory comparison from the plant video
uv run python -m optics.measure

# Launch the interactive overlay
uv run scale-overlay-app
```

Outputs land in `docs/optics/figures/`.

---

## 12. References (with links)

Cross-checked against an adversarially-verified literature sweep
(22 of 25 atomic claims confirmed; 3 refuted and explicitly not used —
see §13). Each entry shows the **type** (primary peer-reviewed, textbook,
secondary, or web cross-check), the **sections it supports**, and a
clickable URL or DOI.

### 12.1 Geometric optics — used in §§ 2, 3, 4

| Source | Type | URL / DOI | Supports |
|---|---|---|---|
| **Hecht, E.** *Optics*, 5th ed. (Pearson, 2017), §5.2 (thin lens) and §5.6 (parallel-plate refraction) | textbook | ISBN 978-0133977226 — [WorldCat](https://www.worldcat.org/title/optics/oclc/953448545) | §2 ``M = i/d_o``; §2.1 ``Δ = t(1 − 1/n)`` |
| **Born, M. & Wolf, E.** *Principles of Optics*, 7th expanded ed. (Cambridge UP, 1999), Ch. 4 and §8.5 | textbook | DOI [10.1017/CBO9781139644181](https://doi.org/10.1017/CBO9781139644181) | §2 Gaussian optics; §5 defocus geometry |
| **Pertuz, S., Puig, D. & García, M. A.** "Analysis of focus measure operators for shape-from-focus." *Pattern Recognition* 46, 1415–1432 (2013) | primary | DOI [10.1016/j.patcog.2012.11.011](https://doi.org/10.1016/j.patcog.2012.11.011) — [PDF](http://isp-utb.github.io/seminario/papers/Pattern_Recognition_Pertuz_2013.pdf) | §4 ``mm/px(d_o) = pitch · d_o / i_fixed``; §6 Gaussian-PSF DfD model |
| Photons-to-Photos, *How Extension Tubes Affect Magnification* | secondary web | [photonstophotos.net](https://photonstophotos.net/GeneralTopics/Close-up/How_Extension_Tubes_Affect_Magnification.htm) | §2 ``m = e/f`` at infinity, ``m_x = m + x/f`` |

### 12.2 Defocus, DoF, and depth-from-defocus — used in §§ 5, 6

| Source | Type | URL / DOI | Supports |
|---|---|---|---|
| **Pentland, A. P.** "A new sense for depth of field." *IEEE TPAMI* 9 (4), 523–531 (1987) | primary | DOI [10.1109/TPAMI.1987.4767940](https://doi.org/10.1109/TPAMI.1987.4767940) | §6 ``σ_h = k · f² · |u − u_f| / (A · u · (u_f − f))`` |
| **Subbarao, M. & Surya, G.** "Depth from defocus: A spatial-domain approach." *IJCV* 13 (3), 271–294 (1994) | primary | DOI [10.1007/BF02028349](https://link.springer.com/article/10.1007/BF02028349) | §6 σ ≈ c/2 mapping |
| **Nayar, S. K. & Nakagawa, Y.** "Shape from focus." *IEEE TPAMI* 16 (8), 824–831 (1994) | primary | DOI [10.1109/34.308479](https://doi.org/10.1109/34.308479) — [Columbia PDF](https://cave.cs.columbia.edu/Statics/publications/pdfs/Nayar_TR89.pdf) | §6 jinc² MTF of pillbox PSF, SML focus measure |
| **Zhou, C., Lin, S. & Nayar, S. K.** "Coded aperture pairs for depth from defocus and defocus deblurring." *IJCV* 93, 53–72 (2011) | primary | DOI [10.1007/s11263-010-0418-7](https://doi.org/10.1007/s11263-010-0418-7) — [PDF](https://cave.cs.columbia.edu/Statics/publications/pdfs/Zhou_IJCV11.pdf) | §6.3.2 front/back ambiguity of circular apertures |
| **Mannan, F. & Langer, M. S.** "Blur calibration for depth from defocus." *Proc. CRV 2016*, 281–288 | primary | DOI [10.1109/CRV.2016.62](https://doi.org/10.1109/CRV.2016.62) — [Academia.edu](https://www.academia.edu/34844453/Blur_Calibration_for_Depth_from_Defocus) | §6.3.1 limits of Gaussian/pillbox PSF |
| **Favaro, P. & Soatto, S.** *3-D Shape Estimation and Image Restoration* (Springer, 2007); Edinburgh CVonline DfD tutorial | textbook + tutorial | [Edinburgh tutorial](https://homepages.inf.ed.ac.uk/rbf/CVonline/LOCAL_COPIES/FAVARO1/dfdtutorial.html) | §6 asymmetry of sharpness vs d_o |
| Wikipedia, *Circle of confusion* | secondary web | [en.wikipedia.org](https://en.wikipedia.org/wiki/Circle_of_confusion) | §5 CoC formula — verbatim cross-check |
| RP Photonics Encyclopedia, *Depth of field* | secondary web | [rp-photonics.com](https://www.rp-photonics.com/depth_of_field.html) | §5.1 DoF formulas, hyperfocal limit |

### 12.3 Fourier optics — used in §§ 5, 6

| Source | Type | URL / DOI | Supports |
|---|---|---|---|
| **Goodman, J. W.** *Introduction to Fourier Optics*, 4th ed. (W. H. Freeman, 2017), Ch. 6 | textbook | ISBN 978-1-319-11916-4 — [Macmillan](https://www.macmillanlearning.com/college/us/product/Introduction-to-Fourier-Optics/p/1319119166) | §6 diffraction OTF and Airy PSF |
| **Smith, W. J.** *Modern Optical Engineering*, 4th ed. (McGraw-Hill, 2008), §11 | textbook | ISBN 978-0071476874 | §6 σ_diff ≈ 0.42–0.45 · λ · N Gaussian fit to Airy |

### 12.4 Sight-glass refraction — used in §2.1 and §6.3.3

| Source | Type | URL / DOI | Supports |
|---|---|---|---|
| **Agrawal, A., Ramalingam, S., Taguchi, Y. & Chari, V.** "A theory of multi-layer flat refractive geometry." *Proc. IEEE CVPR* 2012, 3346–3353 | primary | DOI [10.1109/CVPR.2012.6248073](https://doi.org/10.1109/CVPR.2012.6248073) — [arXiv reformulation](https://arxiv.org/html/2405.18018v1) | §6.3.3 12th-degree exact projection |
| **Chadebecq, F., Vasconcelos, F., Lacher, R., et al.** "Refractive two-view reconstruction for underwater 3D vision." *IJCV* 128, 1101–1117 (2020) | primary | DOI [10.1007/s11263-019-01218-9](https://doi.org/10.1007/s11263-019-01218-9) | §6.3.3 operational consequences |
| Yao et al., underwater calibration comparison (PMC10781309) | primary | [PMC article](https://pmc.ncbi.nlm.nih.gov/articles/PMC10781309/) | §6.3.3 quantitative refraction RMSE |

### 12.5 Crystal-size reference — used in §3.1

| Source | Type | URL / DOI | Supports |
|---|---|---|---|
| **Bubník, Z., Kadlec, P., Urban, D. & Bruhns, M.** *Sugar Technologists Manual*, 9th ed. (Bartens, 1995) | textbook | ISBN 978-3870403324 — [Bartens](https://www.bartens.com/en/books/sugar-technology) | §3.1 typical massecuite crystal size 0.5–1.0 mm |

### 12.6 Specific physical laws referenced

| Law | Formula | First cite | Used in |
|---|---|---|---|
| Gauss thin-lens equation | ``1/f = 1/d_o + 1/i`` | Gauss 1841; Hecht §5.2 | §2 |
| Lateral magnification | ``M = i / d_o`` | Hecht §5.2 | §§ 2, 3, 4 |
| Snell's law (paraxial flat plate) | ``Δ = t · (1 − 1/n)`` | Snell 1621; Hecht §5.6 | §2.1 |
| Circle of confusion (similar triangles) | ``c = A · f · |d_o − d_focus| / (d_o (d_focus − f))`` | Jacobson, *Manual of Photography*; [Wikipedia derivation](https://en.wikipedia.org/wiki/Circle_of_confusion) | §5 |
| Convolution theorem (PSF → OTF) | ``H(u) = FT[PSF(x)]`` | Plancherel 1910; Goodman §2.1 | §6 |
| Airy diffraction pattern | ``I(θ) ∝ [2 J₁(x)/x]²`` | Airy 1835; Born & Wolf §8.5; Goodman §6.4 | §6 |
| Pentland DfD relation | ``σ_h = k f² |u − u_f| / (A u (u_f − f))`` | Pentland 1987 | §6 |

---

## 13. Cross-check audit (every numerical claim, where verified)

Walking the document claim-by-claim. ``D-R`` = deep-research vote
(e.g., 3-0 = three confirm, zero refute); ``code`` = unit-tested in
`tests/test_optics.py`; ``video`` = measured on
`datasets/2026-02-05 10-36-32.mp4`.

| § | Claim | Source(s) | Verification |
|---|---|---|---|
| 1 | ~~Hanwha HCB-6000 1/2.8" sensor, 2.9 µm pitch~~ → analog B/W PAL CCD "ADEMCO VIDEO", PAL sample 6.831 × 6.250 µm | photos (PHOTO) + candidate datasheet (ESTIMATE) | `optics.scale_chain` |
| 1 | Fujinon HF35HA-1B, f=35 mm, F/1.6–22, MOD 0.25 m | Fujinon datasheet | FACT |
| 1 | DIN 8902 sight-glass, 8-bolt flange | operator photo `lens/20260205_122524.jpg` | FACT |
| 1 | Sight-glass thickness 20 mm, n_g ≈ 1.47 | plant Q&A 2026-08-12 + borosilicate | PLANT / ASSUMED |
| 2 | ``M = f / (d_o − f)`` | Hecht §5.2; thin-lens identity | code (`test_thin_lens_round_trip_finite_distance`), D-R 3-0 |
| 2 | ``m = e/f`` at infinity focus; ``m_x = m + x/f`` | Photons-to-Photos, derived from Hecht §5.2 | D-R 3-0; verbatim quote retrieved 2026-06-13 |
| 2.1 | ``Δ = t(1 − 1/n_g) = 6.39 mm`` | Hecht §5.6 paraxial | code (`test_sight_glass_shift_independent_of_distance`), D-R 3-0 |
| 2.1 | Exact flat-port projection is 12th-degree polynomial | Agrawal CVPR 2012 | D-R 3-0 |
| 3 | µm/px at focus = 1.464 × 1.913 (1080p), 3.919 × 3.586 (PAL) at e ≈ 60 mm, d_focus = 55.1 mm | derived from §1–2 | `optics.scale_chain`; ESTIMATE |
| 3.1 | First-decorrelation pixel offset = 42.5 px (median) | autocorrelation, this video | UNSOURCED (no script in the repo) |
| 3.1 | Massecuite crystal size 0.5–1.0 mm | Bubník et al. *Sugar Technologists Manual* | FACT (textbook) |
| 4 | mm/px linear in d_o: ``Δx(d_o) = pitch · d_o / i_fixed`` | Hecht §5.2 + Pertuz 2013 | code (`test_mm_per_pixel_is_linear_in_d_o`), D-R 3-0 |
| 5 | ``c(d_o) = f²/(N(d_focus−f)) · |d_o − d_focus| / d_o`` | Wikipedia CoC verbatim, derived from Hecht §5.2 | code (`test_coc_far_limit_matches_hyperfocal`, `_zero_at_focus`); D-R 3-0; verbatim quote retrieved 2026-06-13 |
| 5 | CoC asymmetric in d_o, symmetric in 1/d_o | Pertuz 2013 (eq. 5); Mannan & Langer 2016 | code (`test_coc_is_asymmetric_in_object_space`, `test_coc_is_symmetric_in_reciprocal_distance`), D-R 3-0 |
| 5 | ``c_∞ = f A / (d_focus − f) = f² / (N (d_focus − f))`` | Wikipedia + Hecht | code (`test_coc_far_limit_matches_hyperfocal`), D-R 3-0 |
| 5.1 | DoF at F/1.6, focus 55.1 mm: ≈ 0.019 mm (1 PAL sample), ≈ 0.038 mm (2 samples) | numerical, from §5 | `scripts/rerun_paper_numbers.py` |
| 5.1 | 1/3 front, 2/3 behind heuristic | none — NOT cited | **D-R refuted 0-3** (claim killed) |
| 6.1 | ``S ∝ (σ² + σ_floor²)^(−5/2) ∝ c^{−5}`` (Gaussian-PSF, Laplacian-variance) | Pertuz 2013 + analytic integral | code (`test_sharpness_gaussian_is_monotone_in_coc`), D-R 3-0 (medium confidence — depends on Gaussian-PSF assumption) |
| 6.1 | σ ≈ c/2 (Gaussian-fit defocus) | Pentland 1987; Subbarao & Surya 1994; Pertuz 2013 | D-R 3-0 |
| 6.1 | σ_diff ≈ 0.42–0.45 · λ · N | Goodman §6.4 + Smith *Modern Optical Engineering* §11 | numeric in `psf.py`; uncertainty bracketed in code docstring |
| 6.2 | Measured tail exponent α = 4.90 fully cropped (4.57 overlay-only, 5.36 contaminated) | Laplacian-variance histogram fit | video MEASURED, code reproducible (`python -m optics.measure`) |
| 6.3.1 | Pillbox MTF = jinc²; geometric MTF oscillates | Nayar & Nakagawa 1994 | D-R 3-0 |
| 6.3.2 | Front/back ambiguity for circular apertures | Zhou, Lin & Nayar 2011 | D-R 3-0 |
| 6.3.3 | Pinhole-model refraction RMSE 2.28–2.42 mm vs 0.26–0.39 mm with explicit model | PMC10781309 | D-R 3-0 |
| 7 | mm/px shifts by ±0.36 % across ±0.2 mm | direct numerical | reproducible: 0.2 / 55.1 |

**Refuted in verification (NOT used in this document):**

1. "DoF is asymmetric regardless of lens settings." Refuted 1-2 (Stanford CS178 applet).
2. "DoF extends 1/3 in front and 2/3 behind." Refuted 0-3 (Living Optics blog).
3. "Defocus kernel sign explicitly encodes front/back side." Refuted 1-2 (Zhou IJCV 2011 misreading).

If you find any other claim in this document that I have not tagged or
cross-checked, please flag it — it is a bug, not a feature.

---

## 14. Hallucination audit (assistant self-check)

Specific numerical claims I have made in §§ 1–8 and the trace I followed
to verify they are not invented. Rows marked *superseded* trace the
2026-06 setup (e = 45 mm, 2.8 µm pitch, d_focus 165 mm) and are kept
only as the audit trail of that revision; current values are in §1 and §12.

| Number | Where | Trace |
|---:|---|---|
| *superseded* — **2.9 µm/px** sensor pitch | §1 | an AI inference (Sony IMX307/IMX327) from the Hanwha price quote; the installed camera is an analog PAL CCD (2026-11-03) |
| *superseded* — **5.57 × 3.13 mm** sensor active | §1 | 1920 × 1080 × 2.9 µm |
| **6.831 × 6.250 µm** per PAL sample | §1 | CCD cell × 14.1875 / 13.5 MHz; `optics.scale_chain` (ESTIMATE) |
| **6.39 mm** glass shift | §2.1 | 20 · (1 − 1/1.47) = 6.395 mm — Hecht §5.6 formula, verified in `test_sight_glass_shift_independent_of_distance` |
| *superseded* — **157.5 mm** d_focus at infinity ring | §2 | 35 · 45 / (45 − 35) = 157.5 — thin-lens equation |
| *superseded* — **165 mm** chosen d_focus | §2 | ESTIMATE within 157.5–200 mm bracket from infinity ring + 4 m ring |
| *superseded* — **10.40 µm/px** at focus | §3 | 2.8 · 165 / 44.42 ≈ 10.40 — direct from `mm_per_pixel_at` |
| *superseded* — **42.5 px** first-decorrelation | §3.1 | UNSOURCED: the Bash block it cites is not in this document or the repo |
| *superseded* — **96.2 px/mm** at focus | §3 | 1000 / 10.40 = 96.15 — reciprocal of µm/px |
| *superseded* — **2355.8 µm** ``c_∞`` at F/4 | §5 | (35/4) · 35 / (165 − 35) = 2.356 mm — `circle_of_confusion(lens, 165, 1e9)` |
| *superseded* — **0.26 mm** DoF at F/4, 1-px | §5.1 | numerical from `circle_of_confusion`; reproducible |
| *superseded* — **4.57** measured α (cropped) | §6.2 | `polyfit` over the 50–95 % quantile histogram on overlay-cropped frames; reproducible by `uv run python -m optics.measure` |
| **5.00** theoretical α | §6.2 | analytic integral of u⁴ · exp(−4π²σ²u²) du in §6.1 |
| *superseded* — **−8.6 %** measured vs theory (cropped) | §6.2 | (4.57 − 5.00) / 5.00 |

Every other number in the document is either:

- a direct call into the optics module (reproducible by re-running the code), or
- a per-figure caption derived in the corresponding plot function in
  `src/optics/plots.py` and visible in the rendered PNG.

---

*Status as of 2026-06-13 (Friday evening): all theoretical claims
cross-checked against verified primary literature; 22 of 25 atomic
deep-research claims confirmed (3 refuted and excluded); 10 unit
tests pass (17 as of 2026-11-03); measured power-law exponent on the plant video matches
theory within 7 % (2 % after the full crop, 2026-11-03); all references have clickable URLs / DOIs; every
numerical claim in §§ 1–8 has a verification trace in §13. Open items
in §9 (extension-tube length, F-number, glass thickness) need on-site
measurement before publishing — they are uncertainty bounds on the
absolute scale, not on the structural results.*

---

## 15. Measurement-error budget (DERIVED)

Generated by ``uv run python -m optics.error_budget`` from ``configs/camera_100.toml``
(2026-11-03, analog-PAL chain). The object-plane scale is ``µm/px = p·f/(e + x)`` per axis:
the glass and the air gap do not enter it. The plant's "≈ 6 cm" tube dominates. The
per-recording 95 % intervals (PAL and 1080p, x and y) are in [`scale_chain.md`](./scale_chain.md).

## Inputs (1 σ)

| Symbol | Value | σ | Source |
|---|---:|---:|---|
| f | 35 | ±0.7 | lens engraving 35 mm (PHOTO); ±2 % CCTV tolerance (ASSUMED) |
| e | 60 | ±2.88675 | Q&A 8(A) "≈ 6 cm" (PLANT), uniform ±5 mm |
| x | 1 | ±0.57735 | focus travel 1 mm, AI guess (ESTIMATE), uniform 0–2 mm |
| px | 6.83102 | ±0.0788778 | µm per PAL sample, CCD cell × clock / 13.5 MHz (ESTIMATE), line mapping uniform ±2 % (optics.scale_chain) |
| py | 6.25 | ±0.0288675 | µm per PAL line = CCD row (ESTIMATE), candidates 6.25–6.30 |
| t | 20 | ±0.5 | Q&A 8(C) "20 mm" (PLANT) |
| a | 20 | ±2.88675 | Q&A 8(B) "≈ 2 cm" (PLANT), uniform ±5 mm |
| n | 1.47 | ±0.03 | borosilicate 1.47 (ASSUMED); soda-lime would be 1.52 |

## Propagated 1 σ per derived quantity (linear; MC check in last column)

| Quantity | Value | σ from f | σ from e | σ from x | σ from px | σ from py | σ from t | σ from a | σ from n | total σ (lin) | total σ (MC) | rel. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| um_per_px_x_PAL | 3.919 | 0.078 | 0.185 | 0.037 | 0.045 | 0.000 | 0.000 | 0.000 | 0.000 | **0.210** | 0.211 | 5.4 % |
| um_per_px_y_PAL | 3.586 | 0.072 | 0.170 | 0.034 | 0.000 | 0.017 | 0.000 | 0.000 | 0.000 | **0.188** | 0.190 | 5.2 % |
| d_focus_mm | 55.082 | 1.503 | 0.950 | 0.190 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | **1.789** | 1.800 | 3.2 % |
| H_to_inner_face_mm | 61.477 | 1.503 | 0.950 | 0.190 | 0.000 | 0.000 | 0.160 | 0.000 | 0.278 | **1.817** | 1.830 | 3.0 % |
| H_behind_front_mm | 21.477 | 1.503 | 0.950 | 0.190 | 0.000 | 0.000 | 0.340 | 2.887 | 0.278 | **3.424** | 3.435 | 15.9 % |
| H2_behind_front_mm | 12.026 | 0.700 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | **0.700** | 0.702 | 5.8 % |

Not in the table (discrete, not Gaussian): the C-mount flange depth. If the plant's ≈ 60 mm already includes the 5 mm CS→C adapter ring, e is 55 mm: µm/px +9 %, d_focus +2.0 mm, H′ shifts −5 mm. Per-recording µm/px with 95 % intervals (PAL and 1080p, x and y): uv run python -m optics.scale_chain.
