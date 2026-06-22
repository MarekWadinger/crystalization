# Crystal Detector

Detects and segments crystals in microscopy images using a fine-tuned
[Cellpose](https://github.com/MouseLand/cellpose) (`cpsam`) model. This is the
deep-learning counterpart to the deterministic [`annotator`](../annotator):
it trades reproducibility for the ability to segment crystals that classical
focus/motion heuristics miss.

Given a microscopy image, the tool:
- finds all crystals with the trained model;
- prints a table of each crystal's ID, centroid, and pixel area;
- saves a side-by-side overlay (`<name>_analyzed.jpg`);
- saves positions to `<name>_crystals.json` (or `.csv` / `.txt`) for downstream
  use or further training.

## Install

```bash
uv sync --group crystal-detector
```

Training/annotation needs the Cellpose GUI. It lives in a **separate** group
(`crystal-detector-gui`) because it pulls Qt (~hundreds of MB) and needs a
display — useless for inference, Docker, and CI, so it is not installed by the
analyze path above:

```bash
uv sync --group crystal-detector-gui
```

## Analyze an image

```bash
uv run crystal-detector-analyze path/to/image.png
```

By default this writes `<name>_analyzed.jpg` and `<name>_crystals.json` next to
the input.

```bash
uv run crystal-detector-analyze image.png --save csv      # Excel-friendly
uv run crystal-detector-analyze image.png --save txt      # plain-text table
uv run crystal-detector-analyze image.png --no-save       # skip positions file
uv run crystal-detector-analyze image.png --outlines-only # outlines on original, no mask fill
uv run crystal-detector-analyze image.png --save-mask     # also dump <name>_mask.npy
uv run crystal-detector-analyze image.png --model PATH     # use a different checkpoint
```

`--save-mask` stores the full per-pixel label array (`np.load(...)`), so any
visualization or area can be recomputed later without re-running the model.

GPU is used automatically when available, otherwise CPU (slower but works).

## Export training frames

```bash
uv run crystal-detector-export-frames path/to/video.mp4 -o training_data
```

Edit the `TIMES` list at the top of `export_frames.py` to choose timestamps.
Each yields `frame_XX_ORIGINAL.png` (raw crop) and `frame_XX_PRE_AI.png`
(flat-field corrected — this is what goes into Cellpose).

## Train your own model

Requires `uv sync --group crystal-detector-gui` (does **not** work in Docker).

1. Export frames (above). The `frame_XX_PRE_AI.png` files are your inputs.
2. Open the GUI: `QT_API=pyqt6 uv run python -m cellpose`
   (the `QT_API` prefix avoids a PyQt5/PyQt6 clash).
3. Click **run cpsam**, then correct masks (right-click to draw,
   Ctrl+right-click to delete) and `Ctrl+S` to save `*_seg.npy` labels.
4. In the **Models** tab, **Train new model**, pointing at the folder with both
   images and `_seg.npy` files. The result lands in `training_data/models/`.
5. Point `analyze` at it: `--model training_data/models/cpsam_YYYYMMDD_HHMMSS`.

## Docker (analyze only)

```bash
docker build -f src/crystal_detector/Dockerfile -t crystal-analyzer .
docker run --rm -v /path/to/images:/data crystal-analyzer /data/sample.png
```

Add `--gpus all` and swap the base image (see the comment in the Dockerfile) for
GPU. Training and the GUI require a local install.

## Model & dataset hosting

The fine-tuned checkpoint is too large for git, so it lives on the
[Hugging Face Hub](https://huggingface.co/MarekWadinger/crystal-detector-cpsam)
(`MarekWadinger/crystal-detector-cpsam`). `analyze.py` downloads and caches it
automatically on first run via `huggingface_hub.hf_hub_download` — **no manual
download, no token** (the repo is public). A local file at
`training_data/models/` or a `--model PATH` argument overrides the download.

### Do I need an HF token / env secret?

- **Running / downloading the public model: no.** Nothing to configure, no `.env`.
- **Uploading a new checkpoint (re-training): yes, once, interactively** —
  `uv run hf auth login` (or `huggingface-cli login`). The token is cached in
  `~/.cache/huggingface/token`; it is **never** committed to the repo. There is
  no shared secret to manage. If you want a shared identity, create an HF
  *organization* and add members — each pushes with their own personal token.

### Publish / update the model (one-time, by a maintainer)

```bash
uv run hf auth login                                    # paste a write token
uv run hf upload MarekWadinger/crystal-detector-cpsam \
    training_data/models/cpsam_YYYYMMDD_HHMMSS cpsam_YYYYMMDD_HHMMSS
```

For the training frames, create a companion **dataset** repo the same way
(`hf upload --repo-type dataset <user>/crystal-detector-frames training_data/`).

Use MLflow only if/when training sweeps need metric tracking — it is the wrong
tool for distributing a single checkpoint.
