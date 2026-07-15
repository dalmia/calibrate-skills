---
name: run-tests
description: Link tests to an agent, run them, poll for results, and present
  pass/fail with judge reasoning. Use when the user says "run my tests", "run
  the test suite", "evaluate my agent" (and they already have tests), "run agent
  tests", or "check if my agent passes". Use onboard instead when the user is
  starting from scratch with no tests yet.
argument-hint: "[agent-uuid-or-name]"
---

# Run agent tests

Run an agent's linked tests, poll the background job, and report which cases
passed or failed. Drives the `calibrate agent-tests` commands. Ask at each step;
if `$ARGUMENTS` carries an agent UUID or name, pre-fill it and skip that
question.

See [`../../references/agent-mode.md`](../../references/agent-mode.md) for how to
read command output (TOON/JSON) and the polling pattern used in Phase 4. Keep
what you *say* to the user plain — see
[`../../references/voice.md`](../../references/voice.md).

## Phase 0: Setup check

```bash
calibrate agents list   # real read — 401 = not signed in, or key for the wrong deployment
```

If unauthenticated, guide the user to `calibrate login` and stop until they are
signed in. Confirm first whether they're on the hosted service
(https://calibrate.artpark.ai) or a self-hosted deployment — the latter needs
`calibrate configure --no-interactive --server-url https://<their-api-host>` set
once *before* `calibrate login`, or its key will 401.
See [`../../overview/calibrate-resources/SKILL.md`](../../overview/calibrate-resources/SKILL.md)
→ *Which Calibrate*.

Resolve the agent. If `$ARGUMENTS` is already a UUID, use it. If it's a name, or
you need to pick one:

```bash
calibrate agents list --output-format json
calibrate agents resolve --names '["<name>"]'
```

Present a numbered list if there's ambiguity and confirm the `agent_uuid` before
going further. Never guess a UUID.

## Phase 1: Ensure tests are linked

Tests only run once they're linked to the agent. Check what's linked:

```bash
calibrate agent-tests list-for-agent --agent-uuid <agent_uuid> --output-format json
```

- **No tests at all** → the agent has nothing to run. Hand off to
  `/build-test-suite` (write cases) or `/import-dataset` (bring an existing
  dataset in), then come back.
- **Tests exist but the ones the user wants aren't linked yet** → link them:

  ```bash
  calibrate agent-tests link --agent-uuid <agent_uuid> \
    --test-uuids '["<test_uuid>", ...]'
  ```

  Already-linked tests are skipped, so re-linking is safe.

Confirm the linked set matches what the user expects before running.

## Phase 2: Launch the run

Run all linked tests and capture the `task_id`:

```bash
calibrate agent-tests run --agent-uuid <agent_uuid> --output-format json
```

Read `task_id` from the JSON. Never fabricate it — if the field is missing,
report the error and stop.

- To run only a subset, add `--test-uuids '["<test_uuid>", ...]'` (each ID must
  be linked to the agent).
- To run across **multiple agents** in one shot, mention
  `calibrate agent-tests run-batch` as the batch option.

## Phase 3: Poll for results

Poll the run until the status is final, backing off between polls (see the
polling pattern in `agent-mode.md`). Report progress each time; never block
silently.

```bash
calibrate agent-tests get-run --task-id <task_id> --output-format json
```

Continue until `status` is `completed` or `failed`. Report only the status the
command actually returns — do not assume completion.

## Phase 4: Present results

Lead with the outcome, **failures first**. For each case show PASS or FAIL and,
for response-judged cases, the judge's reasoning verbatim. Use only numbers and
verdicts present in the output — never invent a score or a count.

```
Test run <task_id> — <n passed> / <total>

FAILURES
  ✗ <test name> — <judge reasoning>
  ...

PASSED
  ✓ <test name>
  ...
```

**Known pattern to flag, not to over-report:** a case where the agent made a
tool call without a text reply often surfaces as a FAIL even though it's usually
correct behavior. Call this out as a likely non-issue rather than treating it as
a real regression — unless the test's hypothesis was specifically about that
tool call, in which case it matters.

## Phase 5: Compare against history

Put this run in context against prior baselines:

```bash
calibrate agent-tests list-runs-for-agent --agent-uuid <agent_uuid> --output-format json
```

Highlight regressions (cases that passed before and now fail) and new passes.

## Handoffs

- **Understand *why* cases failed** → `/analyze-failures`
- **No tests, or not enough** → `/build-test-suite`, `/generate-synthetic-data`,
  or `/import-dataset`
- **Compare models on these tests** → `/benchmark-models`
- **Is the judge trustworthy?** → `/calibrate-evaluator`
- **Tune the judge** → `/iterate-evaluator`
- **Run the full first-eval flow** → `/onboard`
