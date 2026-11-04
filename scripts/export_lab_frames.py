"""Export the sharpest camera frames at each lab sample time for team annotation.

For every sample of the 2026-10-30 run that has microscope photos, the ±60 s
around the sample are split into three 40 s windows; in each, the whole-second
frame with the highest variance of the Laplacian (raw grey crop) is kept.
Frames go to ``annotations/<name>/lab_samples/`` round-robin over the team,
preprocessed like every other annotation frame; ``lab_samples.csv`` maps each
frame to its sample.

    uv run python scripts/export_lab_frames.py "/Volumes/Public/.../2026-10-30 08-45-33.mkv"
"""

import csv
import json
import sys
from pathlib import Path
from typing import Any

import cv2

from crystal_detector.annotate import ANNOTATIONS, ROOT, hhmmss
from crystal_detector.export_frames import crop, flat_field_correction

WHO = ("patrik", "erika", "marian", "marek", "ananya")
HALF_S = 60
WINDOWS = 3


def main(video: Path) -> None:
    side = json.loads((ROOT / "datasets" / f"{video.stem}.json").read_text())
    samples = [s for s in side["samples"] if s["photos"]]
    tag = video.stem.replace(" ", "_")
    cap = cv2.VideoCapture(str(video))
    fps = round(cap.get(cv2.CAP_PROP_FPS))
    rows, k = [], 0
    for s in samples:
        t0 = s["t"] - HALF_S
        cap.set(cv2.CAP_PROP_POS_MSEC, t0 * 1000)
        width = 2 * HALF_S // WINDOWS
        best: list[tuple[float, int, Any]] = [
            (-1.0, 0, None) for _ in range(WINDOWS)
        ]
        for i in range(2 * HALF_S * fps):
            if not cap.grab():
                break
            if i % fps:
                continue  # whole seconds only, so HHMMSS names find the frame again
            _, frame = cap.retrieve()
            grey = cv2.cvtColor(crop(frame), cv2.COLOR_BGR2GRAY)
            sharp = float(cv2.Laplacian(grey, cv2.CV_64F).var())
            w = min(i // fps // width, WINDOWS - 1)
            if sharp > best[w][0]:
                best[w] = (sharp, t0 + i // fps, frame)
        for sharp, t, frame in best:
            name = WHO[k % len(WHO)]
            k += 1
            folder = ANNOTATIONS / name / "lab_samples"
            folder.mkdir(parents=True, exist_ok=True)
            png = folder / f"{tag}_{hhmmss(t)}.png"
            cv2.imwrite(str(png), flat_field_correction(crop(frame)))
            rows.append(
                {
                    "annotator": name,
                    "frame": png.relative_to(ANNOTATIONS).as_posix(),
                    "sample": s["id"],
                    "clock": s["wallclock"][11:16],
                    "video_t_s": t,
                    "offset_s": t - s["t"],
                    "laplacian_var": round(sharp, 1),
                }
            )
            print(
                f"{s['id']} {rows[-1]['clock']} {t - s['t']:+4d} s → {png.relative_to(ROOT)}"
            )
    cap.release()
    with (ANNOTATIONS / "lab_samples.csv").open("w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
