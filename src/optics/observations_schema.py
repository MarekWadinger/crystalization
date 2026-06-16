"""Pydantic schema for video-sidecar annotation JSONs (v2.0).

Each sidecar lives next to its video with the same stem
(``datasets/<stem>.mp4`` ↔ ``datasets/<stem>.json``).

The shape is aligned with **ActivityNet** (segment-based temporal
localization) and **JAMS** (JSON Annotated Music Specification)
conventions:

* point-in-time events carry a single ``t`` (seconds since
  ``media.start_wallclock``);
* time intervals are ``segments`` with ``t_start`` / ``t_end``;
* machine-derived container facts live under ``media.probe``;
* operator-derived facts live at ``media`` top level (stem, anchor,
  timezone, note) and inside ``events`` / ``segments``.

Derived fields (``hms`` strings, frame indices) are **never stored** —
they are computable from ``t`` + ``media.probe.fps``. Helpers exposed
on the models compute them on demand for display.

Two entry points:

* :func:`load_validated(path)` — strict load; raises on inconsistency.
* :func:`recompute_and_write(path)` — re-derive ``t`` from
  ``wallclock`` and write back. Single button after operator edits a
  wallclock.

CLI::

    uv run python -m optics.observations_schema check "datasets/<stem>.json"
    uv run python -m optics.observations_schema fix   "datasets/<stem>.json"
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "2.0"


class Phase(str, Enum):
    """Canonical phase taxonomy for a sugar crystallization strike.

    Ordered to roughly follow the chronological sequence of one strike
    (cleaning → filling → … → discharge → empty → next-batch vacuum).
    Adding a phase is a code change on purpose: the taxonomy is process
    knowledge, not per-batch data.
    """

    cleaning = "cleaning"
    filling = "filling"
    filling_with_bubbles = "filling_with_bubbles"
    bubbles_appear = "bubbles_appear"
    bubbles_intensify = "bubbles_intensify"
    concentration = "concentration"
    stabilization_and_seeding = "stabilization_and_seeding"
    first_crystals_visible = "first_crystals_visible"
    boiling = "boiling"
    drying = "drying"
    aeration = "aeration"
    discharge = "discharge"
    discharge_release = "discharge_release"
    empty = "empty"
    new_batch_vacuum_pull = "new_batch_vacuum_pull"


PHASE_GLOSSES: dict[Phase, str] = {
    Phase.cleaning: "Sweetwater wash / line clearing before next charge.",
    Phase.filling: "Vessel charged with syrup; pre-graining concentration.",
    Phase.filling_with_bubbles: "Filling continues with bubble flux visible.",
    Phase.bubbles_appear: "First bubbles visible at camera as syrup heats.",
    Phase.bubbles_intensify: "Bubble flux peaks during pre-graining heat-up.",
    Phase.concentration: "Evaporation past saturation toward seeding point.",
    Phase.stabilization_and_seeding: (
        "Supersaturation stabilised; seed magma injected; steam restricted."
    ),
    Phase.first_crystals_visible: (
        "Seed crystals visible as small inclusions in the field of view."
    ),
    Phase.boiling: "Growth phase under controlled supersaturation (Slovak: navaranie).",
    Phase.drying: "Final concentration stage before discharge.",
    Phase.aeration: "Vacuum break / vessel aerated for discharge.",
    Phase.discharge: "Active emptying of finished massecuite.",
    Phase.discharge_release: "Massecuite released to centrifuge / receiver.",
    Phase.empty: "Vessel fully discharged; waiting for next batch.",
    Phase.new_batch_vacuum_pull: "Next batch begins; vacuum re-established.",
}


def _format_hms(total_s: float) -> str:
    """Format a non-negative second count as ``HH:MM:SS`` or ``HH:MM:SS.NNN``."""
    if total_s < 0:
        raise ValueError(f"_format_hms got negative seconds: {total_s}")
    total_ms = int(round(total_s * 1000))
    whole, ms = divmod(total_ms, 1000)
    h, rem = divmod(whole, 3600)
    m, s = divmod(rem, 60)
    base = f"{h:02d}:{m:02d}:{s:02d}"
    if ms == 0:
        return base
    return f"{base}.{ms:03d}"


class VideoProbe(BaseModel):
    """ffprobe-derived FACTS about the container (written by ``sidecar_init``)."""

    model_config = ConfigDict(extra="allow")

    container_format: str
    video_codec: str
    width: int
    height: int
    pix_fmt: str
    r_frame_rate: str
    avg_frame_rate: str
    fps: float
    duration_s: float
    bit_rate_bps: int | None = None
    has_audio: bool = False
    file_size_bytes: int | None = None
    probed_at: datetime
    probe_tool: str = "ffprobe"


class Media(BaseModel):
    """Media-file-level metadata (operator anchor + machine probe)."""

    model_config = ConfigDict(extra="allow")

    stem: str
    start_wallclock: datetime
    timezone: str
    note: str | None = None
    probe: VideoProbe | None = None

    @property
    def fps(self) -> float:
        """Frame rate — from ``probe.fps`` if probed, else 30.0 fallback."""
        return self.probe.fps if self.probe is not None else 30.0

    @property
    def duration_s(self) -> float | None:
        """Container duration in seconds (None if not probed)."""
        return self.probe.duration_s if self.probe is not None else None


class Event(BaseModel):
    """A point-in-time annotation on the media timeline.

    ``t`` is the canonical time coordinate (seconds since
    ``media.start_wallclock``) and matches JAMS / ActivityNet usage.
    ``wallclock`` is the operator's source of truth; ``t`` is derived
    and cross-checked by the validator.
    """

    model_config = ConfigDict(extra="allow")

    id: str
    t: float
    wallclock: datetime
    phase: Phase
    label: str
    label_en: str | None = None
    qualifier: str = "exact"
    subphase: str | None = None
    is_seeding: bool = False
    note: str | None = None

    def hms(self) -> str:
        """Render ``t`` as ``HH:MM:SS[.NNN]`` for display."""
        return _format_hms(self.t)

    def frame(self, fps: float) -> int:
        """Compute the integer frame index at ``fps``."""
        return int(round(self.t * fps))


class Segment(BaseModel):
    """A contiguous time interval with a single phase label (ActivityNet shape)."""

    model_config = ConfigDict(extra="allow")

    phase: Phase
    t_start: float
    t_end: float | None = None
    note: str | None = None

    def hms_start(self) -> str:
        """Render ``t_start`` as ``HH:MM:SS[.NNN]`` for display."""
        return _format_hms(self.t_start)

    def hms_end(self) -> str | None:
        """Render ``t_end`` as ``HH:MM:SS[.NNN]`` (None if open-ended)."""
        return _format_hms(self.t_end) if self.t_end is not None else None


class ObservationsFile(BaseModel):
    """Top-level operator-observations file with cross-field validation."""

    model_config = ConfigDict(extra="allow")

    schema_version: str = SCHEMA_VERSION
    media: Media
    events: list[Event] = Field(default_factory=list)
    segments: list[Segment] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    source_document: dict[str, Any] = Field(default_factory=dict)
    scada_legend: dict[str, Any] = Field(default_factory=dict)
    kpi_pairing_hint: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_consistency(self) -> ObservationsFile:
        errors: list[str] = []
        start = self.media.start_wallclock

        seen_ids: set[str] = set()
        for ev in self.events:
            if ev.id in seen_ids:
                errors.append(f"duplicate event id: {ev.id!r}")
            seen_ids.add(ev.id)

            expected_t = (ev.wallclock - start).total_seconds()
            if abs(ev.t - expected_t) > 1e-6:
                errors.append(
                    f"{ev.id}: t={ev.t} ≠ wallclock-derived {expected_t}"
                )

        prev_end: float = 0.0
        for seg in self.segments:
            if seg.t_start < prev_end:
                errors.append(
                    f"segment {seg.phase!r}: t_start={seg.t_start} "
                    f"overlaps previous segment ending at {prev_end}"
                )
            if seg.t_end is not None and seg.t_end < seg.t_start:
                errors.append(
                    f"segment {seg.phase!r}: t_end={seg.t_end} < "
                    f"t_start={seg.t_start}"
                )
            prev_end = seg.t_end if seg.t_end is not None else prev_end

        if errors:
            joined = "\n  - ".join(errors)
            raise ValueError(
                f"observation-file consistency errors:\n  - {joined}"
            )
        return self


def load_validated(path: str | Path) -> ObservationsFile:
    """Load and strictly validate a sidecar JSON."""
    return ObservationsFile.model_validate_json(Path(path).read_text())


def completeness_report(obs: ObservationsFile) -> list[str]:
    """Return human-readable list of next-step suggestions for a sidecar.

    A valid file can still be incomplete — e.g. no seeding event flagged,
    no segments at all, no events at all. This is the "what's next"
    feedback surfaced by the interactive wizard and the ``next`` CLI.
    """
    todo: list[str] = []
    if obs.media.start_wallclock.year < 2000:
        todo.append(
            "media.start_wallclock looks like a placeholder; "
            "confirm against DVR overlay at frame 0."
        )
    if not obs.events:
        todo.append("no events annotated yet — add at least one.")
    if obs.events and not any(e.is_seeding for e in obs.events):
        todo.append(
            "no seeding event flagged (is_seeding=True) — needed for "
            "time_since_seeding_s growth-curve calibration."
        )
    if not obs.segments:
        todo.append(
            "no phase segments yet — KPI snapshots cannot be tagged with a phase."
        )
    if obs.media.probe is None:
        todo.append(
            "media.probe missing — run "
            "`python -m optics.sidecar_init <video> --reprobe`."
        )
    return todo


def recompute_and_write(path: str | Path) -> list[str]:
    """Re-derive ``event.t`` from ``event.wallclock`` and write back.

    Returns the list of changes applied. Use after editing wallclocks:
    this is the "single button" that re-syncs the canonical ``t``
    coordinate.
    """
    path = Path(path)
    raw = json.loads(path.read_text())
    start = datetime.fromisoformat(raw["media"]["start_wallclock"])

    changes: list[str] = []
    for ev in raw.get("events", []):
        wc = datetime.fromisoformat(ev["wallclock"])
        t_f = (wc - start).total_seconds()
        new_t: float | int = int(t_f) if t_f == int(t_f) else t_f
        if ev.get("t") != new_t:
            changes.append(f"{ev['id']}.t: {ev.get('t')!r} → {new_t!r}")
            ev["t"] = new_t

    ObservationsFile.model_validate(raw)
    path.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n")
    return changes


def _cli(argv: list[str]) -> int:
    if not argv or argv[0] not in {"check", "fix", "next", "taxonomy"}:
        sys.stderr.write(
            "usage: python -m optics.observations_schema "
            "{check|fix|next} <path> [<path> ...]\n"
            "       python -m optics.observations_schema taxonomy\n"
        )
        return 2
    if argv[0] == "taxonomy":
        for p in Phase:
            print(f"  {p.value:32s}  {PHASE_GLOSSES[p]}")
        return 0
    cmd, *paths = argv
    if not paths:
        sys.stderr.write(f"{cmd}: requires at least one path\n")
        return 2
    rc = 0
    for path in paths:
        if cmd == "check":
            try:
                load_validated(path)
            except Exception as exc:
                sys.stderr.write(f"{path}: FAIL\n{exc}\n")
                rc = 1
                continue
            print(f"{path}: OK")
            continue
        if cmd == "next":
            obs = load_validated(path)
            todo = completeness_report(obs)
            if not todo:
                print(f"{path}: complete")
            else:
                print(f"{path}: what's next ({len(todo)})")
                for t in todo:
                    print(f"  - {t}")
            continue
        changes = recompute_and_write(path)
        if not changes:
            print(f"{path}: already consistent")
        else:
            print(f"{path}: applied {len(changes)} change(s):")
            for c in changes:
                print(f"  {c}")
    return rc


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
