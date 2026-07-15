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

**Design before you build.** If the user hasn't scoped *what* to test — which
behaviours, which quality dimensions — start with `/design-eval-plan` and come
back with its spec. Writing cases without a plan produces tests that don't map to
how the agent actually fails. If a `.calibrate/eval-plan.md` already exists, build
from it. The reasoning behind case selection lives in
[`../../references/methodology.md`](../../references/methodology.md).

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

No agent yet → hand off to `/connect-agent` first. Capture the `agent_uuid`.

## Phase 1: Choose the test type per case

Every case is one of these types — a suite can mix them across cases:

- **`tool_call`** — deterministic. Assert the agent calls tool X with args Y.
  No judge model, no token cost. Reach for this whenever the correct behavior is
  a specific action rather than a judgment about wording. Each argument is
  checked by a **match type** (see Phase 2).
- **`response`** — quality. An LLM judge scores the reply against `criteria`.
  Needs an existing `evaluator_uuid` plus a `criteria` variable value, and costs
  judge tokens per run.
- **`conversation`** — quality across a full multi-turn exchange, graded by a
  `conversation`-type evaluator. Use only when the thing you're checking spans
  several turns rather than a single reply.

For each behavior you want to cover, decide the type. If a `response` case needs
a judge that doesn't exist yet, hand off to `/design-evaluator` to create it,
then come back with the `evaluator_uuid`.

**Match the evaluator kind to the test.** A `response` case must be graded by an
evaluator of type `llm` (a reply read *with its conversation history*) — **not
`llm-general`**, which is for context-free input/output pairs and is rejected for
response tests. A `conversation` case needs a `conversation`-type evaluator. If
you send `/design-evaluator` off to make a judge, name the type it should be.

## Phase 2: Draft the cases

Start from the hypothesis — what must be true of the agent — and write the
failing and edge cases, not just the happy path (empty input, out-of-policy
requests, ambiguous asks, tool-args boundaries). Each item has:

- **name** — unique within the batch.
- **conversation_history** — a list of `{role, content}` turns leading up to the
  point of evaluation.
- **evaluators** — a list of `{evaluator_uuid, variable_values: {criteria: ...}}`
  for `response` cases.
- **tool_calls** — for `tool_call` cases: the expected calls, each argument
  checked by a match type. Choose the loosest type that still catches a real
  mistake:
  - `{"match_type": "exact", "value": ...}` — must equal, for closed-form args
    (ids, dates, enums).
  - `{"match_type": "llm_judge", "criteria": "..."}` — judged for meaning, where
    surface form varies.
  - `{"match_type": "any"}` — only that the argument was passed.
  - `accept_any_arguments: true` on a call skips argument checks entirely (asserts
    only that the tool was called).

See the full test-item shapes (response and tool_call) in
[`../../references/config-shapes.md`](../../references/config-shapes.md). Show
the drafted cases and confirm before uploading.

## Phase 3: Upload

For many cases, prefer `bulk-create` (at most 500 items per request, names
unique within the batch). Pass `--agent-uuids` to link every created test to the
agent on creation (omit to link none); `--language` writes to each test's
`config.settings.language` (omit to leave unset):

```bash
calibrate tests bulk-create \
  --type tool_call \
  --tests '[<items>]' \
  --agent-uuids '["<agent_uuid>"]' \
  --language <lang> \
  --output-format json
```

For a single case, use `create` — `-c/--config-param` is the test config, a JSON
object with three top-level keys (`history`, `evaluation`, `settings`):

```bash
calibrate tests create \
  --name "<name>" \
  --type response \
  --config-param '<json>' \
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

- **Scope what to test first** → `/design-eval-plan`
- **Need a judge** for a `response` case → `/design-evaluator`
- **Generate a diverse batch from dimensions** → `/generate-synthetic-data`
- **Already have a dataset** to turn into tests → `/import-dataset`
- **Run the tests** you just built → `/run-tests`
- **Full first-eval flow** → `/onboard`
