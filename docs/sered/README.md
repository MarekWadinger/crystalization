# docs/sered/: Sereď sugar plant knowledge

What we know about the plant behind Camera 100 (Slovenské cukrovary
s.r.o., Sereď, AGRANA), where it comes from, and what is still open.
The `sered-plant-expert` agent (`.claude/agents/sered-plant-expert.md`)
answers from these files.

## Evidence hierarchy (use in this order)
1. **Plant Q&A, answered**: `Potrebné dáta a otázky - Zodpovedane.docx` (A. Fedor, 2026-08-12). **Ground truth.**
2. **Direct operator answers**: A. Fedor, 2026-11-03 (recorded below).
3. **Plant DCS screens and data**: DeltaV screenshots, SCADA/lab exports.
4. **Literature**: Bennár 2010 (Sereď thesis), the Gebler & Hotový glossary, kinetics papers.
5. General knowledge: say so explicitly, never present it as fact.

## Settled
- **Camera 100 is on the seed pan.** Plant tag **ZRA** = *očkovací varostroj*.
  - The DeltaV "Udaje ZRA" screen trends exactly our tags (LI1000, PIC1002, QI1003, TI1006, EI1004, S_ZRAVZORCE).
  - The Q&A calls LI1000 "level in the seed pan".
  - Fedor: "ZRA = očkovací varostroj".
- **Seed chain:** seed mills make slurry (*mikroočko*, "prach") → the seed pan grains and grows it → seed massecuite (*očkovacia cukrovina*, DCS "UC"; Czech *záděl* = magma) → seed1 → seed2 → dosed 15–17 % into **A1–A3**, where the product is boiled.
  - Fedor 2026-11-03 names the A pans only.
  - The Q&A says the C stage also starts from seed massecuite, without naming its source. The flow sheet shows C1 cooking its own C-seed.
- **10 µm is the seed, not the product.**
  - Mastersizer slurry: Dv50 6.8 µm.
  - On the seed pan, crystals grow to ~0.3–0.8 mm within one ~3–3.5 h strike (Fedor's microscope run; see `datasets/README.md`).
  - Sereď white sugar is MA 0.76–0.95 mm (Bennár 2010).
- **ZRA expansion:** no document spells it out. "ZR" matches *zrnič* (Czech for vacuum pan) and *zrnenie* (graining). In the paper it is defined once as the seed pan's control-system tag; "seed pan" is used everywhere else.

## Open
- **Camera body.** The installed body is **"ADEMCO VIDEO"** (Honeywell analog PAL CCD; rear panel matches the HCC334/484 family). Photos: Drive `sugar_plant/sered/photos/20260810_111738.jpg`, `20260810_111636.jpg` (rear), the same setup as `docs/lens/` (Feb 2026). "Hanwha HCB-6000" came only from the Polz price quote. **The 2.9 µm pixel pitch and the 1.66 µm/px built on it are unverified** until the model label is known (Marek is on it).
- C-pan seed source (C1 C-seed vs. seed-pan output).
- LI1000 level data for 2026 (promised by the plant); DVR / signal chain; focus distance.
- What `S_ZRAVZORCE/VISKOZITA` computes.

## Manuscript fixes in progress (separate session)
Based on wrong size assumptions, traced 2026-11-03:
- § 7 "crystals stay ≈ 9 µm" retraction.
- Detector area window 80–8000 px², tuned to a guessed ~52 µm.
- TVA 30 vessel from a generic brochure in § 3.5 / § 6.2.

Origins: commits d046215, f024dcb, 512f98e, 2d6d306. The "operator confirmation" stage claims in June had no written source and were replaced by plant citations.

## Files here
| File | Contents |
|---|---|
| `notes_plant_dcs_qa_photos.md` | Topology, per-pan DeltaV recipes and tags, Q&A answers in English, optics answers, site photos, pan drawings, contradictions |
| `notes_data_lab.md` | Data inventory (SCADA/lab files, time ranges, sampling), tag dictionary with typical ranges, lab formulas, KP and cooking-curve sheets, seed-pan strike statistics |
| `notes_literature_models.md` | Bennár 2010, growth kinetics, gPROMS model (generic A-pan benchmark, no crystal size), vision prior art, Yokogawa CI Server |

Every fact in the notes cites its source file. "(interp.)" marks an interpretation.

## Raw sources
- **Rado's shared Drive** "sugar_plant": https://drive.google.com/drive/u/0/folders/1nBOJFR5G2MS7YSo6OiXwsnwO2_CxY8OT. Locally via a My Drive shortcut: `~/Library/CloudStorage/GoogleDrive-<user>/My Drive/sugar_plant/`. Folders: `sered/` (Q&A, schemes, photos, data), `Data2026/`, `video/`, `papers/`, `gproms/`, `translated/`, `yokogawa/`.
- **Department NAS:** `smb://147.175.79.43/Public` → `Fedor/CrystalisationData/` (log in with a personal account).
- **Glossary of terms (English / Slovak):** the front matter of `papers/cep/manuscript.md`.
