# Changelog

<!-- kpi:unreleased -->

## v0.8.0 (2026-06-22)

### Feat

- **optics**: reusable high-pass preprocessing component
- **crystal-detector**: video --time input, GUI launcher, Makefile
- **crystal-detector**: add crystal-detector-gui group for Cellpose GUI
- **crystal-detector**: add Cellpose-based crystal detection PoC
- **optics**: sub-pixel image registration for static-rig frame subtraction
- **optics**: start_frame parameter for sub-window analysis
- **optics**: batch-match b1 predictions for the short clips
- **optics**: unified optics-sidecar CLI + pre-commit hook
- **optics**: v2.0 sidecar schema with ffprobe probe + Phase enum
- add progress reporting with ETA to all CLI pipelines

### Fix

- **optics**: resolution-agnostic crop via auto-detect

## v0.7.0 (2026-06-17)

### Fix

- **optics**: resolution-agnostic crop via auto-detect

## v0.6.0 (2026-06-17)

### Feat

- **optics**: sub-pixel image registration for static-rig frame subtraction

## v0.5.0 (2026-06-17)

### Feat

- **optics**: start_frame parameter for sub-window analysis
- **optics**: batch-match b1 predictions for the short clips
- **optics**: unified optics-sidecar CLI + pre-commit hook
- **optics**: v2.0 sidecar schema with ffprobe probe + Phase enum

## v0.4.0 (2026-06-15)

### Feat

- **optics**: versioned camera config + auto-crop + observation schema

## v0.3.0 (2026-06-15)

### Feat

- **optics**: KPI report module + post-commit auto-bump hook
- **scale-overlay**: Gradio scale-overlay app + static demo renderer
- **optics**: watershed (negative-space) crystal detector
- **optics**: CSD aggregation with single-component log-normal fit
- **optics**: per-crystal depth disambiguation + qualitative figures + contact sheet
- **optics**: geometric model + PSF + frame I/O + plots + alpha fit + tests
- **sharpness-layers**: add Gradio layer-decomposition viewer
- **llm_annotator**: count_crystals returns positions, not just counts
- **llm_annotator**: add CV feature map tools, remove forced injection
- **llm_annotator**: add CLI progress reporting with time estimates
- **llm_annotator**: rewrite prompts for comprehensive crystal annotation
- **llm-annotator**: overhaul Gradio app UX and fix annotation visibility
- **llm_annotator**: add CLI, Gradio app, and public API exports
- **llm_annotator**: add pydantic-ai agent and crystal analysis tools
- **llm_annotator**: add frame I/O and visualization modules
- add llm_annotator module foundation with Pydantic types
- **predictor**: subtract temporal mean before DMD fitting
- introduce predictor module for video decomposition and prediction
- add annotator - crystal video analysis and detection module

### Fix

- **llm_annotator**: tighter area filter, better viz, fix test
- **llm_annotator**: pass downscaled frame as frame_bgr in all paths
- **llm_annotator**: guard empty crops, downscale feature map thumbnails
- **llm_annotator**: remove forced CV injection, keep as optional tool
- **llm_annotator**: CV detections as reference, not constraint
- **llm_annotator**: filter model dropdown to openai: models only
- **llm_annotator**: use CV detector positions, not LLM hallucinations
- **llm_annotator**: use actual pydantic-ai OpenAI model names in dropdown
- **llm_annotator**: apply comprehensive prompt and io improvements
- **llm_annotator**: improve viz with scaling, legend, label backgrounds
- **llm_annotator**: integration fixes after parallel merge

### Refactor

- **llm_annotator**: remove include_classical toggle
