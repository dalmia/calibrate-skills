---
name: onboard
description: Guided end-to-end setup for a first Calibrate evaluation — connect an
  agent, build tests, run them, and (optionally) calibrate the judge against
  humans. Orchestrates the feature skills. Use when the user says "get started",
  "onboard me", "set up Calibrate", "evaluate my agent", or "run my first eval".
argument-hint: "[what-you-want-to-evaluate]"
---

# Calibrate onboarding

Take a first-time user from nothing to a trustworthy evaluation. This skill is an
**orchestrator**: each phase delegates to a feature skill and produces a real
Calibrate object. Persist progress to `.calibrate/onboard.md` (copy the bundled
[`assets/onboard.md`](assets/onboard.md) on first use) so a session can resume at
the first incomplete phase.

Loose inspiration: the local `calibrate-guide` intake flow — phased, resumable,
adaptive. This version targets the cloud API primitives.

## Operating principle: adaptive determinism

Match rigor to the user's expertise:

- **Novice / unspecified** — walk the phases in order, use defaults, run the
  preflight gate, don't over-ask.
- **Expert / explicit** — honor their choices, compress or skip phases they've
  already answered, let them dictate. Defaults are a fallback, not a mandate.

Compress a phase when the user already gave you the answer in passing. The phase
list is structure, not a script.

## Preflight (before any run)

From the project root, run the bundled stdlib gate — it needs nothing installed:

```bash
uv run --no-project /path/to/skills/onboarding/onboard/scripts/validate.py \
  --state .calibrate/onboard.md
```

It exits non-zero and lists what's missing when a required phase is unfilled.
Default-on for novices; an expert may skip it.

## Setup (first use in a project)

```bash
mkdir -p .calibrate
cp /path/to/skills/onboarding/onboard/assets/onboard.md .calibrate/onboard.md
```

Confirm the CLI is installed, then auth, once. `npx skills add` installs only
the skill prose, not the binary — if `calibrate` is missing, have the user
`brew install dalmia/tap/calibrate` before continuing:

```bash
command -v calibrate >/dev/null || echo "calibrate CLI not installed — brew install dalmia/tap/calibrate"
calibrate whoami   # else: calibrate login
```

## Phase 1 — System under test → agent

Ask what the agent does, who uses it, and where it fails today. Write a short
summary into **Phase 1** of `.calibrate/onboard.md`. Then delegate:

→ **`/connect-agent`** — register + `verify-connection`. Record the resulting
`agent_uuid` in the state file. Don't proceed until the connection verifies.

## Phase 2 — Hypothesis → tests

Turn the goal into a falsifiable claim ("when the user gives an ORD-\d+ id, the
agent calls `check_order` with that id"). Write it into **Phase 2**. Then:

→ **`/build-test-suite`** (or **`/import-dataset`** if they already have a
dataset). Name the evaluator type per case as you go: `tool_call` = deterministic
and free; `response` = needs a judge. Record the `test_uuids`.

## Phase 3 — Evaluators (only if needed)

If any case judges response quality, it needs an evaluator:

→ **`/design-evaluator`**. Skip this phase entirely if every case is
`tool_call`. Record the `evaluator_uuid`(s).

## Phase 4 — Run

→ **`/run-tests`** — link tests to the agent, run, poll, and read results.
Present **failures first**. Record the `task_id` and outcome in **Phase 4**.

## Phase 5 — Calibrate the judge (offer, don't force)

Only if the user cares whether the automated scores are trustworthy (they mention
"can I trust this", human review, or high-stakes decisions):

→ **`/calibrate-evaluator`** — measure human↔judge agreement and tune until the
judge matches humans. This is the step that makes the eval *Calibrate*, not just
a test runner. Offer it; don't impose it.

## Phase 6 — Scale + CI

→ **`/benchmark-models`** — compare models across the linked tests.

If the user mentions PRs, CI, releases, or "before we ship", propose wiring
`calibrate agent-tests run` into CI in agent mode (`--agent-mode --no-interactive
--output-format json`), pinned to one cheap model in CI with the full matrix run
locally. Don't force it — only when the signal is there.

## Iterate

Evaluation is a loop, not a line. After Phase 4, expect one of:

- **Expand the test set** — a defect surfaced or coverage is thin → back to
  Phase 2 (`/build-test-suite`), re-run.
- **Tune the hypothesis** — the bar is too loose/strict → edit Phase 2, re-run.
- **Add a model** — → Phase 6 (`/benchmark-models`).
- **Tune the judge** — agreement too low → `/iterate-evaluator` +
  `/calibrate-evaluator`.

Each pass appends to **Phase 4 — Runs** in the state file so prior baselines stay
inspectable. Stop when the user has shipped, wired it into CI, or says they're
done.
