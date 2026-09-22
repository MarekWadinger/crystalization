"""Team annotation of crystal frames: one folder per person, labels in git.

Annotator (after ``git clone`` + ``uv sync --group crystal-detector-gui``)::

    uv run crystal-detector-annotate patrik

opens the Cellpose GUI on your first unlabelled frame
(``annotations/patrik/<stage>/HHMMSS.png``) with the project's fine-tuned
checkpoint pre-registered under *custom models*. In the GUI: pick it and
press **run**, fix the outlines (Shift+click or right-click starts an
outline, move the cursor, click again to close; Ctrl+click on a crystal
deletes it; Cmd on macOS), **Ctrl+S** writes ``HHMMSS_seg.npy`` next to
the image, then **close the window** — the next frame opens by itself.
Closing without saving ends the session. Stages before seeding have no
crystals: delete every proposal and save the empty result — those are the
negatives. Then commit the ``_seg.npy`` files and push.

Maintainer, once::

    uv run crystal-detector-annotate export VIDEO --who patrik,erika,marek,marian

samples one frame per stage per person (distinct timestamps, evenly
spread inside each stage) from the video's ``.json`` sidecar segments.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import cv2

from .analyze import resolve_model
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


def _label(png: Path) -> Path:
    return png.with_name(png.stem + "_seg.npy")


NEGATIVE_STAGES = {"cleaning", "filling_with_bubbles", "concentration"}
_TTY = sys.stdout.isatty()


def _bold(t: str) -> str:
    return f"\033[1m{t}\033[0m" if _TTY else t


def _ok(t: str) -> str:
    return f"\033[32m✔ {t}\033[0m" if _TTY else f"OK  {t}"


def _bad(t: str) -> str:
    return f"\033[31m✘ {t}\033[0m" if _TTY else f"!!  {t}"


def _banner(name: str, png: Path, n_done: int, n_all: int, model: str) -> None:
    stage = png.parent.name
    t = png.stem
    print("\n" + "═" * 64)
    print(
        _bold(
            f" {name} · frame {n_done + 1} of {n_all} · {stage} · {t[:2]}:{t[2:4]}:{t[4:]}"
        )
    )
    print("═" * 64)
    print(f" 1. user-trained models → choose {_bold(model)} → run")
    if stage in NEGATIVE_STAGES:
        print(
            f" 2. {_bold('NO crystals in this stage')}: delete every proposal"
        )
    else:
        print(
            " 2. fix outlines: Shift+click starts, move, Shift+click closes;"
        )
        print("    Ctrl+click (Cmd on Mac) on a crystal deletes it")
    print(
        f" 3. {_bold('Ctrl+S / Cmd+S')} to save, then {_bold('close the window')}"
    )
    print("─" * 64)


def _git_lines(folder: Path, name: str) -> str:
    rel = folder.relative_to(ROOT)
    return (
        f"  git add {rel}\n"
        f'  git commit -m "data(crystal-detector): {name} annotations"\n'
        f"  git pull --rebase && git push"
    )


def annotate(name: str) -> None:
    folder = ANNOTATIONS / name
    frames = sorted(folder.glob("*/*.png"))
    if not frames:
        known = ", ".join(sorted(p.name for p in ANNOTATIONS.iterdir()))
        raise SystemExit(_bad(f"no frames for '{name}'. Known: {known}"))
    if any(_is_lfs_pointer(p) for p in frames):
        raise SystemExit(
            _bad("frames are Git LFS pointers, not images. Run once:")
            + "\n  git lfs install && git lfs pull"
        )
    import contextlib
    import io as _io

    from cellpose import io as cp_io

    print("preparing the fine-tuned model (1.2 GB download on first run)…")
    with contextlib.redirect_stdout(_io.StringIO()):
        model_path = resolve_model()
        cp_io.add_model(str(model_path))  # listed under "custom models"
    env = {**os.environ, "QT_API": os.environ.get("QT_API", "pyqt6")}
    child = (
        "import sys; from cellpose.gui import gui; gui.run(image=sys.argv[1])"
    )
    log = Path.home() / ".cellpose" / "run.log"
    while todo := [p for p in frames if not _label(p).exists()]:
        png = todo[0]
        _banner(
            name, png, len(frames) - len(todo), len(frames), model_path.name
        )
        proc = subprocess.run(
            [sys.executable, "-c", child, str(png)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if proc.returncode != 0:
            raise SystemExit(_bad(f"the GUI crashed — details in {log}"))
        if not _label(png).exists():
            print(_bad("window closed without saving — stopping here"))
            print(
                f"  rerun  uv run crystal-detector-annotate {name}  to continue"
            )
            break
        print(_ok(f"saved {_label(png).relative_to(ROOT)}"))
    done = sum(_label(p).exists() for p in frames)
    print("\n" + "═" * 64)
    if done == len(frames):
        print(_ok(_bold(f"all {done} frames labelled — now commit and push:")))
    else:
        print(
            _bold(f" {done}/{len(frames)} labelled")
            + " — commit what you have:"
        )
    print(_git_lines(folder, name))


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
