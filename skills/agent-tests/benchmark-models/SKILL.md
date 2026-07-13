---
name: benchmark-models
description: Benchmark one agent's linked tests across several models and compare
  them on a leaderboard. Use when the user says "benchmark models", "compare
  models", "which model is best", "run a model bake-off", or "compare gpt vs
  claude on my tests".
argument-hint: "[agent-uuid-or-name]"
---

# Benchmark models

Run an agent's linked tests against multiple models and rank the models on a
leaderboard. Drives the `calibrate agent-tests benchmark` /
`get-benchmark` commands. Ask at each step; if `$ARGUMENTS` already carries an
agent UUID or name, pre-fill it and skip that question.

See [`../../references/agent-mode.md`](../../references/agent-mode.md) for how to
read command output (TOON/JSON) and for the launch-and-poll pattern used in
Phase 5. Keep what you *say* to the user plain — see
[`../../references/voice.md`](../../references/voice.md).

## Phase 0: Setup check

```bash
calibrate whoami
```

If unauthenticated, guide the user:

```bash
calibrate login
```

Resolve the agent to a UUID. If `$ARGUMENTS` is already a UUID, use it. If it's
a name, resolve it; if nothing was passed, list and ask which agent:

```bash
calibrate agents list --output-format json
calibrate agents resolve --names '["<name>"]' --output-format json
```

## Phase 1: Confirm the agent has linked tests

Only **linked** tests are benchmarked, so confirm the agent has some:

```bash
calibrate agent-tests list-for-agent --agent-uuid <agent_uuid> --output-format json
```

If the list is empty, don't launch — the benchmark would have nothing to run.
Hand off first:

- **No tests written yet** → `/build-test-suite`, or `/import-dataset` to bring
  in an existing dataset.
- **Tests exist but aren't linked** → `/run-tests` (a single-model run links the
  tests to the agent).

Come back here once at least one test is linked. Capture the linked test UUIDs;
you'll need them if the user wants to restrict the subset in Phase 4.

## Phase 2: Choose the model set

Collect the list of models to compare. Model names are **provider-qualified**,
e.g. `openai/gpt-4.1`, `anthropic/claude-sonnet-4`. Ask the user which models
they want to pit against each other; two or more is the point.

## Phase 3: Confirm scope and cost

Warn before launching. Benchmarking **N** models over **M** linked tests is
**N x M** agent runs, plus judge tokens for every response-typed test. Give a
one-line order-of-magnitude estimate — e.g. "3 models x 20 tests = 60 agent
runs, plus judging" — and confirm before spending it.

Offer to narrow the run: `--test-uuids` restricts the benchmark to a subset of
the linked tests (each ID must be linked). Omit it to run all linked tests.

## Phase 4: Launch

```bash
calibrate agent-tests benchmark \
  --agent-uuid <agent_uuid> \
  --models '["openai/gpt-4.1","anthropic/claude-sonnet-4"]' \
  --output-format json
```

To restrict to a subset of linked tests, add:

```bash
  --test-uuids '["<test_uuid>", "..."]'
```

Capture `task_id` from the JSON response. Never fabricate it — if it's missing,
report the structured error instead of guessing.

## Phase 5: Poll

The benchmark runs as a background job. Poll until the status is final
(`completed` / `failed`), backing off between polls, per
[`../../references/agent-mode.md`](../../references/agent-mode.md):

```bash
calibrate agent-tests get-benchmark --task-id <task_id> --output-format json
```

Report progress to the user as it advances; don't block silently.

## Phase 6: Present the leaderboard

Build a leaderboard from the terminal `get-benchmark` result — one row per
model with its pass-rate across the tests, **best first**:

```
Model                        Pass-rate
anthropic/claude-sonnet-4    18/20  (90%)
openai/gpt-4.1               16/20  (80%)
```

Use only the numbers the command returned. **Never invent scores.**

Two caveats to surface with the ranking:

- **Trust the judge before trusting the ranking.** Scores are only as good as
  the evaluators producing them. If the response judges haven't been calibrated
  against human labels, a small gap between models may be noise, not signal —
  point the user to `/calibrate-evaluator` before over-reading it.
- **Tool-call-without-text is a known non-failure.** A turn where the agent
  emits a tool call and no user-facing text is expected behavior, not a miss —
  don't count it against a model.

## Handoffs

- **Run tests on a single model (and link them)** → `/run-tests`
- **Trust the judge before trusting the ranking** → `/calibrate-evaluator`
- **Tune the judge that produced these scores** → `/iterate-evaluator`
- **Run the full onboarding flow end to end** → `/onboard`
