"""Real-world scale-grid overlay for the Camera 100 sight-glass video.

The app pairs:

* the geometric scale model from :mod:`optics` (mm/px at object plane is
  linear in object distance d_o);
* a per-pixel sharpness map (Laplacian variance) computed by
  :mod:`annotator.sharpness`;
* an in-frame ruler / grid that the user slides across the depth of field
  to read off real-world dimensions at any chosen depth.

Run with::

    uv run scale-overlay-app
"""
