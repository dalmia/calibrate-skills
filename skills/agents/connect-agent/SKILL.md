---
name: connect-agent
description: Connect or create an agent under test in Calibrate, then verify its
  endpoint is reachable. Use when the user says "connect my agent", "add an
  agent", "create an agent", "set up my bot", or "point Calibrate at my endpoint".
argument-hint: "[agent-name-or-endpoint]"
---

# Connect an agent

Register the agent you want to evaluate in Calibrate and confirm Calibrate can
reach it. Drives the `calibrate agents` commands. Ask at each step; if
`$ARGUMENTS` already carries a name or endpoint, pre-fill it and skip that
question.

See [`../../references/agent-mode.md`](../../references/agent-mode.md) for how to
read command output (TOON/JSON) and [`../../references/config-shapes.md`](../../references/config-shapes.md)
for the `config-param` shape.

## Phase 0: Preflight

```bash
calibrate whoami
```

If unauthenticated, guide the user:

```bash
calibrate login
```

An API key is created under **Workspace settings → API keys**
(https://calibrate.artpark.ai/workspace-settings?tab=api-keys). No account →
send them to https://calibrate.artpark.ai to sign up.

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
- **config-param** (`-c`) — behavioral config; keys depend on type (endpoint,
  headers, model, system prompt). See the config-shapes reference.

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
calibrate agents create --name "<name>" --config-param '<json>' --output-format json
```

Capture `agent_uuid` from the response.

## Phase 3: Verify connection

Don't declare success until Calibrate can actually reach the agent:

```bash
calibrate agents verify-connection --agent-uuid <agent_uuid>
```

Report the result plainly. On failure, surface the structured error (auth,
timeout, bad URL) and fix the endpoint/headers with `calibrate agents update`
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
