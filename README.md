# Crystal Detector

Detects and segments crystals in microscopy images using a fine-tuned [Cellpose](https://github.com/MouseLand/cellpose) (cpsam) model.

Given a microscopy image, the tool:
- finds all crystals using the trained AI model
- prints a table with each crystal's ID, centroid position, and area in pixels
- saves a side-by-side result image (`<name>_analyzed.jpg`) next to the input file
- saves crystal positions to `<name>_crystals.json` (or `.csv` / `.txt`) for use with other tools or future training

---

## Option A — Docker (no local install needed)

Best if you just want to run the tool without touching your Python environment.

> **Note:** Docker only works for running `analyze_crystals.py`. Extracting frames and training a new model in the Cellpose GUI both require a local install (see Option B).

### 1. Install Docker
[https://docs.docker.com/get-docker/](https://docs.docker.com/get-docker/)

### 2. Clone and build
```bash
docker build -t crystal-analyzer .
```
First build takes a few minutes (downloads PyTorch + Cellpose). Subsequent runs are instant.

### 3. Analyze an image
```bash
docker run --rm -v /path/to/your/images:/data crystal-analyzer /data/your_image.png
```
The result is saved as `/path/to/your/images/your_image_analyzed.jpg`.

**Example on Windows (PowerShell):**
```powershell
docker run --rm -v C:\Users\you\microscopy:/data crystal-analyzer /data/sample.png
```

> **NVIDIA GPU:** Add `--gpus all` to the `docker run` command. You also need to swap the base image — see the comment at the top of `Dockerfile`.

---

## Option B — Local install

Required for extracting training frames, using the Cellpose GUI, and training a new model.

### Requirements
- Python 3.10 or newer
- (Optional but recommended) NVIDIA GPU with CUDA drivers for faster inference and training

### Install
pip install -r requirements.txt
pip install cellpose[gui]        # adds the GUI on top of the base cellpose package
```

### Analyze an image
```bash
python analyze_crystals.py path/to/your_image.png
```

By default this saves two files next to the input:
- `your_image_analyzed.jpg` — visual overlay with detected crystals
- `your_image_crystals.json` — crystal positions, centroids, and areas

**Saving in a different format:**
```bash
python analyze_crystals.py your_image.png --save csv   # comma-separated, opens in Excel
python analyze_crystals.py your_image.png --save txt   # plain text table
python analyze_crystals.py your_image.png --no-save    # skip saving positions
```

**Visualization modes:**
```bash
python analyze_crystals.py your_image.png                  # default: colored mask fill + white outlines
python analyze_crystals.py your_image.png --outlines-only  # original image + green outlines only, no mask fill
```

Use `--outlines-only` when you want to verify detections without the mask hiding the crystal surface — outlines are drawn directly on the original image so you can see the texture underneath.

**Saving the full pixel mask:**

To be able to reproduce results exactly later (redraw any visualization, recompute areas, check individual crystals) without re-running the model:
```bash
python analyze_crystals.py your_image.png --save-mask
```
This saves `your_image_mask.npy` — a 2D array the same size as the image where each pixel value is the crystal ID (0 = background). Load it later with:
```python
masks = np.load("your_image_mask.npy")
```

**JSON output example:**
```json
{
  "image": "your_image.png",
  "model": "cpsam_20260517_223507",
  "crystal_count": 12,
  "crystals": [
    { "id": 1, "centroid_x": 412, "centroid_y": 308, "area_px": 4521 },
    { "id": 2, "centroid_x": 198, "centroid_y": 550, "area_px": 3812 }
  ]
}
```

A preview window also opens (close it to continue). In Docker, only the files are saved — no window.

---

## Extracting training frames from video

`export_frames.py` extracts frames at specific timestamps from a microscopy video and saves them to `training_data/`. Use this to prepare new images before re-training in the Cellpose GUI.

**Before running**, open `export_frames.py` and set your video path and the timestamps you want:
```python
VIDEO_PATH = '/path/to/your/video.mp4'

TIMES = [
    "00:30:00",   # 30 minutes into the video
    "01:00:00",   # 1 hour
    "01:45:00",   # 1 hour 45 minutes
    "02:30:00",
]
```

Then run:
```bash
python export_frames.py
```

Saved files per timestamp:
- `frame_XX_ORIGINAL.png` — raw cropped frame (for visual inspection)
- `frame_XX_PRE_AI.png` — flat-field corrected version (this is what goes into Cellpose for training)

---

## Training your own model with the Cellpose GUI

> Requires a local install with `pip install cellpose[gui]`. Does **not** work in Docker.

### 1. Extract frames from your video
Run `export_frames.py` as described above. The `frame_XX_PRE_AI.png` files in `training_data/` are your training images.

### 2. Open the Cellpose GUI
```bash
QT_API=pyqt6 python -m cellpose
```

> **Troubleshooting — `QCheckBox has no attribute checkStateChanged`:** This happens when both PyQt5 and PyQt6 are installed and the wrong one is picked. The `QT_API=pyqt6` prefix fixes it for that run. To fix it permanently for your conda environment so you never need to type it again:
> ```bash
> conda env config vars set QT_API=pyqt6 -n crystal_detection
> conda activate crystal_detection
> ```
> After that, plain `python -m cellpose` works.

### 3. Load an image
- Drag and drop a `frame_XX_PRE_AI.png` file onto the GUI window, or use **File → Load image**.

### 4. Run the base model to get a starting segmentation
- Click **run cpsam** in the segmentation panel.
- Key settings you can adjust before running:
  - **flow threshold** — how strict the boundary detection is (default 0.4, lower = fewer but cleaner masks)
  - **cellprob threshold** — minimum confidence to count as a cell (default 0.0, lower = more detections)
  - **norm percentiles lower/upper** — image contrast normalization range
  - **niter dynamics** — number of iterations for mask refinement (higher = slower but more accurate)
- After running you should see colored masks appear over the crystals.

### 5. Correct the masks manually
- **Draw a new mask** — right-click once to start, move the mouse to trace the crystal outline, then return to the starting point.
- **Delete a wrong mask** — Ctrl + right-click on the mask.
- Repeat for each image until the segmentation looks correct.

### 6. Save the masks
- After correcting each image press `Ctrl+S`.
- This saves a `*_seg.npy` file next to the image — that is the training label.

### 7. Train
- Once you have masks saved for several images, go to the **Models** tab.
- Click **Train new model**. Point it to the folder that contains both your images and the `_seg.npy` files (i.e. `training_data/`).
- Your previously trained custom models are listed under **User-trained models** in the same tab.
- Click **Train** and wait. Training progress is printed to the terminal.
- When done, the new model appears in `training_data/models/` with a timestamp in the name.

### 8. Use your new model
Update `MODEL_PATH` in `analyze_crystals.py` to point to your new model:
```python
MODEL_PATH = Path(__file__).parent / "training_data" / "models" / "cpsam_YYYYMMDD_HHMMSS"
```

---

## Model

The trained Cellpose model is included in `training_data/models/` — no separate download needed.

GPU is used automatically when available. Falls back to CPU otherwise (slower but works).