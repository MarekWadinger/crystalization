"""Export flat-field-corrected training frames from a microscopy video.

Frames are sampled at the timestamps in ``TIMES`` and written to ``OUTPUT_DIR``
as ``frame_XX_ORIGINAL.png`` (raw crop) and ``frame_XX_PRE_AI.png`` (the
corrected image fed to Cellpose for labelling / training).
"""

import sys
from pathlib import Path

import cv2
import numpy as np

OUTPUT_DIR = "training_data"

# Edit these to pick which moments to sample. "HH:MM:SS", "MM:SS", or seconds.
TIMES = [
    "00:30:00",
    "01:00:00",
    "01:30:00",
    "02:00:00",
    "02:30:00",
]


def parse_time(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    parts = [float(p) for p in str(value).strip().split(":")]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0]


def fmt(seconds) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def flat_field_correction(frame_bgr):
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    light_map = cv2.GaussianBlur(gray, (201, 201), 0)
    corrected = gray.astype(np.float32) / (light_map.astype(np.float32) + 1e-5)
    normalized = np.zeros_like(corrected)
    cv2.normalize(corrected, normalized, 0, 255, cv2.NORM_MINMAX)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(normalized.astype(np.uint8))
    return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)


def crop(frame):
    h, w = frame.shape[:2]
    return frame[int(h * 0.1) : int(h * 0.9), int(w * 0.05) : int(w * 0.95)]


def export(video_path: str, output_dir: str = OUTPUT_DIR, times=TIMES):
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: could not open video '{video_path}'")
        sys.exit(1)

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    total_sec = total_frames / fps

    print(f"Video: {video_path}  (length {fmt(total_sec)})")
    print(f"Extracting {len(times)} frames...\n")

    for i, time_entry in enumerate(times):
        sec = parse_time(time_entry)
        if sec > total_sec:
            print(
                f"  [{i + 1}/{len(times)}] {fmt(sec)} — beyond video length, skipping."
            )
            continue

        cap.set(cv2.CAP_PROP_POS_FRAMES, int(sec * fps))
        ret, frame = cap.read()
        if not ret:
            print(
                f"  [{i + 1}/{len(times)}] {fmt(sec)} — could not read frame, skipping."
            )
            continue

        cropped = crop(frame)
        corrected = flat_field_correction(cropped)

        cv2.imwrite(f"{output_dir}/frame_{i:02d}_ORIGINAL.png", cropped)
        cv2.imwrite(f"{output_dir}/frame_{i:02d}_PRE_AI.png", corrected)

        print(f"  [{i + 1}/{len(times)}] frame_{i:02d}  @ {fmt(sec)}")

    cap.release()
    print(f"\nDone! {len(times)} frame pairs saved to '{output_dir}/'.")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Export flat-field-corrected training frames from a video. "
        "Edit TIMES at the top of this file to choose timestamps."
    )
    parser.add_argument("video", help="Path to the input video.")
    parser.add_argument(
        "-o",
        "--output-dir",
        default=OUTPUT_DIR,
        help="Output directory for frames.",
    )
    args = parser.parse_args()
    export(args.video, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
