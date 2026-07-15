---
name: generate-synthetic-data
description: Create a diverse set of synthetic test inputs by naming dimensions
  (persona, scenario, difficulty, language, …) and combining their values into
  varied cases, then upload them as tests. Use when the user says "generate test
  data", "create synthetic tests", "I need more test cases", "make diverse
  inputs", or "cover more scenarios".
argument-hint: "[agent-uuid-or-name]"
---

# Generate synthetic test inputs

Build a diverse batch of test cases by combining **dimensions** rather than
writing inputs one by one. This gives coverage that spans the real variation your
agent sees, instead of ten near-identical happy-path prompts. Adapted from
hamelsmu's *generate-synthetic-data* skill
(https://github.com/hamelsmu/evals-skills, MIT); drives `calibrate tests
bulk-create`.

See [`../../references/methodology.md`](../../references/methodology.md) for why
diverse inputs matter, [`../../references/config-shapes.md`](../../references/config-shapes.md)
for the test-item shape, and
[`../../references/agent-mode.md`](../../references/agent-mode.md) for reading CLI
output. Ask at each step; if `$ARGUMENTS` carries an agent UUID or name, pre-fill
it. Keep what you *say* to the user plain — see
[`../../references/voice.md`](../../references/voice.md).

Best run against an eval plan (`/design-eval-plan`) — the plan tells you which
dimensions and behaviours matter so the generated set is targeted, not random.

## Phase 0: Setup check

```bash
calibrate whoami
```

If unauthenticated, guide the user to `calibrate login`. Confirm the target
agent if these tests will be linked (`calibrate agents list --output-format
json`), or note that they'll be created unlinked.

## Phase 1: Name the dimensions

A dimension is one axis of variation; each has a small set of values. Work them
out with the user from how their agent is actually used. Common axes:

- **persona** — who's talking (new vs returning user, expert vs novice, terse vs
  rambling)
- **scenario** — what they want (the main intents the agent handles)
- **difficulty** — clean request vs ambiguous vs adversarial / out-of-policy
- **input variation** — phrasing, misspellings, code-mixing, multiple values in
  one utterance
- **language / locale** — if the agent serves more than one

Keep each list short (2–5 values). The point is spread, not a combinatorial
explosion.

## Phase 2: Combine and sample

The full cross-product of dimensions is the space of possible cases. It grows
fast — 4 axes of 4 values is 256 — so **sample deliberately** rather than taking
all of it:

- guarantee every value of every dimension appears at least once,
- cover the combinations the eval plan flagged as risky (e.g. adversarial ×
  every scenario),
- then fill with a spread of the rest up to the batch size you agreed.

Tell the user how many cases you'll generate and roughly how they're distributed
before generating. Never silently cap — if you're sampling down from a larger
space, say so and say how many you dropped.

## Phase 3: Render each tuple into a case

Turn each sampled tuple into a concrete test item. For each, write a realistic
`conversation_history` — the turns leading up to the agent's reply, as that
persona in that scenario would actually say it (not a templated stem). Then
attach the expectation:

- **tool-call cases** — the expected `tool_calls` with the right match type per
  argument (exact / judged / any).
- **response cases** — the evaluator(s) to grade the reply, one per dimension
  being checked, with each judge's `criteria`.

See the item shapes and match types in
[`../../references/config-shapes.md`](../../references/config-shapes.md). If a
response case needs an evaluator that doesn't exist yet, hand off to
`/design-evaluator`.

**Dedupe.** Synthetic generation drifts toward samey inputs — drop
near-duplicates so the batch stays genuinely varied. Give each case a unique,
descriptive name (e.g. `<scenario>-<persona>-<n>`).

## Phase 4: Review, then upload

Show the user a sample of the generated cases (a few from different corners of
the space) and the total count, and confirm before uploading. Then bulk-upload
in chunks of ≤500, linking to the agent if wanted:

```bash
calibrate tests bulk-create \
  --type <tool_call|response> \
  --tests '[<items>]' \
  --agent-uuids '["<agent_uuid>"]' \
  --language <lang> \
  --output-format json
```

Capture the created `test_uuid`s from the JSON; never fabricate one. If a chunk
fails, surface the error, fix that chunk, and retry it — don't proceed as if it
succeeded.

## Handoffs

- **Design the plan these dimensions serve** → `/design-eval-plan`
- **Need an evaluator for response cases** → `/design-evaluator`
- **Hand-author specific cases instead** → `/build-test-suite`
- **Run the generated tests** → `/run-tests`
