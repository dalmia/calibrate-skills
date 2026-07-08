# Calibrate external skills

Agent Skills for evaluating AI agents with [Calibrate](https://calibrate.artpark.ai).
Follows the [Agent Skills](https://agentskills.io) open standard, so they work
with Claude Code, Cursor, Windsurf, Codex, and other compatible agents.

Each skill drives the cloud `calibrate` CLI against Calibrate's public API. The
skills cover the full loop: connect an agent, build tests, run them, and —
Calibrate's signature move — **calibrate the LLM judges against human labels** so
the automated scores are trustworthy.

## Quick start

```bash
# Install the Calibrate CLI
brew install dalmia/tap/calibrate

# Authenticate (API key from Workspace settings -> API keys)
calibrate login

# In your agent, run the guided onboarding skill
/onboard
```

## Skills

| Category | Skill | What it does |
| --- | --- | --- |
| Overview | [calibrate-resources](skills/overview/calibrate-resources/) | Orientation: primitives, CLI, auth, which skill to use |
| Onboarding | [onboard](skills/onboarding/onboard/) | Guided end-to-end first evaluation (orchestrator) |
| Agents | [connect-agent](skills/agents/connect-agent/) | Connect/create an agent and verify its connection |
| Tests | [build-test-suite](skills/tests/build-test-suite/) | Author test cases (`tool_call` / `response`) and upload |
| Tests | [import-dataset](skills/tests/import-dataset/) | Turn a CSV / JSONL / HuggingFace dataset into tests |
| Agent tests | [run-tests](skills/agent-tests/run-tests/) | Link tests to an agent, run, and read pass/fail |
| Agent tests | [benchmark-models](skills/agent-tests/benchmark-models/) | Compare models on the agent's tests (leaderboard) |
| Evaluators | [design-evaluator](skills/evaluators/design-evaluator/) | Create a versioned LLM/audio judge (binary/rating) |
| Evaluators | [iterate-evaluator](skills/evaluators/iterate-evaluator/) | Add/tune an evaluator version and pin it live |
| Annotation | [calibrate-evaluator](skills/annotation/calibrate-evaluator/) | Measure human↔judge agreement and tune the judge |

Shared references live in [`skills/references/`](skills/references/)
(`agent-mode.md`, `config-shapes.md`) and are linked from the skills.

## The primitives

Calibrate's public API has five resources — and, deliberately, no persona,
simulation, trace, dashboard, or report resource:

| Primitive | CLI group | Skills |
| --- | --- | --- |
| Agent | `agents` | connect-agent |
| Test | `tests` | build-test-suite, import-dataset |
| Agent-test | `agent-tests` | run-tests, benchmark-models |
| Evaluator | `evaluators` | design-evaluator, iterate-evaluator |
| Annotation task | `annotation-tasks` | calibrate-evaluator |

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

## License

MIT
