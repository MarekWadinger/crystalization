"""Operator-observation loader for pairing video frames with process phases.

Each annotation file under ``docs/operator_notes/*.json`` documents
one strike's events (cleaning → filling → seeding → boiling → drying
→ discharge → next-batch-vacuum) with wallclock timestamps. The loader
converts these into video-frame indices given the video's start
wallclock + fps, and exposes phase lookup for any frame.

Used by:

* ``optics.kpi`` to tag each KPI snapshot with the active phase.
* The (planned) growth-curve self-calibration in ``docs/paper/
  manuscript.md`` §8 — needs ``time_since_seeding_s`` per frame.

Example::

    obs = Observations.from_json("docs/operator_notes/2026-02-04_observations.json")
    obs.phase_at_frame(150_000)
    # -> 'boiling'
    obs.time_since_seeding_s(frame_idx=180_000)
    # -> 1131.0  (s after the e06 graining event)
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
    wallclock_local: datetime
    video_offset_s: int
    video_frame_at_30fps: int
    phase: str
    label_sk: str
    label_en: str
    is_seeding_event: bool = False
    qualifier: str = "exact"
    subphase: str | None = None
    note: str | None = None


@dataclass(frozen=True, slots=True)
class PhaseWindow:
    """A contiguous time interval annotated with a single phase label."""

    phase: str
    from_s: int
    to_s: int | None  # None = open-ended (last window)
    note: str | None = None


@dataclass(frozen=True, slots=True)
class Observations:
    """Loaded operator-observation file with frame-aligned helpers."""

    source_path: Path
    video_start: datetime
    fps: float
    events: tuple[Event, ...]
    windows: tuple[PhaseWindow, ...]
    raw: dict[str, Any]

    @classmethod
    def from_json(cls, path: str | Path) -> Observations:
        """Load a ``docs/operator_notes/*.json`` annotation file."""
        path = Path(path)
        data = json.loads(path.read_text())
        video = data["video"]
        start = datetime.fromisoformat(video["start_wallclock_local"])
        fps = float(video.get("fps_assumed", 30.0))
        events = tuple(
            Event(
                id=e["id"],
                wallclock_local=datetime.fromisoformat(e["wallclock_local"]),
                video_offset_s=int(e["video_offset_s"]),
                video_frame_at_30fps=int(e["video_frame_at_30fps"]),
                phase=e["phase"],
                label_sk=e["label_sk"],
                label_en=e["label_en"],
                is_seeding_event=bool(e.get("is_seeding_event", False)),
                qualifier=e.get("qualifier", "exact"),
                subphase=e.get("subphase"),
                note=e.get("note"),
            )
            for e in data["events"]
        )
        windows = tuple(
            PhaseWindow(
                phase=w["phase"],
                from_s=int(w["from_s"]),
                to_s=int(w["to_s"]) if w.get("to_s") is not None else None,
                note=w.get("note"),
            )
            for w in data.get("derived_phase_windows", [])
        )
        return cls(
            source_path=path,
            video_start=start,
            fps=fps,
            events=events,
            windows=windows,
            raw=data,
        )

    def frame_to_offset_s(self, frame_idx: int) -> float:
        """Convert ``frame_idx`` (zero-based) to seconds since video start."""
        return frame_idx / self.fps

    def offset_s_to_frame(self, offset_s: float) -> int:
        """Convert seconds since video start to ``frame_idx``."""
        return int(round(offset_s * self.fps))

    def wallclock_at_frame(self, frame_idx: int) -> datetime:
        """Absolute wallclock at the given frame."""
        from datetime import timedelta

        return self.video_start + timedelta(
            seconds=self.frame_to_offset_s(frame_idx)
        )

    def phase_at_offset(self, offset_s: float) -> str | None:
        """Return the phase label active at ``offset_s`` (None if no window covers it)."""
        for w in self.windows:
            if offset_s < w.from_s:
                continue
            if w.to_s is None or offset_s < w.to_s:
                return w.phase
        return None

    def phase_at_frame(self, frame_idx: int) -> str | None:
        """Return the phase label active at ``frame_idx``."""
        return self.phase_at_offset(self.frame_to_offset_s(frame_idx))

    @property
    def seeding_event(self) -> Event | None:
        """The graining/seeding event, if annotated."""
        for e in self.events:
            if e.is_seeding_event:
                return e
        return None

    def time_since_seeding_s(
        self, *, frame_idx: int | None = None, offset_s: float | None = None
    ) -> float | None:
        """Seconds elapsed since the seeding event, or None if pre-seeding / no seeding annotated."""
        seed = self.seeding_event
        if seed is None:
            return None
        if offset_s is None and frame_idx is None:
            raise ValueError("Pass frame_idx or offset_s")
        if offset_s is None:
            assert frame_idx is not None
            offset_s = self.frame_to_offset_s(frame_idx)
        delta = offset_s - seed.video_offset_s
        if delta < 0:
            return None
        return delta
