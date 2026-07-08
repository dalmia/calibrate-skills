#!/usr/bin/env python3
"""Preflight gate for the /onboard skill. Stdlib-only — run isolated:

    uv run --no-project scripts/validate.py --state .calibrate/onboard.md

Exits non-zero and lists problems when a required phase is still unfilled. A
phase counts as filled when it has real prose below the italic blurb — not the
`<!-- TODO -->` marker and not only the blurb. This does not call Calibrate or
the network; it only checks that the intake has enough to proceed.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Phases that must contain prose before the first run. Phase 3 (evaluators) and
# Phase 5 (calibration) are optional, so they are not gated here.
REQUIRED_PHASES = (
    "Phase 1 — System under test",
    "Phase 2 — Hypothesis + tests",
)

TODO_RE = re.compile(r"<!--\s*TODO.*?-->", re.IGNORECASE | re.DOTALL)


def phase_blocks(text: str) -> dict[str, str]:
    """Split the intake into {heading: body} on `## ` headings."""
    blocks: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current is not None:
                blocks[current] = "\n".join(buf)
            current = line[3:].strip()
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        blocks[current] = "\n".join(buf)
    return blocks


def is_filled(body: str) -> bool:
    """Filled = has non-blurb, non-TODO, non-metadata prose."""
    stripped = TODO_RE.sub("", body)
    for raw in stripped.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("*") and line.endswith("*"):  # italic blurb
            continue
        if line.startswith("**") or line.startswith("<!--"):  # field / comment
            continue
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Preflight gate for /onboard intake.")
    ap.add_argument("--state", required=True, help="path to .calibrate/onboard.md")
    args = ap.parse_args()

    path = Path(args.state)
    if not path.is_file():
        print(f"error: state file not found: {path}", file=sys.stderr)
        print("hint: copy assets/onboard.md to .calibrate/onboard.md first.", file=sys.stderr)
        return 2

    blocks = phase_blocks(path.read_text(encoding="utf-8"))
    problems: list[str] = []
    for phase in REQUIRED_PHASES:
        body = blocks.get(phase)
        if body is None:
            problems.append(f"missing phase heading: '## {phase}'")
        elif not is_filled(body):
            problems.append(f"phase not filled in: '{phase}' (still TODO/blurb only)")

    if problems:
        print("preflight failed:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    print("preflight ok: required phases are filled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
