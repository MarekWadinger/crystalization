import cv2
import os
import sys
import numpy as np

# --- CONFIGURATION ---
VIDEO_PATH = '/home/ubuntu/Downloads/2026-02-04 11-08-51.mp4'
OUTPUT_DIR = 'training_data'

# Exact timestamps to extract. Format: "HH:MM:SS", "MM:SS", or seconds.
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
    enhanced = clahe.apply(np.uint8(normalized))
    return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)


def crop(frame):
    h, w = frame.shape[:2]
    return frame[int(h * 0.1):int(h * 0.9), int(w * 0.05):int(w * 0.95)]


# --- MAIN ---
os.makedirs(OUTPUT_DIR, exist_ok=True)

cap = cv2.VideoCapture(VIDEO_PATH)
if not cap.isOpened():
    print(f"Error: could not open video '{VIDEO_PATH}'")
    sys.exit(1)

fps          = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
total_sec    = total_frames / fps

print(f"Video: {VIDEO_PATH}  (length {fmt(total_sec)})")
print(f"Extracting {len(TIMES)} frames...\n")

for i, time_entry in enumerate(TIMES):
    sec = parse_time(time_entry)
    if sec > total_sec:
        print(f"  [{i+1}/{len(TIMES)}] {fmt(sec)} — beyond video length, skipping.")
        continue

    cap.set(cv2.CAP_PROP_POS_FRAMES, int(sec * fps))
    ret, frame = cap.read()
    if not ret:
        print(f"  [{i+1}/{len(TIMES)}] {fmt(sec)} — could not read frame, skipping.")
        continue

    cropped   = crop(frame)
    corrected = flat_field_correction(cropped)

    cv2.imwrite(f"{OUTPUT_DIR}/frame_{i:02d}_ORIGINAL.png", cropped)
    cv2.imwrite(f"{OUTPUT_DIR}/frame_{i:02d}_PRE_AI.png", corrected)

    print(f"  [{i+1}/{len(TIMES)}] frame_{i:02d}  @ {fmt(sec)}")

cap.release()
print(f"\nDone! {len(TIMES)} frame pairs saved to '{OUTPUT_DIR}/'.")