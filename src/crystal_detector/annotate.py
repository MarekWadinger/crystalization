"""Team annotation of crystal frames: one folder per person, labels in git.

Annotator (after ``git clone`` + ``uv sync --group crystal-detector-gui``)::

    uv run crystal-detector-annotate patrik

opens the Cellpose GUI on your first unlabelled frame
(``annotations/patrik/<stage>/<video>_HHMMSS.png``; the first video's frames
are plain ``HHMMSS.png``) with the project's fine-tuned
checkpoint preselected under *user-trained models*. In the GUI: press
**run**, fix the outlines (Shift+click or right-click starts an
outline, move the cursor, click again to close; Ctrl+click on a crystal
deletes it; Cmd on macOS), **Ctrl+S** writes ``HHMMSS_seg.npy`` next to
the image, then **close the window** — the next frame opens by itself.
Closing without saving ends the session. Then commit the ``_seg.npy``
files and push.

``uv run crystal-detector-annotate patrik --review`` reopens your labelled
frames one by one (Cellpose loads the label next to the image) so you can
check and fix them; edits autosave.

Maintainer, once per video::

    uv run crystal-detector-annotate export VIDEO --who patrik,erika,marek,marian

samples ``--per-stage`` (default three) frames per crystal-bearing stage
segment per person (seeding → discharge; distinct timestamps, evenly spread
inside each segment) from the video's sidecar segments (``VIDEO.json`` next
to the video, else ``datasets/<stem>.json``). Frames of several videos share
the stage folders, told apart by the video prefix.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from .analyze import resolve_model
from .export_frames import crop, flat_field_correction

ROOT = Path(__file__).resolve().parents[2]
ANNOTATIONS = Path(__file__).resolve().parent / "annotations"
# stages in which crystals are present (seeding → discharge)
CRYSTAL_STAGES = (
    "stabilization_and_seeding",
    "boiling",
    "drying",
    "aeration",
    "discharge_release",
)
PER_PERSON = 3
FIRST_VIDEO = "2026-02-04 11-08-51"  # its frames predate the video prefix


def hhmmss(t: float) -> str:
    t = int(t)
    return f"{t // 3600:02d}{t % 3600 // 60:02d}{t % 60:02d}"


def frame_label(png: Path) -> str:
    """'boiling · 2026-10-30 08-45-33 @ 02:54:21' for an annotation frame."""
    t = png.stem[-6:]
    video = png.stem[:-7].replace("_", " ") or FIRST_VIDEO
    return f"{png.parent.name} · {video} @ {t[:2]}:{t[2:4]}:{t[4:]}"


def _sidecar(video: Path) -> Path:
    """``VIDEO.json`` next to the video, else ``datasets/<stem>.json``."""
    for p in (
        video.with_suffix(".json"),
        ROOT / "datasets" / f"{video.stem}.json",
    ):
        if p.exists():
            return p
    raise SystemExit(
        f"no sidecar for {video.name} (next to it or in datasets/)"
    )


def export(video: Path, who: list[str], per_stage: int = PER_PERSON) -> None:
    events = json.loads(_sidecar(video).read_text())
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise SystemExit(f"cannot open {video}")
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
    tag = video.stem.replace(" ", "_")  # tells videos apart in one folder
    for seg in events["segments"]:
        if seg["phase"] not in CRYSTAL_STAGES:
            continue
        t0, t1 = seg["t_start"], seg["t_end"] or duration
        width = (t1 - t0) / len(who)  # one slice of the stage per person
        for k, name in enumerate(who):
            folder = ANNOTATIONS / name / seg["phase"]
            folder.mkdir(parents=True, exist_ok=True)
            for j in range(per_stage):
                # sub-bin midpoints; j=1 equals the old one-frame sample
                t = round(t0 + (k + (j + 0.5) / per_stage) * width)
                png = folder / f"{tag}_{hhmmss(t)}.png"
                # first video's frames predate the tag: HHMMSS.png
                if png.exists() or (folder / f"{hhmmss(t)}.png").exists():
                    continue
                cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
                ok, frame = cap.read()
                if not ok:
                    print(f"  skip {png} (read failed)")
                    continue
                cv2.imwrite(str(png), flat_field_correction(crop(frame)))
        print(
            f"{seg['phase']:<28} {hhmmss(t0)}–{hhmmss(t1)}  {per_stage} frames each"
        )
    cap.release()


def _is_lfs_pointer(p: Path) -> bool:
    return p.stat().st_size < 300 and p.read_bytes().startswith(
        b"version https://git-lfs"
    )


def _label(png: Path) -> Path:
    return png.with_name(png.stem + "_seg.npy")


_TTY = sys.stdout.isatty()


def _c(code: str, t: str) -> str:
    return f"\033[{code}m{t}\033[0m" if _TTY else t


def _bold(t: str) -> str:
    return _c("1", t)


def _key(t: str) -> str:
    """Anything the user clicks or presses."""
    return _c("1;33", t)


def _ok(t: str) -> str:
    return _c("32", f"✔ {t}") if _TTY else f"OK  {t}"


def _bad(t: str) -> str:
    return _c("31", f"✘ {t}") if _TTY else f"!!  {t}"


MEDALS = ["🥇", "🥈", "🥉", "  "]


def scores() -> list[tuple[int, int, str]]:
    """(labelled, frames, name) per annotator, most labelled first."""
    return sorted(
        (
            (
                len(list(d.glob("*/*_seg.npy"))),
                len(list(d.glob("*/*.png"))),
                d.name,
            )
            for d in ANNOTATIONS.iterdir()
            if d.is_dir()
        ),
        reverse=True,
    )


def _leaderboard(current: str) -> None:
    medals = MEDALS
    print(_c("1;35", " leaderboard"))
    for rank, (done, total, who) in enumerate(scores()):
        bar = _c("32", "█" * done) + _c("90", "░" * (total - done))
        name = _c("1;33", f"{who:<8}") if who == current else f"{who:<8}"
        medal = medals[min(rank, 3)] if done else medals[3]
        print(f"  {medal} {name} {bar} {done}/{total}")


def _banner(name: str, png: Path, n_done: int, n_all: int, model: str) -> None:
    rule = _c("36", "═" * 64)
    print("\n" + rule)
    print(
        _c("1;36", f" {name} · frame {n_done + 1} of {n_all} · ")
        + _c("1;35", frame_label(png))
    )
    print(rule)
    k = _key  # every click / key / menu item in one style
    step = [_c("33", f"{i}.") for i in (1, 2, 3)]
    print(
        f" {step[0]} {k('user-trained models')} → {k('run')} ({k(model)} is preselected)"
    )
    print("    optional: pre-draws the crystal outlines for you to correct;")
    print("    skip it to draw everything yourself")
    print(
        f" {step[1]} fix outlines: {k('Shift+click')} starts, move, {k('Shift+click')} closes;"
    )
    print(
        f"    {k('Ctrl+click')} ({k('Cmd+click')} on Mac) deletes. Every edit autosaves."
    )
    print(
        f" {step[2]} wait for the green {_ok('saved')} line below, then {k('close the window')}"
    )
    print(
        f"    no green line? (you accepted the proposals untouched) press {k('Ctrl+S')} ({k('Cmd+S')})"
    )
    print(_c("36", "─" * 64))


def _ask_yes_no() -> bool:
    while True:
        try:
            answer = input(_bold("  your choice [y/n]: ")).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return False
        if answer in ("y", "n"):
            return answer == "y"
        print("  please type y or n")


def _write_empty_label(png: Path) -> None:
    """Zero-mask *_seg.npy in the GUI's own format (a negative sample)."""
    img = cv2.imread(str(png), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise SystemExit(_bad(f"cannot read {png}"))
    h, w = img.shape
    dat = {
        "masks": np.zeros((h, w), np.uint16),
        "outlines": np.zeros((h, w), np.uint16),
        "colors": np.zeros((0, 3), np.uint8),
        "ismanual": np.zeros(0, bool),
        "filename": str(png),
    }
    np.save(
        _label(png), np.asarray(dat, dtype=object)
    )  # same as GUI's dict save


def _stage_labels(folder: Path, name: str) -> str:
    """git-add the person's labels; return the commands left for them."""
    commit = f'git commit -m "data(crystal-detector): {name} annotations"'
    push = "git pull --rebase && git push"
    added = subprocess.run(
        ["git", "add", str(folder)], cwd=ROOT, capture_output=True
    )
    if added.returncode != 0:
        return f"  git add {folder.relative_to(ROOT)}\n  {commit}\n  {push}"
    return f"  {commit}\n  {push}"


def _frames(name: str) -> tuple[Path, list[Path]]:
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
    return folder, frames


def _prepare_model() -> Path:
    import contextlib
    import io as _io

    from cellpose import io as cp_io
    from cellpose import models as cp_models

    print(
        _c(
            "90",
            "preparing the fine-tuned model (1.2 GB download on first run)…",
        )
    )
    # Cellpose's add_model copies into ~/.cellpose/models but never creates
    # that folder, so on a machine where the GUI has not run yet the copy
    # fails and the model never reaches the "custom models" dropdown.
    model_dir = Path(cp_models.MODEL_DIR)
    model_dir.mkdir(parents=True, exist_ok=True)
    with contextlib.redirect_stdout(_io.StringIO()):
        model_path = resolve_model()
        cp_io.add_model(str(model_path))  # listed under "custom models"
    if not (model_dir / model_path.name).exists():
        raise SystemExit(_bad(f"could not register the model in {model_dir}"))
    print(_ok(f"{model_path.name} ready under user-trained models"))
    return model_path


def _open_gui(png: Path, progress: str = "") -> float | None:
    """Run the GUI on one frame; report autosaves live; return last save mtime."""
    env = {
        **os.environ,
        "QT_API": os.environ.get("QT_API", "pyqt6"),
        "CRYSTAL_PROGRESS": progress,  # shown in the window title
    }
    child = (
        "import sys; from crystal_detector import gui_filters; "
        "gui_filters.install(); from cellpose.gui import gui; "
        "gui.run(image=sys.argv[1])"
    )
    label = _label(png)
    before = label.stat().st_mtime if label.exists() else None
    proc = subprocess.Popen(
        [sys.executable, "-c", child, str(png)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    saved_at = before
    while proc.poll() is None:
        if label.exists() and label.stat().st_mtime != saved_at:
            verb = "saved" if saved_at is None else "saved again"
            saved_at = label.stat().st_mtime
            print(
                _ok(f"{verb} {label.name} — keep editing or close the window")
            )
        time.sleep(0.5)
    if proc.returncode != 0:
        log = Path.home() / ".cellpose" / "run.log"
        raise SystemExit(_bad(f"the GUI crashed — details in {log}"))
    return saved_at


def annotate(name: str) -> None:
    folder, frames = _frames(name)
    _leaderboard(name)
    model = _prepare_model().name
    while todo := [p for p in frames if not _label(p).exists()]:
        png = todo[0]
        _banner(name, png, len(frames) - len(todo), len(frames), model)
        progress = f"{len(frames) - len(todo) + 1}/{len(frames)}"
        if _open_gui(png, progress) is None:
            # Cellpose greys out Ctrl+S at zero masks, so an empty frame can
            # only be labelled from here.
            print(_bad("no label saved for this frame"))
            print(
                f"  {_c('1;32', 'y')} = there were no crystals: save an EMPTY label, next frame"
            )
            print(
                f"  {_c('1;31', 'n')} = stop for now (nothing lost, this frame comes up first next time)"
            )
            if not _ask_yes_no():
                print(
                    _c(
                        "36",
                        f"  stopped. To continue:  uv run crystal-detector-annotate {name}",
                    )
                )
                break
            _write_empty_label(png)
            print(_ok(f"saved empty {_label(png).name}"))
    done = sum(_label(p).exists() for p in frames)
    print("\n" + _c("36", "═" * 64))
    _leaderboard(name)
    if done == len(frames):
        print(_ok(_bold(f"all {done} frames labelled")))
    else:
        print(_bold(f" {done}/{len(frames)} labelled"))
    lines = _stage_labels(folder, name)
    staged = "git add" not in lines
    what = "staged for commit" if staged else "to add and commit"
    print(f" your labels are {what} — run:")
    print(_c("36", lines))
    print(
        _c(
            "90",
            f" to check them later:  uv run crystal-detector-annotate {name} --review",
        )
    )


def review(name: str) -> None:
    folder, frames = _frames(name)
    labelled = [p for p in frames if _label(p).exists()]
    if not labelled:
        raise SystemExit(_bad(f"{name} has no labels yet"))
    _prepare_model()  # keeps the custom model in the dropdown
    for i, png in enumerate(labelled):
        rule = _c("36", "═" * 64)
        print("\n" + rule)
        print(
            _c("1;36", f" review {name} · {i + 1} of {len(labelled)} · ")
            + _c("1;35", frame_label(png))
        )
        print(rule)
        n = int(np.load(_label(png), allow_pickle=True).item()["masks"].max())
        print(
            f" {n} crystals labelled — fix if needed (edits autosave), then close"
        )
        before = _label(png).stat().st_mtime
        _open_gui(png, f"review {i + 1}/{len(labelled)}")
        changed = _label(png).stat().st_mtime != before
        print(_ok("label updated") if changed else _c("90", " unchanged"))
        if i + 1 < len(labelled):
            try:
                if (
                    input(_bold("  Enter = next, q = quit: ")).strip().lower()
                    == "q"
                ):
                    break
            except (EOFError, KeyboardInterrupt):
                print()
                break
    lines = _stage_labels(folder, name)
    print("\n" + _c("36", "═" * 64))
    print(
        " changed labels are staged — run:"
        if "git add" not in lines
        else " run:"
    )
    print(_c("36", lines))


def main() -> None:
    ap = argparse.ArgumentParser(description="Annotate your crystal frames.")
    ap.add_argument("name", help="your folder under annotations/, or 'export'")
    ap.add_argument("video", nargs="?", type=Path, help="export only")
    ap.add_argument("--who", help="export only: comma-separated names")
    ap.add_argument(
        "--per-stage",
        type=int,
        default=PER_PERSON,
        help="export only: frames per person in each crystal stage",
    )
    ap.add_argument(
        "--review",
        action="store_true",
        help="reopen your labelled frames to check them",
    )
    a = ap.parse_args()
    if a.name == "export":
        if not (a.video and a.who):
            ap.error("export needs VIDEO and --who a,b,c")
        export(a.video, a.who.split(","), a.per_stage)
    elif a.review:
        review(a.name)
    else:
        annotate(a.name)


if __name__ == "__main__":
    sys.exit(main())
