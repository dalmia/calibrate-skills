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

## Get the latest instructions

Both the skill and the CLI on this machine can be months behind. Update both
before anything else, following
[`../../references/startup.md`](../../references/startup.md):

```bash
npx -y skills update run-tests -g -y ; npx -y skills update run-tests -p -y
```

```bash
have=$(calibrate version < /dev/null 2>/dev/null | head -1 | awk '{print $2}')
want=$(curl -fsS https://api.github.com/repos/dalmia/calibrate-cli/releases/latest 2>/dev/null | sed -n 's/.*"tag_name": *"v\{0,1\}\([^"]*\)".*/\1/p' | head -1)
if [ -z "$have" ]; then
  brew install dalmia/tap/calibrate
elif [ -n "$want" ] && [ "$have" != "$want" ]; then
  brew update >/dev/null 2>&1 && brew upgrade dalmia/tap/calibrate >/dev/null 2>&1
fi
calibrate version < /dev/null 2>/dev/null | head -1 || echo "calibrate is not installed"
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

  **Linking is rejected when the test was built for the other kind of agent.**
  A `general` test only links to a `general` agent; `response` and
  `conversation` tests only link to a `conversation` agent; a `tool_call` test
  links to whichever kind matches the key it carries (`input` or `history`).
  Tell the user plainly that the test was written for a different kind of agent
  than this one, so it can't be run here — a test has to be built for the kind
  of agent it runs against. Either pick a matching agent, or send them to
  `/build-test-suite` to write cases for this one.

- **Some linked tests should come off** → unlink them in one call with
  `calibrate agent-tests bulk-unlink --agent-uuid <agent_uuid> --test-uuids '["<test_uuid>", ...]'`
  (check `--help` for the exact flags). Tests that weren't linked are skipped;
  the response's `deleted_count` is how many links were removed. Confirm the
  list with the user first.

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
  `calibrate agent-tests run-batch` as the batch option. An agent can come back
  skipped with reason `over_row_limit` (more linked tests than the workspace
  allows in one run): tell the user, and offer to run a subset with
  `--test-uuids`.

## Phase 3: Poll for results

Poll the run until the status is final, backing off between polls (see the
polling pattern in `agent-mode.md`). Report progress each time; never block
silently.

```bash
calibrate agent-tests get-run --task-id <task_id> --output-format json
```

Continue until `status` is `completed` or `failed`. Report only the status the
command actually returns — do not assume completion.

Read the flags on the result before you present it:

- `error` is a string (the reason the run couldn't be carried out), not a
  boolean. If it is set, report that reason in plain words instead of a score.
- `aborted` — someone stopped the run. Results so far are kept; cases that never
  ran have `not_run` set and count as neither passed nor failed.
- `stopped_early` — the run gave up before starting every case because too many
  failed in a row.
- `unanswered_tests` — cases where the agent or the judge couldn't be reached.
  These are included in `failed`, but they say nothing about the agent
  (`unanswered` is set on each such case, with the error in `reasoning`).

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

If the run was stopped, ended early, or has unanswered cases, say so right under
the headline count and don't read the pass rate as a verdict on the agent. For
unanswered cases, offer to re-run once the agent is reachable. Show those and
cases that never ran in their own groups, not under FAILURES. In plain words:
"4 of the 20 tests couldn't get an answer from your agent, so I'd treat 12/16 as
the real score" — not field names.

For a big run, `get-run` can return light rows per case (`mode=summary`: ID,
name, verdict, short reason). Read a single case in full with
`GET /agent-tests/run/{task_id}/results/{test_uuid}` (`test_uuid` is on each
case) when the user asks why one failed.

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

- **No tests, or not enough** → `/build-test-suite` or `/import-dataset`
- **Compare models on these tests** → `/benchmark-models`
- **Is the judge trustworthy?** → `/calibrate-evaluator`
- **Tune the judge** → `/iterate-evaluator`
- **Run the full first-eval flow** → `/onboard`
