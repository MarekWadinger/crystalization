# datasets/

One **sidecar JSON per recording**: `<video stem>.json`. The schema is in
`src/optics/observations_schema.py`, and the operator how-to is
`docs/operator_notes/sidecar_guide.md`. Validate with
`uv run optics-sidecar check "<file>.json"`. Large videos are not in git;
the table says where each one lives.

## Data availability

The CEP paper ([`papers/cep/`](../papers/cep/)) cites the archived
recordings, sidecars and code at Zenodo DOI `10.5281/zenodo.XXXXXXX`
(placeholder: not yet deposited). Until then, the table below says where
each recording lives.

## Recordings

| Sidecar | What it is | Video location |
|---|---|---|
| `2026-02-04 11-08-51.json` | Camera 100, end of one seed-pan strike (b1, level passes the glass 11:46:10) and one full strike (b2: seeding 12:30, level passes the glass 16:00:10). Canonical example. | Drive `sugar_plant/video/2026-02-04 11-08-51.mp4` |
| `2026-02-05 10-18-50.json`, `10-36-32`, `10-37-26` | Short Camera 100 clips (DVR screen recordings, 1080p). Recording date disputed, see below. | `.mp4` next to the sidecar |
| `Záznam 2026-03-10 183943.json` | Screen capture (2026-03-10) of a player showing the long PAL recording at t = 38.8 s | `.mp4` next to the sidecar |
| `microscope_annotations.csv` | All burned-in microscope measurements of the 2026-10-30 run, one row per line (AI transcription, see below) | here (force-added: `datasets/*` is git-ignored) |
| `2026-10-30 08-45-33.json` | Seed-pan lab run by A. Fedor: 2 strikes (seeding 11:30 and 15:22), lab samples and microscope photos | NAS `\\147.175.79.43\Public\Fedor\CrystalisationData\ZRA-2026-10-30\Videos\`: lossless FFV1 `.mkv` (123 GB) + H.264 30 GB and 9.2 GB. Also Drive `sugar_plant/Data2026/` (9.2 GB LQ) |

All recordings are from **the seed pan** (plant tag ZRA, *očkovací varostroj*):
slurry (*mikroočko*) goes in, and seed massecuite for the A pans comes out.
Sources: plant Q&A (ground truth) and A. Fedor, 2026-11-03. See `docs/sered/README.md`.

## Sidecar `2026-10-30 08-45-33.json`: extra blocks

The schema allows extra keys. This sidecar adds:
- **`samples`**: 21 samples. Each has its wallclock / `t`, the raw refractometer and polarimeter readings with dilution factors (from `ZRA.xlsx`), the operator log line (from `ZRA.docx`), and its microscope photos with the camera's own clock.
- **`lab_legend`**: the lab formulas. sacharizácia = refract × 2; polarizácia = polari × 2 (standard syrup) or × 4 (massecuite); purity = pol / sach × 100 (derived, not stored).
- **`photo_clock`**: the microscope camera (OptikaCam3) clock is wrong (date 2115). wallclock = camera_time + offset, with offset in **[10:14:57, 10:16:31]**. The bounds come from sample ordering: each photo is taken after its own sample and before the next one. The seeding pair is excluded. Result: ±47 s around the midpoint.
- **`kpi_pairing_hint`**: two seedings (b1-e03, b2-e02). `Observations.seeding_event` returns only the first, so `time_since_seeding_s` is wrong for batch 2.

Video start 08:45:33 comes from the filename. It is cross-checked by two video-time pairs in `ZRA.docx` (10:57 ↔ 2:12:00, 11:30 ↔ 2:44:00).

## Crystal-size ground truth on the seed pan (A. Fedor, 2026-10-30)

The measurements exist **only as green annotations burned into the microscope JPGs**: lines drawn in the microscope software, values in mm. They are in no spreadsheet; the `ZRA.xlsx` "čas mikroskop" column is empty. Photos are in NAS `…\ZRA-2026-10-30\Pictures\` and on Drive `sugar_plant/Data2026/`.

**All 54 photos carry annotations.** They were transcribed on 2026-11-03 into `microscope_annotations.csv`: 1061 crystal labels (1052 with a readable value) and 4 reference lines. Columns: photo, sample id and time (from the run sidecar), camera time and the photo wallclock at the midpoint of the `photo_clock` offset, kind (`crystal` or `scale`), value, raw text, reader (`AI`), confidence, photo note. 18 labels are `low` confidence because a line, another label or the image edge overprints them; 9 of those have no usable value (`value_mm` empty).

Sizes vs time since seeding (`uv run python scripts/microscope_summary.py`; seeding b1 11:29:33, b2 15:22:00 from the sidecar):

| Batch | Sample | min after seeding | n | min / median / max (µm) |
|---|---|---|---|---|
| – | `MICRO.jpg` (slurry reference) | – | 4 | 10 / 13 / 19 |
| b1 | 11:30 `PREDOCKOM` (before seeding) | 0 | 6 | 18 / 33 / 42 |
| b1 | 11:32 | 2 | 13 | 22 / 29 / 35 |
| b1 | 11:46 | 16 | 17 | 15 / 37 / 222 |
| b1 | 12:07 | 37 | 50 | 38 / 114 / 271 |
| b1 | 12:19 | 49 | 49 | 96 / 155 / 349 |
| b1 | 12:30 | 60 | 37 | 62 / 199 / 317 |
| b1 | 12:49 | 79 | 60 | 56 / 276 / 611 |
| b1 | 13:06 | 96 | 35 | 154 / 355 / 596 |
| b1 | 13:32 | 122 | 26 | 220 / 483 / 1137 |
| b1 | 14:10 | 160 | 38 | 193 / 486 / 929 |
| b1 | 14:20 | 170 | 51 | 189 / 452 / 995 |
| b2 | 15:22 (incl. 40× photo) | 0 | 20 | 2 / 10 / 23 |
| b2 | 15:33 | 11 | 68 | 15 / 37 / 69 |
| b2 | 15:52 | 30 | 50 | 22 / 103 / 218 |
| b2 | 16:14 | 52 | 130 | 44 / 170 / 471 |
| b2 | 16:31 | 69 | 121 | 40 / 209 / 628 |
| b2 | 16:58 | 96 | 109 | 87 / 225 / 808 |
| b2 | 17:48 | 146 | 103 | 117 / 299 / 695 |
| b2 | 18:04 (after tightening) | 162 | 65 | 101 / 399 / 961 |

The re-read agrees with the 4 photos read on 2026-11-02 (`MICRO` 10–19 µm, `POOCKU cca 1 MINUTA` 22–35 µm, 13 crystals, `13-32` 0.228–0.821 mm, 8 crystals, `POSUS-18-04` 0.306–0.743 mm, 7 crystals). Two corrections to the earlier table: the 11:32 sample is 2–2.5 min after the 11:29:33 seeding (filename "cca 1 minúta"), and the "~2 h after seeding" sample 13:32 is 122 min.

Caveats:
- Values were transcribed from the overlay text by an AI assistant (2026-11-03, one reading), not exported from the microscope software. A second, independent reading has not been done.
- The measurer is not named in any file (most likely A. Fedor: his folder and his run).
- The operator picked which crystals to measure and drew one chord each, so these are ranges and medians of chosen crystals, not distributions. Large single values (1.137 mm at 13:32, 0.995 mm at 14:20) may be agglomerates.
- The `PREDOCKOM` (before seeding) photo already shows 18–42 µm crystals. Why is open (residual footing, or spontaneous nucleation).
- b2 15:22: lines of 2–3 µm (15-23.jpg) are a few pixels long, below the optical resolution.
- Scale: `13-06-3.jpg` carries the field size, 2.867 × 2.137 mm over 2048 × 1536 px (1.40 µm/px horizontally, 1.39 vertically). The earlier "≈ 1.45 µm/px" for this objective was approximate. `MICRO.jpg` (0.318 mm) and `POOCKU` (0.386 mm, label overprinted) carry a horizontal reference line.

For comparison, the seed slurry measured by Mastersizer ("Zuckerslurry Se 2025-01-16") gives Dv10/Dv50/Dv90 1.56/6.81/18.5 µm and D[4;3] 8.7 µm: `docs/Granulometry_Zuckerslurry Se 2025-01-16 A.pdf`.

## Sidecar `2026-02-04 11-08-51.json`: notes

- Events come from the operator's **typed** phone note (`docs/operator_notes/Krystal_260204_161114.pdf`, pp. 1–2; not handwritten), pp. 2–3 are phone photos of the DeltaV trend.
- Matching SCADA (seed pan only, 30 s, 11:00–17:00, no level tag) is in Drive `sugar_plant/sered/data/Paulen_data.xlsx`.
- Timing anchors checked 2026-11-03 with `uv run --with openpyxl python scripts/check_anchors.py`:

| Event | Sidecar | Video (1 fps) | SCADA | Operator note |
|---|---|---|---|---|
| b1 agitator stop | – | ~11:44:43 | EI1004 < 1 A at 11:45:30 | – |
| b1-e00 level passes the glass | 11:46:10 | 11:46:10–11:46:16 | vented 11:46:00 | "okolo 11:48 vyprázdnenie" |
| b1-e01 picture static | 11:46:30 | 11:46:31 | viscosity probe uncovered 11:48:00 | – |
| b2-e01b vacuum | 11:50:52 | (event read from video) | PIC1003 < −30 kPa at 11:51:30 | – |
| b2-e06 seeding | 12:30:00 | – | steam valve cut at 12:31:30 | 12:30 |
| b2 agitator stop | – | ~15:59:28 | EI1004 < 1 A at 15:59:30 | – |
| b2-e10 level passes the glass | 16:00:10 | 16:00:10–16:00:23 | vented 16:00:00 | "15:59 vypúšťanie" |
| b2-e10b picture static | 16:00:30 | 16:00:29 | probe uncovered 16:02:00 | – |
| b2-e11 vacuum | 16:07:18 | – | PIC1003 < −30 kPa at 16:08:00 | 16:07 |

  So 11:46:10 and 16:00:10 are video-observed (the level falls past the window), not the operator's 11:48 / 15:59. The DVR clock agrees with the SCADA clock to about ±30 s.
- Fixed 2026-11-03: `kpi_pairing_hint` (`b2-e06`, offset 4880.5 s), the label copied into `b2-e01b`, the `uplne vyprazdnenie` label (not in the note), the typos `pb2-rve` and `eb2-10b`, the stale `b1-10b_pred` (now `b1-e10b_pred`, recomputed), segments re-aligned to the events (the pre-11:46 footage is the end of the previous strike, not "discharge"), and the stem.
- After `b2-e10b` (16:00:30) the camera sees drained glass. Annotation frames sampled from the old `discharge_release` segment (17420.5–17900.5 s) after 17510.5 s show no massecuite.

## Recording date of the 1080p clips

The clip sidecars put the `2026-02-05 *` clips on 2026-02-04 (operator statement, June 2026, commit 42aee0a). `uv run python scripts/check_clip_overlap.py` contradicts it:
- If it were true, clip `10-37-26` (live camera until DVR 11:09:06) would share ~28 s of frames with the PAL recording (from 11:08:39.5). SIFT matching finds at most 6 inliers per frame (no match) over PAL t = 0–150 s. The positive control, `Záznam 2026-03-10 183943`, matches the same PAL frames with ~950 inliers per frame.
- File birth times are 2026-02-05 (`10-18-50` 10:33:52, `10-37-26` 11:15:04, i.e. the recording ends), as in the filenames.
- PC-minus-DVR clock offset: 174 s for the clips, 11.5 s for the PAL recording.

If the clips are from 2026-02-05, no operator log or SCADA covers them, so their phase and time since seeding are unknown. The "≈2 h after seeding" of clip `10-36-32` was a batch-match prediction (b1 seeding 08:36:35 ⇒ 1 h 57 min). Even on 2026-02-04 the trend photo gives b1 seeding ≈ 08:49:30 ± 3 min (steam cut at 08:47:55 on the photo, −1.5 min photo bias measured on b2), i.e. 1 h 41 min–1 h 48 min. The date is kept in the sidecars until the author decides.

The DVR display scaling (PAL → 1080p) could therefore not be measured by registration. What remains is the geometry: pillarbox active columns 43–1881 (1838 px) over the full 1080 rows, i.e. sx = 2.553, sy = 1.875, sx/sy = 1.362 **if** the DVR shows the full 720 × 576 raster. The "CH01" text box (DVR-drawn in both outputs, so only indicative) is 65 × 21 px in PAL and 172 × 39 px in the clip.

The ratio 70/77.6 behind the batch match is an operator input whose measurement is not recorded (plausibly lengths of the b1 and b2 cycles on the trend photo, Krystal PDF p. 3).
