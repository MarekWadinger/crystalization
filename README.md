# Crystalization

Research into crystal formation analysis from microscopy video.

### Quick Start

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

## **Annotator**

Classical computer vision tool for layer decomposition and crystal detection. No ML — deterministic pipeline using focus, motion, and depth signals.

See [src/annotator/README.md](src/annotator/README.md) for full documentation.

### Usage

```bash
uv sync --group annotator

# Interactive parameter tuner (recommended first step)
uv run annotator-app

# Batch analysis
uv run annotator-analyze video.mov -o stats.csv --detailed crystals.csv

# Visualization
uv run annotator-visualize video.mov -o viz.mp4

# Annotate original video with detections
uv run annotator-annotate video.mov crystals.csv -o annotated.mp4
```

## Predictor

Dynamic mode decomposition for crystal formation prediction. Decomposes a video into a series of dynamic modes that can be used to filter relevant modes that correspond to crystal edges movement.

See [src/predictor/README.md](src/predictor/README.md) for full documentation.

### Usage

```bash
uv sync --group predictor

# Interactive parameter tuner (recommended first step)
uv run predictor-app
```

## LLM Annotator

LLM-powered crystal annotation using a vision LLM (OpenAI GPT via pydantic-ai). Provides rich semantic annotation -- crystal system classification, growth stage assessment, and persistent crystal tracking across frames with structured Pydantic-validated output.

See [src/llm_annotator/README.md](src/llm_annotator/README.md) for full documentation.

### Usage

```bash
uv sync --group llm-annotator

# Interactive UI
uv run llm-annotator-app

# CLI annotation
uv run llm-annotator-annotate video.mov -o annotations.json
```

## Crystal Detector

Deep-learning crystal segmentation using a fine-tuned [Cellpose](https://github.com/MouseLand/cellpose) (`cpsam`) model. The ML counterpart to the deterministic Annotator -- detects and measures individual crystals in a microscopy image, exporting centroids and pixel areas. Includes a training-frame exporter and Cellpose-GUI training workflow.

The model checkpoint is hosted on the [Hugging Face Hub](https://huggingface.co/MarekWadinger/crystal-detector-cpsam) (public, no token needed) and downloaded automatically on first run.

See [src/crystal_detector/README.md](src/crystal_detector/README.md) for full documentation.

### Usage

```bash
uv sync --group crystal-detector

# Detect crystals in an image (downloads the model on first run)
uv run crystal-detector-analyze image.png

# Export training frames from a video
uv run crystal-detector-export-frames video.mp4 -o training_data
```

## Strike Annotation (optics-sidecar)

Every video in `datasets/` is paired with a JSON sidecar that records
operator-observed events on the crystallisation strike timeline (cleaning
through filling, seeding, boiling, and discharge). The `optics-sidecar`
CLI manages these files, validates them on every `git commit`, and provides
an interactive wizard for annotating new recordings.

```bash
uv run optics-sidecar wizard "datasets/2026-02-05 10-18-50.mp4"
uv run optics-sidecar check  "datasets/2026-02-04 11-08-51.json"
```

See [`docs/operator_notes/sidecar_guide.md`](docs/operator_notes/sidecar_guide.md)
for the full operator guide, including a worked end-to-end example and
troubleshooting reference.

## Development

```bash
# Install all dependencies (annotator + dev tools)
uv sync --group dev

# Set up pre-commit hooks
uv run pre-commit install
```
