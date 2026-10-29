---
name: build-test-suite
description: Author evaluation test cases for an agent in Calibrate and bulk-upload
  them. Use when the user says "write test cases", "build a test suite", "add
  tests for my agent", or "create test cases".
argument-hint: "[agent-uuid-or-name]"
---

# Build a test suite

Design evaluation test cases for an agent under test and upload them in bulk.
Drives the `calibrate tests` commands. Ask at each step; if `$ARGUMENTS` already
carries an agent UUID or name, pre-fill it and skip that question.

See [`../../references/agent-mode.md`](../../references/agent-mode.md) for how to
read command output (TOON/JSON) and [`../../references/config-shapes.md`](../../references/config-shapes.md)
for the exact test-item shape. Keep what you *say* to the user plain — see
[`../../references/voice.md`](../../references/voice.md).
When you finish a step, give the user the address for the tests you just added, as
[`../../references/links.md`](../../references/links.md) sets out.

## Get the latest instructions

Both the skill and the CLI on this machine can be months behind. Update both
before anything else, following
[`../../references/startup.md`](../../references/startup.md):

```bash
npx -y skills update build-test-suite -g -y ; npx -y skills update build-test-suite -p -y
```

```bash
have=$(calibrate version 2>/dev/null | head -1 | awk '{print $2}')
want=$(curl -fsS https://api.github.com/repos/dalmia/calibrate-cli/releases/latest 2>/dev/null | sed -n 's/.*"tag_name": *"v\{0,1\}\([^"]*\)".*/\1/p' | head -1)
if [ -n "$want" ] && [ "$have" != "$want" ]; then
  if command -v brew >/dev/null 2>&1; then
    brew update >/dev/null 2>&1
    brew install dalmia/tap/calibrate >/dev/null 2>&1 || brew upgrade dalmia/tap/calibrate >/dev/null 2>&1
  else
    arch=$(uname -m); case "$arch" in aarch64|arm64) arch=arm64 ;; *) arch=x86_64 ;; esac
    case "$(uname -s)" in
      Linux)  os=Linux;   bin=calibrate ;;
      Darwin) os=Darwin;  bin=calibrate ;;
      *)      os=Windows; bin=calibrate.exe ;;
    esac
    dest=$(command -v calibrate || echo "$HOME/.local/bin/$bin")
    tmp=$(mktemp -d)
    if [ "$os" = Windows ]; then
      curl -fsSL -o "$tmp/c.zip" "https://github.com/dalmia/calibrate-cli/releases/download/v${want}/calibrate-cli_${os}_${arch}.zip" && unzip -oq "$tmp/c.zip" -d "$tmp"
    else
      curl -fsSL "https://github.com/dalmia/calibrate-cli/releases/download/v${want}/calibrate-cli_${os}_${arch}.tar.gz" | tar xz -C "$tmp"
    fi
    if [ -f "$tmp/$bin" ]; then
      mkdir -p "$(dirname "$dest")"
      chmod +x "$tmp/$bin"
      cp "$tmp/$bin" "$dest"
    fi
    rm -rf "$tmp"
  fi
fi
calibrate version 2>/dev/null | head -1 || echo "calibrate is not installed"
```

Then re-read this `SKILL.md` from the path you loaded it from and follow that
copy: what is in your context is the version from before the update, and the
steps below may have changed.

Do all of this silently. `startup.md` names the one case worth telling the user
about.

## Phase 0: Setup check

```bash
calibrate agents list   # real read — 401 = not signed in, or key for the wrong deployment
```

If unauthenticated, run `calibrate login` (an API key lives under **Workspace
settings → API keys**, https://calibrate.artpark.ai/workspace-settings?tab=api-keys).

Confirm the target agent. If `$ARGUMENTS` gave a UUID, use it. If it gave a
name, resolve it:

```bash
calibrate agents resolve --names '["<name>"]' --output-format json
```

Otherwise inventory agents and ask which one to test:

```bash
calibrate agents list --output-format json
```

No agent yet → hand off to `/connect-agent` first. Capture the `agent_uuid`
**and that agent's `interaction_type`** from the same listing — it is on every
item, and it decides which test types are even possible. Never ask the user for
it; you already have it.

## Phase 1: Choose the evaluator type per case

The agent's `interaction_type` fixes the menu — a suite can mix the types
available to it across cases:

For a `conversation` agent (called with the exchange so far):

- **`conversation`** — quality, over the whole exchange rather than one reply.
  An LLM judge scores the conversation end to end. Every `conversation` test
  must keep at least one evaluator.
- **`tool_call`** — deterministic. Assert the agent calls tool X with args Y.
  No judge model, no token cost. Reach for this whenever the correct behavior is
  a specific action rather than a judgment about wording.
- **`response`** — quality. An LLM judge scores the reply against `criteria`.
  Needs an existing `evaluator_uuid` plus a `criteria` variable value, and costs
  judge tokens per run.

For a `general` agent (called with one plain input):

- **`tool_call`** — same as above: deterministic, no judge, no token cost.
- **`general`** — quality. One input goes in, one output comes back, and an LLM
  judge scores that pair on its own, with no conversation around it —
  summarizing, extracting, classifying. Needs an `evaluator_uuid` of type
  `llm-general` plus its variable values, and costs judge tokens per run.

For each behavior you want to cover, decide the type. A judged case needs a
judge the user chose. If the user hasn't told you what a good answer looks like
yet, stop and hand off to `/design-evaluator`: its Phase 1 explains judges to
the user and lets them pick the qualities to check. Never attach a judge they
didn't choose, including one that already exists in the workspace. Come back
with the `evaluator_uuid`s — a `general` case needs an `llm-general`
evaluator, a `response` case an `llm` one.

A test built for one kind of agent will not link to the other: the backend
rejects it. There is no converting one into the other — rebuild the case for the
kind of agent you're actually testing (swap the conversation for a single input,
or the other way round).

## Phase 2: Draft the cases

Start from the hypothesis — what must be true of the agent — and write the
failing and edge cases, not just the happy path (empty input, out-of-policy
requests, ambiguous asks, tool-args boundaries). Each item has:

- **name** — unique within the workspace, not just within this batch.
- **the input** — which key depends on the agent's `interaction_type`. For a
  `conversation` agent, `conversation_history`: a list of `{role, content}`
  turns leading up to the point of evaluation. For a `general` agent, `input`:
  one standalone prompt string, no conversation around it.
- **evaluators** — a list of `{evaluator_uuid, variable_values: {criteria: ...}}`
  for `response` and `general` cases.
- **tool_calls** — the expected calls, for `tool_call` cases.

See the test-item shape in
[`../../references/config-shapes.md`](../../references/config-shapes.md). Show
the drafted cases and confirm before uploading.

## Phase 3: Upload

For many cases, prefer `bulk-create` (at most 500 items per request, names
unique within the workspace as well as within the batch). `--type` applies to every row, so **one batch is one
type** — split a mixed suite into one batch per type. Pass `--agent-uuids` to
link every created test to the agent on creation (omit to link none);
`--language` writes to each test's `config.settings.language` (omit to leave
unset):

```bash
calibrate tests bulk-create \
  --type <response|conversation|tool_call|general> \
  --tests '[<items>]' \
  --agent-uuids '["<agent_uuid>"]' \
  --language <lang> \
  --output-format json
```

For a single case, use `create` — `-c/--config-param` is the test config. It
carries `evaluation` (required, its `type` matching `--type`), optional
`settings`, and the input: `history` for a conversation agent, `input` for a
general agent. Note the name: the single-test config says `history` where a bulk
row says `conversation_history`.

The judge does **not** go in the config here. `create` takes a separate
`-e/--evaluators` flag, and leaving it off creates the test with no judge
attached and no complaint. A bulk row is the other way round: the judge is part
of the item.

```bash
calibrate tests create \
  --name "<name>" \
  --type <response|conversation|tool_call|general> \
  --config-param '<json>' \
  --evaluators '[{"evaluator_uuid": "<uuid>", "variable_values": {"criteria": "..."}}]' \
  --output-format json
```

Capture the created `test_uuid`s from the JSON output. Never fabricate a UUID —
if a command fails, surface the structured error and fix the payload.

## Phase 4: Verify

Confirm the tests landed:

```bash
calibrate tests list --output-format json
calibrate tests get --test-uuid <test_uuid> --output-format json
```

To amend a case, edit its config and re-upload:

```bash
calibrate tests update --test-uuid <test_uuid> --config-param '<json>'
```

## Handoffs

- **Need a judge** for a `response` or `general` case → `/design-evaluator`
- **Already have a dataset** to turn into tests → `/import-dataset`
- **Run the tests** you just built → `/run-tests`
- **Full first-eval flow** → `/onboard`
