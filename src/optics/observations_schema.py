"""Pydantic schema for ``docs/operator_notes/*.json`` annotation files.

The original ``Observations`` dataclass in :mod:`optics.observations` is a
loader without validation. This module adds a Pydantic v2 schema that
**enforces internal consistency**: the redundant fields
``video_offset_s``, ``video_offset_hms`` and ``video_frame_at_30fps`` must
all be derivable from the single source of truth ``wallclock_local`` and
the file-level ``start_wallclock_local`` + ``fps_assumed``. The
``derived_phase_windows`` chain must be monotone and reference real event
ids. Loading a stale file raises ``ValidationError`` listing every
mismatch.

Two entry points:

* :func:`load_validated(path)` — strict load; raises if anything is
  inconsistent. Use this from production code paths.
* :func:`recompute_and_write(path)` — derive ``video_offset_s``,
  ``video_offset_hms``, ``video_frame_at_30fps`` from ``wallclock_local``
  (the only field the operator hand-edits) and write the file back. Use
  this after editing wallclocks so the rest stays in sync — no more
  manual arithmetic.

CLI::

    uv run python -m optics.observations_schema check docs/.../foo.json
    uv run python -m optics.observations_schema fix   docs/.../foo.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _format_hms(total_s: float) -> str:
    """Format a non-negative second count as ``HH:MM:SS`` or ``HH:MM:SS.NNN``.

    If ``total_s`` is integer-valued, the millisecond suffix is omitted;
    otherwise three decimal places are emitted.
    """
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


class VideoMeta(BaseModel):
    """File-level video metadata."""

    model_config = ConfigDict(extra="allow")

    filename_stub: str
    start_wallclock_local: datetime
    timezone: str
    fps_assumed: float
    duration_s: float | None = None
    duration_source: str | None = None
    note: str | None = None


class Event(BaseModel):
    """One operator-annotated event on the strike timeline."""

    model_config = ConfigDict(extra="allow")

    id: str
    wallclock_local: datetime
    video_offset_s: float
    video_offset_hms: str
    video_frame_at_30fps: int
    phase: str
    label_sk: str = ""
    label_en: str = ""
    qualifier: str = "exact"
    subphase: str | None = None
    is_seeding_event: bool = False
    note: str | None = None


class PhaseWindow(BaseModel):
    """A contiguous time interval annotated with a single phase label."""

    model_config = ConfigDict(extra="allow")

    phase: str
    from_s: float
    to_s: float | None = None
    from_hms: str
    to_hms: str | None = None
    duration_min: int | None = None
    note: str | None = None


class ObservationsFile(BaseModel):
    """Top-level operator-observations file with cross-field validation."""

    model_config = ConfigDict(extra="allow")

    schema_version: str = "1.0"
    video: VideoMeta
    source_document: dict[str, Any] = Field(default_factory=dict)
    process_context: dict[str, Any] = Field(default_factory=dict)
    phase_taxonomy: dict[str, str] = Field(default_factory=dict)
    scada_parameter_legend: dict[str, Any] = Field(default_factory=dict)
    events: list[Event]
    derived_phase_windows: list[PhaseWindow] = Field(default_factory=list)
    kpi_pairing_hint: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_consistency(self) -> ObservationsFile:
        errors: list[str] = []
        start = self.video.start_wallclock_local
        fps = self.video.fps_assumed

        seen_ids: set[str] = set()
        for ev in self.events:
            if ev.id in seen_ids:
                errors.append(f"duplicate event id: {ev.id!r}")
            seen_ids.add(ev.id)

            expected_offset = (ev.wallclock_local - start).total_seconds()
            if abs(ev.video_offset_s - expected_offset) > 1e-6:
                errors.append(
                    f"{ev.id}: video_offset_s={ev.video_offset_s} "
                    f"≠ wallclock-derived {expected_offset}"
                )

            expected_hms = _format_hms(expected_offset)
            if ev.video_offset_hms != expected_hms:
                errors.append(
                    f"{ev.id}: video_offset_hms={ev.video_offset_hms!r} "
                    f"≠ derived {expected_hms!r}"
                )

            expected_frame = int(round(expected_offset * fps))
            if ev.video_frame_at_30fps != expected_frame:
                errors.append(
                    f"{ev.id}: video_frame_at_30fps={ev.video_frame_at_30fps} "
                    f"≠ derived {expected_frame} (offset {expected_offset}s × {fps} fps)"
                )

        prev_to: float = 0.0
        for win in self.derived_phase_windows:
            if win.from_s < prev_to:
                errors.append(
                    f"window {win.phase!r}: from_s={win.from_s} "
                    f"overlaps previous window ending at {prev_to}"
                )
            if win.to_s is not None and win.to_s < win.from_s:
                errors.append(
                    f"window {win.phase!r}: to_s={win.to_s} < from_s={win.from_s}"
                )
            if win.from_hms != _format_hms(win.from_s):
                errors.append(
                    f"window {win.phase!r}: from_hms={win.from_hms!r} "
                    f"≠ derived {_format_hms(win.from_s)!r}"
                )
            if win.to_s is not None and win.to_hms != _format_hms(win.to_s):
                errors.append(
                    f"window {win.phase!r}: to_hms={win.to_hms!r} "
                    f"≠ derived {_format_hms(win.to_s)!r}"
                )
            prev_to = win.to_s if win.to_s is not None else prev_to

        if errors:
            joined = "\n  - ".join(errors)
            raise ValueError(
                f"observation-file consistency errors:\n  - {joined}"
            )
        return self


def load_validated(path: str | Path) -> ObservationsFile:
    """Load and strictly validate an observations file."""
    return ObservationsFile.model_validate_json(Path(path).read_text())


def recompute_and_write(path: str | Path) -> list[str]:
    """Recompute every derived field from ``wallclock_local`` and write back.

    Returns the list of changes applied (event ids and field names). Use
    after editing wallclocks: this is the "single button" that re-syncs
    ``video_offset_s``, ``video_offset_hms`` and ``video_frame_at_30fps``
    so no manual arithmetic is required.

    Window timestamps (``from_s``/``to_s`` and their hms strings) are
    *not* auto-recomputed because windows can encode operator-chosen
    boundaries that don't coincide with any single event; their consistency
    is still checked on the way out.
    """
    path = Path(path)
    raw = json.loads(path.read_text())
    start = datetime.fromisoformat(raw["video"]["start_wallclock_local"])
    fps = float(raw["video"].get("fps_assumed", 30.0))

    changes: list[str] = []
    for ev in raw["events"]:
        wc = datetime.fromisoformat(ev["wallclock_local"])
        offset_s_f = (wc - start).total_seconds()
        offset_s: float | int = (
            int(offset_s_f) if offset_s_f == int(offset_s_f) else offset_s_f
        )
        hms = _format_hms(offset_s_f)
        frame = int(round(offset_s_f * fps))
        for key, new in (
            ("video_offset_s", offset_s),
            ("video_offset_hms", hms),
            ("video_frame_at_30fps", frame),
        ):
            if ev.get(key) != new:
                changes.append(f"{ev['id']}.{key}: {ev.get(key)!r} → {new!r}")
                ev[key] = new

    for win in raw.get("derived_phase_windows", []):
        derived_from_hms = _format_hms(float(win["from_s"]))
        if win.get("from_hms") != derived_from_hms:
            changes.append(
                f"window[{win['phase']}].from_hms: "
                f"{win.get('from_hms')!r} → {derived_from_hms!r}"
            )
            win["from_hms"] = derived_from_hms
        if win.get("to_s") is not None:
            derived_to_hms = _format_hms(float(win["to_s"]))
            if win.get("to_hms") != derived_to_hms:
                changes.append(
                    f"window[{win['phase']}].to_hms: "
                    f"{win.get('to_hms')!r} → {derived_to_hms!r}"
                )
                win["to_hms"] = derived_to_hms

    ObservationsFile.model_validate(raw)

    path.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n")
    return changes


def _cli(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] not in {"check", "fix"}:
        sys.stderr.write(
            "usage: python -m optics.observations_schema {check|fix} <path>\n"
        )
        return 2
    cmd, path = argv
    if cmd == "check":
        try:
            load_validated(path)
        except Exception as exc:
            sys.stderr.write(f"{exc}\n")
            return 1
        print(f"{path}: OK")
        return 0
    changes = recompute_and_write(path)
    if not changes:
        print(f"{path}: already consistent")
    else:
        print(f"{path}: applied {len(changes)} change(s):")
        for c in changes:
            print(f"  {c}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
