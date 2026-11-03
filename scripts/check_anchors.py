"""Check the strike timing anchors of the 2026-02-04 recording.

Three independent sources, all on 2026-02-04:

1. **Video** (``video``): the long PAL recording, 1 fps thumbnails around
   each anchor. Two signatures are reported in DVR-clock time
   (``start_wallclock + t``): the agitator stop (frame-to-frame motion
   falls below 50 % of its baseline) and the massecuite level passing
   below the sight glass (frame contrast, std of grey levels, rises
   above 1.6x its baseline).
2. **SCADA** (``scada``): ``Paulen_data.xlsx`` (ZRA only, 30 s, 11:00-17:00).
   Agitator current EI1004 < 1 A, vacuum PIC1003 PV > -10 kPa (vented),
   viscosity probe QI1003 at its 65 floor (probe uncovered: pan
   emptying), vacuum < -30 kPa again (next batch), steam valve
   PIC1002 OUT drop from 100 % to <= 50 % (the 'limited steam' at seeding).
   Needs ``openpyxl``: ``uv run --with openpyxl python scripts/...``.
3. **Trend photo** (``trend``): page 3 of
   ``docs/operator_notes/Krystal_260204_161114.pdf``, a phone photo of the
   DeltaV "Varostroj ZRA" trend, 2026-02-03 21:00 -> 02-04 18:00. The
   cyan trace is the steam valve opening. Vertical cyan edges are located
   column-wise and converted to time with the axis labels (piecewise
   linear between label centres). Needs ``pdftoppm`` (poppler).

    uv run --with openpyxl python scripts/check_anchors.py [video|scada|trend]

Without an argument all three run. Paths default to the Google Drive
layout in ``datasets/README.md``.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DRIVE = (
    Path.home()
    / "Library/CloudStorage/GoogleDrive-marek.wadinger@stuba.sk"
    / "My Drive/sugar_plant"
)
VIDEO = DRIVE / "video" / "2026-02-04 11-08-51.mp4"
SIDECAR = ROOT / "datasets" / "2026-02-04 11-08-51.json"
SCADA = DRIVE / "sered" / "data" / "Paulen_data.xlsx"
PDF = ROOT / "docs" / "operator_notes" / "Krystal_260204_161114.pdf"
DAY = datetime(2026, 2, 4)
ANCHORS = ("b1-e00", "b2-e10")
# trend photo: crop of page 3 (fractions of the page) and label order
CROP = (0.262, 0.525, 0.960, 0.803)  # x0, y0, x1, y1
LABELS = [-3, 0, 3, 6, 9, 12, 15, 18]  # h on 02-04 (21:00 on 02-03 = -3)


def _hms(t: datetime) -> str:
    return t.strftime("%H:%M:%S")


def video() -> None:
    side = json.loads(SIDECAR.read_text())
    t0 = datetime.fromisoformat(side["media"]["start_wallclock"])
    ev = {e["id"]: e for e in side["events"]}
    for aid in ANCHORS:
        ta = float(ev[aid]["t"])
        start = ta - 150.0
        cmd = [
            "ffmpeg", "-loglevel", "error", "-ss", f"{start}", "-i",
            str(VIDEO), "-t", "300", "-vf", "fps=1,scale=180:144",
            "-f", "rawvideo", "-pix_fmt", "gray", "-",
        ]  # fmt: skip
        raw = subprocess.run(cmd, check=True, capture_output=True).stdout
        f = np.frombuffer(raw, np.uint8).reshape(-1, 144, 180)[
            :, 20:130, 10:170
        ]
        f = f.astype(float)
        sd = f.std((1, 2))
        mot = np.r_[np.nan, np.abs(np.diff(f, axis=0)).mean((1, 2))]
        base_sd, base_mot = np.median(sd[:60]), np.nanmedian(mot[1:60])
        # smooth motion over 5 s so single duplicated frames do not trigger
        k = np.convolve(np.nan_to_num(mot), np.ones(5) / 5, mode="same")
        stop = int(np.argmax(k[5:] < 0.5 * base_mot)) + 5
        level = int(np.argmax(sd > 1.6 * base_sd))
        settle = level + int(np.argmax(k[level:] < 0.2 * base_mot))

        def at(i: int) -> str:
            return _hms(t0 + timedelta(seconds=start + i))

        print(
            f"{aid}: sidecar {ev[aid]['wallclock'][11:]} | video: agitator "
            f"stop ~{at(stop)}, level below glass {at(level)}, picture "
            f"static {at(settle)} (contrast {base_sd:.0f} -> "
            f"{sd[level + 5]:.0f})"
        )


def _scada_rows() -> tuple[list[str], list[list]]:
    import openpyxl  # ty: ignore[unresolved-import]  # optional, see docstring

    wb = openpyxl.load_workbook(SCADA, read_only=True, data_only=True)
    rows = list(wb.worksheets[0].iter_rows(values_only=True))
    return list(rows[1]), [r for r in rows[2:] if r[0] is not None]


def scada() -> None:
    tags, rows = _scada_rows()
    col = {t: i for i, t in enumerate(tags)}
    t = [r[0] for r in rows]

    def first(tag: str, cond, after: datetime, before: datetime) -> str:
        for ti, r in zip(t, rows):
            if after <= ti <= before and cond(r[col[tag]]):
                return _hms(ti)
        return "-"

    for name, a, b in (
        ("b1 end", DAY.replace(hour=11, minute=30), DAY.replace(hour=12)),
        ("b2 end", DAY.replace(hour=15, minute=50), DAY.replace(hour=16, minute=20)),
    ):  # fmt: skip
        stop = first("EI1004/AI1/PV.CV", lambda v: v < 1.0, a, b)
        vent = first("PIC1003_PID/PID1/PV.CV", lambda v: v > -10.0, a, b)
        empty = first("QI1003/AI1/PV.CV", lambda v: v < 65.5, a, b)
        after_empty = datetime.combine(
            DAY, datetime.strptime(empty, "%H:%M:%S").time()
        )
        vac = first(
            "PIC1003_PID/PID1/PV.CV", lambda v: v < -30.0, after_empty, b
        )
        print(
            f"{name}: agitator off {stop}, vented {vent}, viscosity probe "
            f"uncovered {empty}, vacuum re-pulled {vac}"
        )  # fmt: skip
    a, b = DAY.replace(hour=12, minute=15), DAY.replace(hour=12, minute=45)
    cut = first("PIC1002_PID/AO1/OUT.CV", lambda v: v <= 50.0, a, b)
    print(f"b2 seeding: steam valve 100 % -> <= 50 % at {cut}")


def trend() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "p"
        subprocess.run(
            ["pdftoppm", "-r", "300", "-f", "3", "-l", "3", "-png",
             str(PDF), str(out)],
            check=True,
        )  # fmt: skip
        img = cv2.imread(str(next(Path(tmp).glob("p*.png"))))
        if img is None:
            raise SystemExit("pdftoppm produced no page image")
        page = img.astype(int)
    h, w = page.shape[:2]
    x0, y0, x1, y1 = (int(c * s) for c, s in zip(CROP, (w, h, w, h)))
    c = page[y0:y1, x0:x1]
    hh = c.shape[0]
    # axis labels: white text in the band under the plot
    band = (c.min(2) > 170)[int(0.912 * hh) : int(0.962 * hh)]
    xs = np.where(band.any(0))[0]
    groups, cur = [], [xs[0]]
    for x in xs[1:]:
        if x - cur[-1] <= 14:
            cur.append(x)
        else:
            groups.append(cur)
            cur = [x]
    groups.append(cur)
    centres = [(g[0] + g[-1]) / 2 for g in groups][: len(LABELS)]
    # 'Wed 4' is a date label, not centred on its tick: drop it
    xs_cal = [x for x, hr in zip(centres, LABELS) if hr != 0]
    hr_cal = [hr for hr in LABELS if hr != 0]

    def to_time(x: float) -> datetime:
        return DAY + timedelta(hours=float(np.interp(x, xs_cal, hr_cal)))

    b, g, r = c[..., 0], c[..., 1], c[..., 2]
    cyan = (b > 150) & (g > 150) & (r < 160) & (np.abs(b - g) < 70)
    cnt = cyan[int(0.15 * hh) : int(0.87 * hh)].sum(0)
    edges = np.where(cnt > 150)[0]
    runs, cur = [], [edges[0]]
    for x in edges[1:]:
        if x - cur[-1] <= 2:
            cur.append(x)
        else:
            runs.append(cur)
            cur = [x]
    runs.append(cur)
    px_h = (xs_cal[-1] - xs_cal[0]) / (hr_cal[-1] - hr_cal[0])
    print(
        f"trend axis: {len(centres)} labels, {px_h:.1f} px/h at 300 dpi "
        f"(1 px = {3600 / px_h:.0f} s)"
    )
    for run in runs:
        xm = float(np.average(run, weights=cnt[run]))
        if to_time(xm) >= DAY.replace(hour=7):
            print(f"  cyan edge x={xm:7.1f}  ->  {_hms(to_time(xm))}")


def main() -> None:
    which = sys.argv[1:] or ["scada", "trend", "video"]
    for name in which:
        print(f"== {name}")
        {"video": video, "scada": scada, "trend": trend}[name]()


if __name__ == "__main__":
    main()
