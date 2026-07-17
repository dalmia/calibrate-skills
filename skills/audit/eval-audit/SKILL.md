---
name: eval-audit
description: Audit an existing Calibrate setup and surface problems, most serious
  first — thin test coverage, wrong evaluator types, judges trusted without
  calibration, agents that can't be reached. Use when the user says "audit my
  evals", "is my eval setup any good", "review my tests", "what's wrong with my
  evaluation", or "check my Calibrate setup".
argument-hint: "[agent-uuid-or-name]"
---

# Audit an evaluation setup

A read-only check-up of an existing Calibrate setup. Inspects the agent, its
tests, and its evaluators, and reports what's weak — ranked by how much it
undermines trust in the numbers — with the skill that fixes each one. Changes
nothing. Adapted from hamelsmu's *eval-audit* skill
(https://github.com/hamelsmu/evals-skills, MIT).

See [`../../references/methodology.md`](../../references/methodology.md) for the
bar each check measures against and
[`../../references/agent-mode.md`](../../references/agent-mode.md) for reading
output. Keep what you *say* to the user plain — see
[`../../references/voice.md`](../../references/voice.md).

## Phase 0: Setup check

```bash
calibrate whoami
```

If unauthenticated, guide the user to `calibrate login`.

## Phase 1: Gather the setup

Resolve the agent (from `$ARGUMENTS` or `calibrate agents list`), then pull its
tests, its runs, and the evaluators in play:

```bash
calibrate agents list --output-format json
calibrate agent-tests list-for-agent --agent-uuid <agent_uuid> --output-format json
calibrate agent-tests list-runs-for-agent --agent-uuid <agent_uuid> --output-format json
calibrate evaluators list --output-format json
```

Read the actual test configs and evaluator versions you need to judge the checks
below — don't audit from counts alone.

## Phase 2: Run the checks

Work through these. Each is a finding only if it actually holds for this setup.

- **Reachability** — can Calibrate reach the agent at all? If runs are failing
  for connection reasons, nothing else matters. (Severity: critical.)
- **Right evaluator kind for response tests** — response tests must be graded by
  a judge that reads the reply *with its conversation history*, not a
  standalone input/output judge. A response test wired to the wrong judge kind
  either errors or scores blind to the conversation. (Severity: high.)
- **Judges calibrated against people** — is any evaluator being trusted at scale
  without ever being checked against human labels? An uncalibrated judge is a
  guess; every number it produces inherits that. (Severity: high.)
- **Coverage shape** — do the tests include failure and edge cases, or only
  happy-path? A suite that only asserts the obvious can't catch regressions.
  (Severity: medium.)
- **One judge doing too much** — is a single evaluator grading several unrelated
  qualities at once? Split into one evaluator per dimension. (Severity: medium.)
- **Match-type fit** — are tool-call arguments checked with the right match type
  (exact where deterministic, judged where semantic, any where only presence
  matters)? Over-strict exact matches cause false failures; over-loose `any`
  hides real ones. (Severity: low–medium.)
- **Staleness** — have the tests been run recently, or is the last run old
  against a since-changed agent? (Severity: low.)

## Phase 3: Report, worst first

Rank findings by severity and lead with the most serious. For each, state the
problem plainly, why it undermines trust, and the fix:

```
Eval audit — <agent>

CRITICAL
  • <finding> — <why it matters> → <skill>

HIGH
  • <finding> — <why> → <skill>

MEDIUM / LOW
  • ...

Looks good
  • <checks that passed>
```

Fix routing:

- reachability → `/connect-agent`
- wrong evaluator kind / uncalibrated judge → `/design-evaluator`,
  `/calibrate-evaluator`, `/iterate-evaluator`
- thin coverage → `/design-eval-plan`, `/build-test-suite`,
  `/generate-synthetic-data`
- one judge doing too much → `/design-eval-plan` (re-decompose), `/design-evaluator`
- stale / never analyzed → `/run-tests`, `/analyze-failures`

Report only what you verified. If a check couldn't be run, say so rather than
guessing a verdict.

## Handoffs

- **Design/redesign the plan** → `/design-eval-plan`
- **Fix a judge** → `/calibrate-evaluator`, `/iterate-evaluator`
- **Fill coverage gaps** → `/build-test-suite`, `/generate-synthetic-data`
- **Dig into a specific run's failures** → `/analyze-failures`
