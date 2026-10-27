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
When you finish a step, give the user the address for the labelling task and the results, as
[`../../references/links.md`](../../references/links.md) sets out.

## Get the latest instructions

Both the skill and the CLI on this machine can be months behind. Update both
before anything else, following
[`../../references/startup.md`](../../references/startup.md):

```bash
npx -y skills update calibrate-evaluator -g -y ; npx -y skills update calibrate-evaluator -p -y
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

## What to tell the user before labelling

The user may not know that the scores come from AI and can be wrong. Before
setting anything up, say it in plain words, along these lines:

> The pass and fail scores come from AI evaluators, and they can be wrong. They
> are weakest on things that are a matter of opinion, like whether an answer is
> kind or simple enough, and on those even two people can disagree. So before
> you change your agent based on these scores, let's check them: a few people
> label about 20 of your agent's answers by hand, and we see how often the
> evaluators agree with them, and how often the people agree with each other.

Say "evaluator", never judge (see [`voice.md`](../../references/voice.md)).

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

Gather about 20 items the evaluator will judge (all of them if the run has fewer).
Real agent outputs are best — pull them from the run the user just looked at
(`calibrate agent-tests get-run --task-id <t>`). Link every evaluator the run
used to the task, so one round of labelling checks all of them. Fewer
than ~20 makes the agreement number noisy; more is steadier.

Create the task and link the evaluator. **`--type` has to match what the
evaluator judges** — the task type sets the shape of every item, so a mismatch
hands the judge something it can't read:

| Evaluator being calibrated | `--type` | Each item's `payload` |
| --- | --- | --- |
| `llm` (a reply, with the conversation before it) | `llm` | `name`, `chat_history`, `agent_response` |
| `llm-general` (one input and one answer) | `llm-general` | `name`, `input`, `output` |
| `conversation` (a whole conversation) | `conversation` | `name`, `transcript` |
| `stt` (a transcript) | `stt` | `name`, `reference_transcript`, `predicted_transcript` |

An agent that takes one input at a time is judged by an `llm-general` evaluator,
so its calibration task is `llm-general` too.

```bash
calibrate annotation-tasks create \
  --name "<evaluator> calibration" \
  --type <llm|llm-general|conversation|stt|tts> \
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

Field names per task type, translations or rewrites shown to annotators,
tool-call items, `metadata`, and `evaluator_results` are in
[`config-shapes.md`](../../references/config-shapes.md). If the agent's reply is
a tool call, label it with a `tool-call` evaluator, not a text judge.

## Phase 2: Collect human labels

People label the items in Calibrate's labelling form. Each person gets a link
of their own and needs no Calibrate account.

**How many people.** At least two people must label the same items. That is
the only way to see how often people agree with each other, which is the most
you can expect from an evaluator (Phase 4). Ask the user who will label, by
name. If one person labelling everything is all they can manage, say plainly
that this leaves no way to tell an unclear rule from a weak evaluator, and ask
for a second person on at least a shared set of about 10 items.

Add each person once (`--name` is unique in the workspace; reuse an existing
annotator from `calibrate annotators list` instead of creating a duplicate):

```bash
calibrate annotators create --name "<name>" --output-format json
```

Create one labelling job per person. By default, everyone labels every item and
must write a reason with each score: without reasons, a disagreement between
two people can't be explained afterwards. Repeat `--annotator-ids` once per
person; a JSON list is sent as one id:

```bash
calibrate annotation-tasks create-labelling-jobs --task-uuid <t> \
  --annotator-ids <annotator_1> --annotator-ids <annotator_2> \
  --select-all --reasoning-mode required --output-format json
```

If labelling everything twice is too much work, give both people a shared set
of about 10 items (`--item-ids` instead of `--select-all`, both annotators in
one call), then split the remaining items between them with one call per person.

Each job in the response has a `public_token`. Send every person their own
link: `https://calibrate.artpark.ai/annotate-job/<public_token>`. On a
self-hosted Calibrate, use the address the user opens Calibrate at in place of
`https://calibrate.artpark.ai`.

Progress is on the task: `calibrate annotation-tasks get --task-uuid <t>` lists
each job's `completed_item_count` out of `item_count`. Wait until every job is
done before reading agreement; a few labelled items say almost nothing.

**Labels the user already has** (from a spreadsheet, say) can be added directly
instead, one call per annotator (`--annotator-id` is required whenever any item
carries annotations). Labels go under `annotations`, keyed by evaluator UUID,
with `value` (a bool for a binary evaluator, a number for a rating one) and
`reasoning`:

```bash
calibrate annotation-tasks add-items --task-uuid <t> \
  --annotator-id <human_id> \
  --items '[{"payload":{"name":"item-1"},"annotations":{"<evaluator_uuid>":{"value":true,"reasoning":"meets the bar"}}}]'
```

Each evaluator UUID in `annotations` must be linked to the task.

## Phase 3: Run the evaluator on the same items

```bash
calibrate annotation-tasks create-evaluator-run --task-uuid <t> \
  --evaluators '[{"evaluator_id":"<evaluator_uuid>"}]' \
  --select-all --output-format json
```

`--evaluators` takes objects, not plain IDs: a list of strings is refused with
"cannot unmarshal string". Each entry runs that evaluator's live version unless
it also carries `evaluator_version_id`. Pass `--select-all`, or list the items
with `--item-ids`; the command needs one of them.

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

Where the numbers live in the `get-agreement` response:

- `human_human` is the ceiling across all annotators (`current`, `pair_count`).
  There is no trend over time any more — no `series`, `bucket` or `days`.
- `evaluators_with_humans.current` is the overall human↔judge number across
  every linked evaluator.
- `evaluators[]` has one entry per evaluator: `current` (human↔judge),
  `inter_annotator` (that evaluator's own human ceiling), and `result` /
  `human_result` (counts and means of what the judge and the people answered).
- Each of those blocks also carries a chance-corrected `kappa`, with
  `kappa_type` saying which kind. Prefer `kappa` when the answers are lopsided
  (say, nearly all pass), because raw agreement looks high by luck;
  `chance_agreement` is what luck alone would give. Pass/fail and rating
  answers are never merged into one kappa.
- `kappa` can be null. `kappa_blank_reason` says why: `too_few_items` (only one
  item compared) or `everyone_agreed` (no spread to measure). Treat both as "not
  enough to tell", not as zero.
- Per-annotator kappa is on the annotator listing as `kappa_by_kind`; use it to
  spot one annotator who disagrees with the rest.

Read them **for each evaluator separately**, from its `evaluators[]` entry:

- **People often disagree on an evaluator's quality** (`inter_annotator` low)
  → the rule is unclear. Help the user agree on what it means, and rewrite that
  evaluator's instructions, before judging the evaluator.
- **People agree, the evaluator doesn't** (`current` well below
  `inter_annotator`) → change the evaluator's instructions (Phase 5).
- **The evaluator agrees with people about as often as they agree with each
  other** → it is as good as it can get. Don't push it toward 100%.

Expect the weakest agreement, between people and with the evaluator, on
qualities that are a matter of opinion.

Report both numbers plainly, per evaluator, with how many items they rest on
(`pair_count`). If you quote the chance-corrected one, say it as "agreement once
luck is accounted for" (1 is perfect, 0 is no better than guessing). If it is
blank, say there weren't enough labelled items, or everyone gave the same
answer, so it can't be told apart from luck. Never fabricate — if the run
didn't finish, say so.

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
judge is safe to run unattended, and only then go back to improving the agent:
scores from an evaluator that disagrees with people would steer those changes
the wrong way.

## When to remind the user

An evaluator checked on 20 answers may still be wrong on the 200 it scores
later. `run-tests` and `benchmark-models` point here after showing results.

Remind only when a run covers a larger set of tests than any run before it for
this agent. Check:

```bash
calibrate agent-tests list-runs-for-agent --agent-uuid <agent_uuid> --output-format json
```

Compare this run's `total_tests` with the largest `total_tests` among the
earlier runs. If it is not larger, say nothing. If it is larger, count, for each
evaluator the run used, how many items people have labelled for it: find the
tasks that link it (`calibrate annotation-tasks list`), and count that
evaluator's rows in
`calibrate annotation-tasks get-summary --task-uuid <t> --compact --limit 500`
where at least one annotator's entry is not null. Every assigned annotator
appears in `annotations` from the start, as `null` until they label the item, so
a non-empty `annotations` map is not a label.
If that count is below this run's test count, add one line after the results,
naming the numbers, for example:

> These evaluators were checked against people on 20 answers, and this run
> scored 120. Want a few people to label about 20 of the new answers, to check
> they still agree?

Say it once for that run, then drop it.

## Handoffs

- Version mechanics / rubric rewrite → `/iterate-evaluator`
- Rethink the evaluator from scratch → `/design-evaluator`
- Judge now trusted → `/run-tests`, `/benchmark-models` at scale
