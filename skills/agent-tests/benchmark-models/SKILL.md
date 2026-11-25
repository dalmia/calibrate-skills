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
When you finish a step, give the user the address for the benchmark and its results, as
[`../../references/links.md`](../../references/links.md) sets out.

## Get the latest instructions

Both the skill and the CLI on this machine can be months behind. Update both
before anything else, following
[`../../references/startup.md`](../../references/startup.md):

```bash
npx -y skills update benchmark-models -g -y ; npx -y skills update benchmark-models -p -y
```

```bash
have=$(calibrate version 2>/dev/null | head -1 | awk '{print $2}')
want=$(curl -fsS https://api.github.com/repos/dalmia/calibrate-cli/releases/latest 2>/dev/null | sed -n 's/.*"tag_name": *"v\{0,1\}\([^"]*\)".*/\1/p' | head -1)
if [ -n "$want" ] && [ "$have" != "$want" ]; then
  if command -v brew >/dev/null 2>&1; then
    brew update >/dev/null 2>&1
    brew install dalmia/tap/calibrate >/dev/null 2>&1 || brew upgrade dalmia/tap/calibrate >/dev/null 2>&1
  else
    arch=$(uname -m); case "$arch" in aarch64|arm64) arch=arm64 ;; *) arch=x86_64 ;; esac
    case "$(uname -s)" in
      Linux)  os=Linux;   bin=calibrate ;;
      Darwin) os=Darwin;  bin=calibrate ;;
      *)      os=Windows; bin=calibrate.exe ;;
    esac
    dest=$(command -v calibrate || echo "$HOME/.local/bin/$bin")
    tmp=$(mktemp -d)
    if [ "$os" = Windows ]; then
      curl -fsSL -o "$tmp/c.zip" "https://github.com/dalmia/calibrate-cli/releases/download/v${want}/calibrate-cli_${os}_${arch}.zip" && unzip -oq "$tmp/c.zip" -d "$tmp"
    else
      curl -fsSL "https://github.com/dalmia/calibrate-cli/releases/download/v${want}/calibrate-cli_${os}_${arch}.tar.gz" | tar xz -C "$tmp"
    fi
    if [ -f "$tmp/$bin" ]; then
      mkdir -p "$(dirname "$dest")"
      chmod +x "$tmp/$bin"
      cp "$tmp/$bin" "$dest"
    fi
    rm -rf "$tmp"
  fi
fi
calibrate version 2>/dev/null | head -1 || echo "calibrate is not installed"
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

If unauthenticated, guide the user:

```bash
calibrate login
```

Resolve the agent to a UUID. If `$ARGUMENTS` is already a UUID, use it. If it's
a name, resolve it; if nothing was passed, list and ask which agent:

```bash
calibrate agents list --output-format json
calibrate agents resolve --names '<name>' --output-format json
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

Models run several at a time by default. If the agent is the user's own service
and could be overloaded or rate-limited, offer to run them one after another
instead (`parallel_models` false on the benchmark call; check
`calibrate agent-tests benchmark --help` for the flag). It's slower but gentler
on their service.

Offer to narrow the run: `--test-uuids` restricts the benchmark to a subset of
the linked tests (each ID must be linked). Omit it to run all linked tests.

## Phase 4: Launch

```bash
calibrate agent-tests benchmark \
  --agent-uuid <agent_uuid> \
  --models openai/gpt-4.1 \
  --models anthropic/claude-sonnet-4 \
  --output-format json
```

Repeat `--models` once per model. Don't pass a JSON list (`--models '["a","b"]'`),
even though `calibrate agent-tests benchmark --help` shows one: the CLI sends it
as a single model named `["a","b"]`, every test comes back unanswered, and the
run still reports `done`. Check with `--dry-run` if unsure: the request should
list each model separately.

A benchmark counts one row per model per test, so 5 models over 20 tests is 100
rows. If the workspace's per-run limit is lower, the call is refused with "This
run would process N rows, above this workspace's limit of M". Tell the user the
numbers, and offer to run fewer models or tests per run, or to ask a workspace
admin to raise the limit.

To restrict to a subset of linked tests, add:

```bash
  --test-uuids '["<test_uuid>", "..."]'
```

Capture `task_id` from the JSON response. Never fabricate it — if it's missing,
report the structured error instead of guessing.

## Phase 5: Poll

The benchmark runs as a background job. Poll until the status is final: `done`,
`failed` or `cancelled`. A finished job says `done`, never `completed`, and
`cancelled` means someone stopped it. Back off between
polls, per [`../../references/agent-mode.md`](../../references/agent-mode.md):

```bash
calibrate agent-tests get-benchmark --task-id <task_id> --compact --output-format json
```

`--compact` does more here than it does on a single run: it drops every
per-case row, setting each model's `test_results` to null. What survives is each
model's counts and `leaderboard_summary`, which is all you need while polling. A
benchmark repeats its per-case text once per model, so the full result is the
largest thing these skills ever read. Don't pair `--compact` with
`--only-failed`: there are no case rows left to filter. Drop `--compact` when
you want the failures.

Report progress to the user as it advances; don't block silently.

The result carries most of the same flags as a single run: `error` is a string
reason (not a boolean), `aborted` (stopped by a user; unrun cases are neither passed nor
failed), `stopped_early` (a model quit after too many failures in a row, also
reported per model), and `unanswered_tests` (cases where the agent or judge
couldn't be reached). Unlike a single run, `unanswered_tests` is not at the top
level here: it sits on each entry of `model_results`. `parallel_models` echoes
how it ran, and the flag that sets it is `--parallel-models`. One model's answer on one case reads in full with
`calibrate agent-tests get-run-case --task-id <task_id> --test-uuid <test_uuid> --model <model>`.

## Phase 6: Present the leaderboard

Don't build this by hand. The result carries `leaderboard_summary` already: one
row per model, sorted, with `model`, `passed`, `total`, `pass_rate`, latency,
cost and tokens, plus a pass rate per evaluator. It survives `--compact`. Read
it and show it, **best first**:

```
Model                        Pass-rate
anthropic/claude-sonnet-4    18/20  (90%)
openai/gpt-4.1               16/20  (80%)
```

Use only the numbers the command returned. **Never invent scores.**

If any model has unanswered cases or stopped early, its pass-rate is not a fair
comparison — say so next to the row (e.g. "5 of its tests got no answer") and
offer to re-run it before the user acts on the ranking.

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
