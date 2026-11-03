# Sereď sugar plant: notes A (Q&A docs, DeltaV screens, pan drawings, site photos)

BASE = `/Users/mw/Library/CloudStorage/GoogleDrive-marek.wadinger@stuba.sk/My Drive/sugar_plant/sered/`
Short source keys used below:
- **[ZOD]** `Potrebné dáta a otázky - Zodpovedane.docx` (answered Q&A; author/lastModifiedBy Adam Fedor, modified 2026-08-12)
- **[Q0]/[Q1]/[Q3]** `Potrebne dáta a otázky.docx`, `(1)`, `(3)`: byte-identical text (same md5), the original unanswered version
- **[Q2]** `Potrebne dáta a otázky (2).docx`: revised question wording + 1 comment by Radoslav Paulen (2026-07-03)
- **[FIG]** optical-layout figure embedded in [ZOD] and [Q2] (`word/media/image1.png`, identical md5 in both)
- **[S:<name>]** `schemes/<name>.png` (DeltaV Operate screenshots, timestamped 11/15/2025 ~23:30, user SCADMINISTRATOR)
- **[SCHEME]** `schemes/scheme_Sugar.pdf` (scanned hand-drawn flow sheet, has a text layer)
- **[DWG-V]** `schemes/varostroj.pdf`, **[DWG-R]** `varostroj_rez.pdf`, **[DWG-T]** `varostroj_topna_komora.pdf`, **[DWG-B]** `varostroj_bridovy_priestor.pdf` (scanned Hungarian drawings, no text layer; pypdf extracted 0 characters, so I read the rendered images)
- **[P:<file>]** `photos/<file>.jpg`

"(interp.)" marks my own reading, not something a file says outright.

---

## 1. Plant topology & material flow

**Three-product boiling scheme (A / B / C)** [SCHEME]:
- Thick juice -> **Standard syrup** (štandardný sirup, "SS"). A white runoff and B sugar also go back to standard syrup. Thick juice goes straight to the B pans too (dashed line).
- **A product:** standard syrup -> **A-seed vacuum pan 1x30 t** -> **A-seed receiver** -> seeds the **A vacuum pans 3x60 t** -> A-massecuite receiver -> A-centrifuges -> **white sugar -> silo**, A white runoff, A green runoff.
- **B product:** A green runoff (and thick juice) -> **B vacuum pans 2x60 t** -> B-massecuite receiver -> B-centrifuges -> B sugar (goes to standard syrup), B white runoff, B green runoff.
- **C product:** B green runoff and Af-syrup -> **C2 vacuum pan**. **C1 vacuum pan -> C-seed receiver -> C2** (black arrow; C1 is shown as the C-seed pan). C massecuite receiver -> **VCC** (vertical cooling crystallizer) -> C-centrifuges -> C sugar -> AF-centrifuge -> Af-sugar (to standard syrup) / Af-syrup. Also **molasses**. "Prelimer B-M" receives Af-syrup.

**Pan names on the DCS** [S:Varna_all]: A1, A2, A3, **ZRA**, B1, B2, C1, C2. The 30 t seed pan on [SCHEME] lines up with ZRA (interp.: ZRA is the only seed pan on the A side of the DCS, and its recipe has slurry, formation and seeding steps).

**Seed route (ZRA -> A pans, and C)** [S:Varostroj ZRA_prehlad], [S:Varna_all], [S:Varostroj A1_udaje], [S:Varostroj C1_udaje]:
- ZRA discharges into **"Refrizerant seed1"** (seed receiver directly below ZRA; 60.1 °C, 67.4 %). Pumps **BEH1/BEH2** ("Dialkovo" = remote control) send it up a magenta line to **"Refrizerant seed2"** (62.3 °C, 46.5 %).
- The A pans take **UC** (*očkovacia cukrovina*, seed massecuite; interp.: UC is the abbreviation the recipes use) from Seed2. A1/A2/A3 setpoint: "Hladina SEED2 pre dávkovanie UC inak var na vodu" = 0 % (minimum Seed2 level needed to dose UC, otherwise the pan boils on water). "Porcia UC" = 15 % (A1, A3) and 17 % (A2). "Poloha ventilu sirupu pri nátahu UC" = 20 %.
- C1 and C2 also carry the same "Hladina SEED2 pre dávkovanie UC" setpoint (C1 80 %, C2 10 %), so C pans can also take seed from Seed2 [S:C1_udaje], [S:C2_udaje].
- **This supports the known context** "ZRA seed massecuite seeds the A and C pans": [ZOD] says "A a C stage ... natiahne sa očkovacia cukrovina" (A and C stages draw in seed massecuite).
- **Seed mills** "MLYN NA OCKO (veľký / malý)" (seed mill, large/small): "Čas mletia" 300 min [S:Varostroj A1_prehlad]. Interp.: these make the slurry (*mikroočko*).
- Small slurry-pot icon + **"Potvrď očko"** (confirm seed) button on ZRA, B1, B2, C1, and C2 has the pot icon. B1/B2 also have "Neočkovať" (do not seed) [S:Varna_all], [S:B1_prehlad], [S:C1_prehlad]. Interp.: B pans are seeded directly with slurry; the B recipes have no UC parameters.
- Small tanks **"Cseed1"** (53.1 °C, 14.9 %) and **"Cseed2"** (36.0, 88.8 %, "MAX") appear on [S:Varna_all]. Interp.: these are the C-seed receivers fed by C1.

**Feed syrups (shown on the pan screens):**
- A pans and ZRA: "Standard sirup" tank (~71 %, ~79 °C). A pans also show **CSA 1 / CSA 2** (~34 % / 52 %) [S:A1..A3_prehlad].
- B and C pans: **CSA 1, CSA 2, CSB AfS** [S:B1/B2/C1/C2_prehlad].
- Interp.: CSA = A green-runoff syrup tank, CSB AfS = B green runoff / Af-syrup tank, which matches [SCHEME].
- Water ("Voda") goes to every pan. ZRA has "BV z B5" = brydová voda (vapour condensate) from condensate tank B5 [S:ZRA_prehlad].

**Massecuite receivers** [S:Varna_all]:
- A refrizerant (A1-A3 drop into it, ~89 %, 62.5 °C; "A odstredivky" = to A centrifuges)
- B refrizerant (20.8 %, 63.9 °C)
- **C spúšťací** (C drop tank, ~77 %, 51.8 °C) -> pump with LIC -> crystallizers **C1..C6** (VCC train; 85.2 %, C6 53 °C / 15 %) [S:C1_prehlad], [S:C2_prehlad]

**Heating vapour (bryda) per pan** [S:Varna_all], [S:*_prehlad]:
- A1, A2, A3 and ZRA show the heating-steam line "**4A.B**" (vapour from evaporator body 4A).
- B1, B2, C1 and C2 show "**3.B**" (3rd vapour).
- "III.bryda" lines enter the tops of the pans (interp.: vapour for steaming out/"Para na zavzdušnenie").
- Header pressures: "Tlak 3.Brydy" ≈ −1…−3.8 kPa, "Tlak 4A.Brydy" ≈ −0.5…−2.8 kPa [S:*_prehlad]. Interp.: these are gauge pressures.
- **This contradicts [ZOD]** (see §7).

**Evaporator** [S:Odparka_para], [S:Odparka_stava]:
- Bodies 4A, 1, 2, 3A, 3B, 4B, 5 (+ "Odparka 5AB"); vapour headers I–V Bryda.
- Live steam: TI529 137.5 °C, PI530 ≈ 173 kPa, **≈ 53 t/h**. Body 1 SP 170 kPa (gauge, interp.), 123 °C.
- Body 3B ≈ 20 kPa / 104 °C. Body 4A ≈ −0.1…−1.2 kPa / 94 °C. Body 4B ≈ −21 kPa / 93 °C. Body 5 ≈ −42 kPa / 83 °C.
- "Vakuum A varna" −82.8 kPa, "Vakuum B varna" −88.9 kPa (pan-house vacuum systems).
- Condensate tanks A1–A4, B1–B5 (interp.: named after evaporator bodies, not pans). "Varostroje A" / "Varostroje B,C" condensate returns via LIC546 / LIC545.
- Thin/standard juice tanks: TS1/TS2 (interp.: tenká šťava), SS1/SS2 (standard syrup, 70.5 %), LS1/LS2. Trend pens: "Hustota TS", "Hustota SS".
- Heaters DZ14–DZ18, DZ5, TZ17. "Chladič cukru" (sugar cooler).

---

## 2. Per-pan recipe & tags

### 2.1 Tag pattern (DeltaV), all pans [S:*_prehlad], [S:*_udaje]
Loop numbers: ZRA = 10xx, A1 = 11xx, A2 = 12xx, A3 = 13xx, B1 = 14xx, B2 = 15xx, C1 = 16xx, C2 = 17xx.

| Tag (xx = loop) | Faceplate label | Meaning / units |
|---|---|---|
| `PICxx02/AI1/PV.CV` | Podtlak | in-pan pressure (vacuum), kPa gauge (−100…+50) |
| `QIxx03/AI1/PV.CV` | Viskozita (B pans: "Hustota") | "viscosity" signal, shown in **Bx** (range 65…95 Bx, setpoints up to 110 Bx). [ZOD]: for C1 it "should directly represent the Brix in the pan" |
| `LIxx00/AI1/PV.CV` | Hladina | pan level, % (0–100) |
| `TIxx05/AI1/PV.CV` (ZRA: `TI1006`) | Teplota | massecuite temperature, °C |
| `EIxx04/AI1/PV.CV` | Prúd miešadla | stirrer motor current, A (0…180 A) |
| `S_<PAN>/VZORCE/VISKOZITA.CV` | Sekvenci… | sequence/formula viscosity value (≈ QI value) |
| `QICxx00_PID/PID1/{PV,SP,OUT}.CV` | Sirup do Cx | feed-syrup valve controller ("Ventil riadi viskozita"). PV = density/Bx (= QIxx03 per [ZOD]), OUT = valve % |
| `QICxx01_PID/PID1/OUT.CV` | Voda do Cx | water valve controller, % opening [ZOD] |
| `TICxx02_PID/PID1/{PV,SP,OUT}.CV` | Tlak pary | heating-steam controller. PV/SP in kPa (C pans) or °C (A pans, ZRA). OUT = steam valve %. Only C2 has `TIC1702_PID/XFR1/OUT.CV` "Výstup klapky na paru" (steam damper output) |
| `LIC1702B_PID/PID1/CAS_IN.CV` | (C2 only) | level-based cascade into the C2 steam controller ("HLADINA" mode on the steam valve) |
| `PIC1001` (field tag) | ZRA, Rosemount, range −50…+50 kPa [P:1786375479358] | Interp.: ZRA heating-steam/chamber pressure transmitter. Its range cannot cover −80 kPa vacuum |

Faceplate boxes on the overview screens show PV / SP / OUT % plus the mode (CAS / LO / MAN):
- Vacuum: ZRA CAS −80.6 / −81.0 kPa / 100 %.
- Syrup: ZRA CAS 81.5 / 81.1 / 65.8 % "Ventil riadi viskozita" (valve controls viscosity).
- Water: ZRA LO 81.5 / 80.7 / 0 %.
- Steam: ZRA LO 69.5 / 80.0 °C / 30 % "Ventil riadi teplota" (valve controls temperature) [S:ZRA_prehlad].
- Interp.: for ZRA/A pans the steam-loop PV equals the massecuite temperature (69.5 °C). For C2 the steam PV (−3.3 kPa) equals the pressure shown under the steam valve, i.e. heating-chamber pressure.

Steam-valve control mode per pan [S:Varna_all]: A1/A2/B1/B2/ZRA "Teplota" (temperature), A3 "L", C1 "TLAK" (pressure), C2 "HLADINA" (level).

Sequence phases seen ("Hlásenie kroku" = step, "Hlásenie podmienky" = waiting condition):
- Navarovanie (boiling-up)
- "Navarovanie a obmedzená para" (boiling-up with limited steam; ZRA, waiting "Čakám na čas pary")
- Zavzdušnenie (breaking vacuum; B1)
- Vypúšťanie (discharge; A3 "Čakám 13 min pokiaľ sa var vyprázdni" = waiting 13 min for the strike to drain)
- Sušenie (drying/tightening; B1)
- Odstavený (shut down; C1)
- Recipe vocabulary: zahustenie (concentration), formovanie (formation), stabilizácia, očkovanie (seeding), riedenie (dilution), vyparovanie (steaming-out), umývanie (washing)

### 2.2 ZRA, seed pan (full detail) [S:Varostroj ZRA_udaje], [S:Varostroj ZRA_prehlad]
Live values 15.11.2025 23:32: Podtlak −80.6 kPa, Viskozita 81.5, Hladina 50.5 %, Teplota 69.5 °C, stirrer 10.3 A, **KP 1.130, KP_akt 1.210**, step "Navarovanie a obmedzená para". Trend: level rose 0→~55 % after a dump at ~22:50, vacuum was broken ~22:50–22:55.

| Group | Parameter (Slovak) | Value |
|---|---|---|
| Main | Max hladina refrižerant pre spustenie (max receiver level to allow start) | 12 % |
| | Minimum SS pre nátah (min standard-syrup tank level to fill) | 0 % |
| Level | Hladina pre zapnutie miešadla a vykurovacej pary (stirrer + heating steam on) | 30 % |
| | Hladina zahustenie (concentration) | 45 % |
| | Hladina pre začiatok navarovania (start boiling-up) | 45 % |
| | Hladina pre koniec navarovania (end boiling-up) | 100 % |
| | Hladina pre začiatok umývania / umývania prístrojov | 3 % / 2 % |
| Vacuum (−100…+50 kPa) | Min podtlak pre otvorenie hlavnej klapky (main vapour valve) | −62 kPa |
| | Podtlak pre navarovanie | −81 kPa |
| | **Podtlak očko., form., stab.** (seeding, formation, stabilization) | −81 kPa |
| | Podtlak pre zahustenie a riedenie | −81 kPa |
| | Podtlak pre začatie vypúšťania (start discharge) | −20 kPa |
| | Max tlak vo varostroji pri zavzdušnení | 12 kPa |
| Steam (0…180 kPa / 0…150 °C) | % otvorenia parného ventilu na začiatku | 44.2 % |
| | Tlak pary pri zahustení (concentration) | 75 kPa |
| | Tlak vykurovacej pary pri formovaní | −45 kPa |
| | Teplota pary pri navarovaní | 80 °C |
| | Tlak pary pri vare na vode | 60 kPa |
| | Tlak vykurovacej pary pri stabilizácii | −45 kPa |
| Viscosity (65…95 Bx) | Kvocient čistoty SS (purity of standard syrup) | 93.40 % |
| | **Koeficient presýtenia** (supersaturation coefficient, seeding target) | **1.13** |
| | Viskozita stabilizácia | 80.72 Bx |
| | Viskozita formovanie | 80.72 Bx |
| | Viskozita koniec navarovania | 90 Bx |
| | Viskozita koniec sušenia | 95 Bx |
| | Viskozita konečné riedenie (final dilution) | 91.5 Bx |
| | (side fields) koef. stabilizácia 0.00, koef. formovania 0.00, konšt. prepnutie podtlaku 0.03 | |
| Current (0…180 A) | Prúd pre koniec sušenia / riedenia | 17 A / 14 A |
| Times | Čas otvorenia pary na začiatku | 300 s |
| | Čas stabilizácie | 100 s (live counter 101) |
| | Čas prechodu SP pary pri vare na vode | 60 s |
| | Čas sušenia | 20 000 s |
| | Čas čakania pre vyparovanie | 900 s |
| | Čas umývania / vyparovania rozdeľovača a prístrojov | 3 s / 5 s |
| | Čas riedenia | 0 s |
| | **Čas formovania / Čas očkovania** | **3 s / 3 s** |
| | Čas pary začiatok | 500 s (live 444) |
| | % otvorenia pary pre obmedzenie (limited steam) | 30 % |
| | Čas pary začiatok navarovania | 1020 s |
| Other | Poloha ventilu sirupu pri riedení (syrup valve during dilution) | 20 % |

[ZOD] describes the ZRA procedure in words:
1. Draw in a set % of syrup (per the graphic).
2. Concentrate to the required density.
3. Operators set the supersaturation coefficient so the slurry can be added; the boiler decides when to seed, depending on the quality of the incoming syrup.
4. Once that density is reached, the micro-seed (*mikroočko*) goes in.
- The "Podtlak očko., form., stab." and KP 1.13 parameters match this description (interp.).
- Pan size: [SCHEME] "A-seed vacuum pan 1x30 t". Discharge: Refrizerant seed1 -> BEH1/2 -> Refrizerant seed2 [S:ZRA_prehlad].

### 2.3 A1 / A2 / A3, A-product pans (3x60 t [SCHEME]) [S:Varostroj A1/A2/A3_udaje]

| Parameter | A1 | A2 | A3 |
|---|---|---|---|
| Minimum pre naťahovanie UC (Seed2 level for UC draw) | −2 % | −2 % | −3 % |
| Hladina SEED2 pre dávkovanie UC inak var na vodu | 0 % | 0 % | 0 % |
| Minimum SS pre nátah / Minimum CSA pre riedenie | 2 % / 15 % | 2 / 15 | 2 / 15 |
| Max hladina refrižerant pre spustenie | 30 % | 30 % | 30 % |
| Level: miešadlo on / zahustenie / start navar. / end navar. / umývanie | 35/46/60/100/5 % | 35/46/55/100/9.5 % | 35/45/55/100/5 % |
| Min podtlak hlavná klapka / nastavený podtlak / zahustenie a riedenie | −55 / −85 / −85 kPa | same | same |
| Podtlak pre začatie vypúšťania / max tlak pri zavzdušnení | −15 / 20 kPa | −10 / 20 | −17 / 20 |
| % parného ventilu na začiatku / pri stabilizácii / pri nátahu UC | 32 / 35 / 0 % | 35 / 35 / 0 | 35 / 35 / 0 |
| Teplota pary pri navarovaní / pri vare na vode | 88 / 80 °C | 91 / 80 | 87 / 80 |
| Kvocient čistoty SS | 93.0 % | 94.5 % | 94.5 % |
| **Koeficient presýtenia KP** | **1.10** | **1.15** | **1.15** |
| Viskozita stabilizácia / koniec navar. / koniec sušenia / konečné riedenie (Bx) | 84 / 92 / 110 / 110 | 84 / 91 / 110 / 110 | 83 / 89 / 110 / 95 |
| Prúd koniec sušenia / riedenia | 75 / 51 A | 72 / 51 | 75 / 51 |
| Čas otvorenia pary na začiatku / stabilizácie / sušenia | 500 / 30 / 10 000 s | 250 / 30 / 10 000 | 250 / 30 / 1 000 000.06 (interp.: effectively disabled) |
| Čas čakania pre vyparovanie / umývania | 900 / 3 s | 900 / 3 | 900 / 3 |
| Porcia UC / Porcia CSA pre riedenie | 15 % / 0 % | 17 % / 0 | 15 % / 0 |

- Live 23:31, A1: −80.8 kPa, 90.1, level 91.8 %, 69.3 °C, 39.9 A, KP_akt 2.226, step Navarovanie.
- Live 23:31, A2: level 62.2 %, KP_akt 1.631.
- Live 23:31, A3: discharging (Vypúšťanie), −5.5 kPa, level 0.4 %.
- Tags: A1 PIC1102, QI1103, LI1100, TI1105, EI1104. A2 is 12xx, A3 is 13xx.

### 2.4 B1 / B2, B-product pans (2x60 t [SCHEME]) [S:Varostroj B1/B2_udaje]

| Parameter | B1 | B2 |
|---|---|---|
| Minimum CSB pre nátah / Minimum CSA (B1) or SS (B2) pre nátah / Min CSB pre riedenie | 3 / 0 / 5 % | 9 / 0 / 5 % |
| Max hladina refrižerant pre spustenie | 75 % | 60 % |
| Level: miešadlo / zahustenie / start navar. / end navar. | 30 / 45 / 46 / 100 % | same |
| Level: start of upper / lower steaming-out | 25 / 1 % | 25 / 3 % |
| Min podtlak hlavná klapka / nastavený / zahustenie a riedenie / vypúšťanie / max zavzdušnenie | −40/−90/−90/−10/10 kPa | same |
| % parného ventilu na začiatku | 50 % | 50 % |
| Teplota pary: stabilizácia / navarovanie / var na vode / formovanie | 90/85/78/85 °C | 90/90/86.6/90 °C |
| Viskozita formovanie / stabilizácia / koniec navar. / koniec sušenia / konečné riedenie | 85/86/90/105/105 Bx | 86/87/94/105/102 Bx |
| Prúd koniec sušenia / riedenia | 76 / 42 A | 75 / 42 A |
| Times: para začiatok / stabilizácia / stab. bez pary / formovanie / sušenie | 300/30/5/60/12 000 001 s | 300/60/5/60/12 000 s |
| Times: vyparovanie / vyparovanie rozdeľovača / riedenie / **očkovanie** | 1000/10/10/**1 s** | 1000/20/10/**1 s** |
| Teplota pre koniec vyparovania / Porcia CSB pre riedenie | 105 °C / 25 m³ | 100 °C / 25 m³ |
| Hladina pre povolenie otvoriť / zakázanie CSB | 100 / 100 % | 100 / 100 % |

- No KP/UC fields. Formation + 1 s seeding + "Potvrď očko" fit direct slurry seeding (interp.).
- Live, B1: −25.4 kPa, density 89.1, level 92.5 %, step Zavzdušnenie.
- Live, B2: −86.3 kPa, level 48.1 %, Navarovanie.
- Tags: B1 PIC1402, QI1403 ("Hustota"), LI1400, TI1405, EI1404. B2 is 15xx.

### 2.5 C1 / C2, C-product pans [S:Varostroj C1/C2_udaje]

| Parameter | C1 | C2 |
|---|---|---|
| Minimum CSB / CSA pre nátah | 5 / 5 % | 1.6 / 8 % |
| Max hladina refrižerant pre spustenie (seedu) | 40 % (10 % for seed) | 40 % |
| Minimum pre naťahovanie UC / Hladina SEED2 pre dávkovanie UC | 5 % / 80 % | 10 % / 10 % |
| Level: miešadlo / zahustenie / start navar. / end navar. | 20/40/55/100 % | 20/40/55/100 % |
| Level: start of upper / lower steaming-out | 30 / 2 % | 25 / 3 % |
| Vacuum: hlavná klapka / zahustenie / nastavený / riedenie / vypúšťanie / zavzdušnenie | −55/−95/−95/−95/−20/−10 kPa | −55/−95/−95/−10/10 kPa |
| % parného ventilu na začiatku / pri nátahu seedu | 35 / 30 % | 35 / 30 % (+ min. closing during boiling 80 %) |
| Tlak pary (kPa): zahustenie / stabilizácia / formovanie / začiatok navar. / koniec navar. / var na vode-sušenie / sušenie | 25/25/25/30/30/15/38 | stab. 15, form. 15, var na vode 20, sušenie 40 |
| Kvocient čistoty | 73 % | 73 % |
| **KP pre varenie so seedom / KP pre varenie seedu** | **1.10 / 1.30** | 1.10 / (none) |
| Viskozita očkovania / formovanie / stabilizácia / koniec navar. / koniec sušenia / konečné riedenie | 86/86.92/86.92/92/91/92 Bx | 87/86/86/92/99/94 Bx |
| Prúd koniec sušenia / riedenia / varenia seedu | 44 / 44 / 42 A | 42 / 54 A |
| Times: para začiatok / stabilizácia / vyparovanie / očkovanie / očkovanie seedu / vyparovanie seed | 300/50/600/10/10/10 s | 300/50/600/10/–/10 s; Čas formovania 120 s; **Čas navarovania 195 min** |
| Teplota pre koniec vyparovania | 105 °C | 108 °C |
| Hladina pre preskočenie na var na vode / Čas var na vode | 5 % / 1000 s | – |
| Min hladina horný seed pre zastavenie dávkovania seedu | 8 % | 8 % |

- C1 has a steam-pressure ramp versus level ("TLAK vs HLADINA"): P_zač 30 kPa at L_zač 55 % -> P_kon 30 kPa at L_kon 100 % [S:C1_udaje].
- C1 and C2 have a dilution block ("Riedenie": total set / amount per cycle, number of cycles 3) and "Riedenie_OLD".
- C1 cooks C-seed itself (KP 1.30, "varenie seedu") and pan-to-pan transfer to C2 (KP 1.10 "with seed"). This matches [SCHEME] C1 -> C-seed receiver -> C2.
- Live, C1: Odstavený (shut down), 109 °C (interp.: steaming out).
- Live, C2: −88.7 kPa, 93.2, level 96.5 %, 76 °C, 47.9 A, "0.0 m³/h" water flow.
- Tags: C1 PIC1602, QI1603, LI1600, TI1605, EI1604. C2 is 17xx.

### 2.6 Pan drawings ([DWG-*], Láng Gépgyár Budapest, "Cukorkristályosító készülék" = sugar crystallizing apparatus)
- **[DWG-V]**, drawing 1-24187-1-00, 1:20, drawing no. 983/1963:
  - 300 m² heating surface ("300 m² ft"), **"500 q töltetű" = 50 t charge**, weight 23 000 kg.
  - Shell Ø4500×12. Central downtake Ø1250×4. Calandria Ø4520×2112 (8400 kg). Vapour body Ø4500×2650 (5060 kg). Vapour mantle Ø4500×1738.
  - Total height ≈ 6575 mm. Conical bottom Ø4706 with Ø700 outlet.
  - Design pressure: heating space 2.2 at, vapour space 76 cmHg vacuum. Test pressure 3.3 at. Water-filled weight 106 t.
  - Massecuite level marks ("Pépszintek"): 500 q at γ = 1.3 and 1.4 kg/dm³; lower marks 195 q (γ 1.3) / 210 q (γ 1.4). Interp.: the lower marks are the minimum footing over the calandria.
  - Nozzle list: XIX "Világítóablak mosás" (light-window washing), XX "Figyelőablak mosás" (observation-window washing), XXIV "Habzásfigyelő" (foam watch), XXV–XXVII steam inlets (retur, I. pára, II. pára). The sight glasses are oval, in a column spaced 340 mm.
  - Reference users: Hatvan, Szolnok, Petőháza, Szerencs sugar factories.
- **[DWG-R]**, 1-24297-1-00 (1965): same 300 m² / 500 q class, ≈ 21 500 kg, has a central circulator/downtake. Users: Sarkad, Sárvár, Selyp.
- **[DWG-T]**, calandria (Fűtőtest) for a 300 m² crystallizer:
  - "(500 q töltet)" (handwritten, could read 600 or 800; interp. 500), 1:10, ~14 000 kg, 1-25263-4-00, copy dated 1982.11.
  - Shell Ø4500×12, circulation tube Ø1635×10, tube length ≈ 1200 mm, bottom Ø3500 -> Ø1800 -> outlet Ø770.
- **[DWG-B]**, vapour body (Páratest / "Parné teleso", Slovak annotation):
  - "~220 m² ff. cukorkristályosító / varostroj 200 m² v.p.", 1:10, 5870 kg, 1-23356-1-00, dated 1989.
  - Body Ø3500×10 / Ø1300×6 vapour outlet. Has the column of 4 oval sight glasses (350 mm pitch) and a Ø550 manhole.
- Pan nameplate photo [P:1786375479250], interp. B1 because it follows the B1 shot [P:1786375479238]:
  - Láng 1983, serial ~13089.
  - Design pressure: outer space vacuum, inner space 2.2 bar. Test pressure 2 / 3.2 bar. Temperature 20–150 °C.
  - **Volume 70.8 m³ (outer = massecuite side) / 8.35 m³ (inner = steam side) (interp.)**. Weight 25 500 kg. Heating surface **300 m²**.

---

## 3. Q&A answers [ZOD] (question -> answer, English; Slovak terms in parentheses)

1. **Drawings for pan dimensions?** -> Supplied for the 60 t units ("Sú dodané pre 60t zariadenia"). These are the [DWG-*] PDFs.
2. **During initial filling (0 -> 40–60 % level), is the juice valve 100 % open?** -> ZRA: draw in a set % of syrup, concentrate to the required density, set the supersaturation coefficient (*koeficient presýtenia*), the boiler (*varič*) decides when to seed depending on the quality of the incoming syrup, and at that density the micro-seed (*mikroočko*) goes in. A and C stages are fixed: fill to level, concentrate, then draw in seed massecuite (*očkovacia cukrovina*). **Valves are fully open during filling; these are two separate valves.**
3. **After 60 %, does QIC1600_PID/PID1/OUT.CV (syrup to C1) give the controller position, with manual operator interventions in QIC1601_PID/PID1/OUT.CV (water to C1)?** -> Yes. It covers both manual and automatic interventions. Syrup = % syrup inflow, water = % water addition. **Water is added in the C stage mainly to reduce the load on the stirrer** (*zaťaženie miešadla*).
4. **QI1603/AI1/PV.CV (Hustota C1) and QIC1600_PID/PID1/PV.CV are identical. Is this the Brix in the pan?** -> Density (*hustota*) "should directly represent the Brix in the pan".
5. **Brix of the syrup entering the pan / diluting the magma?** -> Lab only (*iba labáky*). The lab values for 26.10–1.11.2025 and 4.2.2026 were requested; no values were given. [Q2] comment (R. Paulen): not measured online, should be in the lab-data Google Sheet (link in comment).
6. **TIC1602_PID/PID1/PV.CV = heating-steam pressure, gauge? SP = setpoint for absolute pressure, not the differential? OUT = steam valve opening? Same steam as evaporator body 4A? Data request (1-min 26.10–1.11.2025, 30-s 4.2.2026 11–17 h)** -> "These steam pressures and also the heating-steam pressure are all pressures **inside the pan**." **All pans except ZRA get vapour from 4A; ZRA gets it from the 3rd vapour** (*z 3 brydy*). Hourly data are already available.
7. **LI1000/AI1/PV.CV = level in the seed pan (*hladina v očkovacom varostroji*), same windows** -> Requested, to be delivered later. This confirms **LI1000 = ZRA level and ZRA = očkovací varostroj**. [Q0] had asked "the Excel only has refrigerant; is there a separate massecuite-level signal for ZRA?"
8. **Optics, four unknowns of [FIG]:**
   - (A) spacer ring between lens and camera body (*medzikrúžok*; we estimated 45 mm) -> **≈ 6 cm**
   - (B) lens front to outer face of the sight glass -> **≈ 2 cm** (photos available)
   - (C) sight-glass thickness -> **20 mm, diameter 150 mm** ([FIG] itself says "2 mm")
   - (D) lamp to inner glass face -> it is an **optical fibre**; there is a gap that could not be measured because of the position; "very close to the glass", **est. 1–2 mm**
9. **Lens aperture and focus** -> **F = 1.6** "if I read it correctly". Focus distance in mm was not shown on the lens.
10. **DVR make/type/signal/codec/rescaling** -> "will be supplied, they know about it", and **"they do not record, they only have a signal-processing device"** (*nenahrávajú – majú iba zariadenie na spracovanie signálu*).

**What the other versions change:** [Q0]=[Q1]=[Q3] is the original. [Q2] reworded it and is the direct precursor of [ZOD].
- [Q0] asked specifically for documentation for **C1 and ZRA** dimensions.
- [Q0] said the A4 evaporator ("odparka A4"); [Q2]/[ZOD] say "teleso 4A".
- [Q0] asked focus "in m, read from the ring"; [Q2] asks "in mm, from the lens".
- [Q2] added the exact data windows (26.10.2025 0:01 – 1.11.2025 23:00 @1 min; 4.2.2026 11:00–17:00 @30 s).
- [Q0] referenced attachment "18_optical_layout_sk_variables.png".

---

## 4. Camera / optics facts
- [FIG] optical chain: camera body labelled **"Hanwha HCB-6000"** (sensor plane "snímač") -> spacer ring (A) -> **Fujinon HF35HA-1B, length 29.5 mm** -> air gap (B) -> sight glass (*priezor*, C) -> massecuite -> lamp -> massecuite.
- Focus plane = inner glass surface ("rovina, kde kamera ostrí"). **Our assumption**: it is drawn on our own [FIG], which we sent with the questions; the plant did not state it. With the lamp 1–2 mm from the inner face (8(D)), the image is a backlit projection through a ~1–2 mm slurry slab, sharp at the glass if this assumption holds.
- Photos confirm the lens: **FUJINON 1:1.6/35 mm HF35HA-1B**, FUJIFILM Corporation, made in China [P:20260810_112218], [P:20260810_112208].
  - Aperture ring reads 1.6–2 near the index [P:20260810_112120/112128].
  - Focus ring markings NEAR…FAR, with a locking screw [P:20260810_112149–112202]. No distance scale value is legible in mm (matches [ZOD]).
- **Camera body in photos is labelled "ADEMCO VIDEO"** (white analog box camera) [P:1786375479369/379/391], [P:20260810_111738/111741].
  - Rear panel [P:20260810_111636]: DIP switches L/L–INT, AI–AES, VIDEO, D.D., AGC OFF, BLC OFF, NC; V-PHASE pot, ALC pot, BNC "VIDEO" out, 2-pin power terminal, POWER LED.
  - Interp.: this is a classic analog CVBS camera with auto-iris (video-drive) support, which is consistent with PAL output.
- Mounting [P:20260810_111738]: camera on a **Fotomate quick-release plate on an angle bracket bolted to the sight-glass flange**. The lens appears to sit almost against the glass, but the photos (tape measure + lens body as ruler; also [P:20260810_111741], [P:1786375479369/391]) read the lens front ≈ 35–46 mm from the glass, not the "≈ 2 cm" of 8(B), and the spacer tube ≈ 37–42 mm, not "≈ 6 cm" (2026-11-03 analysis). A tape measure was laid from the flange outward (~29 cm span to the rear of the body).
  - A blue armoured cable with a steel ferrule enters the flange at the top. Interp.: this is the **fibre-optic light guide** (lamp) passing through the window flange, which matches [ZOD] "optical fibre".
- Sight glass: round, bolted flange, heavy deposit/fouling around it. Bolt count not determinable: no photo (Aug or [`docs/lens/`](../lens/) Feb) shows the full bolt circle, and heads of two sizes are visible on the part that is shown. (An earlier reading here said ~12; `docs/lens/README.md` records 8 from the operator.)
- Plant has no recording: only a signal-processing device [ZOD]. The PAL recordings must come from elsewhere (interp.).

---

## 5. Photos ([P:*], 42 files; 23 dated by EXIF 2026-08-10 11:16–11:35, Samsung Galaxy S24 Ultra; 19 "17863754xxxxx.jpg" have no EXIF)
- **Site visit with person at an open pan manhole** (large round door, grated step) [P:1786375479150/167/187]. Interp.: an inspection of a pan interior during the off-season.
- **Pan B1 exterior** [P:1786375479238]:
  - Large "B1" lettering.
  - Two oval sight glasses with tall lamp housings (vertical light tubes) beside them.
  - Láng nameplate, pressure gauge, a small controller box.
- **B1 piping** [P:1786375479208/225]: lines labelled **MSZ** and **KSZ**, "Voda B1"; valves with green-cap position sensors.
  - [S:Varna_all] shows "Para / SS / KSZ" lines at the pan bottoms and "MSZ" at B/C. Interp.: these are steam/syrup line codes.
- **Nameplates** [P:1786375479250/264/298/334]: Láng Gépgyár, 1983 (details in §2.6).
  - The older plate [P:1786375479334] reads "Fűtőtérben … ATM, Páratérben … ATM".
  - Technická inšpekcia a.s. inspection stickers on all plates.
- **Pan C1** [P:1786375479284]: "C1", painted **"30T"** level/tonnage mark next to the sight glasses, gauges.
- **Pan A3** [P:1786375479310/322]: "A3", "A produkt č. 3", painted **"40T" and "30T"** marks beside a vertical column of oval sight glasses with lamp housings. Interp.: tonnage at that level.
- **ZRA instrumentation** [P:1786375479346/358]: new Rosemount pressure transmitter (housing 3151-3302-1000/AD, Wessling), handwritten **"ZRA", "PIC 1001", "−50 ÷ +50 kPa"**, still bagged, on a 3-valve manifold on a large insulated line.
- **Valve actuators** [P:1786375479404], [P:20260810_111613/617/622]: PMV EP5 electro-pneumatic positioner (4–20 mA, made in Sweden); Alfa Laval actuator Mod. 4F0A0, P max 10 bar; butterfly valve.
- **Camera at sight glass** [P:1786375479369–391], [P:20260810_111636–111741]: Ademco Video camera + Fujinon lens on a Fotomate bracket, tape-measure shots, fibre cable into the flange.
  - Interp. that this is ZRA: the shots are adjacent in sequence to the ZRA transmitter photos. No pan label is visible in the frame.
- **Lens close-ups** [P:20260810_112120–112218]: aperture/focus rings, model print (see §4).
- **Inside a pan** [P:20260810_112837/112839/112845]:
  - A small round sight glass seen from inside, just **above the top tube plate of the calandria** (tube holes visible).
  - A bent U-shaped tube in front of the glass. Interp.: a window-washing spray pipe (drawing nozzle "Figyelőablak mosás") or the fibre/lamp holder.
  - 112845 is a hazy/condensed view through the glass.
- [P:20260810_113401–113502]: heavily encrusted cylindrical fittings inside the pan / on the wall (mottled scale) and the inside of a window ring (113444). Interp.: deposits and fouling near the window.

---

## 6. Open / unanswered questions
- Brix of feed syrup entering the pans: lab only, values not delivered [ZOD]; [Q2] comment points to the lab-data sheet.
- LI1000 (ZRA level) data: "will be delivered later" [ZOD].
- DVR/signal chain make, model, codec, rescaling: "will be supplied" [ZOD]. The plant states it does not record at all.
- Focus distance (mm) not readable from the lens [ZOD], [P:20260810_112149–112202].
- Lamp-to-glass distance only estimated (1–2 mm) [ZOD].
- Spacer ring "≈ 6 cm" and lens-glass gap "≈ 2 cm" are rough ("cca") [ZOD].
- Which evaporator vapour heats which pan is ambiguous (see §7).
- Exact meaning of PIC1001 (field) versus DCS PIC1002 (ZRA Podtlak) is not documented. Interp.: PIC1001 = steam-side pressure.
- Abbreviations not defined in any file: CSA, CSB AfS, UC, SS, MSZ, KSZ, KP_akt. My readings: UC = očkovacia cukrovina; SS = štandardný sirup; KP = koeficient presýtenia (setpoint) / KP_akt (actual).
- Which pan the camera photos show is not labelled. The ZRA sequence context suggests ZRA (interp.).
- Pan volume: drawings say 50 t charge (500 q), the flow sheet and [ZOD] say 60 t, and the nameplate gives 70.8 m³. The working volume / tonnage-to-level mapping (painted 30T/40T marks) is not specified.

## 7. Contradictions
1. **Camera body:** [FIG] says "Hanwha HCB-6000", but every camera photo shows a body labelled **"ADEMCO VIDEO"** [P:1786375479369], [P:20260810_111738]. Possibly a relabelled/OEM body or a different camera; this needs confirmation.
2. **Sight-glass thickness:** [FIG] says C = **2 mm**; [ZOD] answer says **20 mm** (Ø150 mm).
3. **Spacer ring:** team estimate 45 mm [Q0]/[ZOD] versus plant answer **≈ 60 mm** [ZOD].
4. **Heating vapour:** [ZOD] says all pans use 4A vapour except ZRA, which uses 3rd vapour. The DCS screens show **ZRA and A1–A3 on "4A.B" and B1, B2, C1, C2 on "3.B"** [S:Varna_all], [S:ZRA_prehlad], [S:C1_prehlad].
5. **TIC1602 meaning:** the question assumes heating-steam pressure; [ZOD] says the pressures are "inside the pan". The DCS trend labels **PIC1602** as "Podtlak" (in-pan vacuum), while C-pan steam-loop PVs (e.g. C2 −3.3 kPa) look like heating-chamber pressure. TIC vs PIC loops share number xx02. Treat the semantics as unresolved.
6. **Pan size:** [ZOD] "drawings for 60 t units" and [SCHEME] "3x60 t / 2x60 t", but the drawing title blocks say **500 q (50 t) charge** [DWG-V], [DWG-R]. [DWG-B] is a different ~220 m² / 200 m² vapour body. The nameplate gives 300 m², 70.8 m³ [P:1786375479250].
7. **Known context "ZRA seeds A and C pans":** largely **verified**:
   - ZRA = očkovací varostroj (LI1000) [ZOD]; A-seed pan 1x30 t [SCHEME]; Seed2 -> UC dosing in A1–A3 and C1/C2 recipes.
   - Nuance: [SCHEME] shows **C2 seeded from the C1 C-seed receiver**, and C1 has its own "varenie seedu" KP 1.30 recipe. So the C stage can use its own C-seed rather than (or as well as) ZRA seed.
   - B pans appear slurry-seeded directly (interp.).
   - ZRA is fed with standard syrup (purity 93.4 %) [S:ZRA_udaje].
   - Mastersizer Dv50 6.8 µm slurry and "Camera 100" are **not mentioned** in any file in my scope.
8. **Viscosity vs Brix:** the QI signal is labelled "Viskozita" (°) on overviews and "Hustota" on B1, its setpoints are in **Bx** with values up to 110 Bx (>100 is physically impossible for true Brix), yet [ZOD] says it "should directly represent Brix". Interp.: it is a consistency/density-derived index, not true Brix.
