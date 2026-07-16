---
name: design-evaluator
description: Author a new evaluator (LLM or audio judge) in Calibrate and set its
  first live version. Use when the user says "create an evaluator", "add a judge",
  "score responses on X", "make an LLM judge", or "define a rubric".
argument-hint: "[evaluator-name]"
---

# Design an evaluator

Create a new evaluator — a versioned LLM/audio judge — and its first live
version. An evaluator scores agent output against a rubric you write. `create`
makes v1 and sets it live. Ask at each step; if `$ARGUMENTS` already carries a
name, pre-fill it and skip that question.

See [`../../references/agent-mode.md`](../../references/agent-mode.md) for how to
read command output (TOON/JSON) and
[`../../references/config-shapes.md`](../../references/config-shapes.md) for the
`version-param` shape. Keep what you *say* to the user plain — see
[`../../references/voice.md`](../../references/voice.md).

An evaluator is a **versioned** judge: the object holds a history of versions,
one of which is live. Here you author v1. Later tuning is a separate flow
(`/iterate-evaluator`).

## Phase 0: Setup check

```bash
calibrate agents list   # real read — 401 = not signed in, or key for the wrong deployment
```

If unauthenticated, guide the user:

```bash
calibrate login
```

An API key is created under **Workspace settings → API keys**
(https://calibrate.artpark.ai/workspace-settings?tab=api-keys). No account →
send them to https://calibrate.artpark.ai to sign up.

List existing evaluators so you don't duplicate one — and so the user can reuse
or tune a built-in default instead of authoring from scratch:

```bash
calibrate evaluators list --output-format json
```

The list includes the built-in defaults. If a judge already covers the intent,
present it and ask whether to reuse it (hand to `/build-test-suite`) rather than
create another. If a default is close but its rubric needs adjusting, don't
rebuild it here — defaults are editable, so hand to `/iterate-evaluator` to tune
it. Author from scratch only when no default is close.

## Phase 1: Decide what it judges

Two axes fix the evaluator's shape. Ask both before writing any prompt.

- **data-type** — the modality the judge reads: `text` (grades a text reply or
  transcript) or `audio` (grades synthesized speech / audio output).
- **output-type** — how it scores:
  - `binary` — pass/fail. Uses the default `Correct` / `Wrong` labels unless you
    override them. Best for "did the reply do X?" checks.
  - `rating` — a labeled scale (e.g. 1–5). Requires an `output_config` that
    defines each scale point and its label. Use when a graded judgment is more
    useful than pass/fail.

If `rating`, collect the scale points and a short label for each.

## Phase 2: Write the judge prompt and variables

Draft the `system_prompt`. It may contain `{{variable}}` placeholders — commonly
a single `{{criteria}}` — filled per-test-case from that test's
`variable_values`. This lets one evaluator score many different criteria.

Declare each variable as `{"name", "description", "default"}`.

**Warn the user before proceeding:** variable **names are frozen after v1**.
Later versions can change a variable's description or default, but cannot add,
remove, or rename one. Choose the variable set deliberately now — a good default
is a single `criteria` variable, which keeps the judge reusable across tests.

Show the drafted prompt, variables, and (for rating) the scale, and confirm.
See the `version-param` shape in
[`../../references/config-shapes.md`](../../references/config-shapes.md).

## Phase 3: Choose the judge model

Pick a `judge_model` sized to the expected case volume. Prefer a cheap-enough
model (e.g. a mini model) unless the rubric genuinely needs a stronger one — a
judge runs once per test case, so cost scales with the suite. Model names are
provider-qualified, e.g. `openai/gpt-4.1`.

## Phase 4: Create

Show a summary and confirm before creating:

```
Evaluator summary
  Name:        <name>
  Data type:   text | audio
  Output type: binary | rating
  Judge model: <judge_model>
  Variables:   <names>
```

```bash
calibrate evaluators create \
  --name "<name>" \
  --data-type text \
  --evaluator-type <type> \
  --output-type binary \
  --version-param '{"judge_model":"openai/gpt-4.1","system_prompt":"...{{criteria}}...","variables":[{"name":"criteria","description":"what must hold","default":""}]}' \
  --output-format json
```

For a `rating` evaluator, add the scale to `version-param` — an ordered array of
scale points under `scale`, not a `labels` map:
`"output_config": {"scale": [{"value": 1, "name": "..."}, {"value": 5, "name": "..."}]}`.

`--name` must be unique within the workspace. Capture `evaluator_uuid` from the
JSON response — never fabricate it. This creates the evaluator and sets **v1
live**.

## Phase 5: Sanity check + next steps

Confirm the version landed and is live:

```bash
calibrate evaluators get --evaluator-uuid <evaluator_uuid>
```

This shows the full version history. Report plainly:

```
Evaluator created
  ID:      <evaluator_uuid>
  Name:    <name>
  Live:    v1
```

An unvalidated judge is a guess. Strongly recommend validating it against human
labels before trusting it at scale — a judge that disagrees with people will
quietly skew every eval that uses it.

## Handoffs

- **Validate this judge against human labels** (strongly recommended before
  relying on it) → `/calibrate-evaluator`
- **Add or tune versions later** → `/iterate-evaluator`
- **Attach this evaluator to response test cases** → `/build-test-suite`
- **Run the full first-eval flow** → `/onboard`
