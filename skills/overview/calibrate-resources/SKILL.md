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

**Confirm the *key works* with a real read, not `whoami`.** `calibrate whoami`
prints the resolved server URL and the configured key's source — useful for
checking *which* host and key are in play — but it never calls the server, so it
can't tell you the key is actually valid. For that, use a real read like
`calibrate agents list`: a `401` there means not signed in, or a key for the
wrong deployment (see *Which Calibrate* below).

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
- **Self-hosted** — the user's team runs its own Calibrate. Point the CLI at
  their **API host** once with `configure` (it persists to
  `~/.config/calibrate/config.yaml`), then have them log in — the key is then
  validated against, and every later command reaches, their backend with no
  repeated flags:

  ```bash
  calibrate configure --no-interactive --server-url https://<their-calibrate-api-host>
  calibrate login        # then have the user log in / paste their key
  calibrate agents list  # verify: empty list (200) = success; 401 = key not valid there
  ```

  **Order matters: `configure` the host *before* `login`.** Do the `configure`
  step yourself once you've found the host (it's just the URL, not a secret); the
  key is the user's to enter. Resolution is flag > env > config, so a one-off
  `--server-url …` or `CALIBRATE_SERVER_URL` still overrides per call, and
  `calibrate whoami` shows the resolved URL and where it came from — use it to
  confirm the host landed.

  **Finding the API host is your job, not the user's — do it silently.** Ask
  them only for the web address they open (that is all a non-technical user
  reliably knows), tell them you'll take it from there, then work it out without
  narrating. Don't hand-write the search each time — run the helper:

  ```bash
  scripts/find-backend.sh <web-address>   # best guess on stdout, alternates on stderr
  host=$(scripts/find-backend.sh <web-address>)   # capture it directly
  ```

  It fetches the app and its JS (where the backend host is compiled in — a
  Next.js app proxies `/api/*` same-origin, so it isn't visible in the top-level
  network tab) and prints the likely API host, preferring one on the front end's
  own parent domain. Take the top hit; if it looks wrong, the stderr list and
  whoever set the deployment up are your fallbacks. Do **not** report back that
  "the web address isn't the one I need" — that turns your own request into a
  bait-and-switch. The user hears the outcome ("logged you in against your
  deployment"), never the front-end/back-end gap. If they happen to know the
  API/backend URL, take it directly. Once `configure` has set the host, the key
  is stored by `login` and the host by config, so plain commands (no flag) reach
  their deployment from then on.

See
[`../../references/agent-mode.md`](../../references/agent-mode.md) for output
formats and [`../../references/config-shapes.md`](../../references/config-shapes.md)
for payload shapes. Keep what you *say* to the user plain — see
[`../../references/voice.md`](../../references/voice.md).

## The five primitives

| Primitive | What it is | CLI group | Skill |
| --- | --- | --- | --- |
| **Agent** | The agent you're testing (endpoint or internal-LLM) | `agents` | `/connect-agent` |
| **Test** | A conversation + expectation (`response`, `tool_call`, `conversation`) | `tests` | `/build-test-suite`, `/generate-synthetic-data`, `/import-dataset` |
| **Agent-test** | Linking tests to an agent, running them, reading results | `agent-tests` | `/run-tests`, `/analyze-failures`, `/benchmark-models` |
| **Evaluator** | A versioned LLM/audio judge (binary or rating) | `evaluators` | `/design-evaluator`, `/iterate-evaluator` |
| **Annotation task** | Human labels + human↔judge agreement | `annotation-tasks` | `/calibrate-evaluator` |

Two skills cut across all of these rather than mapping to one primitive:
`/design-eval-plan` (decide *what* to evaluate before building anything) and
`/eval-audit` (a read-only check-up of an existing setup). The design reasoning
they apply lives in
[`../../references/methodology.md`](../../references/methodology.md) and
[`../../references/judge-prompts.md`](../../references/judge-prompts.md).

## Typical flow

1. `/design-eval-plan` — decide what to measure and how, before building.
2. `/connect-agent` — register + verify the agent.
3. `/build-test-suite`, `/generate-synthetic-data`, or `/import-dataset` — author
   test cases.
4. `/design-evaluator` — if any test judges response quality (type `llm` for a
   reply in a conversation).
5. `/run-tests` — run and read pass/fail.
6. `/analyze-failures` — group the failures and decide what to fix.
7. `/calibrate-evaluator` — prove the judge agrees with humans before trusting it.
8. `/benchmark-models` — compare models once the harness is trustworthy.
9. `/iterate-evaluator` — tune the judge and reset its live version.

`/onboard` runs this whole flow interactively for a first-time user;
`/eval-audit` reviews a setup that already exists.

## Not in the public API

Calibrate's public API is single-turn tests, evaluators, and annotation-based
judge calibration. There is **no** persona/simulation, trace, dashboard, or
report resource — don't offer skills for those here.
