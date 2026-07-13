# Maintaining the Calibrate skills

This repo is a set of Agent Skills that drive the `calibrate` CLI. `main` is
served live to every `npx skills add dalmia/calibrate-skills`, so keep it
installable — CI runs `scripts/check_skills.py` on every push.

## Two registers — don't blur them

Each `SKILL.md` is read by an agent, and that agent then talks to a possibly
non-technical end user. Keep the two separate:

- **Instructions** (headings, CLI flags, `config-param`, TOON, UUIDs, polling)
  are precise notes *for the agent*. Keep them precise — don't dumb them down.
- **What the agent says to the user** must be plain and free of that machinery.

The failure mode is leakage: the agent echoes the skill's own vocabulary back to
the user. Models mirror the register of the text they read — so a heading named
`Preflight` comes out as "pre-flight checks," and "not the binary" becomes "the
calibrate CLI binary isn't installed." Guard against it:

- **Keep mechanics jargon out of headings** — headings get echoed verbatim.
  Banned in headings (CI-enforced): `preflight` (use "setup check"),
  `system under test` (use "your agent" / "describe your agent"),
  `adaptive determinism`.
- **How the running agent should speak** lives in
  [`skills/references/voice.md`](skills/references/voice.md). Read it before you
  change any user-facing prose.
- **Every `SKILL.md` links `voice.md`** alongside `agent-mode.md` — CI enforces
  this too.

## When you add or edit a skill

- Link `../../references/voice.md` from the skill's reference line.
- Keep agent-only mechanics (UUIDs, `config-param`, TOON, polling, error shapes)
  out of anything the agent would say aloud — `voice.md` has the say-instead
  table. This includes internal field/key names (`type=connection`, `agent_url`,
  `endpoint`, `system_prompt`) and step-by-step plumbing narration ("let me check
  the schema"): the user needs the input request and the outcome, nothing between.
- Run `python3 scripts/check_skills.py` before pushing.
