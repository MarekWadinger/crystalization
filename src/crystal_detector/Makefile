# Convenience targets for the crystal_detector component.
# Run from anywhere, e.g.  make -C src/crystal_detector analyze IMAGE=frame.png
# Paths (IMAGE/VIDEO) are resolved from the repo root so datasets/... just works.

ROOT := $(realpath $(dir $(lastword $(MAKEFILE_LIST)))/../..)

IMAGE ?=
VIDEO ?=
TIME  ?= 00:00:00
MODEL ?=
OUT   ?= training_data
MODEL_ARG := $(if $(MODEL),--model $(MODEL),)

.PHONY: help install gui-install analyze analyze-video export gui annotate

help:
	@echo "crystal_detector — make targets:"
	@echo "  make install                          install inference deps (uv group)"
	@echo "  make gui-install                      install Cellpose GUI deps (Qt)"
	@echo "  make analyze IMAGE=path.png           detect crystals in an image"
	@echo "  make analyze-video VIDEO=v.mp4 TIME=00:18:00   detect in a video frame"
	@echo "  make export VIDEO=v.mp4 [OUT=dir]     export training frames"
	@echo "  make gui                              launch GUI to annotate / retrain"
	@echo "  make annotate NAME=patrik             open the GUI on your unlabelled frames"
	@echo "  optional: MODEL=path/to/checkpoint    use a non-default model"

install:
	cd $(ROOT) && uv sync --group crystal-detector

gui-install:
	cd $(ROOT) && uv sync --group crystal-detector-gui

analyze:
	@test -n "$(IMAGE)" || { echo "Usage: make analyze IMAGE=path.png"; exit 2; }
	cd $(ROOT) && uv run crystal-detector-analyze "$(IMAGE)" $(MODEL_ARG)

analyze-video:
	@test -n "$(VIDEO)" || { echo "Usage: make analyze-video VIDEO=v.mp4 [TIME=00:18:00]"; exit 2; }
	cd $(ROOT) && uv run crystal-detector-analyze "$(VIDEO)" --time $(TIME) $(MODEL_ARG)

export:
	@test -n "$(VIDEO)" || { echo "Usage: make export VIDEO=v.mp4 [OUT=dir]"; exit 2; }
	cd $(ROOT) && uv run crystal-detector-export-frames "$(VIDEO)" -o "$(OUT)"

gui:
	cd $(ROOT) && uv run crystal-detector-gui

annotate:
	@test -n "$(NAME)" || { echo "Usage: make annotate NAME=<your folder under annotations/>"; exit 2; }
	cd $(ROOT) && uv run crystal-detector-annotate "$(NAME)"
