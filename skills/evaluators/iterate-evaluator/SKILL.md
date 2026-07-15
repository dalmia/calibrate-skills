---
name: iterate-evaluator
description: Add a new version to an existing evaluator and make it the live one — the
  judge-prompt tuning loop. Use when the user says "tune my evaluator", "improve
  the judge prompt", "new evaluator version", "the judge is wrong on X", "update
  my rubric", or "roll back the evaluator".
argument-hint: "[evaluator-uuid-or-name]"
---

# Iterate on an evaluator

Evaluators are versioned. Tuning a judge doesn't overwrite it — you add a new
version and (usually) make it the live one. Old versions stay for
comparison and rollback. Drives the `calibrate evaluators` commands. Ask at each
step; if `$ARGUMENTS` already carries a UUID or name, pre-fill it and skip the
lookup.

Built-in **default** evaluators are editable too, not just ones you authored —
tune them with the same flow below. So "the judge is wrong on X" is fixable even
when the judge is one of the defaults.

Reference: [`../../references/config-shapes.md`](../../references/config-shapes.md)
(evaluator version + variable shapes). Keep what you *say* to the user plain —
see [`../../references/voice.md`](../../references/voice.md).

This skill is the version-mechanics half of the calibration loop in
[`../../annotation/calibrate-evaluator/SKILL.md`](../../annotation/calibrate-evaluator/SKILL.md).
Don't tune blind — that loop tells you *what* the judge gets wrong; this one
changes it. Measure before and after with `/calibrate-evaluator`.

## Phase 0: Setup check

```bash
calibrate whoami
```

If unauthenticated, `calibrate login`.

Resolve the evaluator and read its current state — the live version, its
`system_prompt`, `judge_model`, and declared `variables`:

```bash
calibrate evaluators get --evaluator-uuid <uuid> --output-format json
```

If the user gave a name, find the UUID first:

```bash
calibrate evaluators list --output-format json
```

Note the live version and the variable names — you'll need both. The variable
names are frozen (Phase 3); capture them now.

## Phase 1: Diagnose

Pin down what the judge gets wrong before touching the prompt. The strongest
signal is disagreement data — the items where the judge diverged from humans in
the calibration loop, not guesswork.

- If the user has run `/calibrate-evaluator`, pull the diverging items from its
  `get-summary` output and read the concrete failing cases.
- If they haven't, ask for specific examples: an input, what the judge said,
  and what the correct label was. Vague "it's too lenient" isn't enough to tune
  against — get real cases.

State the failure pattern in one sentence before drafting. If there's no
grounded case, hand back to `/calibrate-evaluator` to produce one.

## Phase 2: Draft the new version

Rewrite the `system_prompt` so it would score the failing cases correctly, and
confirm the draft with the user. Hold these fixed unless they're the actual
problem:

- **Variable names** — frozen after v1. You may change a variable's
  `description` or `default`, but you **cannot add, remove, or rename** one. If
  the fix needs a different variable set, this is a new evaluator, not a new
  version — hand off to `/design-evaluator`.
- **`judge_model`** — keep the same model unless model choice is the failure
  (e.g. the judge can't follow a nuanced rubric at all). Prompt changes are the
  first lever; swap the model only when the prompt can't carry it.
- **`output_config`** — keep the same scale points/labels so old and new
  versions stay comparable. A `rating` evaluator requires `output_config`; a
  `binary` one keeps the default Correct/Wrong unless overridden.

If the user actually needs a different variable set, stop here and route to
`/design-evaluator` — don't try to force it through a version.

## Phase 3: Publish

Show the diff (old vs new `system_prompt`) and confirm before publishing.
Default to making it live:

```bash
calibrate evaluators create-version --evaluator-uuid <uuid> \
  --judge-model <model> \
  --system-prompt "<sharpened prompt>" \
  --variables '[{"name":"criteria","description":"...","default":""}]' \
  --output-config '<json>' \
  --make-live true \
  --output-format json
```

- Omit `--variables` if the prompt has none.
- Omit `--output-config` for a binary evaluator on default labels; include it
  for `rating` (required) or custom binary labels.
- `--make-live` defaults to `true`.

Offer **`--make-live false`** when the user wants to validate before switching
production — it stages the version without repointing the live version, so you
can A/B it against humans first and only promote it once agreement holds.

Capture the new version id from the JSON response.

## Phase 4: Re-validate — don't declare victory on inspection

A better-looking prompt is not a better judge. Confirm agreement actually
improved by re-running the judge on the **same** annotation items and
re-measuring — no new human labels needed.

Hand off to [`/calibrate-evaluator`](../../annotation/calibrate-evaluator/SKILL.md)
Phase 3–4: `create-evaluator-run` on the same task, then `get-agreement` /
`get-summary`. Compare human↔judge agreement against the pre-change number and
the human↔human ceiling.

If it regressed, roll back by making an older version live again:

```bash
calibrate evaluators create-version --evaluator-uuid <uuid> \
  --judge-model <old-model> --system-prompt "<previous prompt>" --make-live true
```

(`evaluators get` holds the full history to copy the previous version from.)
Then re-check. Iterate until human↔judge reaches the human↔human ceiling.

## Handoffs

- Measure agreement before and after — the loop this feeds → `/calibrate-evaluator`
- Need a different variable set → new evaluator → `/design-evaluator`
- Judge now trusted, run it at scale → `/run-tests`, `/benchmark-models`
- Full first-eval flow → `/onboard`
