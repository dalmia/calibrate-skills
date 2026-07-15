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
(https://calibrate.artpark.ai/workspace-settings?tab=api-keys).

### Which Calibrate — hosted or self-hosted

A key only validates against the deployment it was created in: a key from a
self-hosted Calibrate will 401 against the hosted service, and vice versa. This
is the most common "my API key doesn't work" cause. **Before `calibrate login`,
confirm which deployment the user is on** (see [`voice.md`](../../references/voice.md)
for how to ask):

Two different URLs are in play — keep them apart:

- **Web address** (frontend) — what the user opens in a browser to sign in and
  create their key, e.g. `https://calibrate.artpark.ai`.
- **API host** (backend) — what the CLI talks to, and the *only* thing
  `--server-url` accepts, e.g. `https://api.calibrate.artpark.ai`.

They are **not** the same host, and there is no fixed rule mapping one to the
other — hosted uses an `api.` prefix, but a self-hosted app at
`calibrate.example.org` might call `calibrate-backend.example.org`. So **never
pass the web address to `--server-url`** and never guess the API host from the
web address by pattern.

- **Hosted at https://calibrate.artpark.ai** — the CLI already defaults to the
  hosted API host, so plain `calibrate login` works; nothing extra to do.
- **Self-hosted** — the user's team runs its own Calibrate. You need their
  deployment's **API host**, then:

  ```bash
  calibrate login --server-url https://<their-calibrate-api-host>
  ```

  Ask them for the API/backend URL directly if they know it. If they only know
  the web address, find the API host from the running app — open its network
  requests in the browser's DevTools and read where the API/XHR calls go (that
  host is the backend), or ask whoever set the deployment up. Confirm the host
  with the user before using it. If later commands still hit the hosted service,
  persist it with `calibrate configure --server-url https://<their-calibrate-api-host>`.

See
[`../../references/agent-mode.md`](../../references/agent-mode.md) for output
formats and [`../../references/config-shapes.md`](../../references/config-shapes.md)
for payload shapes. Keep what you *say* to the user plain — see
[`../../references/voice.md`](../../references/voice.md).

## The five primitives

| Primitive | What it is | CLI group | Skill |
| --- | --- | --- | --- |
| **Agent** | The agent you're testing (endpoint or internal-LLM) | `agents` | `/connect-agent` |
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
7. `/iterate-evaluator` — tune the judge and reset its live version.

`/onboard` runs this whole flow interactively for a first-time user.

## Not in the public API

Calibrate's public API is single-turn tests, evaluators, and annotation-based
judge calibration. There is **no** persona/simulation, trace, dashboard, or
report resource — don't offer skills for those here.
