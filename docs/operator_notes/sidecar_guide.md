# Video Sidecar Annotation Guide

**Last Updated:** 2026-06-16
**Audience:** Plant operator — no Python knowledge required.
**Tool:** `uv run optics-sidecar`

A sidecar is a JSON file that lives next to a video file and holds your
observations about what happened during that strike. The pairing is by
filename: `datasets/2026-02-04 11-08-51.mp4` and
`datasets/2026-02-04 11-08-51.json` are the same strike seen two ways.

---

## When to create a sidecar

Create one for every new video before any analysis runs. Without a sidecar
the software cannot know which phase the camera is looking at, and crystal
growth curves cannot be computed relative to the seeding moment.

---

## The five commands you will use most

### 1. Start a new sidecar for a freshly downloaded video

```bash
uv run optics-sidecar wizard "datasets/2026-02-05 10-18-50.mp4"
```

The wizard asks you questions one at a time and writes the JSON when you
are done. Use this for any new video. Answer in the language shown (English
is fine for all fields).

### 2. Check that a sidecar is valid

```bash
uv run optics-sidecar check "datasets/2026-02-04 11-08-51.json"
```

Prints `OK` if valid, or a list of problems if not. This command also runs
automatically on every `git commit` that touches a sidecar — you cannot
commit a broken file.

### 3. Find out what is still missing

```bash
uv run optics-sidecar next "datasets/2026-02-04 11-08-51.json"
```

Prints "what's next" suggestions: no seeding event flagged, no segments
added, etc. Run this after the wizard to see what to fill in next.

### 4. Fix timestamps after editing a wallclock

```bash
uv run optics-sidecar fix "datasets/2026-02-04 11-08-51.json"
```

If you corrected a wallclock time by hand, run `fix` to recompute the
internal `t` field. Without this step the validator will reject the file.

### 5. See all recognised phase names

```bash
uv run optics-sidecar taxonomy
```

Prints every valid phase value with a one-line description. Copy-paste
values from this list when editing the JSON directly.

---

## End-to-end worked example

**Scenario:** you have just downloaded a new video to `datasets/`.

**Step 1 — Create the sidecar.**

```bash
uv run optics-sidecar wizard "datasets/2026-02-05 10-18-50.mp4"
```

The wizard runs ffprobe automatically, fills in the video dimensions and
frame rate, then asks you for:

- `start_wallclock` — the wall-clock time shown on the DVR display at
  frame 0. Read it off the video. Format: `2026-02-05T10:18:50`.
- `timezone` — e.g. `Europe/Bratislava`.
- An optional note about the strike.

After you answer, it writes `datasets/2026-02-05 10-18-50.json` and
prints the path.

**Step 2 — Add your first event.**

Open the JSON in any text editor. Find the `"events"` array. Add an entry:

```json
{
  "id": "e01",
  "phase": "cleaning",
  "label": "cistenie pred plnenim",
  "label_en": "cleaning before filling",
  "wallclock": "2026-02-05T10:19:15",
  "t": 25.0,
  "is_seeding": false,
  "qualifier": "exact"
}
```

The `t` field is seconds since `start_wallclock`. If you are not sure of
the exact value, just set `t` to any number and run:

```bash
uv run optics-sidecar fix "datasets/2026-02-05 10-18-50.json"
```

This recomputes `t` from your `wallclock` value automatically.

**Step 3 — Mark the seeding event.**

When you add the event where the seed was injected (slurry/mikroočko in the seed pan, seed massecuite in A/C pans), set `"is_seeding": true`.
This is required for the growth-curve analysis. Without it `next` will
remind you every time.

```json
{
  "id": "e05",
  "phase": "stabilization_and_seeding",
  "label": "zaockavanie",
  "label_en": "seeding",
  "wallclock": "2026-02-05T12:44:00",
  "t": 9070.0,
  "is_seeding": true,
  "qualifier": "exact"
}
```

**Step 4 — Add a segment.**

Segments cover a continuous time range with one phase label. They are used
to tag every KPI snapshot with the phase that was active. Find the
`"segments"` array and add:

```json
{
  "phase": "boiling",
  "t_start": 9070.0,
  "t_end": 14400.0,
  "note": "main growth phase"
}
```

`t_end` can be omitted (or set to `null`) for a segment that is still open.

**Step 5 — Validate and commit.**

```bash
uv run optics-sidecar check "datasets/2026-02-05 10-18-50.json"
uv run optics-sidecar next  "datasets/2026-02-05 10-18-50.json"
git add "datasets/2026-02-05 10-18-50.json"
git commit -m "feat(sidecar): annotate 2026-02-05 10-18-50 strike"
```

The pre-commit hook runs `check` automatically. If it fails it tells you
exactly which field is wrong.

---

## Phase taxonomy reference

Run `uv run optics-sidecar taxonomy` for the authoritative list. The table
below is for quick reference.

| Phase value | Slovak gloss | English gloss | When it happens |
|---|---|---|---|
| `cleaning` | Sladkovodné pranie | Sweetwater wash | Before the charge; clears the lines |
| `filling` | Plnenie | Filling | Vessel charged with syrup |
| `filling_with_bubbles` | Plnenie s bublinami | Filling with bubbles | Bubbles visible during charge |
| `bubbles_appear` | Prvé bubliny | First bubbles appear | Syrup heats up past boiling |
| `bubbles_intensify` | Bubliny zosilnejú | Bubble flux peaks | Pre-graining heat-up |
| `concentration` | Zahusteenie | Concentration | Evaporation past saturation |
| `stabilization_and_seeding` | Zaočkovanie | Seeding | Seed injected (slurry in seed pan, seed massecuite in A/C); steam cut back |
| `first_crystals_visible` | Prvé kryštály | First crystals visible | Seeds appear in camera view |
| `boiling` | Navaranie | Boiling / growth phase | Controlled supersaturation growth |
| `drying` | Sušenie | Drying | Final concentration before discharge |
| `aeration` | Prevzdušnenie | Aeration | Vacuum broken for discharge |
| `discharge` | Vypúšťanie | Discharge | Active emptying of massecuite |
| `discharge_release` | Uvoľnenie | Discharge release | Massecuite to centrifuge |
| `empty` | Prázdne | Empty | Vessel fully discharged |
| `new_batch_vacuum_pull` | Nová várka — vakuum | New batch vacuum pull | Vacuum re-established for next batch |

The `Phase` enum in `src/optics/observations_schema.py` is the single
source of truth. If a value is not in that list, the validator rejects it.

---

## Troubleshooting

### "observation-file consistency errors: t= ... != wallclock-derived ..."

You edited a `wallclock` field by hand but did not update `t`. Run:

```bash
uv run optics-sidecar fix "datasets/<stem>.json"
```

This recomputes every `t` from its `wallclock` automatically.

### "duplicate event id: ..."

Two events share the same `id` string. Each event must have a unique id
such as `"e01"`, `"e02"`, etc. Renumber one of them.

### "segment ... overlaps previous segment ending at ..."

A segment's `t_start` is earlier than the end of the previous segment.
Segments must not overlap. Check the `t_start` and `t_end` values and
close any gap or remove the overlap.

### "value is not a valid enumeration member" on `phase`

The phase value you typed is not in the taxonomy. Run:

```bash
uv run optics-sidecar taxonomy
```

Copy the exact string from the left column. Phase names are lowercase with
underscores and must match exactly.

### "media.probe missing — run ..."

The sidecar was created without an ffprobe pass, or the video was moved.
Run:

```bash
uv run optics-sidecar reprobe "datasets/<stem>.mp4"
```

This refreshes the probe block without touching your events or segments.

### Pre-commit hook blocks a commit

The hook runs `check` on every changed `datasets/*.json`. If check fails,
fix the problem (see above), then `git add` the file again and retry the
commit. The hook never modifies files — it only reports errors.

---

## FAQ

**Why a sidecar JSON next to the video?**
The video and its annotations stay together as a pair — you cannot move
one without the other going with it. The JSON is git-tracked even though
raw videos are not, so the annotations are in version control without
storing gigabytes of video.

**Why is fps not in the schema as a top-level field?**
Frame rate is a property of the video container, not of your observations.
It is stored under `media.probe.fps` (written by ffprobe) and treated as a
machine fact. If you need to display frame numbers, compute them from `t`
and `probe.fps`; never store computed frame indices in the JSON.

**What if I need a new phase?**
Adding a phase requires a one-line change to the `Phase` enum in
`src/optics/observations_schema.py`. It is intentionally a code change
rather than a config change, because each phase name is process knowledge
shared across all batches. Ask the researcher to add it — takes under five
minutes and goes through normal code review.

**Can I edit the JSON directly without the wizard?**
Yes. The JSON is plain text. Edit it in any editor, then run `check` to
confirm it is valid. Use `fix` after changing any `wallclock` value.

**Where is the canonical example?**
`datasets/2026-02-04 11-08-51.json` — the Sereď batch with 14 events and
11 segments. It passes `check` and reports `complete` under `next`.
