"""Detect and measure crystals in a microscopy image with Cellpose (cpsam)."""

import json
import sys
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
import torch
from cellpose import models, utils

# Checkpoint is hosted on the Hugging Face Hub (public — no token needed) and
# cached locally on first run. A local file at DEFAULT_MODEL_PATH, or any path
# passed via --model, takes precedence over the download.
HF_REPO_ID = "MarekWadinger/crystal-detector-cpsam"
HF_MODEL_FILE = "cpsam_20260517_223507"
DEFAULT_MODEL_PATH = (
    Path(__file__).parent / "training_data" / "models" / HF_MODEL_FILE
)

FLOW_THRESHOLD = 0.9
CELLPROB_THRESHOLD = -2.0


def resolve_model(model_path: Path = DEFAULT_MODEL_PATH) -> Path:
    """Return a local checkpoint path, downloading from the HF Hub if absent."""
    if model_path.exists():
        return model_path
    from huggingface_hub import hf_hub_download

    print(
        f"Model not found locally — downloading {HF_REPO_ID} from Hugging Face..."
    )
    return Path(hf_hub_download(repo_id=HF_REPO_ID, filename=HF_MODEL_FILE))


def flat_field_correction(img_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    light_map = cv2.GaussianBlur(gray, (201, 201), 0)
    corrected = gray.astype(np.float32) / (light_map.astype(np.float32) + 1e-5)
    normalized = np.zeros_like(corrected)
    cv2.normalize(corrected, normalized, 0, 255, cv2.NORM_MINMAX)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(normalized.astype(np.uint8))
    return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2RGB)


def crop(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    return img[int(h * 0.10) : int(h * 0.90), int(w * 0.05) : int(w * 0.95)]


def save_results(
    crystals: list[dict], image_path: str, fmt: str, model_name: str
):
    stem = Path(image_path).stem
    if fmt == "json":
        out_path = Path(image_path).with_name(stem + "_crystals.json")
        data = {
            "image": Path(image_path).name,
            "model": model_name,
            "crystal_count": len(crystals),
            "crystals": [
                {
                    "id": c["id"],
                    "centroid_x": c["centroid"][0],
                    "centroid_y": c["centroid"][1],
                    "area_px": c["area_px"],
                }
                for c in crystals
            ],
        }
        out_path.write_text(json.dumps(data, indent=2))
    elif fmt == "csv":
        out_path = Path(image_path).with_name(stem + "_crystals.csv")
        lines = ["id,centroid_x,centroid_y,area_px"]
        for c in crystals:
            lines.append(
                f"{c['id']},{c['centroid'][0]},{c['centroid'][1]},{c['area_px']}"
            )
        out_path.write_text("\n".join(lines))
    else:
        out_path = Path(image_path).with_name(stem + "_crystals.txt")
        lines = [
            f"{'id':>4}  {'centroid_x':>10}  {'centroid_y':>10}  {'area_px':>10}"
        ]
        lines.append("-" * 42)
        for c in crystals:
            lines.append(
                f"{c['id']:>4}  {c['centroid'][0]:>10}  {c['centroid'][1]:>10}  {c['area_px']:>10}"
            )
        out_path.write_text("\n".join(lines))

    print(f"Results saved: {out_path}")


def save_mask(masks: np.ndarray, image_path: str):
    out_path = Path(image_path).with_name(Path(image_path).stem + "_mask.npy")
    np.save(str(out_path), masks)
    print(f"Mask saved: {out_path}")


def analyze(
    image_path: str,
    save_fmt: str | None = "json",
    outlines_only: bool = False,
    save_mask_npy: bool = False,
    model_path: Path = DEFAULT_MODEL_PATH,
) -> list[dict]:
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        print(f"Error: file '{image_path}' not found.")
        sys.exit(1)

    img_bgr = crop(img_bgr)
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    preprocessed = flat_field_correction(img_bgr)

    model_path = resolve_model(model_path)
    print(f"Loading model: {model_path}")
    model = models.CellposeModel(
        gpu=torch.cuda.is_available(), pretrained_model=str(model_path)
    )

    print("Detecting crystals...")
    masks, flows, _ = model.eval(
        preprocessed,
        diameter=None,
        flow_threshold=FLOW_THRESHOLD,
        cellprob_threshold=CELLPROB_THRESHOLD,
    )

    crystal_ids = np.unique(masks)
    crystal_ids = crystal_ids[crystal_ids != 0]

    outlines = utils.outlines_list(masks)
    outline_by_id = {
        int(cid): coords.tolist() for cid, coords in zip(crystal_ids, outlines)
    }

    crystals = []
    for cid in crystal_ids:
        pixel_mask = masks == cid
        area = int(np.sum(pixel_mask))
        ys, xs = np.where(pixel_mask)
        cx, cy = int(np.mean(xs)), int(np.mean(ys))
        crystals.append(
            {
                "id": int(cid),
                "centroid": (cx, cy),
                "area_px": area,
                "outline": outline_by_id.get(int(cid), []),
            }
        )

    crystals.sort(key=lambda r: r["area_px"], reverse=True)

    print(f"\nCrystals found: {len(crystals)}")
    print(
        f"{'#':>4}  {'Centroid X':>10}  {'Centroid Y':>10}  {'Area (px²)':>12}"
    )
    print("-" * 42)
    for i, c in enumerate(crystals, 1):
        cx, cy = c["centroid"]
        print(f"{i:>4}  {cx:>10}  {cy:>10}  {c['area_px']:>12}")

    _visualize(
        img_rgb, masks, crystals, image_path, outlines_only=outlines_only
    )

    if save_fmt:
        save_results(crystals, image_path, save_fmt, model_path.name)

    if save_mask_npy:
        save_mask(masks, image_path)

    return crystals


def _visualize(
    img_rgb: np.ndarray,
    masks: np.ndarray,
    crystals: list[dict],
    image_path: str,
    outlines_only: bool = False,
):
    fig, axes = plt.subplots(1, 2, figsize=(20, 9))
    fig.suptitle(f"Crystal analysis — {Path(image_path).name}", fontsize=13)

    axes[0].imshow(img_rgb)
    axes[0].set_title("Original image")
    axes[0].axis("off")

    if outlines_only:
        overlay = img_rgb.copy()
        for c in crystals:
            coords = np.array(c["outline"])
            if len(coords):
                overlay[coords[:, 1], coords[:, 0]] = [0, 255, 0]
    else:
        rng = np.random.default_rng(42)
        color_lut = np.zeros((masks.max() + 1, 3), dtype=np.uint8)
        for cid in np.unique(masks):
            if cid != 0:
                color_lut[cid] = rng.integers(80, 255, 3)
        colored = color_lut[masks]
        overlay = (img_rgb * 0.55 + colored * 0.45).astype(np.uint8)
        for c in crystals:
            coords = np.array(c["outline"])
            if len(coords):
                overlay[coords[:, 1], coords[:, 0]] = [255, 255, 255]

    axes[1].imshow(overlay)
    axes[1].set_title(f"Detected crystals: {len(crystals)}", fontsize=12)
    axes[1].axis("off")

    if not outlines_only:
        for c in crystals:
            cx, cy = c["centroid"]
            axes[1].annotate(
                f"{c['id']}\n{c['area_px']} px²",
                xy=(cx, cy),
                fontsize=6.5,
                color="white",
                ha="center",
                va="center",
                bbox=dict(
                    boxstyle="round,pad=0.25", fc="black", alpha=0.55, lw=0
                ),
            )

    plt.tight_layout()

    out_path = Path(image_path).with_name(
        Path(image_path).stem + "_analyzed.jpg"
    )
    plt.savefig(str(out_path), dpi=150, bbox_inches="tight")
    print(f"Visualization saved: {out_path}")
    plt.show()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Detect crystals in a microscopy image."
    )
    parser.add_argument(
        "image", nargs="?", default="img.png", help="Path to input image"
    )
    parser.add_argument(
        "--save",
        choices=["json", "csv", "txt"],
        default="json",
        help="Format for saving crystal positions (default: json).",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Do not save crystal positions to file.",
    )
    parser.add_argument(
        "--outlines-only",
        action="store_true",
        help="Show only crystal outlines on the original image, no filled mask.",
    )
    parser.add_argument(
        "--save-mask",
        action="store_true",
        help="Save the full pixel mask as <name>_mask.npy for exact reproduction later.",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=DEFAULT_MODEL_PATH,
        help="Path to the Cellpose model checkpoint.",
    )
    args = parser.parse_args()

    fmt = None if args.no_save else args.save
    analyze(
        args.image,
        save_fmt=fmt,
        outlines_only=args.outlines_only,
        save_mask_npy=args.save_mask,
        model_path=args.model,
    )


if __name__ == "__main__":
    main()
