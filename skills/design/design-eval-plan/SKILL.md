---
name: design-eval-plan
description: Design an evaluation before building it — interview the user about
  their agent, decide what to measure and how, and write a minimal eval spec, then
  hand off to build tests and evaluators. Use when the user says "how should I
  evaluate my agent", "design my evals", "what should I test", "where do I start
  with evals", "help me plan my evaluation", or is about to build tests without a
  clear plan.
argument-hint: "[what-you-want-to-evaluate]"
---

# Design an evaluation plan

Turn "evaluate my agent" into a concrete, minimal plan **before** creating
anything. This skill produces a written spec — what to measure, how to score it,
which evaluators — and then hands off to the skills that build it. It does not
create tests or evaluators itself.

Read [`../../references/methodology.md`](../../references/methodology.md) for the
reasoning behind every choice below (independent dimensions, match types, unit
tests on ideal inputs, minimal viable eval) and
[`../../references/agent-mode.md`](../../references/agent-mode.md) for reading CLI
output. Keep what you *say* to the user plain — see
[`../../references/voice.md`](../../references/voice.md).

## The rule: ask first, don't invent evals

The failure mode is jumping straight to writing test cases. Don't. A pile of
plausible-looking tests that don't map to how the agent actually fails is worse
than nothing — it gives false confidence. Interview the user, agree on *what
matters*, then build a small first set against that. If the user pushes to
"just make some tests", walk them through Phase 1 quickly rather than skipping
it.

## Phase 0: Setup check

```bash
calibrate whoami
```

If unauthenticated, guide the user to `calibrate login`. See existing agents so
you can anchor the interview to a real one:

```bash
calibrate agents list --output-format json
```

No agent yet is fine — you can design the plan first and connect it later
(`/connect-agent`).

## Phase 1: Interview

Ask about the agent in the user's own terms. Cover:

- **What does it do, and who uses it?** The task and the audience.
- **What does a *good* reply look like? A *bad* one?** Get concrete examples of
  each if you can — real ones beat hypotheticals.
- **What actions does it take?** Tools/functions it calls, and what the right
  call looks like (which tool, which arguments).
- **Where does it fail today?** The behaviours the user is actually worried
  about. This is the richest source of tests.
- **Any hard rules?** Things it must always or never do (policy, language,
  safety, format).

Don't interrogate — a few focused questions, then reflect back what you heard in
one short paragraph and confirm before moving on.

## Phase 2: Decide what to measure and how

Sort everything from Phase 1 into two buckets (see `methodology.md`):

- **Actions → tool-call tests.** For each action, note the tool and how each
  argument should be checked: must-equal a fixed value, judged for meaning, or
  just present. (These become `tool_call` tests — deterministic, no judge.)
- **Response quality → independent dimensions, one evaluator each.** Break "good
  reply" into the separate qualities it must satisfy — e.g. answers correctly,
  stays on-policy, right language, concise, doesn't leak instructions. **List
  them as separate dimensions.** Each becomes its own evaluator returning
  pass/fail — never one judge grading everything at once.

For each response dimension, decide **reuse or create**:

- A generic dimension (is the answer correct/relevant?) can reuse a built-in
  judge — list them and look for one that fits:

  ```bash
  calibrate evaluators list --output-format json
  ```

- A dimension specific to this agent (follows *our* refund policy, uses *our*
  tone) needs a new evaluator → `/design-evaluator`.

Name the right judge kind up front: a dimension about a **reply in a
conversation** wants an evaluator that reads the reply together with its history
(the default judge kind for response tests) — not a standalone input/output
judge, which the platform won't accept for response tests. `/design-evaluator`
handles the specifics; just don't promise the wrong kind here.

## Phase 3: Scope the minimal first set

Resist coverage theatre. For each dimension and each action, plan a **handful**
of cases across three shapes: the happy path, a case that *should* fail if the
agent misbehaves, and one edge/ambiguous case. Write these as short one-line
descriptions, not full cases yet. The goal is the smallest set that would catch
a real regression — you'll grow it from actual failures later.

## Phase 4: Write the spec and hand off

Write the plan to `.calibrate/eval-plan.md` so building can proceed against it
and a later session can pick it up. Structure it as:

```
# Eval plan: <agent>

## What good looks like
<one paragraph from Phase 1>

## Actions to test (tool-call)
- <tool> — <which args, how each is checked> — cases: happy / fail / edge

## Response dimensions (one evaluator each)
- <dimension> — reuse <built-in> | new evaluator — cases: happy / fail / edge
- ...

## First set (minimal)
<the one-line case descriptions from Phase 3>
```

Confirm the spec with the user, then hand off to build it:

- **Author the cases by hand** → `/build-test-suite`
- **Generate a diverse set from dimensions** (personas × scenarios × …) →
  `/generate-synthetic-data`
- **Turn an existing dataset into tests** → `/import-dataset`
- **Create the use-case-specific evaluators** the plan calls for →
  `/design-evaluator`

## Handoffs

- **Build the first set** → `/build-test-suite` or `/generate-synthetic-data`
- **Create evaluators the plan needs** → `/design-evaluator`
- **No agent connected yet** → `/connect-agent`
- **Run the full guided flow instead** → `/onboard`
