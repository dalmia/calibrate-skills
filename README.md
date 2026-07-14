# Calibrate external skills

Agent Skills for evaluating AI agents with [Calibrate](https://calibrate.artpark.ai).
Follows the [Agent Skills](https://agentskills.io) open standard, so they work
with Claude Code, Cursor, Windsurf, Codex, and other compatible agents.

## Overview

Each skill drives the cloud `calibrate` CLI against Calibrate's public API. The
skills cover the full loop: connect an agent, build tests, run them, and —
Calibrate's signature move — **calibrate the LLM judges against human labels** so
the automated scores are trustworthy.

## Skills

| Category | Skill | What it does |
| --- | --- | --- |
| Overview | [calibrate-resources](skills/overview/calibrate-resources/) | Orientation: primitives, CLI, auth, which skill to use |
| Onboarding | [onboard](skills/onboarding/onboard/) | Guided end-to-end first evaluation (orchestrator) |
| Agents | [connect-agent](skills/agents/connect-agent/) | Create an agent on Calibrate or connect your existing agent |
| Tests | [build-test-suite](skills/tests/build-test-suite/) | Author test cases (`tool_call` / `response`) and upload |
| Tests | [import-dataset](skills/tests/import-dataset/) | Turn a CSV / JSONL / HuggingFace dataset into tests |
| Agent tests | [run-tests](skills/agent-tests/run-tests/) | Link tests to an agent, run, and read pass/fail |
| Agent tests | [benchmark-models](skills/agent-tests/benchmark-models/) | Compare models on the agent's tests (leaderboard) |
| Evaluators | [design-evaluator](skills/evaluators/design-evaluator/) | Create a versioned LLM/audio judge (binary/rating) |
| Evaluators | [iterate-evaluator](skills/evaluators/iterate-evaluator/) | Add/tune an evaluator version and pin it live |
| Annotation | [calibrate-evaluator](skills/annotation/calibrate-evaluator/) | Measure human↔judge agreement and tune the judge |

Shared references live in [`skills/references/`](skills/references/)
(`agent-mode.md`, `config-shapes.md`) and are linked from the skills.

Each skill maps to one of Calibrate's public API resources — and, deliberately,
there is no persona, simulation, trace, dashboard, or report skill, because the
public API has no such resource:

| Primitive | CLI group | Skills |
| --- | --- | --- |
| Agent | `agents` | connect-agent |
| Test | `tests` | build-test-suite, import-dataset |
| Agent-test | `agent-tests` | run-tests, benchmark-models |
| Evaluator | `evaluators` | design-evaluator, iterate-evaluator |
| Annotation task | `annotation-tasks` | calibrate-evaluator |

## Quick start

Pick the command for your agent — without `--agent`, the installer picks
whichever agent it detects first, which may not be the one you want:

```bash
# Claude Code
npx skills add dalmia/calibrate-skills --agent claude-code -g

# Cursor
npx skills add dalmia/calibrate-skills --agent cursor

# Windsurf
npx skills add dalmia/calibrate-skills --agent windsurf

# Codex
npx skills add dalmia/calibrate-skills --agent codex
```

If the skills are installed correctly, you should see a new `/onboard` skill along with a few other skills mentioned [here](https://calibrate.artpark.ai/docs/agents/skills#available-skills). If the skills don't appear instantly, restart your session and open a new chat session after installing so the skills are picked up.

Then install the CLI, authenticate, and run the guided onboarding skill:

```bash
brew install dalmia/tap/calibrate
calibrate login          # API key from Workspace settings → API keys
```

Install a single skill instead of all of them, or list what's available:

```bash
npx skills list dalmia/calibrate-skills
npx skills add dalmia/calibrate-skills/onboard --agent claude-code -g
```

### Manual installation

```bash
# Clone the repository
git clone https://github.com/dalmia/calibrate-skills.git

# Copy a skill (or the whole skills/ tree) into your agent's skills directory,
# e.g. .claude/skills/ for Claude Code or .cursor/skills/ for Cursor
cp -r calibrate-skills/skills/onboarding/onboard ~/.claude/skills/
```

## Skill structure

Each skill is a directory with `SKILL.md` as the entrypoint:

```
skills/<category>/<skill-name>/
├── SKILL.md          # instructions (required)
├── references/       # detailed docs (optional)
├── assets/           # templates / scaffolds (optional)
└── scripts/          # utilities (optional)
```

Frontmatter follows the Agent Skills standard:

```yaml
---
name: skill-name
description: What this skill does and the phrases that should trigger it
argument-hint: "[expected-arguments]"
---
```

## Requirements

- Calibrate CLI (`brew install dalmia/tap/calibrate`)
- A Calibrate account + API key ([calibrate.artpark.ai](https://calibrate.artpark.ai))
- An Agent Skills–compatible agent (Claude Code, Cursor, …)

## API reference

**Base URL:** `https://api.calibrate.artpark.ai`

The skills drive the `calibrate` CLI, which wraps this API. To call it directly,
pass your workspace key in the `X-API-Key` header:

```bash
curl https://api.calibrate.artpark.ai/agents \
  -H "X-API-Key: your_api_key"
```

Full interactive reference: [calibrate.artpark.ai/api-reference](https://calibrate.artpark.ai/api-reference).

## Documentation

See [calibrate.artpark.ai](https://calibrate.artpark.ai) for the full Calibrate
documentation, CLI reference, and API keys guide.

## License

MIT
