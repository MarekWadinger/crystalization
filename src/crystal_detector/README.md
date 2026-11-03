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

Frames for the team live in `annotations/<name>/<stage>/`, tracked with Git
LFS; labels are committed next to each frame as `<frame>_seg.npy`. Two videos
are sampled, only in crystal-bearing stages, with timestamps from the
video's sidecar in `datasets/`:

| Video | Frame names | Stages | Per person | Annotators |
| --- | --- | --- | --- | --- |
| `2026-02-04 11-08-51` (plant strike, PAL) | `HHMMSS.png` | seeding, boiling, drying, aeration, discharge × 3 | 15 | patrik, erika, marian, marek |
| `2026-10-30 08-45-33` (ZRA lab run on the NAS, two batches) | `2026-10-30_08-45-33_HHMMSS.png` | seeding, boiling, drying of each batch × 2 | 12 | patrik, erika, marian, marek, ananya |

`HHMMSS` is the offset into that video (not the clock time), so a frame can
be found again in the source video. Ananya also has 15 frames of the first
video: copies of the middle frame of patrik's, erika's and marian's triplet
in each stage, so her labels double as an inter-annotator check. The
fine-tune keeps every copy of a held-out frame out of training.

```bash
git lfs install && git lfs pull                   # once, if the PNGs are LFS pointers
uv sync --group crystal-detector-gui              # once
uv run crystal-detector-annotate patrik           # opens the GUI on your next unlabelled frame
```

The command registers the project's fine-tuned checkpoint with Cellpose and
opens one frame at a time; the terminal prints the steps for each frame:

1. *Optional:* under **user-trained models** (the checkpoint is preselected) press
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

The panel is trimmed for our grey frames: colour modes other than gray and
spectral, the gradXY/cellprob views, the generic cpsam model box and
Cellpose's own filter are hidden, and **Image filtering** sits right under
**Views**. Run the fine-tuned model from **user-trained models** (preselected);
its progress bar and ROI count sit there too. Below, **How to** lists the
keys and **Progress** shows the team leaderboard (you in bold) and the last
action ("saved ✓ …"); the window title names the frame and your count.

Under **Image filtering** the GUI offers the repo's deterministic
preprocessors as buttons: **Ananya** (Ananya Lohani's enhancement from
[Cryst_CNN](https://github.com/ananyalohani-bit/Cryst_CNN): CLAHE + sharpen,
brightness leveling, CLAHE + sharpen; see `enhance.py`), **flat-field** (what
`analyze.py` feeds the model), **high-pass** (`optics.highpass`) and
**sharpness** (`annotator.sharpness`). They change what you see and what
**run** segments; **none** restores the original. Labels stay bound to the
original pixels: the filtered image is never written into `_seg.npy`, so
training always sees the same flat-field frames as inference.

Under **user-trained models**, **add rule candidates** runs her crystal rules
on her enhanced frame and adds her *crystal* candidates as filled boxes
wherever there is no outline yet, so it never touches what the model or you
drew: on an empty frame you get all of them, after **run** only the ones the
model missed. Ctrl+click the false ones away.

Both are ports of her notebooks with her settings unchanged. They run on her
pixel grid (her frames are the PAL channel upscaled to 1080 rows): the frame
is resampled using `configs/camera_100.toml`, which works only for exported
annotation frames (648 or 1728 px wide); on other images the GUI says so and
does nothing. The enhancement leaves out her background reference image
(`back.png`, not in her repo). The GUI applies both to the frame as Cellpose
loaded it (contrast-stretched to 0–255), not to the PNG bytes. Her boxes
cover the bright body, so few overlap a hand-drawn outline by half or more;
her *skip* candidates were sorted by her CNN, whose trained model is not in
her repo.

`uv run crystal-detector-annotate patrik --review` reopens your labelled frames
one at a time with the label loaded, so you can check and fix them.

Maintainer, to sample frames from a video: `uv run crystal-detector-annotate
export VIDEO --who a,b,c,d [--per-stage 3]` (frames per person in each
stage segment from seeding to discharge; earlier stages have no crystals and
are not annotated). The sidecar is read from next to the video or from
`datasets/<stem>.json`, so videos on the NAS work in place. The second video
was exported with:

```bash
uv run crystal-detector-annotate export \
  "/Volumes/Public/Fedor/CrystalisationData/ZRA-2026-10-30/Videos/2026-10-30 08-45-33.mkv" \
  --who patrik,erika,marian,marek,ananya --per-stage 2
``` For a
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

## Fine-tune on the team's annotations

```bash
make -C src/crystal_detector finetune            # or: uv run crystal-detector-finetune
make -C src/crystal_detector finetune EPOCHS=30  # shorter run
```

Pools every labelled frame under `annotations/`, holds out one frame per
person (their middle boiling frame), continues training from the current checkpoint with the
Cellpose GUI defaults (lr 1e-5, weight decay 0.1, 100 epochs), and writes:

- `training_data/models/cpsam_YYYYMMDD_HHMMSS` — the new checkpoint (gitignored)
- `training_data/eval/*.png` — each held-out frame as *label | current | new*
- a terminal table of crystal counts and AP@0.5, current vs new

Nothing switches over automatically. To adopt the new checkpoint, try it with
`crystal-detector-analyze --model <path>`, upload it with `hf upload`, and
change `HF_MODEL_FILE` in `analyze.py`. `--max-frames 4 --epochs 1` is a
two-minute smoke test of the pipeline.

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
