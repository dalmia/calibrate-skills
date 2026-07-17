---
name: analyze-failures
description: Read a finished test run, group the failures into themes, and turn
  each theme into a concrete next action. Use when the user says "why did my tests
  fail", "analyze the failures", "what's going wrong", "categorize the errors",
  "what should I fix", or after a run comes back with failures.
argument-hint: "[agent-uuid-or-task-id]"
---

# Analyze test failures

A run that says "6 of 20 failed" isn't useful until you know *why* and *what to
do*. This skill reads the failing cases, groups them into a few themes, and turns
each theme into a specific next step. Adapted from hamelsmu's *error-analysis*
skill (https://github.com/hamelsmu/evals-skills, MIT); drives `calibrate
agent-tests`.

See [`../../references/agent-mode.md`](../../references/agent-mode.md) for reading
command output. Keep what you *say* to the user plain — see
[`../../references/voice.md`](../../references/voice.md).

## Phase 0: Setup check

```bash
calibrate whoami
```

If unauthenticated, guide the user to `calibrate login`.

## Phase 1: Get the run

If `$ARGUMENTS` is a run/task id, read it directly. Otherwise resolve the agent
and find the run to analyze:

```bash
calibrate agents list --output-format json
calibrate agent-tests list-runs-for-agent --agent-uuid <agent_uuid> --output-format json
calibrate agent-tests get-run --task-id <task_id> --output-format json
```

Use the most recent completed run unless the user names another. Only analyze a
run whose status is final — say so if it hasn't finished.

## Phase 2: Read every failure

Pull the failing cases and, for response-judged ones, the **judge's reasoning
verbatim**. Read them — don't summarize from counts. For each failure note:

- what the test expected,
- what the agent actually did / said,
- the judge's stated reason (for response cases) or the argument diff (for
  tool-call cases).

## Phase 3: Group into themes

Cluster the failures by root cause, not by test name. Typical clusters:

- **Agent is wrong** — it genuinely misbehaves (wrong tool, wrong value,
  off-policy reply). Real defects.
- **Test/expectation is wrong** — the case asserts something the agent needn't
  do, or the bar is miscalibrated. Fix the test, not the agent.
- **Judge is wrong** — the reply is fine but the evaluator scored it fail (or
  vice-versa). The judge needs tuning, or hasn't been calibrated against people.
- **Known non-issue** — a case where the agent made a tool call with no text
  reply often surfaces as FAIL even though it's correct behaviour. Flag it as a
  likely non-issue unless the test's whole point was that tool call.

State each theme in one sentence with a count and one or two example cases.

## Phase 4: Turn each theme into an action

Lead with the outcome, failures first, then map each theme to a next step:

```
Run <task_id> — <n failed> / <total>

THEME: <one-line description> (<count>)
  examples: <case>, <case>
  → <the action>
```

Actions to recommend:

- **Agent is wrong** → the defect is real; the user fixes their agent. If the
  behaviour isn't covered well, expand the suite → `/build-test-suite` or
  `/generate-synthetic-data`.
- **Test/expectation wrong** → amend the case (`calibrate tests update`) or
  drop it.
- **Judge wrong** → tune the judge → `/iterate-evaluator`, and if it was never
  checked against people, → `/calibrate-evaluator` first (you may be tuning
  against a bar no human agrees with).
- **Known non-issue** → note it, don't treat as a regression.

Don't invent a fix you can't ground in a failure you actually read. If a theme is
ambiguous, say what you'd need to disambiguate it.

## Handoffs

- **Judge is scoring wrong** → `/iterate-evaluator`, `/calibrate-evaluator`
- **Coverage is thin** → `/build-test-suite`, `/generate-synthetic-data`
- **Re-run after fixes** → `/run-tests`
- **Audit the whole pipeline** → `/eval-audit`
