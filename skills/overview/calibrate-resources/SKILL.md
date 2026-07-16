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
calibrate agents list                # confirm auth with a real call
```

**Confirm auth with a real read, not `whoami`.** `calibrate whoami` only prints
the locally configured key and its source — it never calls the server, so it
"passes" even when the key is invalid or belongs to a different deployment. Use a
real read like `calibrate agents list`: a `401` there means not signed in, or a
key for the wrong deployment (see *Which Calibrate* below).

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

  **Finding the API host is your job, not the user's — do it silently.** Ask
  them only for the web address they open (that is all a non-technical user
  reliably knows), tell them you'll take it from there, then work it out without
  narrating: fetch the app and read the backend URL out of its JavaScript
  bundle / network calls (a Next.js app proxies `/api/*` same-origin, so the
  real host is compiled into the JS, not visible in the top-level network tab),
  or ask whoever set the deployment up. Do **not** report back that "the web
  address isn't the one I need" — that turns your own request into a
  bait-and-switch. The user hears the outcome ("logged you in against your
  deployment"), never the front-end/back-end gap. If they happen to know the
  API/backend URL, take it directly.

  **The host does not persist — every command needs `--server-url`.** Login
  stores the *key* (in the keychain, reused automatically — you never pass it
  again), but it does **not** remember the host. A later `calibrate agents list`
  with no flag falls back to the hosted default and 401s. So for a self-hosted
  user, `--server-url https://<their-calibrate-api-host>` must ride on **every**
  `calibrate` call in the flow — the auth check, listing, running tests, all of
  it — while the key is supplied once and reused:

  ```bash
  calibrate login       --server-url https://<their-calibrate-api-host>   # key stored once
  calibrate agents list --server-url https://<their-calibrate-api-host>   # host repeated
  ```

  To avoid repeating the flag, the host *can* be persisted with
  `calibrate configure --server-url …` or a `CALIBRATE_SERVER_URL` env var — but
  that rewrites the user's global CLI config, so **don't do it without asking**;
  default to threading the flag through each command instead.

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
