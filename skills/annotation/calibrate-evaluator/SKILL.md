---
name: calibrate-evaluator
description: Calibrate an LLM judge against human labels — build an annotation
  task, collect human annotations, run the judge on the same items, measure
  human-vs-judge agreement, and tune the evaluator until it matches humans. Use
  when the user says "is my judge any good", "check my evaluator against humans",
  "measure agreement", "calibrate the judge", or "can I trust the LLM judge".
argument-hint: "[evaluator-uuid-or-name]"
---

# Calibrate an evaluator against humans

An LLM judge is only trustworthy once it agrees with people. This is Calibrate's
signature loop: label a sample by hand, have the judge label the same sample,
measure agreement, and tune the judge until the gap closes. Drives the
`calibrate annotation-tasks` and `evaluators` commands.

References: [`../../references/agent-mode.md`](../../references/agent-mode.md)
(output/polling), [`../../references/config-shapes.md`](../../references/config-shapes.md)
(item + evaluator shapes). Keep what you *say* to the user plain — see
[`../../references/voice.md`](../../references/voice.md).

## Phase 0: Setup check

```bash
calibrate agents list   # real read — 401 = not signed in, or key for the wrong deployment
```

Resolve the target evaluator and confirm its live version + data-type:

```bash
calibrate evaluators get --evaluator-uuid <id> --output-format json
```

If the user gave a name, `calibrate evaluators list` to find the UUID first.

## Phase 1: Assemble the sample

Gather 20–50 items the evaluator will judge. Real agent outputs are best — pull
them from a recent run (`calibrate agent-tests get-run --task-id <t>`). Fewer
than ~20 makes the agreement number noisy; more is steadier. Deliberately
include **both** outputs that should pass and outputs that should fail — a sample
that's almost all passes can't tell you whether the judge catches failures
(Phase 4).

Create the task and link the evaluator:

```bash
calibrate annotation-tasks create \
  --name "<evaluator> calibration" \
  --type conversation \
  --evaluator-ids '["<evaluator_uuid>"]' \
  --output-format json
```

Capture `task_uuid`. (To link an evaluator later:
`calibrate annotation-tasks set-evaluators --task-uuid <t> --evaluator-ids '["<e>"]'`.)

Seed the items to be labeled. Each item is an `AnnotationItemPayload`: a
required `payload` (its shape depends on the task `--type`, but `payload.name` is
always required and must be unique in the task) and an optional `annotations`
map. Unlabeled to start:

```bash
calibrate annotation-tasks add-items --task-uuid <t> \
  --items '[{"payload":{"name":"item-1", ...}}]'
```

## Phase 2: Collect human labels

Have annotators label every item. Seed known human labels inline, one call per
annotator (`--annotator-id` is required whenever any item carries annotations).
Labels go under `annotations`, keyed by evaluator UUID, with `value` (a bool for
a binary evaluator, a number for a rating one) and optional `reasoning`:

```bash
calibrate annotation-tasks add-items --task-uuid <t> \
  --annotator-id <human_id> \
  --items '[{"payload":{"name":"item-1"},"annotations":{"<evaluator_uuid>":{"value":true,"reasoning":"meets the bar"}}}]'
```

Each evaluator UUID in `annotations` must be linked to the task.

Use **two or more** annotators when you can — that yields an inter-annotator
agreement number, which is your human ceiling (Phase 4).

## Phase 3: Run the judge on the same items

```bash
calibrate annotation-tasks create-evaluator-run --task-uuid <t> \
  --evaluators '["<evaluator_uuid>"]' --output-format json
```

Capture `job_uuid` and poll to completion:

```bash
calibrate annotation-tasks get-evaluator-run --task-uuid <t> --job-uuid <j>
```

## Phase 4: Measure agreement

```bash
calibrate annotation-tasks get-agreement --task-uuid <t> --output-format json
calibrate annotation-tasks get-summary   --task-uuid <t> --output-format json
```

Read agreement two ways:

- **human ↔ human** — the ceiling. If annotators don't agree with each other,
  the rubric is ambiguous; fix the evaluator's criteria before blaming the
  judge.
- **human ↔ judge** — the score that matters. Judge it against the human
  ceiling, **not** against 100%. A judge that matches humans as often as humans
  match each other is as good as it can get.

Don't stop at one overall number. A judge can look agreeable overall while being
blind to one class — so read the two error directions separately (the framing in
hamelsmu's *validate-evaluator*, https://github.com/hamelsmu/evals-skills):

- **true-positive rate** — of the cases humans passed, how many did the judge
  pass? A low rate means the judge is too harsh (false failures).
- **true-negative rate** — of the cases humans failed, how many did the judge
  fail? A low rate means the judge is too lenient (it rubber-stamps bad output)
  — usually the more dangerous error.

This especially matters when the sample is **imbalanced**: if 90% of items pass,
a judge that blindly passes everything scores 90% agreement while catching zero
real failures. Make sure the sample has enough of both classes to measure both
rates, and report them separately, not just the headline agreement.

Report the numbers plainly. Never fabricate — if the run didn't finish, say so.

## Phase 5: Tune and re-check (the loop)

If human↔judge agreement is below the human ceiling, the judge prompt is the
lever:

1. Pull the items where judge and humans diverged (from `get-summary`).
2. Sharpen the evaluator's `system_prompt` to cover those cases (hand off to
   `/iterate-evaluator` for the version mechanics).
3. Publish a new live version:

   ```bash
   calibrate evaluators create-version --evaluator-uuid <id> \
     --judge-model <model> --system-prompt "<sharpened>" --make-live true
   ```

4. Re-run Phase 3–4 on the **same items** — no new human labels needed.

Repeat until human↔judge agreement reaches the human↔human ceiling. Then the
judge is safe to run unattended.

## Handoffs

- Version mechanics / rubric rewrite → `/iterate-evaluator`
- Rethink the evaluator from scratch → `/design-evaluator`
- Judge now trusted → `/run-tests`, `/benchmark-models` at scale
