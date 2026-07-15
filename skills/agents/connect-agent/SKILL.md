---
name: connect-agent
description: Connect or create an agent under test in Calibrate, then verify its
  endpoint is reachable. When the user has a codebase but no endpoint, add a
  Calibrate route and infer its auth from the code. Use when the user says
  "connect my agent", "add an agent", "create an agent", "set up my bot", "point
  Calibrate at my endpoint", "expose my agent to Calibrate", or "convert my
  codebase so Calibrate can test it".
argument-hint: "[agent-name-or-endpoint]"
---

# Connect an agent

Register the agent you want to evaluate in Calibrate and confirm Calibrate can
reach it. Drives the `calibrate agents` commands. Ask at each step; if
`$ARGUMENTS` already carries a name or endpoint, pre-fill it and skip that
question.

See [`../../references/agent-mode.md`](../../references/agent-mode.md) for how to
read command output (TOON/JSON) and [`../../references/config-shapes.md`](../../references/config-shapes.md)
for the `config-param` shape. Keep what you *say* to the user plain — see
[`../../references/voice.md`](../../references/voice.md).

## Phase 0: Setup check

First confirm the CLI itself is installed — `npx skills add` installs only the
instructions, not the `calibrate` command itself:

```bash
command -v calibrate >/dev/null || echo "calibrate CLI not installed"
```

If it's missing, stop and have the user install it, then re-run:

```bash
brew install dalmia/tap/calibrate
```

(No account yet? https://calibrate.artpark.ai). Only once the command is present,
check auth:

```bash
calibrate agents list   # real read — 401 = not signed in, or key for the wrong deployment
```

If unauthenticated, first confirm which Calibrate the user is on — the hosted
service at https://calibrate.artpark.ai, or a self-hosted deployment. A key only
works against the deployment it came from, so this determines the login command:

```bash
calibrate login                                          # hosted
calibrate login --server-url https://<their-api-host>    # self-hosted
```

For self-hosted, ask for the URL of their deployment's API host — often not the
same as the web address they visit (see
[`../../overview/calibrate-resources/SKILL.md`](../../overview/calibrate-resources/SKILL.md)
→ *Which Calibrate*). An API key is created under **Workspace settings → API
keys** (https://calibrate.artpark.ai/workspace-settings?tab=api-keys) on hosted,
or the equivalent settings page on their deployment. No account → send them to
https://calibrate.artpark.ai to sign up.

Inventory what already exists so you don't create a duplicate:

```bash
calibrate agents list --output-format json
```

If agents exist, present a numbered list and ask whether to configure an
existing one (skip to Phase 3) or create a new one.

## Phase 1: Identify the agent

Ask what the agent does and how Calibrate should reach it. Collect:

- **name** — unique, human-readable.
- **type** — how the agent connects. Load
  [`references/connection-types.md`](references/connection-types.md) for the
  per-type required fields and pitfalls.
- **config-param** (`-c`) — behavioral config; keys depend on type. See
  [`references/connection-types.md`](references/connection-types.md) for exact keys.

Which path you're on:

- Already has a **live URL** → `--type connection` with `agent_url` (+ `agent_headers`
  if they name any) and go to Phase 2.
- Has a **codebase but no endpoint** ("expose my agent", "convert my code") → do
  Phase 1.5 first.
- Has **no service at all** → `--type agent` with `llm.model` + `system_prompt`;
  go to Phase 2.

### Phase 1.5: Expose an endpoint from the codebase

When the user points you at a codebase instead of a URL, load
[`references/expose-endpoint.md`](references/expose-endpoint.md) and follow it:

1. **Inspect before editing.** Search the codebase for an existing
   Calibrate-style route so you don't duplicate or clobber working wiring. If one
   is already present and conforms to the contract, don't touch the code — reuse
   its path. If it's present but mis-wired, report the exact mismatch and propose
   a targeted fix. Only when none exists do you add one.
2. Add (or fix) a thin `POST /calibrate/test` route that reuses the agent's model
   call and returns `{"response": ...}` (+ `tool_calls` if the agent emits them).
   Show the diff; the user applies and deploys it.
3. **Infer auth from the code** — scan routes/middleware for the header + scheme.
   If the code requires none, create the agent with **no** `agent_headers` and don't
   ask. If it reads a secret from an env var, set the header and ask **only** for
   that value. Never ask a blanket "are there headers?".
4. Ask only for the **deploy base URL** (the code can't know it); the `agent_url` is
   `<base-url>/calibrate/test` (or the existing route's path). Then continue to
   Phase 2 with `agent_url` + inferred `agent_headers`.

## Phase 2: Create

Show a summary and confirm before creating:

```
Agent summary
  Name:        <name>
  Type:        <type>
  Endpoint:    <url or "internal">
  Config keys: <keys set>
```

```bash
calibrate agents create --name "<name>" --type <agent|connection> --config-param '<json>' --output-format json
```

Capture `agent_uuid` from the response.

## Phase 3: Verify connection

Don't declare success until Calibrate can actually reach the agent:

```bash
calibrate agents verify-connection --agent-uuid <agent_uuid>
```

Report the result plainly. On failure, surface the structured error (auth,
timeout, bad URL) and fix `agent_url`/`agent_headers` with `calibrate agents update`
rather than moving on:

```bash
calibrate agents update --agent-uuid <agent_uuid> --config-param '<json>'
```

To turn agent names into UUIDs elsewhere:

```bash
calibrate agents resolve --names '["<name>"]'
```

## Phase 4: Summary + next steps

```
Agent connected
  ID:   <agent_uuid>
  Name: <name>
  Dashboard: https://calibrate.artpark.ai/agents/<agent_uuid>
```

Hand off to whatever the user needs next:

- **Write test cases** for this agent → `/build-test-suite`
- **Import an existing dataset** as tests → `/import-dataset`
- **Run the full first-eval flow** → `/onboard`
