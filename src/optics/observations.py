"""Operator-observation loader for pairing video frames with process phases.

Each annotation file is a sidecar JSON living **next to its video**
with the same stem — e.g. ``datasets/2026-02-04 11-08-51.mp4`` has
``datasets/2026-02-04 11-08-51.json`` beside it.

The on-disk schema (v2.0) follows ActivityNet/JAMS conventions:

* ``media.start_wallclock`` is the operator's anchor;
* every event carries a canonical ``t`` (seconds since
  ``media.start_wallclock``);
* time intervals are ``segments`` with ``t_start`` / ``t_end``.

This module exposes a lightweight dataclass loader (no pydantic
dependency in the hot path). Strict validation lives in
:mod:`optics.observations_schema`.

Used by:

* ``optics.kpi`` to tag each KPI snapshot with the active phase.
* The (planned) growth-curve self-calibration in
  ``papers/cep/sections/growth.tex`` — needs ``time_since_seeding_s`` per frame.

Example::

    obs = Observations.from_video("datasets/2026-02-04 11-08-51.mp4")
    obs.phase_at_frame(150_000)
    # -> 'boiling'
    obs.time_since_seeding_s(frame_idx=180_000)
    # -> 1131.0  (s after the seeding event)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class Event:
    """One operator-annotated event on the strike timeline."""

    id: str
    wallclock: datetime
    t: float
    phase: str
    label: str
    label_en: str | None = None
    is_seeding: bool = False
    qualifier: str = "exact"
    subphase: str | None = None
    note: str | None = None


@dataclass(frozen=True, slots=True)
class Segment:
    """A contiguous time interval annotated with a single phase label."""

    phase: str
    t_start: float
    t_end: float | None
    note: str | None = None


@dataclass(frozen=True, slots=True)
class Observations:
    """Loaded sidecar file with frame-aligned helpers."""

    source_path: Path
    start_wallclock: datetime
    fps: float
    events: tuple[Event, ...]
    segments: tuple[Segment, ...]
    raw: dict[str, Any]

    @classmethod
    def sidecar_path(cls, video_path: str | Path) -> Path:
        """Return the sidecar JSON path for a video (same stem, ``.json``)."""
        return Path(video_path).with_suffix(".json")

    @classmethod
    def from_video(cls, video_path: str | Path) -> Observations:
        """Load the sidecar JSON sitting next to ``video_path``."""
        return cls.from_json(cls.sidecar_path(video_path))

    @classmethod
    def from_json(cls, path: str | Path) -> Observations:
        """Load a v2.0 sidecar JSON."""
        path = Path(path)
        data = json.loads(path.read_text())
        media = data["media"]
        start = datetime.fromisoformat(media["start_wallclock"])
        probe = media.get("probe") or {}
        fps = float(probe.get("fps", 30.0))
        events = tuple(
            Event(
                id=e["id"],
                wallclock=datetime.fromisoformat(e["wallclock"]),
                t=float(e["t"]),
                phase=e["phase"],
                label=e["label"],
                label_en=e.get("label_en"),
                is_seeding=bool(e.get("is_seeding", False)),
                qualifier=e.get("qualifier", "exact"),
                subphase=e.get("subphase"),
                note=e.get("note"),
            )
            for e in data.get("events", [])
        )
        segments = tuple(
            Segment(
                phase=s["phase"],
                t_start=float(s["t_start"]),
                t_end=float(s["t_end"])
                if s.get("t_end") is not None
                else None,
                note=s.get("note"),
            )
            for s in data.get("segments", [])
        )
        return cls(
            source_path=path,
            start_wallclock=start,
            fps=fps,
            events=events,
            segments=segments,
            raw=data,
        )

    def frame_to_t(self, frame_idx: int) -> float:
        """Convert ``frame_idx`` (zero-based) to seconds since media start."""
        return frame_idx / self.fps

    def t_to_frame(self, t: float) -> int:
        """Convert seconds since media start to ``frame_idx``."""
        return int(round(t * self.fps))

    def wallclock_at_frame(self, frame_idx: int) -> datetime:
        """Absolute wallclock at the given frame."""
        from datetime import timedelta

        return self.start_wallclock + timedelta(
            seconds=self.frame_to_t(frame_idx)
        )

    def phase_at_t(self, t: float) -> str | None:
        """Return the phase label active at ``t`` seconds since media start."""
        for s in self.segments:
            if t < s.t_start:
                continue
            if s.t_end is None or t < s.t_end:
                return s.phase
        return None

    def phase_at_frame(self, frame_idx: int) -> str | None:
        """Return the phase label active at ``frame_idx``."""
        return self.phase_at_t(self.frame_to_t(frame_idx))

    @property
    def seeding_event(self) -> Event | None:
        """The graining/seeding event, if annotated."""
        for e in self.events:
            if e.is_seeding:
                return e
        return None

    def time_since_seeding_s(
        self, *, frame_idx: int | None = None, t: float | None = None
    ) -> float | None:
        """Seconds since the seeding event, or ``None`` if pre-seeding."""
        seed = self.seeding_event
        if seed is None:
            return None
        if t is None and frame_idx is None:
            raise ValueError("Pass frame_idx or t")
        if t is None:
            assert frame_idx is not None
            t = self.frame_to_t(frame_idx)
        delta = t - seed.t
        if delta < 0:
            return None
        return delta
