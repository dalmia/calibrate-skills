#!/usr/bin/env python3
"""Repo-level validation for the Calibrate skills.

Since `npx skills add dalmia/calibrate-skills` serves the default branch live,
`main` must always be installable. This gate runs in CI on every push/PR:

  - every SKILL.md has YAML frontmatter with name + description
  - skill `name` matches its directory name (npx skills resolves by name)
  - no broken relative links between skill files
  - the onboarding preflight script fails on a blank intake and passes on a
    filled one

Stdlib-only; run with `python3 scripts/check_skills.py` from the repo root.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"


def fail(msg: str, problems: list[str]) -> None:
    problems.append(msg)


def check_frontmatter(problems: list[str]) -> None:
    for f in sorted(SKILLS.rglob("SKILL.md")):
        text = f.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
        rel = f.relative_to(ROOT)
        if not m:
            fail(f"{rel}: missing YAML frontmatter", problems)
            continue
        fm = m.group(1)
        name_m = re.search(r"^name:\s*(\S+)", fm, re.MULTILINE)
        if not name_m:
            fail(f"{rel}: frontmatter missing `name`", problems)
        elif name_m.group(1) != f.parent.name:
            fail(
                f"{rel}: name '{name_m.group(1)}' != directory '{f.parent.name}'",
                problems,
            )
        if not re.search(r"^description:", fm, re.MULTILINE):
            fail(f"{rel}: frontmatter missing `description`", problems)


def check_links(problems: list[str]) -> None:
    for f in sorted(ROOT.rglob("*.md")):
        for m in re.finditer(r"\]\((\.\.?/[^)]+\.md)\)", f.read_text(encoding="utf-8")):
            target = (f.parent / m.group(1)).resolve()
            if not target.exists():
                fail(f"{f.relative_to(ROOT)}: broken link -> {m.group(1)}", problems)


def check_preflight(problems: list[str]) -> None:
    script = SKILLS / "onboarding/onboard/scripts/validate.py"
    blank = SKILLS / "onboarding/onboard/assets/onboard.md"
    if not script.exists() or not blank.exists():
        fail("onboarding preflight script or intake asset missing", problems)
        return

    def run(state: Path) -> int:
        return subprocess.run(
            [sys.executable, str(script), "--state", str(state)],
            capture_output=True,
        ).returncode

    if run(blank) == 0:
        fail("preflight passed on a blank intake (should fail)", problems)

    filled = blank.read_text(encoding="utf-8")
    for todo in re.findall(r"<!--\s*TODO[^>]*-->", filled):
        filled = filled.replace(todo, "filled in with real prose for CI.", 1)
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as tf:
        tf.write(filled)
        tmp = Path(tf.name)
    try:
        if run(tmp) != 0:
            fail("preflight failed on a filled intake (should pass)", problems)
    finally:
        tmp.unlink(missing_ok=True)


def main() -> int:
    problems: list[str] = []
    check_frontmatter(problems)
    check_links(problems)
    check_preflight(problems)
    if problems:
        print("skill-check FAILED:")
        for p in problems:
            print(f"  - {p}")
        return 1
    n = len(list(SKILLS.rglob("SKILL.md")))
    print(f"skill-check OK: {n} skills, frontmatter + links + preflight valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
