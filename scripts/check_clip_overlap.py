"""Test whether a 1080p DVR clip overlaps the long PAL recording.

The clips ``datasets/2026-02-05 *.mp4`` are screen recordings of the DVR's
display; their sidecars put them on 2026-02-04 (an operator statement from
June 2026, commit 42aee0a). If that is true, the end of clip
``10-37-26`` (DVR clock 10:34:32 + 2256 s) overlaps the start of the long
PAL recording (DVR clock 11:08:39.5), and the same camera frames appear in
both. The script

1. finds where the clip carries live camera signal after the nominal
   overlap start (the DVR's blue "No Signal" screen and black frames are
   excluded);
2. matches SIFT features of clip frames in that window against PAL frames
   over ``--pal-span`` s and counts RANSAC affine inliers (a same-frame
   pair gives hundreds; unrelated frames give < 10);
3. runs the same matcher on a positive control: the screen capture
   ``Záznam 2026-03-10 183943.mp4`` against the same PAL frames;
4. for every pair with >= ``--min-inliers`` inliers, reports the frame lag
   and the fitted affine PAL pixel -> video pixel (``sx, sy, tx, ty``,
   OpenCV ``estimateAffine2D``, pixel centres at integer coordinates);
5. reports the clip's pillarbox (active columns) and the "CH01" DVR text
   box in both videos, the geometry that remains when no pair matches.

Usage::

    uv run python scripts/check_clip_overlap.py --out /tmp/overlap.json

The PAL path defaults to the Google Drive location in
``datasets/README.md``. Output is JSON on stdout (and ``--out``).
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "datasets"
PAL_DEFAULT = (
    Path.home()
    / "Library/CloudStorage/GoogleDrive-marek.wadinger@stuba.sk"
    / "My Drive/sugar_plant/video/2026-02-04 11-08-51.mp4"
)
CLIP_DEFAULT = DATA / "2026-02-05 10-37-26.mp4"
CONTROL_DEFAULT = DATA / "Záznam 2026-03-10 183943.mp4"
PAL_SIDECAR = DATA / "2026-02-04 11-08-51.json"
PAL_W, PAL_H = 720, 576
FPS = 30.0
# PAL regions carrying DVR text (date/clock at the top, "CH01" at the
# bottom); they differ between videos and are masked out.
TEXT_BOXES = ((0, 0, PAL_W, 44), (200, 490, 520, 560))


def _start(sidecar: Path) -> datetime:
    meta = json.loads(sidecar.read_text())["media"]
    return datetime.fromisoformat(meta["start_wallclock"])


def _probe(path: Path) -> tuple[int, int]:
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path),
    ]  # fmt: skip
    out = subprocess.run(cmd, check=True, capture_output=True, text=True)
    w, h = (int(v) for v in out.stdout.strip().split(",")[:2])
    return w, h


def _stream(
    path: Path, t0: float, dur: float, fps: float | None = None
) -> Iterator[tuple[float, np.ndarray]]:
    """Yield ``(t, gray frame)`` from ``t0`` for ``dur`` s.

    ``-ss`` before ``-i`` with re-encoding is frame-accurate in ffmpeg;
    ``t`` is the video time of each frame at the nominal frame rate.
    """
    w, h = _probe(path)
    vf = ["-vf", f"fps={fps}"] if fps else []
    cmd = [
        "ffmpeg", "-loglevel", "error", "-ss", f"{t0:.4f}", "-i", str(path),
        "-t", f"{dur:.4f}", *vf, "-f", "rawvideo", "-pix_fmt", "gray", "-",
    ]  # fmt: skip
    step = 1.0 / (fps or FPS)
    with subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    ) as proc:
        assert proc.stdout is not None
        n = 0
        while len(buf := proc.stdout.read(w * h)) == w * h:
            yield t0 + n * step, np.frombuffer(buf, np.uint8).reshape(h, w)
            n += 1


def _live(frame: np.ndarray) -> bool:
    """Camera picture, not the DVR's black or blue 'No Signal' screen."""
    core = frame[frame.shape[0] // 4 : -frame.shape[0] // 4]
    return float(core.mean()) > 40.0 and float(core.std()) > 8.0


def _pal_mask() -> np.ndarray:
    m = np.full((PAL_H, PAL_W), 255, np.uint8)
    for x0, y0, x1, y1 in TEXT_BOXES:
        m[y0:y1, x0:x1] = 0
    return m


class Matcher:
    """SIFT + ratio test + RANSAC affine, PAL frame -> other frame."""

    def __init__(self, pal: list[tuple[float, np.ndarray]]) -> None:
        self.sift = cv2.SIFT_create(3000)  # ty: ignore[unresolved-attribute]
        self.bf = cv2.BFMatcher()
        mask = _pal_mask()
        self.pal = [(t, *self.sift.detectAndCompute(f, mask)) for t, f in pal]

    def best(self, frame: np.ndarray, half: bool = True) -> dict:
        s = 0.5 if half else 1.0
        img = cv2.resize(frame, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        m = np.full(img.shape, 255, np.uint8)  # drop top/bottom text bands
        m[: int(0.06 * img.shape[0])] = 0
        m[int(0.86 * img.shape[0]) :] = 0
        kp2, d2 = self.sift.detectAndCompute(img, m)
        out = {"inliers": 0}
        if d2 is None:
            return out
        for t, kp1, d1 in self.pal:
            if d1 is None:
                continue
            pairs = self.bf.knnMatch(d1, d2, k=2)
            good = [a for a, b in pairs if a.distance < 0.75 * b.distance]
            if len(good) < 6:
                continue
            src = np.array([kp1[g.queryIdx].pt for g in good], np.float32)
            dst = np.array([kp2[g.trainIdx].pt for g in good], np.float32) / s
            a, inl = cv2.estimateAffine2D(src, dst, ransacReprojThreshold=4)
            if a is not None and int(inl.sum()) > out["inliers"]:
                out = {
                    "inliers": int(inl.sum()),
                    "pal_t": round(t, 3),
                    "sx": round(float(a[0, 0]), 4),
                    "sy": round(float(a[1, 1]), 4),
                    "tx": round(float(a[0, 2]), 2),
                    "ty": round(float(a[1, 2]), 2),
                    "shear": [
                        round(float(a[0, 1]), 4),
                        round(float(a[1, 0]), 4),
                    ],
                }
        return out


def _search(
    matcher: Matcher, video: Path, t0: float, dur: float, step: float
) -> list[dict]:
    rows = []
    for t, f in _stream(video, t0, dur, fps=1.0 / step):
        if not _live(f):
            rows.append({"t": round(t, 3), "live": False, "inliers": 0})
            continue
        r = matcher.best(f)
        r["t"] = round(t, 3)
        r["live"] = True
        if "pal_t" in r:
            r["lag_s"] = round(t - r["pal_t"], 3)
        rows.append(r)
    return rows


def _ch01_box(frames: list[np.ndarray]) -> list[int]:
    """Bounding box of the static dark 'CH01' text outline (bottom)."""
    st = np.asarray(frames, float)
    m = ((st.mean(0) < 60) & (st.std(0) < 25)).astype(np.uint8)
    h = m.shape[0]
    n, _, stats, _ = cv2.connectedComponentsWithStats(m)
    s = stats[1:]
    s = s[(s[:, 1] > 0.75 * h) & (s[:, 1] < 0.98 * h) & (s[:, 4] > 3)]
    if not len(s):
        return []
    return [
        int(s[:, 0].min()),
        int(s[:, 1].min()),
        int((s[:, 0] + s[:, 2]).max()),
        int((s[:, 1] + s[:, 3]).max()),
    ]


def main() -> None:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--pal", type=Path, default=PAL_DEFAULT)
    ap.add_argument("--clip", type=Path, default=CLIP_DEFAULT)
    ap.add_argument("--control", type=Path, default=CONTROL_DEFAULT)
    ap.add_argument("--pal-span", type=float, default=150.0)
    ap.add_argument("--pal-fps", type=float, default=5.0)
    ap.add_argument("--step", type=float, default=2.5, help="clip step, s")
    ap.add_argument("--min-inliers", type=int, default=50)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()

    pal_start = _start(PAL_SIDECAR)
    clip_start = _start(a.clip.with_suffix(".json"))
    nominal = (pal_start - clip_start).total_seconds()

    pal = list(_stream(a.pal, 0.0, a.pal_span, fps=a.pal_fps))
    matcher = Matcher(pal)

    # live window of the clip from 5 s before the nominal overlap start
    t0 = nominal - 5.0
    thumbs = [(t, _live(f)) for t, f in _stream(a.clip, t0, 240.0, fps=10)]
    live_ts = [t for t, ok in thumbs if ok]
    first_dead = next((t for t, ok in thumbs if not ok), None)
    live_end = first_dead if first_dead is not None else thumbs[-1][0]
    clip_rows = _search(matcher, a.clip, t0, live_end - t0, a.step)
    ctrl_rows = _search(matcher, a.control, 0.0, 9.0, 1.0)

    def summary(rows: list[dict]) -> dict:
        hits = [r for r in rows if r["inliers"] >= a.min_inliers]
        live = [r for r in rows if r["live"]]
        return {
            "frames_tested": len(live),
            "max_inliers": max((r["inliers"] for r in live), default=0),
            "matched_frames": len(hits),
            "median_lag_s": (
                float(np.median([r["lag_s"] for r in hits])) if hits else None
            ),
            "affine_median": (
                {
                    k: float(np.median([r[k] for r in hits]))
                    for k in ("sx", "sy", "tx", "ty")
                }
                if hits
                else None
            ),
            "rows": rows,
        }

    clip_mid = [f for _, f in _stream(a.clip, t0, min(20.0, live_end - t0))]
    ref = clip_mid[len(clip_mid) // 2]
    cols = ref.mean(0) > 12.0
    x0, x1 = int(np.argmax(cols)), int(len(cols) - np.argmax(cols[::-1]))
    res = {
        "pal": str(a.pal),
        "clip": str(a.clip),
        "pal_start_wallclock": pal_start.isoformat(),
        "clip_start_wallclock": clip_start.isoformat(),
        "nominal_lag_s": nominal,
        "clip_live_from_s": live_ts[0] if live_ts else None,
        "clip_live_until_s": live_end,
        "nominal_overlap_live_s": round(live_end - nominal, 2),
        "pal_frames": len(pal),
        "pal_span_s": a.pal_span,
        "min_inliers": a.min_inliers,
        "clip_vs_pal": summary(clip_rows),
        "control_vs_pal": summary(ctrl_rows),
        "pillarbox_active_x": [x0, x1],
        "pillarbox_sx": round((x1 - x0) / PAL_W, 4),
        "full_height_sy": round(ref.shape[0] / PAL_H, 4),
        "ch01_box_pal": _ch01_box([f for _, f in pal[:40]]),
        "ch01_box_clip": _ch01_box(clip_mid[::15]),
    }
    res["pillarbox_sx_over_sy"] = round(
        res["pillarbox_sx"] / res["full_height_sy"], 4
    )
    text = json.dumps(res, indent=1)
    print(text)
    if a.out:
        a.out.write_text(text + "\n")


if __name__ == "__main__":
    main()
