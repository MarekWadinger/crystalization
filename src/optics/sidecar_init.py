"""Generate a sidecar observations JSON for a video.

Probes the video with ``ffprobe`` and writes a template
``<stem>.json`` next to it, pre-filled with machine-derived facts
(codec, resolution, fps, duration, bitrate) under ``video.probe`` and
placeholders for operator-supplied fields (start wallclock, events).

The output is **schema-valid the moment it is written**: it round-trips
through ``ObservationsFile`` before being saved, so a freshly generated
sidecar will always pass the pre-commit validator.

CLI::

    uv run python -m optics.sidecar_init "datasets/2026-02-05 10-18-50.mp4"
    # → wrote: /abs/path/datasets/2026-02-05 10-18-50.json

    uv run python -m optics.sidecar_init "<video>" --interactive
    # → step-by-step wizard: anchor → events → segments → validate → "what's next"
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from optics.observations_schema import (
    PHASE_GLOSSES,
    Event,
    Media,
    ObservationsFile,
    Phase,
    Segment,
    VideoProbe,
    completeness_report,
)


def _ffprobe_json(video_path: Path) -> dict[str, Any]:
    """Run ``ffprobe -show_streams -show_format`` and return parsed JSON."""
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            str(video_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    out: dict[str, Any] = json.loads(proc.stdout)
    return out


def _parse_rational(s: str) -> float:
    """Parse ``"30/1"`` → 30.0; ``"0/0"`` → 0.0."""
    if "/" not in s:
        return float(s)
    num, den = s.split("/", 1)
    n, d = float(num), float(den)
    return n / d if d != 0 else 0.0


def probe_video(video_path: str | Path) -> VideoProbe:
    """Return a :class:`VideoProbe` for a video file."""
    video_path = Path(video_path)
    data = _ffprobe_json(video_path)
    streams = data["streams"]
    fmt = data["format"]

    vstreams = [s for s in streams if s.get("codec_type") == "video"]
    astreams = [s for s in streams if s.get("codec_type") == "audio"]
    if not vstreams:
        raise RuntimeError(f"No video stream found in {video_path}")
    v = vstreams[0]

    r_frame_rate = v.get("r_frame_rate", "0/0")
    avg_frame_rate = v.get("avg_frame_rate", r_frame_rate)
    return VideoProbe(
        container_format=fmt.get("format_name", "?"),
        video_codec=v["codec_name"],
        width=int(v["width"]),
        height=int(v["height"]),
        pix_fmt=v.get("pix_fmt", "?"),
        r_frame_rate=r_frame_rate,
        avg_frame_rate=avg_frame_rate,
        fps=_parse_rational(r_frame_rate),
        duration_s=float(fmt["duration"]),
        bit_rate_bps=int(fmt["bit_rate"]) if "bit_rate" in fmt else None,
        has_audio=bool(astreams),
        file_size_bytes=int(fmt["size"]) if "size" in fmt else None,
        probed_at=datetime.now(timezone.utc),
        probe_tool="ffprobe",
    )


_STEM_TIME_RE = re.compile(
    r"(?P<date>\d{4}-\d{2}-\d{2})[ _](?P<hh>\d{2})[-:](?P<mm>\d{2})[-:](?P<ss>\d{2})"
)


def _guess_start_wallclock(stem: str) -> datetime | None:
    """Try to parse ``YYYY-MM-DD HH-MM-SS`` from a filename stem."""
    m = _STEM_TIME_RE.search(stem)
    if not m:
        return None
    return datetime.fromisoformat(f"{m['date']}T{m['hh']}:{m['mm']}:{m['ss']}")


def build_template(
    video_path: str | Path, timezone_name: str = "Europe/Bratislava"
) -> ObservationsFile:
    """Construct a template :class:`ObservationsFile` for ``video_path``.

    Operator fields are seeded with reasonable guesses (start wallclock
    parsed from the filename stem if it looks like ``YYYY-MM-DD HH-MM-SS``)
    and must be confirmed by the operator before the sidecar is trusted.
    """
    video_path = Path(video_path)
    probe = probe_video(video_path)
    stem = video_path.stem
    guessed_start = _guess_start_wallclock(stem) or datetime(
        1970, 1, 1, 0, 0, 0
    )
    return ObservationsFile(
        media=Media(
            stem=stem,
            start_wallclock=guessed_start,
            timezone=timezone_name,
            note=(
                "TEMPLATE — confirm media.start_wallclock against DVR overlay "
                "(filename time may be off by seconds)."
            ),
            probe=probe,
        ),
        events=[],
    )


def write_template(video_path: str | Path, *, overwrite: bool = False) -> Path:
    """Write a sidecar JSON for ``video_path``; return the JSON path."""
    video_path = Path(video_path)
    sidecar = video_path.with_suffix(".json")
    if sidecar.exists() and not overwrite:
        raise FileExistsError(
            f"{sidecar} already exists (pass --overwrite to replace)"
        )
    obj = build_template(video_path)
    payload = obj.model_dump(mode="json", exclude_none=False)
    sidecar.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    )
    return sidecar


def reprobe_sidecar(video_path: str | Path) -> Path:
    """Refresh ONLY the ``video.probe`` block of an existing sidecar.

    Preserves every operator-edited field; rewrites the probe block from
    a fresh ``ffprobe`` run. Use when the underlying video file changes
    (re-export, re-mux, replacement file at the same path).
    """
    video_path = Path(video_path)
    sidecar = video_path.with_suffix(".json")
    raw = json.loads(sidecar.read_text())
    probe = probe_video(video_path)
    raw.setdefault("media", {})["probe"] = probe.model_dump(mode="json")
    ObservationsFile.model_validate(raw)
    sidecar.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n")
    return sidecar


def _prompt(label: str, default: str | None = None) -> str:
    """Prompt for a single line; return stripped input or default."""
    suffix = f" [{default}]" if default is not None else ""
    raw = input(f"  {label}{suffix}: ").strip()
    if not raw and default is not None:
        return default
    return raw


def _prompt_yes_no(label: str, *, default: bool = False) -> bool:
    """Prompt for yes/no; default applies on empty input."""
    d = "Y/n" if default else "y/N"
    raw = input(f"  {label} [{d}]: ").strip().lower()
    if not raw:
        return default
    return raw.startswith("y")


def _prompt_phase(label: str) -> Phase:
    """Prompt for a phase from the canonical taxonomy by index."""
    phases = list(Phase)
    print(f"  {label}:")
    for i, p in enumerate(phases):
        print(f"    [{i:2d}] {p.value:32s}  {PHASE_GLOSSES[p]}")
    while True:
        raw = input("    pick #: ").strip()
        try:
            idx = int(raw)
            return phases[idx]
        except (ValueError, IndexError):
            print(f"    ? invalid pick {raw!r} — enter 0..{len(phases) - 1}")


def _prompt_wallclock(label: str, start: datetime) -> datetime:
    """Prompt for an event wallclock.

    Accepts either full ISO (``2026-02-04T11:46:10``) or just ``HH:MM:SS[.NNN]``
    on the same date as ``start``.
    """
    while True:
        raw = input(f"  {label}: ").strip()
        try:
            if "T" in raw or len(raw) > 12:
                return datetime.fromisoformat(raw)
            return datetime.fromisoformat(f"{start.date().isoformat()}T{raw}")
        except ValueError as exc:
            print(f"    ? could not parse {raw!r}: {exc}")


def _interactive(video_path: Path, *, overwrite: bool) -> Path:
    """Step-by-step wizard: anchor → events → segments → validate."""
    sidecar = video_path.with_suffix(".json")
    if sidecar.exists() and not overwrite:
        raise FileExistsError(
            f"{sidecar} already exists (pass --overwrite to replace)"
        )
    template = build_template(video_path)
    probe = template.media.probe
    assert probe is not None

    print(f"\n=== Sidecar wizard for {video_path.name} ===")
    print(
        f"    probe: {probe.width}×{probe.height} {probe.video_codec} "
        f"@ {probe.fps:g}fps, {probe.duration_s:.1f}s\n"
    )

    print("[1/4] Media anchor")
    guessed = template.media.start_wallclock
    start_raw = _prompt("start_wallclock (ISO)", guessed.isoformat())
    start = datetime.fromisoformat(start_raw)
    tz = _prompt("timezone", template.media.timezone)
    note = _prompt("note (optional)", "")
    media = Media(
        stem=template.media.stem,
        start_wallclock=start,
        timezone=tz,
        note=note or None,
        probe=probe,
    )

    print("\n[2/4] Events (point-in-time annotations)")
    events: list[Event] = []
    while _prompt_yes_no("add event?", default=False):
        ev_id = _prompt("id (e.g. e00, seeding)", f"e{len(events):02d}")
        wc = _prompt_wallclock("wallclock", start)
        phase = _prompt_phase("phase")
        label = _prompt("label (source language, usually SK)", "")
        label_en = _prompt("label_en (optional)", "") or None
        is_seeding = _prompt_yes_no(
            "is this the seeding event?", default=False
        )
        ev_note = _prompt("note (optional)", "") or None
        events.append(
            Event(
                id=ev_id,
                t=(wc - start).total_seconds(),
                wallclock=wc,
                phase=phase,
                label=label,
                label_en=label_en,
                is_seeding=is_seeding,
                note=ev_note,
            )
        )
        print(f"    + {ev_id} @ t={events[-1].t:.1f}s  phase={phase.value}")

    print("\n[3/4] Segments (contiguous phase intervals)")
    segments: list[Segment] = []
    while _prompt_yes_no("add segment?", default=False):
        phase = _prompt_phase("phase")
        t_start = float(_prompt("t_start (seconds since media start)"))
        t_end_raw = _prompt("t_end (seconds, blank for open-ended)", "")
        t_end = float(t_end_raw) if t_end_raw else None
        seg_note = _prompt("note (optional)", "") or None
        segments.append(
            Segment(phase=phase, t_start=t_start, t_end=t_end, note=seg_note)
        )
        end_disp = f"{t_end:.1f}" if t_end is not None else "open"
        print(f"    + {phase.value}: {t_start:.1f}s → {end_disp}s")

    print("\n[4/4] Validating + writing…")
    obj = ObservationsFile(media=media, events=events, segments=segments)
    payload = obj.model_dump(mode="json", exclude_none=False)
    sidecar.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    )
    print(f"    ✓ wrote: {sidecar.resolve()}")

    todo = completeness_report(obj)
    if todo:
        print(f"\nWhat's next ({len(todo)}):")
        for t in todo:
            print(f"  - {t}")
    else:
        print("\nFile is complete. Run `make figs` to refresh KPI plots.")
    return sidecar


def _cli(argv: list[str]) -> int:
    overwrite = "--overwrite" in argv
    reprobe = "--reprobe" in argv
    interactive = "--interactive" in argv
    positional = [a for a in argv if not a.startswith("--")]
    if len(positional) != 1:
        sys.stderr.write(
            "usage: python -m optics.sidecar_init <video> "
            "[--overwrite] [--reprobe] [--interactive]\n"
        )
        return 2
    video = Path(positional[0])
    if not video.exists():
        sys.stderr.write(f"no such video: {video}\n")
        return 1
    if interactive:
        sidecar = _interactive(video, overwrite=overwrite)
    elif reprobe:
        sidecar = reprobe_sidecar(video)
    else:
        sidecar = write_template(video, overwrite=overwrite)
    print(f"\nopen:  file://{sidecar.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
