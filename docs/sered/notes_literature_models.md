# Sereď sugar plant expert: notes C (literature, gPROMS, Yokogawa)

BASE = `/Users/mw/Library/CloudStorage/GoogleDrive-marek.wadinger@stuba.sk/My Drive/sugar_plant`.
File tags used below: `[Bennár]` = papers/Optimalizácia zvyšovania výťažnosti cukru pri získavaní sacharózy z cukrovej repy.pdf;
`[Hernández]` = papers/mths_hernandez.Report 02_10.pdf; `[gPJ]` = gproms/Sugar_plant_Crystallization_v7.gPJ;
`[Georgieva]` = papers/Growth_based/Knowledge_based_hybrid_modelling_Georgeiva_et_al.pdf; other tags are the file stems.
Text was extracted with pypdf. Some symbols were lost, mainly µ, which sometimes came out as "m". Those places are flagged.
"(interp.)" marks my own inference rather than something stated in the source.

---

## 1. Literature table

| Citation (file) | Topic | Key numbers | Relevance to a vision CSD monitor on seed pan ZRA |
|---|---|---|---|
| Bennár M. (2010), PhD thesis, Slovak University of Agriculture in Nitra (SPU), FBP; supervisor T. Bojňanská. `[Bennár]` | Yield optimisation **measured at Slovenské cukrovary s.r.o. Sereď**, campaigns 2005–2009. Topics: white-sugar sieve PSD vs micro-seed ("mikroočko") volume and seed-massecuite draw; C-massecuite (zadinová) cooling maturation; extraction; biogas. | Optimum: 1100 cm³ mikroočko + 20 % seed-massecuite draw → MA 0.76 mm, CV 38 % (Rens method). A-sugar MA 0.76–0.95 mm (Rens). Seeding with micro-seed at S = 1.05–1.15. See §5. | **The only source that is directly about Sereď.** Gives ground truth on the ZRA → A-pan seeding chain and the final product size. Seed count, not seed mass, sets final MA. |
| Lima F.A.R.D. (2026), PhD thesis, NTNU, *ML-Enhanced Process Systems Engineering…* `[Fernando_Thesis_NTNU]` | UDE hybrid models, symbolic regression, symbolic-regression controller (SRC) on PLCs, multi-agent LLM workflow "Dyad". Case studies are **K₂SO₄** and paracetamol, not sucrose. | K₂SO₄ size-dependent growth constant γ = 2.390×10⁻³ µm⁻¹; k_v = 1.349 (Ch. 2). Moments μ0–μ3 came from image analysis (Sympatec microscope analyser). | **No Sereď content.** Useful as a method: image-derived moments feed a hybrid PBM. R. Paulen (STU) sat on the examination committee (Preface), which is the likely link to this project (interp.). |
| Hernández R. (2011), MSc report, TU Dortmund, *Optimal Allocation of Shared Resources in an Integrated Sugar Production Plant*. Supervisors Simora, Wegerhoff, **R. Paulen**. `[Hernández]` | Re-implements the HYCON2 sugar-factory benchmark (evaporation + A-crystallisation), originally EcosimPro from Univ. of Valladolid, in gPROMS. Dynamic optimisation of steam use. | Pan: Vmax 55 m³, D 4.43 m, calandria 360 m². Seeding at Brix 78.2 %, 10–15 kg seed, ≥40 s. Tightening ends at 14 cSt. Growth law R_g = k_g(S−1)^g. See §2–3. | **This is the documentation of the gPROMS model.** It has no PBM and no crystal size. A camera could supply the missing size/count state (interp.). |
| Damour C., Benne M., Grondin-Perez B., Chabriat J.-P. (2010), *Control Eng. Practice* 18, 839–844. `[Damour et al. (2010)]` | Soft sensor for crystal mass m_c, dissolved-sucrose concentration and mother-liquor purity in a **last-stage (C) cane** pan (Bois Rouge, Réunion). No PBM. | Metastable zone 1.00 < σ < 1.35. J_c = c_c(ρ_f F_f − ṁ_vap) + α_c. Fitted α_Q = 1.8177, α_vap = 1.6455, α_c = 0.9217 kg/s. Data sampled every 30 s. m_c rises to ≈2.5×10⁴ kg in ≈90 min. | Shows the 9-ODE moment model (Eqs. 1–9) and a mass-only reduction. Vision could add μ0/μ3 that this soft sensor lacks (interp.). |
| Damour C. et al. (2011), *J. Process Control* 21, 46–54. `[damour et al. (2011)]` | Multivariable linearising control of (m_c, concentration) with an extended Luenberger observer, on the same Bois Rouge last-stage model. | Liquor volumes per slope 26–46 m³ (Table). Conductivity κ is the industrial proxy for σ. | Control-side context. The same no-CSD model family. |
| Morales H., di Sciascio F., Aguirre-Zapata E., Amicarelli A.N. (2023), *J. Process Control* 129, 103065. doi:10.1016/j.jprocont.2023.103065 (file named "2022") `[Morales et al.(2022)]` | UKF-based supersaturation soft sensor for the **last (C) stage**, Urbano Noris factory, Cuba. | Seed added at S ≈ 1.20. Uses a Wiklund–Vavrinecz saturation equation. Notes that K-Patents SeedMaster is the only commercial online-σ instrument. Converges within <3 min. | σ estimation is complementary to imaging. A camera gives growth (dL/dt), which constrains σ through G(σ) (interp.). |
| Georgieva P., Meireles M.J., Feyo de Azevedo S. (2003), *Chem. Eng. Sci.* 58, 3699–3713 `[Georgieva]` | Knowledge-based hybrid model (mechanistic balances + NN for G, B0, agglomeration) of an **industrial fed-batch evaporative pan** in a cane-sugar refinery (Portugal). | Pan 35 m³ working volume, 194 m² heat-transfer area, 90 min batch. Seed 0.16 kg, seed MA 10–12 "m" (µm lost in extraction), seed CV 80 %. Seed at S = 1.15. Target MA 0.5–0.6 mm, CV 28–32 %. Kinetic constants Kg = 265, Kn = 0.721, Kag = 1.36×10⁻⁵. | **The best quantitative template for a seeded white-sugar pan.** Seed size ≈ 10 µm matches our 6.8 µm Dv50 slurry. Final-CSD table gives measured MA 0.48–0.68 mm. |
| Meng Y., Yu S., Zhang J., Qin J., et al. (2019), *J. Food Eng.* 257, 44–55. doi:10.1016/j.jfoodeng.2019.03.026 `[Meng et al.(2019)_hybrid]` | Hybrid data-driven (σ, purity) + moment model for **industrial cane** batch pans (Guangxi). Reuses the Georgieva kinetics. | Pan to 48 m³, 200–240 min. Brix 81→93. Target MA 0.8–0.9 mm. Massecuite at 58–68 °C. σ kept in 1 < S < 1.3. Data every 1 min. | Same group as Zhang 2020 (vision). Gives typical pan trajectories. |
| Quintana-Hernández P., Bolaños-Reynoso E., Miranda-Castro B., Salcedo-Estrada L. (2004), *AIChE J.* 50(7), 1407–1417. doi:10.1002/aic.10133 `[Quintana Hernandez et al.]` | Lab **cooling** batch crystallisation of cane sugar, 2.23 L. PBM with power-law B0, G and an agitation term. 11 parameters fitted. CSD measured online with a Malvern MasterSizer S. | G = K_g S^g N^q. g = 1.0–1.5 (mean 1.3). Initial size L0 = 15.1 µm. Final D(4,3) 382–571 µm (SD 156–201 µm) after 180 min. ρ_c = 1.588 g/cm³, k_v = π/6. Fit error 7.7 %. | A laser-diffraction reference CSD, like our Mastersizer. Shows that seed ≈15 µm grows to ≈0.5 mm in 3 h. |
| Bakir T., Othman S., Puel F., Hammouri H. (2005/06), 44th IEEE CDC. doi:10.1109/CDC.2005.1583161 `[Bakir et al]` | Continuous–discrete high-gain observer that reconstructs the full CSD from a finite-difference PBM and sparse measurements (e.g. FBRM counts). Generic solute, simulation only. | Csat = A exp(−ΔHc/RT). Primary + secondary nucleation. Outputs moments, L = μ1/μ0 and CV. | **Directly applicable architecture:** feed periodic camera CSD snapshots (discrete outputs) into a PBM observer (interp.). |
| Leeming R., Mahmud T., Roberts K.J., et al. (2023), *Ind. Eng. Chem. Res.* 62, 11067–11081. doi:10.1021/acs.iecr.3c00371 `[Leeming et al.]` | Digital twin: 1D PBM in **gPROMS FormulatedProducts** + PharmaMV MPC of supersaturation. Hexamine–ethanol, 500 mL, ATR-FTIR. | Relative σ setpoints 0.012–0.036. G = 2.6×10⁻² ΔC^1.95 m/s. | Shows how a gPROMS PBM is coupled to MPC. Not sucrose. |
| Zhang Y., Zhao S., et al. (2024), Li₂CO₃ multi-stage cascade reactive-heating MSMPR crystallisation `[Zhang et al.(2024)]` | Decoupling nucleation and growth. Process model + dynamic programming for yield. | Not sucrose. | Tangential: the idea of decoupling seed generation (ZRA) from growth (A/C pans) (interp.). |
| Zhang J., Meng Y., Wu J., Qin J., et al. (2020), *J. Food Eng.* 280, 109965. doi:10.1016/j.jfoodeng.2020.109965 `[Zhang et al._Image classification]` | **Vision on industrial cane-sugar pans:** InceptionResNetV2 classifies the 5 operator-defined pan stages from microscope images of samples taken with a rod. | IDS UI-5490S camera, 3840×2748, **1.67 µm sensor pixel**, 6 fps, 25 mm lens, FOV 8.8×6.6 mm. 1000 images per class, Mingyang factory, 2017/18. Accuracy 0.901 (0.83–0.99 per class). | Closest prior art to Camera 100. It is offline sampling and stage *classification*, not sizing. |
| Zong S., Zhou G., Li M., Wang X. (2023), *Particuology* 74, 173–183. doi:10.1016/j.partic.2022.07.002 `[Image_deep_learn_cont_crys]` | Mask R-CNN instance segmentation of in-situ images from a **10 m³ industrial continuous crystalliser** at high solids. Pharmavision 2D probe. | Probe 6.5 m deep. Imaging cavity 1 mm, depth of focus ≈0.4 mm, 1 frame / 5 s. 2000×1536 px. 70,908 crystals labelled (≈10 person-days). Precision 86.8 %, recall 90.3 %. Pixel size printed as "2 mm", almost certainly 2 µm (interp.). | **Most relevant segmentation reference:** dense, overlapping crystals, and the effect of training-set size (1000 vs 100 images). |
| Chen S., Liu T., Xu D., Huo Y., Yang Y. (2019), Proc. 38th Chinese Control Conf., 7933ff. `[Image_based_Measurement_of_Population_Growth_Rate…]` | Mask R-CNN + ellipse fitting + KDE-smoothed CSD. A population growth-rate index from SVRE (symmetric KL divergence) and CSD dispersion. β-L-glutamic acid, cooling. | ≈3 fps on an RTX 2080Ti. Recommends >2000 labelled crystals. | A ready recipe for turning per-frame CSDs into a real-time growth-rate signal for ZRA (interp.). |
| Zhang K., Wang W., et al. (2022), *Measurement* 189, 110589 `[CNN_regression_ash]` | CNN *regression* of coal ash content from microscope images. Label-distribution smoothing; synthetic data for small, imbalanced sets. | 0.31 % error on 1145 test images. | A method for direct image → scalar regression (e.g. image → D50) when labels are scarce (interp.). |
| He K., Zhang X., Ren S., Sun J. (2016), *Deep Residual Learning*, CVPR `[ResNet]` | ResNet backbone. | ImageNet 3.57 % top-5 (ensemble). | Generic backbone reference only. |

---

## 2. Kinetics and key equations (with source)

**Sucrose solubility in pure water (Vavrinecz)**, w_s in % dry substance, t in °C, valid −13…100 °C `[Bennár p.40]` `[Hernández Eq. 3.43]` `[gPJ K1–K5]`:
`w_s = 64.447 + 0.08222 t + 1.6169e-3 t² − 1.558e-6 t³ − 4.63e-8 t⁴`, and `H0 = w_s/(100−w_s)` (g sucrose/g water).
Note: `[Hernández]` prints the third coefficient as 1.1669e-3. `[Bennár]` and `[gPJ]` both use 1.6169e-3, so the Hernández value is a typo (interp.).

**Impure solution, saturation coefficient** `[Hernández Eq. 3.40–3.41]` `[gPJ]`:
`C_eq = H0(T) · y_sat` with `y_sat = A·Rn + B + (1−B)·exp(C·Rn)` and Rn = M_imp/M_water.
Values: A = 0.25, B = 0.764, C = −1.84 (`[gPJ]` Asx/Bs/Cs; `[Hernández]` Table C.7).
`[Bennár p.40]` gives the same idea as H_n = H0·K_n, where K_n (koeficient nasýtenia) rises as purity falls.

**Supersaturation:**
- Coefficient form: `S = (M_sac/M_water) / (y_sat·H0)` `[gPJ]`. `[Bennár p.41]` writes K_p = H/H_n.
- Relative form: `σ = S − 1` `[Hernández Eq. 3.39]`.
- Metastable / operating limits by source:

| Source | Range |
|---|---|
| `[Georgieva]` | 1 < S < 1.2 |
| `[Meng]` | 1 < S < 1.3 |
| `[Damour 2010]` | 1.00 < σ < 1.35 |
| `[gPJ]` | path constraint S ≤ 1.32 (`Sviol`) |
| `[Bennár p.90]` | growth "stops" at S = 1.2 in C-cooling |

- Seeding point by source:

| Source | Seeding at |
|---|---|
| `[Georgieva]` | S = 1.15 |
| `[Morales]` | S ≈ 1.20 |
| `[Bennár p.43]` | 1.05–1.15 with micro-seed |
| `[Bennár p.43]` shock seeding | 1.2–1.4 |
| `[Bennár p.43]` waiting method | up to 1.5 (not recommended) |

**Growth-rate laws:**
- `[Georgieva Eq. 24]`, reused by `[Meng Eq. 3-1]`:
  `G = Kg·exp[−57000/(R(T+273))]·(S−1)·exp[−13.863(1−P_sol)]·(1 + 2·v/V_m)` in m/s, with Kg = 265.
  The last factor depends on volume fraction and was partly garbled in extraction. Treat its exact form as uncertain.
  Constants: R = 8.314, ρ_c = 1580 kg/m³, k_v = 0.65 (Table 8).
  - Worked example (interp.), S = 1.15, last factor ≈ 1:

    | T, P_sol | G |
    |---|---|
    | 70 °C, P_sol = 0.95 | ≈ 4.2×10⁻⁸ m/s ≈ **2.5 µm/min ≈ 150 µm/h** |
    | 70 °C, P_sol = 0.90 | ≈ 75 µm/h |
    | 65 °C, P_sol = 0.95 | ≈ 111 µm/h |
    | 75 °C, P_sol = 0.95 | ≈ 199 µm/h |

  - At 150 µm/h, ≈ 1–3 h of growth takes a ~10 µm seed to ~0.15–0.45 mm (interp.). That fits the observed ZRA discharge of ~200–350 µm (MEMORY note) and A-sugar MA ≈ 0.5–1 mm after a second growth stage (interp.).
- Nucleation `[Georgieva Eq. 25]`: `B0 = Kn·2.894e12·G^0.51·(μ̃1/(k_v V_m))^0.53·V_m`, Kn = 0.721.
- Agglomeration kernel `[Georgieva Eq. 26]`: `β = Kag·G·(μ̃1/V_m²)`, Kag = 1.36e-5.
- Lab cooling `[Quintana]`: `B0 = Kb S^b Mc^j N^p`, `G = Kg S^g N^q`, `α(L) = Ka S^a Mc^k N^r`. g = 1.0–1.5 (mean 1.3), with Kg and Kb per run in Table 3. Heat of crystallisation ΔHc = −12.2115 − 0.7937 T.
- Reduced HYCON2 law `[Hernández Eq. 3.44]` `[gPJ]`: `R_g = k_dt·|S − 1|^α`, with k_dt = 0.1 (marked "######Check value" in `[gPJ]`) and α = 2.7.
  `[Hernández]` says g ≈ 1 means mass-transfer control and g > 1 means surface-integration control.

**Moment model for 1st-stage (high-purity) pans** `[Damour 2010 Eqs. 1–9]`:
- Mass balances for m_w, m_i, m_s and m_c (dm_c/dt = J_c).
- Energy balance on T_mg.
- `dμ0/dt = B0 + ½β0μ0²`
- `dμ1/dt = Gv·μ0`
- `dμ2/dt = 2Gv·μ1 + β0μ0²`
- `dμ3/dt = 3Gv·μ2 + 3β0μ1μ2`
- This is in volume coordinates. Damour et al. call it the "widely used momentum model … dedicated to 1st stage processes (Wright & White 1974)". **This is the model class appropriate for ZRA/A pans** (interp.).

**Crystallisation mass rate without a PBM** `[gPJ Tachas]` (garbled as Eq. 3.45 in `[Hernández]`):
`W_cris = (stage3+stage4)·[R_g·k_sf·N^(1/3)·M_cris^(2/3)/(ρ_s·K_v)^(2/3) + W_cris,in]`, with k_sf = 5.02, K_v = 0.75, N = 1e6.
- Interpretation (interp.): this assumes N identical crystals of size L, with M = ρK_vNL³ and area = k_sf·N·L². Then R_g is a mass flux (kg m⁻² s⁻¹).
- With N = 1e6 the implied L is unphysical: L ≈ 32 mm at M_cris = 40 t. So N is a lumped tuning constant, not a crystal count.
- For comparison, 100 kg of 6.8 µm seed is ≈2.7×10¹⁴ crystals (my calculation with ρ = 1588 kg/m³, k_v = 0.75).
- **A camera-derived crystal count or mean size would turn N and L into measured states** (interp.).

**Other correlations in `[gPJ]`:**
- Crystal density: ρ_c = 1587.9/(1 + 1.07e-4 (T − 15)) kg/m³.
- Mother-liquor viscosity (Brix/purity/T): `log10 μ = 22.46·d − 0.114 + c(1.1 + 43.1·a·d^1.25)`, with a crystal-content correction k_visc. Used as the end-of-tightening trigger.
- Evaporation-rate empirical coefficient: Kq = 0.7, kevap_est = 15.92, …

---

## 3. gPROMS model (`[gPJ]`)

- **Format:** plain XML. gPROMS ModelBuilder project, gMB_Version 7.0.9. Readable; model bodies sit in CDATA blocks.
  - Created by **HERNANDEZR**, 2013-10-20.
  - Last modified by **paulen**, 2022-08-11.
  - Variable and unit names are Spanish (Tacha = vacuum pan, Malaxador = mixer/strike receiver, Jarabe = syrup, Pureza = purity, Masacocida = massecuite). This shows its origin in the Univ. of Valladolid EcosimPro HYCON2 benchmark `[Hernández §4.1]`.
- **Which pan:** **not Sereď-specific, and not ZRA.** Top unit `CazRed` contains `TachasPrimera` (TachasPrimeraClase, "first-class / A-product pans"). Its parts:
  - 3 identical pans `TachasI1..3` (TachasR → Tachas)
  - storage tank `DepLS` (D 4 m, Vmax 170 m³)
  - splitter
  - 3 malaxadors (sinks)
  - steam source III (2.1 bar)
  - sequence generator `GenSecuencia` (cycle "Tiempo" = 23583 s ≈ 6.6 h between loads)
  - syrup feed `Jarabe`: 76 °Bx, purity 95 %, 81.5 °C, 14.46 kg/s
  - Three A-pans match the Sereď count (3 pans for A-product, `[Bennár p.58]`). That may be coincidence: the benchmark plant also has 3 A-pans (interp.).
- **States per pan (`Tachas`):** M (massecuite mass), M_sac, M_imp, M_cris, H (enthalpy), M_vapor, T_cham, controller integrators, timers, and Sviol (constraint integral). Algebraic: M_water, V, level, P_s, P_cham (ideal gas), P_eq, W_evap, S, viscosity, and others.
  **There is no crystal size, no number density and no moments** (confirmed by reading the full variable list).
- **Sequence (SELECTOR):** CHARGE → CONCENTRATION → SEEDING → GROWING → TIGHTENING → DISCHARGE → WAITING.

  | Transition | Trigger |
  |---|---|
  | CHARGE → CONCENTRATION | level > 55 % |
  | CONCENTRATION → SEEDING | Brix > BrixT(1) = 78.2 |
  | SEEDING → GROWING | TimeSeed > 40 s and seed fed |
  | GROWING → TIGHTENING | level > 98 % |
  | TIGHTENING → DISCHARGE | viscosity > ViscTight = 14 |

  - In GROWING the Brix setpoint follows the Brix–level curve BrixT = [78.2, 78, 82.15, 84.85, 87.55, 90.05] at LevelT = [50.81, 66.34, 74.25, 82.17, 90.08, 98] %.
  - The `[Hernández]` table instead lists a flat 78 %, so v7 has a modified curve (interp.).
- **Pan parameters (each pan):**

  | Group | Values |
  |---|---|
  | Geometry | Vmax 55 m³, D 4.43 m, Vcham 30 m³, h_tubes 1.15 m, A_cal 360 m², V_cal 45 m³ |
  | Heat transfer | Usen 1500, Uevap_mx 2000, Ulimp 10 |
  | Saturation | A/B/C = 0.25 / 0.764 / −1.84 |
  | Kinetics | k_dt 0.1, α 2.7, k_sf 5.02, K_v 0.75, N 1e6 |
  | Seed | **WcrisInP = 2.5 kg/s for ≥40 s ⇒ ≈100 kg seed per strike** (my calculation). `[Hernández]` Table C.8 has 10 kg/s, while the text says "10–15 kg" |
  | Pressure setpoints | chamber 0.2–0.22 bar; calandria 1.2 → 1.45–1.6 bar; growing-ramp time 5700 s |

  The seed is a **mass flow with no seed size or count**.
- **Process `SugarProcess`:** simulates 94,332 s. DASOLV solver, tolerances 1e-6 / 1e-8.
- **Optimisation `Opt1_8b_SS`:** dynamic, horizon 48,200 s, 11 intervals. Controls are evaporator Brix setpoint (68–72) and per-pan pressure factor Pfactor (0.8–1.2). It minimises `Caz.Evap.Objective_Function`.
  The model as stored has no `Evap` unit, so this entity looks stale or inherited from a fuller version (interp.).
- **Bottom line:** a plant-wide steam/scheduling model of an A-pan station with a lumped mass-growth law. It cannot predict CSD. To serve the vision monitor it would need a moment/PBM extension (μ0–μ3 as in `[Damour 2010]` or `[Georgieva]`), seeded from the measured slurry Dv50 and count (interp.).

---

## 4. Yokogawa CI Server

`yokogawa/ci_server/ciserver.pdf` is a 2-page documentation map. Its Japanese text did not extract properly.
`EN/` has 39 English user manuals (`IM 36K…-01EN`, 1st edition, Jan 2021, release R1.01) plus a `.pdx` search index. They cover:
- Read Me First, licence, OSS, Release Information, Setup, Security Guide
- Engineering Modules: I/O Processes, Alarms, Reporting, Historical
- Edit Module, Advanced Operating Graphics, Excel Add-in, **OPC Interface**
- Alarm System Performance Analysis, Tutorial, System Design/Management, High Availability, Active Directory
- Class/Object, Alarm, History and Audit-Trail Management Engineering
- BUS / ITEM / EQUIPMENT Service Engineering, **Data Access Engineering**, Data Set Service, Exchange Tool
- Class Description Language (Traditional/Java), Report Generation Language, Data Set Service Language
- CI Portal, Setup File Editor, Graphic Display Setup, Report Server Setup

**What it is.** Yokogawa's "Collaborative Information Server" is a plant-wide supervisory, information and historian layer. Data live in "items" (process values with alarm states and sub-items such as integrators). It provides alarm management, historian, reporting, HMI graphics, OPC/OPC UA, and "CI Exchange" tools that import from CENTUM VP, STARDOM, ProSafe-RS and Prodigy (`IM 36K01A50` Release Info contents; `IM 36K10G10` Tutorial §3.1).

**Why it is here (interp.).** Sereď's DCS/historian layer is most likely Yokogawa (CENTUM VP + CI Server). These manuals would be the reference for pulling pan tags into the project via OPC UA / Data Access / Excel add-in: Brix, level, pressures, steam, seeding events. Those tags would time-align Camera 100 frames with process state and give phase labels. Nothing in the files I read names Sereď explicitly; confirm with the plant.

---

## 5. Facts about Sereď found in the theses

All from `[Bennár]` unless noted. Bennár's own PSD data came from the plant during campaigns 2005–2009, with the help of plant management.
- **Owner/plant:** Slovenské cukrovary s.r.o., Sereď (p.3, p.58). In 2010 Slovakia had 2 sugar factories with 205,000 t sugar capacity; typical processing ≈4000 t beet/day (Úvod, p.11).
- **Process line (p.58):**
  - beet pumps → 2 stone catchers → 2 weed catchers → washer → 3 slicers
  - **DC 12 extractor**
  - pre-/main liming + 1st carbonatation in 2 large tanks → decanter → Alfa-Laval or Putsch filters → 2nd carbonatation → filtration
  - **7-effect evaporator**
  - vacuum evaporative crystallisation in **3 kinds of pans: 3 for A-product, 2 for intermediate massecuite, 2 for C (zadinová) massecuite**
  - crystallisers → 3 filtering centrifuges → drying, sizing, packing
  - Plant scheme: Obr. 4 (Brňo 2009).
  - Not stated: whether ZRA is one of these 7 or a separate seed pan ("očkovací varostroj"). (open)
- **Seeding chain (p.42–43, p.59–60, p.80):** micro-seed ("mikroočko" = suspension of sugar particles in alcohol, glossary p.11) is dosed into the **seed pan ("očkovací varostroj")** at a constant Brix. The resulting **seed massecuite ("očkovacia cukrovina")** is drawn into the A pans at a constant Brix, as a % of pan.
  - Constants: Brix at micro-seed dosing, Brix at seed-massecuite addition, standard-syrup level at base charge, boiling curve.
  - Campaign variables: micro-seed volume (cm³) and seed-massecuite draw (%) (p.80, citing Brňo 2009).
  - This matches the known ZRA role (seed pan feeding A and C) (interp.).
- **Micro-seed doses tested:** 1000 or 1100 cm³ per seed strike. Seed-massecuite draw 15 / 19 / 19 / 20 / 22 % (variants A–E, p.59–60).
- **White A-sugar PSD:** ICUMSA GS2/9-37 sieving, Retsch AS 200, sieves 2.00/1.00/0.80/0.63/0.40/0.32/0.16 mm, sampled after each A strike.

  | Variant | MA (Rens) | CV (Rens) | Butler / Powers MA | On 1.00 mm sieve |
  |---|---|---|---|---|
  | A (1000 cm³, 15 %) | 0.95 mm | 39.4 % | 1.07 / 1.10 | 44 % |
  | B (1000, 19 %) | 0.85 | 33.2 % | — | — |
  | C (1100, 19 %) | 0.86 | 38.0 % | — | — |
  | **D (1100, 20 %) = recommended** | **0.76** | **38.4 %** | — | **21.8 %** |
  | E (1100, 22 %) | 0.86 | 37.3 % | — | — |

  - Variant D has the most even 1.0–0.4 mm fractions. A ≥22 % draw gives too many crystals that do not reach target size (Závery p.111).
  - Rens method judged most accurate.
  - **So Sereď A-sugar MA ≈ 0.75–0.95 mm (Rens), CV ≈ 33–40 %** (Tab. 5–13).
  - Mechanism stated: final size is set by the *number* of seed crystals, i.e. micro-seed volume × draw fraction (p.86–87).
- **Boiling practice (literature section, generic; p.42–45):**
  - syrup prepared at 85 °C and diluted to 70–75 °Bx
  - boiling point rises 70–75 → 78–82 °C under vacuum
  - final massecuite dried to 94–95 °Bx over 0.5–1.5 h
  - end judged by conductometer
  - 60–75 % of the sugar crystallises in the pans
  - A-massecuite crystallisers 2–6 h; C-massecuite 24–70 h
- **C-massecuite at Sereď (p.88):**
  - 2 pans of **60 t** massecuite each, forced circulation, 8–12 h strike, pH adjusted to 9 with NaOH, dried to 94 °Bx
  - dropped into 2 receivers of 55 t at 80–85 °C, then an **8-stage horizontal cooling line (refrižeranty)**, 85 → 49 °C, residence 42–48 h
  - molasses purity 64.7–68.5 %, versus a 60–64 % target (p.90)
  - S reached 1.2 in the last cooler in variants A, C, E, F
- **Centrifuges (generic, p.45):** batch charge 850–1500 kg.
- **`[Fernando_Thesis_NTNU]`:** no Sereď information; its link to the project is via R. Paulen (interp.).
- **`[Hernández]` / `[gPJ]`:** the HYCON2 benchmark plant (Valladolid). No Sereď names, tags or numbers found.

---

## 6. Open questions

1. Is ZRA one of the 7 pans listed by Bennár (the "2 for intermediate massecuite"?) or a separate seed pan? Bennár's "očkovací varostroj" fits ZRA, but no tag names appear in any file I read.
2. Seed-size conflict. Georgieva's seed MA is 10–12 µm and Quintana's L0 is 15 µm. Both match the 6.8 µm Mastersizer slurry and the expected ~200–350 µm ZRA discharge. Is "10 µm end product" therefore the *slurry*, not the ZRA output? The literature supports the slurry reading (interp.).
3. The Bennár micro-seed doses (1000–1100 cm³ alcohol slurry) are from 2005–09. What are the current dose and seed-massecuite draw (%) at Sereď?
4. Will the gPROMS v7 model be extended with moments/PBM for ZRA? It currently has no size state, an unphysical lumped N = 1e6, and seed mass only, plus a "Check value" flag on k_dt and a stale optimisation entity that references `Caz.Evap`.
5. Yokogawa CI Server: is it actually the Sereď historian? Which tags exist for ZRA (Brix, level, P_cham, P_cal, steam, seed-dosing events), at what sampling rate, and via OPC UA or Data Access?
6. The Georgieva G law includes a volume-fraction factor (1 + 2v/V_m) that was garbled in extraction. It should be checked against the PDF image before being used in code.
7. Units of Quintana's K_g (µm/min?) were not recovered from the text extraction.
