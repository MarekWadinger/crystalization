"""Crystal detection via a fine-tuned Cellpose (cpsam) model.

A deep-learning counterpart to the deterministic :mod:`annotator`: given a
single microscopy image, it segments individual crystals, reports each one's
centroid and pixel area, and writes a side-by-side overlay plus a
positions file (JSON/CSV/TXT) for downstream use or further training.

Run with::

    uv run crystal-detector-analyze image.png
    uv run crystal-detector-export-frames video.mp4   # training-frame export

The model checkpoint is too large for git; see this component's README for
download / hosting (Hugging Face Hub recommended).
"""
