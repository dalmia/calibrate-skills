---
name: calibrate-resources
description: Orientation for evaluating agents with Calibrate — the primitives
  (agents, tests, agent-tests, evaluators, annotation tasks), the CLI, auth, and
  which skill to reach for. Load when the user asks "what is Calibrate", "how do
  I evaluate with Calibrate", "what can Calibrate do", or seems unsure where to
  start.
---

# Calibrate: resources and orientation

Calibrate is an evaluation platform for AI agents. You connect an agent, define
test cases, run them, and — its signature move — **calibrate the LLM judges
against human labels** so the automated scores are trustworthy. These skills
drive the `calibrate` CLI against the public API.

## Setup

```bash
brew install dalmia/tap/calibrate    # install the CLI
calibrate login                      # authenticate (API key from workspace settings)
calibrate whoami                     # confirm auth
```

API key: **Workspace settings → API keys**
(https://calibrate.artpark.ai/workspace-settings?tab=api-keys). See
[`../../references/agent-mode.md`](../../references/agent-mode.md) for output
formats and [`../../references/config-shapes.md`](../../references/config-shapes.md)
for payload shapes.

## The five primitives

| Primitive | What it is | CLI group | Skill |
| --- | --- | --- | --- |
| **Agent** | The system under test (endpoint or internal-LLM) | `agents` | `/connect-agent` |
| **Test** | A conversation + evaluators (`tool_call` or `response`) | `tests` | `/build-test-suite`, `/import-dataset` |
| **Agent-test** | Linking tests to an agent and running them | `agent-tests` | `/run-tests`, `/benchmark-models` |
| **Evaluator** | A versioned LLM/audio judge (binary or rating) | `evaluators` | `/design-evaluator`, `/iterate-evaluator` |
| **Annotation task** | Human labels + human↔judge agreement | `annotation-tasks` | `/calibrate-evaluator` |

## Typical flow

1. `/connect-agent` — register + verify the agent.
2. `/build-test-suite` (or `/import-dataset`) — author test cases.
3. `/design-evaluator` — if any test judges response quality.
4. `/run-tests` — run and read pass/fail.
5. `/calibrate-evaluator` — prove the judge agrees with humans before trusting it.
6. `/benchmark-models` — compare models once the harness is trustworthy.
7. `/iterate-evaluator` — tune the judge and re-pin its live version.

`/onboard` runs this whole flow interactively for a first-time user.

## Not in the public API

Calibrate's public API is single-turn tests, evaluators, and annotation-based
judge calibration. There is **no** persona/simulation, trace, dashboard, or
report resource — don't offer skills for those here.
