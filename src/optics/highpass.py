"""Spatial high-pass filter for sight-glass frames.

    residual = | image − GaussianBlur(image, σ) |

Subtracts everything varying slower than ~σ pixels — the LED illumination
gradient, bulk brightness shifts, and the fixed crack/rupture pattern baked
into the glass — while keeping fine-grained crystal edges. Needs no reference
frame and no temporal window, so it works on a single still image as well as a
video, which is why it is the default preprocessing step for the static-rig
recordings (see ``scripts/rq4_rupture_removal_methods.py`` Method 3, which this
component generalises).

Usage::

    from optics.highpass import highpass
    residual = highpass(gray_or_bgr, sigma_px=25.0)   # float32, same shape

CLI (image or video in, processed file out)::

    uv run optics-highpass datasets/frame.png
    uv run optics-highpass "datasets/2026-02-04 11-08-51.mp4" --crop -o /tmp/hp.mp4
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np

from .video_io import DEFAULT_CROP, open_and_crop, resolve_crop

DEFAULT_SIGMA_PX = 25.0
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".m4v"}


def highpass(
    image: np.ndarray, sigma_px: float = DEFAULT_SIGMA_PX
) -> np.ndarray:
    """Return ``|image − GaussianBlur(image, σ)|`` as float32 (same shape).

    Computed in float to avoid uint8 underflow; clip + cast for display.
    """
    if sigma_px <= 0:
        raise ValueError("sigma_px must be > 0")
    k = max(3, int(round(sigma_px * 6)) | 1)  # ~6σ support, odd, ≥ 3
    src = image.astype(np.float32)
    lowpass = cv2.GaussianBlur(src, (k, k), sigma_px)
    return np.abs(src - lowpass)


def _to_uint8(residual: np.ndarray) -> np.ndarray:
    return np.clip(residual, 0, 255).astype(np.uint8)


def highpass_image(
    in_path: str,
    out_path: str,
    sigma_px: float = DEFAULT_SIGMA_PX,
    crop=None,
) -> None:
    """Apply the high-pass filter to one image file and save the result."""
    img = cv2.imread(str(in_path))
    if img is None:
        raise FileNotFoundError(f"could not read image '{in_path}'")
    if crop is not None:
        img = crop.apply(img)
    cv2.imwrite(str(out_path), _to_uint8(highpass(img, sigma_px)))
    print(f"High-pass image saved: {out_path}")


def highpass_video(
    in_path: str,
    out_path: str,
    sigma_px: float = DEFAULT_SIGMA_PX,
    crop=None,
) -> int:
    """Apply the high-pass filter to every frame of a video. Returns frame count."""
    box = resolve_crop(str(in_path), crop) if crop is not None else None
    cap, _, n, fps = open_and_crop(
        str(in_path), box if box is not None else DEFAULT_CROP
    )

    writer = None
    out_w = out_h = 0
    i = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if box is not None:
            frame = box.apply(frame)
        processed = _to_uint8(highpass(frame, sigma_px))
        if writer is None:
            # mp4v requires even dimensions — trim to the nearest even size,
            # taken from the actual processed frame so writer/frame always match.
            out_h = processed.shape[0] - (processed.shape[0] % 2)
            out_w = processed.shape[1] - (processed.shape[1] % 2)
            writer = cv2.VideoWriter(
                str(out_path),
                cv2.VideoWriter.fourcc(*"mp4v"),
                fps,
                (out_w, out_h),
            )
            if not writer.isOpened():
                cap.release()
                raise RuntimeError(
                    f"could not open VideoWriter for '{out_path}' "
                    "(codec/size issue)"
                )
        writer.write(processed[:out_h, :out_w])
        i += 1
        if i % 500 == 0:
            print(f"  {i}/{n} frames...")
    cap.release()
    if writer is not None:
        writer.release()
    print(f"High-pass video saved: {out_path}  ({i} frames)")
    return i


def main():
    parser = argparse.ArgumentParser(
        description="High-pass filter: remove illumination gradient and static "
        "glass ruptures from a sight-glass image or video."
    )
    parser.add_argument("input", help="Image or video file.")
    parser.add_argument(
        "-o",
        "--out",
        default=None,
        help="Output path (default: <input>_highpass.<ext> next to input).",
    )
    parser.add_argument(
        "--sigma",
        type=float,
        default=DEFAULT_SIGMA_PX,
        help=f"Low-pass Gaussian sigma in px (default: {DEFAULT_SIGMA_PX:g}).",
    )
    parser.add_argument(
        "--crop",
        action="store_true",
        help="Apply the sight-glass overlay crop first (auto-detected for video).",
    )
    args = parser.parse_args()

    inp = Path(args.input)
    is_video = inp.suffix.lower() in VIDEO_EXTS
    out = (
        Path(args.out)
        if args.out
        else inp.with_name(f"{inp.stem}_highpass{inp.suffix}")
    )
    if is_video:
        crop = resolve_crop(str(inp)) if args.crop else None
        highpass_video(str(inp), str(out), args.sigma, crop=crop)
    else:
        highpass_image(
            str(inp),
            str(out),
            args.sigma,
            crop=DEFAULT_CROP if args.crop else None,
        )


if __name__ == "__main__":
    main()
