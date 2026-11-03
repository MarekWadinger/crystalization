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
| `2026-02-04 11-08-51.json` | Camera 100, full seed-pan strike (seeding 12:30, discharge 15:59). Canonical example. | Drive `sugar_plant/video/2026-02-04 11-08-51.mp4` |
| `2026-02-05 10-18-50.json`, `10-36-32`, `10-37-26` | Short Camera 100 clips (DVR screen recordings, 1080p) | `.mp4` next to the sidecar |
| `Záznam 2026-03-10 183943.json` | Screen capture of a clip | `.mp4` next to the sidecar |
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

| Photo | Moment | Annotated sizes | Scale line |
|---|---|---|---|
| `MICRO.jpg` | reference shot of the seed slurry (no sample time) | 10, 12, 14, 19 µm | 0.318 mm |
| `POOCKU cca 1 MINUTA.jpg` | ~1 min after seeding (sample 11:32) | 22–35 µm (13 crystals) | 0.386 mm |
| `13-32.jpg` | sample 13:32, ~2 h after seeding | 0.228–0.821 mm (8 crystals) | none |
| `POSUS-18-04.jpg` | after tightening, batch 2 (18:04) | 0.306–0.743 mm (7 crystals) | none |

Caveats:
- Values were transcribed from the overlay text by an AI assistant (2026-11-02), not exported from the microscope software.
- Only these 4 of 54 photos have been read; the others probably carry annotations too.
- The measurer is not named in any file (most likely A. Fedor: his folder and his run).
- The operator picked which crystals to measure, so these are ranges, not distributions.
- 10×/4× calibration consistency (≈ 0.57 vs ≈ 1.45 µm per displayed pixel, ratio ≈ 2.5) was checked approximately from pixel lengths.

For comparison, the seed slurry measured by Mastersizer ("Zuckerslurry Se 2025-01-16") gives Dv50 6.8 µm and D[4;3] 8.7 µm: `docs/Granulometry_Zuckerslurry Se 2025-01-16 A.pdf`.

## Sidecar `2026-02-04 11-08-51.json`: notes

- Events come from the operator's handwritten log (`docs/operator_notes/Krystal_260204_161114.pdf`).
- Size notes were corrected 2026-11-03: the earlier "~50 µm seed / A-product 500–800 µm" values were unsourced.
- Matching SCADA (seed pan only, 30 s, 11:00–17:00, no level tag) is in Drive `sugar_plant/sered/data/Paulen_data.xlsx`.
- Known issue: `kpi_pairing_hint.seeding_event_id` says `"e06"`, but the event id is `"b2-e06"`.
