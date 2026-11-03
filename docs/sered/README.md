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
  - On the seed pan, the median of the operator-measured crystals is 29 µm 2 min after seeding, 114 µm at 37 min, 483 µm at 122 min and 452–486 µm at 160–170 min (Fedor's run 2026-10-30, all 54 photos: `datasets/microscope_annotations.csv`, `scripts/microscope_summary.py`; operator-picked crystals, AI-read).
  - Sereď white sugar is MA 0.76–0.95 mm (Bennár 2010).
- **ZRA expansion:** no document spells it out. "ZR" matches *zrnič* (Czech for vacuum pan) and *zrnenie* (graining). In the paper it is defined once as the seed pan's control-system tag; "seed pan" is used everywhere else.

## Timing of the 2026-02-04 recording (checked 2026-11-03)
- The DVR overlay clock agrees with the SCADA clock to about ±30 s (agitator stop and venting seen in both; `scripts/check_anchors.py`).
- The discharge anchors 11:46:10 and 16:00:10 are video-observed (level passes the glass). The operator note's "okolo 11:48" and "15:59" are coarser times of the same discharges.
- SCADA puts the b2 seeding steam cut at 12:31:30 (note: 12:30).
- The DeltaV trend photo (Krystal PDF p. 3) puts the previous strike's seeding at ~08:49:30 ± 3 min (interp.: the same steam-cut signature as b2).
- The 1080p clips `2026-02-05 *` are most likely from 2026-02-05, not 02-04: no shared frames with the PAL recording, and file birth times on 02-05 (`scripts/check_clip_overlap.py`). The operator statement of June 2026 says 02-04; the author decides. Details: `datasets/README.md`.

## Open
- **Camera body.** The installed body is **"ADEMCO VIDEO"**, an analog B/W PAL CCD box camera. Photos: Drive `sugar_plant/sered/photos/20260810_111738.jpg`, `20260810_111636.jpg` (rear), the same setup as `docs/lens/` (Feb 2026). The config candidate is the **Ademco ACM570E class** (1/3" CCD, 752 × 582 cells of 6.50 × 6.25 µm), alternative ACM380E class (500 × 582, 9.8 × 6.3 µm); an earlier note here matched the rear panel to the Honeywell HCC334/484 family. None is confirmed until the model sticker is read. "Hanwha HCB-6000" came only from the Polz price quote and is ruled out (colour CMOS, no DIP switches). The scale in use is per axis from the analog chain (1.464 × 1.913 µm per clip px, 3.92 × 3.59 µm per PAL sample; `docs/optics/scale_chain.md`); the old 2.9 µm pitch and 1.66 µm/px are retired.
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
- **Glossary of terms (English / Slovak):** `papers/cep/sections/appendix_glossary.tex`.
