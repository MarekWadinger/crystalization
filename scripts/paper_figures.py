"""Collect every figure of the CEP paper into ``papers/cep/figures/``.

The figure list is every image link in ``papers/cep/manuscript.md``.
The analytic figures are redrawn first; the rest are copied as committed
in ``docs/optics/figures/``. Basenames are kept.

Run from anywhere::

    uv run --frozen --group optics python scripts/paper_figures.py
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "papers" / "cep"
OUT = PAPER / "figures"

# Cheap, data-free generators (seconds, no video needed).
# ponytail: the frame-based figures (00, 07-12, 14, 17) are copied, not
# redrawn; they need the plant videos under datasets/. Add their modules
# (optics.qualitative, optics.measure, optics.disambiguate, optics.csd,
# optics.detect_watershed) here once the videos are on Zenodo.
GENERATORS = (
    "optics.plots",
    "optics.optical_layout",
    "optics.pipeline_diagram",
)


def figure_sources() -> list[Path]:
    """Return the image files linked from the manuscript, in order."""
    text = (PAPER / "manuscript.md").read_text()
    links = re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)", text)
    return [(PAPER / link).resolve() for link in links]


def main() -> None:
    for module in GENERATORS:
        subprocess.run([sys.executable, "-m", module], cwd=ROOT, check=True)
    sources = figure_sources()
    OUT.mkdir(exist_ok=True)
    for src in sources:
        shutil.copy2(src, OUT / src.name)
    names = {src.name for src in sources}
    assert names, "no image links in manuscript.md"
    assert all((OUT / n).stat().st_size > 0 for n in names)
    print(f"{len(names)} figures in {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
