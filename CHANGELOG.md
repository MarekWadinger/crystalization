# Changelog

<!-- kpi:unreleased -->

## v0.13.0 (2026-11-05)

### Fix

- **optics**: DIN 8902 glass, focus travel 0 at the FAR stop, tube naming

## v0.12.0 (2026-11-05)

### Fix

- **optics**: drop the camera-candidate term from the scale budget

## v0.11.0 (2026-11-05)

### Feat

- **optics**: side photo panel in the optical-layout figure
- **scripts**: untuned Cellpose vs microscope slope at matched times
- **scripts**: microscope anchor noise and watershed seed sweep
- **softsensor**: process-signal baseline from the plant KP formula
- **softsensor**: crystal-growth EKF with observability and leave-one-strike-out tests
- **datasets**: blind matched-time tracing of camera crystals vs lab
- **scripts**: label-free detector checks (seed sweep, strike time course)
- **scripts**: rerun every computed paper number from the current config
- **datasets**: transcribe all 54 microscope photos of the ZRA run
- **crystal-detector**: export lab-matched frames for annotation
- **optics**: layout figure colours lengths by source class
- **config**: source class on every camera input, enforced by test
- **crystal-detector**: frame switcher, explicit done, filter dropdown
- **crystal-detector**: Ananya's enhancement and rules in a decluttered annotation GUI
- **paper**: add CEP Makefile with figures, pdf, check, clean
- **paper**: collect CEP figures into papers/cep/figures

### Fix

- **paper**: Cellpose-vs-lab slope and counts from their script
- **paper**: check every citation against the sentence citing it
- **config**: camera body length is ASSUMED, not ESTIMATE
- **optics**: neutral figure text; fig 10 on log axes in PAL samples
- **optics**: diffraction at the working F-number; fig 08 fit over its band
- **datasets**: flag the 02-04 date of the 1080p clips as contradicted
- **datasets**: verify strike anchors, repair the 02-04 sidecar
- **optics**: per-axis pixel scale from the analog PAL chain
- **crystal-detector**: suggest a chore commit for annotations
- **paper**: skip comment lines in highlights check
- **paper**: read LaTeX log with replacement for non-UTF-8 bytes

## v0.10.0 (2026-11-03)

### Feat

- **optics**: detector size window in camera config

## v0.9.0 (2026-11-03)

### Feat

- **agents**: add sered-plant-expert with cited Sereď plant notes
- **sidecar**: annotate 2026-10-30 08-45-33 ZRA lab run
- **crystal_detector**: add repo preprocessors as Cellpose GUI filters
- **crystal-detector**: finetune command with held-out evaluation
- **crystal-detector**: three frames per crystal-bearing stage, no negatives
- **crystal-detector**: --review reopens labelled frames for checking
- **crystal-detector**: stage labels automatically, leave only commit and push
- **crystal-detector**: coloured annotate output with a team leaderboard
- **crystal-detector**: readable annotate console output
- **crystal-detector**: annotate loops over frames with the fine-tuned model registered
- **crystal-detector**: per-person annotation frames (LFS) and annotate command
- **optics**: to-scale optical layout figure and measurement error budget
- **optics**: site-measured geometry and IMX327 pixel pitch in camera config

### Fix

- **sidecar**: replace unsourced sizes and strike type in 2026-02-04 notes
- **optics**: near/far overlay demo offsets follow the configured focus
- **optics**: ship camera_100.toml inside the wheel
- **optics**: high-pass kernel for σ < 1 px and auto-detected crop for video
- **crystal-detector**: spell out both outcomes of the no-label prompt
- **crystal-detector**: handle Cellpose autosave and the zero-mask save rule
- **crystal-detector**: confirm each Ctrl+S live while the GUI is open
- **optics**: shorten pipeline diagram label so it fits its box

### Refactor

- **optics**: make camera_100.toml the single source of optical parameters

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
