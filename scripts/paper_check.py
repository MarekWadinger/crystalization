"""Cheap CEP submission checks for ``papers/cep/``.

Pages <= 20 (from ``main.log``), abstract <= 250 words (the ``abstract``
environment in ``main.tex`` or ``sections/*.tex``), 3-5 highlights of
<= 85 characters (``highlights.txt``, one per line). A check whose input
file is missing is skipped. Exit 1 if any check fails.

    python3 scripts/paper_check.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1] / "papers" / "cep"
MAX_PAGES, MAX_WORDS, MAX_CHARS = 20, 250, 85


def main() -> int:
    errors: list[str] = []

    log = PAPER / "main.log"
    pages = re.search(r"Output written on \S+ \((\d+) page", _read(log))
    if pages:
        n = int(pages.group(1))
        print(f"pages: {n} (limit {MAX_PAGES}, whole PDF)")
        if n > MAX_PAGES:
            errors.append(f"{n} pages > {MAX_PAGES}")
    else:
        print("pages: skipped (no main.log; run make pdf)")

    tex = "\n".join(
        _read(p) for p in [PAPER / "main.tex", *PAPER.glob("sections/*.tex")]
    )
    body = re.search(r"\\begin{abstract}(.*?)\\end{abstract}", tex, re.S)
    if body:
        text = re.sub(r"(?<!\\)%.*", "", body.group(1))
        n = len(text.split())
        print(f"abstract: {n} words (limit {MAX_WORDS})")
        if n > MAX_WORDS:
            errors.append(f"abstract {n} words > {MAX_WORDS}")
    else:
        print("abstract: skipped (no abstract environment)")

    lines = _read(PAPER / "highlights.txt").splitlines()
    items = [line.strip() for line in lines if line.strip()]
    if items:
        print(f"highlights: {len(items)} (3-5, <= {MAX_CHARS} chars each)")
        if not 3 <= len(items) <= 5:
            errors.append(f"{len(items)} highlights, need 3-5")
        errors += [
            f"highlight {len(h)} chars > {MAX_CHARS}: {h}"
            for h in items
            if len(h) > MAX_CHARS
        ]
    else:
        print("highlights: skipped (no highlights.txt)")

    for e in errors:
        print(f"FAIL {e}", file=sys.stderr)
    return 1 if errors else 0


def _read(path: Path) -> str:
    # LaTeX logs are not guaranteed UTF-8.
    return path.read_text(errors="replace") if path.exists() else ""


if __name__ == "__main__":
    sys.exit(main())
