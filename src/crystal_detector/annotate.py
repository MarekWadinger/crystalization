"""Team annotation of crystal frames: one folder per person, labels in git.

Annotator (after ``git clone`` + ``uv sync --group crystal-detector-gui``)::

    uv run crystal-detector-annotate patrik

opens the Cellpose GUI on the first of your frames that has no label yet
(``annotations/patrik/<stage>/HHMMSS.png``). In the GUI: **run cpsam**,
fix the outlines (right-drag draws, Ctrl+right-click deletes), **Ctrl+S**
writes ``HHMMSS_seg.npy`` next to the image, then **File → Load image**
for the next one. Stages before seeding have no crystals: delete every
proposal and save the empty result — those are the negatives. Then commit
the ``_seg.npy`` files and push.

Maintainer, once::

    uv run crystal-detector-annotate export VIDEO --who patrik,erika,marek,marian

samples one frame per stage per person (distinct timestamps, evenly
spread inside each stage) from the video's ``.json`` sidecar segments.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import cv2

from .export_frames import crop, flat_field_correction

ROOT = Path(__file__).resolve().parents[2]
ANNOTATIONS = Path(__file__).resolve().parent / "annotations"
SKIP_STAGES = {"discharge", "empty"}  # pre-recording tail / 34 s window


def hhmmss(t: float) -> str:
    t = int(t)
    return f"{t // 3600:02d}{t % 3600 // 60:02d}{t % 60:02d}"


def export(video: Path, who: list[str]) -> None:
    events = json.loads(video.with_suffix(".json").read_text())
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise SystemExit(f"cannot open {video}")
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
    for seg in events["segments"]:
        if seg["phase"] in SKIP_STAGES:
            continue
        t0, t1 = seg["t_start"], seg["t_end"] or duration
        width = (t1 - t0) / len(who)
        for k, name in enumerate(who):
            t = round(t0 + (k + 0.5) * width)  # whole s: name reproduces seek
            folder = ANNOTATIONS / name / seg["phase"]
            folder.mkdir(parents=True, exist_ok=True)
            png = folder / f"{hhmmss(t)}.png"
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ok, frame = cap.read()
            if not ok:
                print(f"  skip {png} (read failed)")
                continue
            cv2.imwrite(str(png), flat_field_correction(crop(frame)))
        print(f"{seg['phase']:<28} {hhmmss(t0)}–{hhmmss(t1)}  1 frame each")
    cap.release()


def _is_lfs_pointer(p: Path) -> bool:
    return p.stat().st_size < 300 and p.read_bytes().startswith(
        b"version https://git-lfs"
    )


def annotate(name: str) -> None:
    folder = ANNOTATIONS / name
    frames = sorted(folder.glob("*/*.png"))
    if not frames:
        known = ", ".join(sorted(p.name for p in ANNOTATIONS.iterdir()))
        raise SystemExit(f"no frames for '{name}'. Known: {known}")
    if any(_is_lfs_pointer(p) for p in frames):
        raise SystemExit(
            "frames are Git LFS pointers, not images. Run once:\n"
            "  git lfs install && git lfs pull"
        )
    todo = [p for p in frames if not p.with_name(p.stem + "_seg.npy").exists()]
    print(f"{name}: {len(frames) - len(todo)}/{len(frames)} labelled")
    if not todo:
        print("all done — commit and push:")
    else:
        os.environ.setdefault("QT_API", "pyqt6")  # before cellpose import
        from cellpose.gui import gui

        print(f"opening {todo[0].relative_to(ROOT)} — Ctrl+S saves the label")
        gui.run(image=str(todo[0]))
        done = sum(p.with_name(p.stem + "_seg.npy").exists() for p in frames)
        print(f"\n{name}: {done}/{len(frames)} labelled. Commit and push:")
    rel = folder.relative_to(ROOT)
    print(
        f"  git add {rel}\n"
        f'  git commit -m "data(crystal-detector): {name} annotations"\n'
        f"  git push"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Annotate your crystal frames.")
    ap.add_argument("name", help="your folder under annotations/, or 'export'")
    ap.add_argument("video", nargs="?", type=Path, help="export only")
    ap.add_argument("--who", help="export only: comma-separated names")
    a = ap.parse_args()
    if a.name == "export":
        if not (a.video and a.who):
            ap.error("export needs VIDEO and --who a,b,c")
        export(a.video, a.who.split(","))
    else:
        annotate(a.name)


if __name__ == "__main__":
    sys.exit(main())
