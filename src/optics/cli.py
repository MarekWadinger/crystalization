"""Unified ``optics-sidecar`` CLI.

One entry point for every operation on a video-sidecar JSON. Picks the
right subcommand dispatcher behind the scenes; users never have to
remember which Python module owns which action.

Subcommands::

    optics-sidecar new <video>          # blank template (ffprobe-filled)
    optics-sidecar wizard <video>       # step-by-step interactive walkthrough
    optics-sidecar reprobe <video>      # refresh media.probe block
    optics-sidecar check <json>...      # strict validate (used by pre-commit)
    optics-sidecar fix <json>...        # recompute event.t from wallclock
    optics-sidecar next <json>...       # show "what's next" hints
    optics-sidecar taxonomy             # print canonical phase list

Wired in ``pyproject.toml`` under ``[project.scripts]``::

    optics-sidecar = "optics.cli:main"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from optics.observations_schema import (
    PHASE_GLOSSES,
    Phase,
    completeness_report,
    load_validated,
    recompute_and_write,
)
from optics.sidecar_init import (
    _interactive,
    reprobe_sidecar,
    write_template,
)


def _cmd_new(args: argparse.Namespace) -> int:
    path = write_template(args.video, overwrite=args.overwrite)
    print(f"wrote: {path.resolve()}")
    print(f"open:  file://{path.resolve()}")
    return 0


def _cmd_wizard(args: argparse.Namespace) -> int:
    path = _interactive(Path(args.video), overwrite=args.overwrite)
    print(f"\nopen:  file://{path.resolve()}")
    return 0


def _cmd_reprobe(args: argparse.Namespace) -> int:
    path = reprobe_sidecar(args.video)
    print(f"reprobed: {path.resolve()}")
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    import json

    rc = 0
    for p in args.paths:
        try:
            sv = json.loads(Path(p).read_text()).get("schema_version", "")
        except Exception as exc:
            sys.stderr.write(f"{p}: FAIL (not valid JSON)\n{exc}\n")
            rc = 1
            continue
        if not str(sv).startswith("2."):
            print(f"{p}: SKIP (schema_version={sv!r}; not a v2.x sidecar)")
            continue
        try:
            load_validated(p)
        except Exception as exc:
            sys.stderr.write(f"{p}: FAIL\n{exc}\n")
            rc = 1
            continue
        print(f"{p}: OK")
    return rc


def _cmd_fix(args: argparse.Namespace) -> int:
    for p in args.paths:
        changes = recompute_and_write(p)
        if not changes:
            print(f"{p}: already consistent")
        else:
            print(f"{p}: applied {len(changes)} change(s):")
            for c in changes:
                print(f"  {c}")
    return 0


def _cmd_next(args: argparse.Namespace) -> int:
    for p in args.paths:
        obs = load_validated(p)
        todo = completeness_report(obs)
        if not todo:
            print(f"{p}: complete")
            continue
        print(f"{p}: what's next ({len(todo)})")
        for t in todo:
            print(f"  - {t}")
    return 0


def _cmd_taxonomy(_: argparse.Namespace) -> int:
    for ph in Phase:
        print(f"  {ph.value:32s}  {PHASE_GLOSSES[ph]}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="optics-sidecar",
        description=(
            "Manage video-sidecar JSONs (one JSON next to every video, "
            "same stem). See `optics-sidecar taxonomy` for the canonical "
            "phase list."
        ),
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    new = sub.add_parser("new", help="create a blank template sidecar")
    new.add_argument("video")
    new.add_argument("--overwrite", action="store_true")
    new.set_defaults(func=_cmd_new)

    wiz = sub.add_parser("wizard", help="step-by-step interactive walkthrough")
    wiz.add_argument("video")
    wiz.add_argument("--overwrite", action="store_true")
    wiz.set_defaults(func=_cmd_wizard)

    rep = sub.add_parser("reprobe", help="refresh media.probe from ffprobe")
    rep.add_argument("video")
    rep.set_defaults(func=_cmd_reprobe)

    chk = sub.add_parser("check", help="strict validate (pre-commit)")
    chk.add_argument("paths", nargs="+")
    chk.set_defaults(func=_cmd_check)

    fix = sub.add_parser("fix", help="recompute event.t from wallclock")
    fix.add_argument("paths", nargs="+")
    fix.set_defaults(func=_cmd_fix)

    nxt = sub.add_parser("next", help="show what's left to fill in")
    nxt.add_argument("paths", nargs="+")
    nxt.set_defaults(func=_cmd_next)

    tax = sub.add_parser("taxonomy", help="print canonical phase list")
    tax.set_defaults(func=_cmd_taxonomy)

    return p


def main() -> int:
    """Console-script entry point: ``optics-sidecar``."""
    args = _build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
