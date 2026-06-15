#!/usr/bin/env bash
# Post-commit hook: when a commit touches src/optics/, run the KPI snapshot
# pipeline and bump to the next 0.x.0 release with commitizen.
#
# Install once:   uv run pre-commit install --hook-type post-commit
# Disable per run: SKIP_OPTICS_RELEASE=1 git commit ...
#
# Recursion guard: the bump commit itself (subject starts with "bump:")
# does not retrigger the pipeline.
set -euo pipefail

if [[ "${SKIP_OPTICS_RELEASE:-0}" == "1" ]]; then
    exit 0
fi

LAST_MSG=$(git log -1 --pretty=%s)
if [[ "${LAST_MSG}" == bump:* ]]; then
    # Avoid recursing into our own release commit.
    exit 0
fi

# Only fire when the just-landed commit actually touched src/optics/.
if ! git diff-tree --no-commit-id --name-only -r HEAD | grep -q '^src/optics/'; then
    exit 0
fi

echo "[optics-release] src/optics/ touched — running KPI pipeline + cz bump"

# Activate the project's venv so `uv run` is fast and `ty`/`ruff` are on PATH.
ROOT="$(git rev-parse --show-toplevel)"
cd "${ROOT}"

# Run KPI report, append/update CHANGELOG.md "unreleased" block.
uv run python -m optics.kpi --update-changelog >/dev/null

# Stage CHANGELOG.md so cz bump picks it up in the release commit.
git add CHANGELOG.md

# Bump minor: 0.X.0 -> 0.(X+1).0; this also writes the [Unreleased] block
# into a versioned heading and creates a "bump: ..." commit + tag.
SKIP_OPTICS_RELEASE=1 uv run cz bump --increment minor --yes >/dev/null
echo "[optics-release] released v$(uv run cz version --project)"
