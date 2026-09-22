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

## Analyze an image or video frame

```bash
uv run crystal-detector-analyze path/to/image.png

# straight from a video — grabs the frame at the given timestamp:
uv run crystal-detector-analyze path/to/video.mp4 --time 00:18:00
```

Input can be an image, or a video plus `--time` (`HH:MM:SS`, `MM:SS`, or
seconds; defaults to the first frame). By default this writes
`<name>_analyzed.jpg` and `<name>_crystals.json` next to the input (for video,
`<videostem>_HHMMSS_*`).

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

## Annotate & retrain (improve the model)

### Team annotation

Frames for the team live in `annotations/<name>/<stage>/HHMMSS.png`: three
frames per person in each crystal-bearing stage (seeding → discharge, 15 per
person), tracked with Git LFS. Labels are committed next to them as
`HHMMSS_seg.npy`.

```bash
git lfs install && git lfs pull                   # once, if the PNGs are LFS pointers
uv sync --group crystal-detector-gui              # once
uv run crystal-detector-annotate patrik           # opens the GUI on your next unlabelled frame
```

The command registers the project's fine-tuned checkpoint with Cellpose and
opens one frame at a time; the terminal prints the steps for each frame:

1. *Optional:* under **user-trained models** choose the checkpoint and press
   **run** — it pre-draws crystal outlines for you to correct.
2. Fix outlines: **Shift+click** (or right-click) starts an outline, move the
   cursor, click again to close it; **Ctrl+click** on a crystal deletes it
   (Cmd on macOS). Cellpose autosaves after every edit and the terminal prints
   a green *saved* line each time.
3. Wait for the green line, then **close the window**; the next frame opens by
   itself. If no green line appeared (you accepted the proposals untouched),
   press `Ctrl+S` / `Cmd+S` first.

Closing a frame without a label asks whether the frame had no crystals (`y`
writes an empty label) or whether to stop (`n`, nothing lost). When done, the
command stages your `_seg.npy` files and prints the commit and push lines.

`uv run crystal-detector-annotate patrik --review` reopens your labelled frames
one at a time with the label loaded, so you can check and fix them.

Maintainer, to (re)sample frames: `uv run crystal-detector-annotate export
VIDEO --who a,b,c,d` (three frames per person in each stage from seeding to
discharge; earlier stages have no crystals and are not annotated). For a
cross-stage fine-tune, pool the images and labels into one folder first; the
GUI's **Train new model** only sees the folder of the loaded image.

One-time: install the GUI deps (Qt — does **not** work in Docker):

```bash
uv sync --group crystal-detector-gui
```

Then the annotate → train loop:

1. Export frames to label: `uv run crystal-detector-export-frames video.mp4 -o training_data`
   (the `frame_XX_PRE_AI.png` files are your inputs).
2. Launch the GUI: `uv run crystal-detector-gui`
   (wraps `python -m cellpose`, pre-setting `QT_API=pyqt6` to dodge the
   PyQt5/PyQt6 clash).
3. Load a frame, click **run cpsam**, then correct masks (Shift+click or right-click
   starts an outline, click again to close it; Ctrl+click deletes) and `Ctrl+S` to save `*_seg.npy` labels.
4. In the **Models** tab, **Train new model**, pointing at the folder with both
   images and `_seg.npy` files. The result lands in `training_data/models/`.
5. Use it: `crystal-detector-analyze image.png --model training_data/models/cpsam_YYYYMMDD_HHMMSS`.
6. Publish the improved checkpoint (optional): `uv run hf upload MarekWadinger/crystal-detector-cpsam <new-model> <name>`.

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
