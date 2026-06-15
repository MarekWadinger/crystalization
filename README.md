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

## Development

```bash
# Install all dependencies (annotator + dev tools)
uv sync --group dev

# Set up pre-commit hooks
uv run pre-commit install
```
