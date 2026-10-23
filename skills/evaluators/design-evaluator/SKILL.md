---
name: design-evaluator
description: Author a new evaluator (LLM or audio judge) in Calibrate and set its
  first live version. Use when the user says "create an evaluator", "add a judge",
  "score responses on X", "make an LLM judge", or "define a rubric".
argument-hint: "[evaluator-name]"
---

# Design an evaluator

Create a new evaluator — a versioned LLM/audio judge — and its first live
version. An evaluator scores agent output against a rubric you write. `create`
makes v1 and sets it live. Ask at each step; if `$ARGUMENTS` already carries a
name, pre-fill it and skip that question.

See [`../../references/agent-mode.md`](../../references/agent-mode.md) for how to
read command output (TOON/JSON) and
[`../../references/config-shapes.md`](../../references/config-shapes.md) for the
`version-param` shape. Keep what you *say* to the user plain — see
[`../../references/voice.md`](../../references/voice.md).

An evaluator is a **versioned** judge: the object holds a history of versions,
one of which is live. Here you author v1. Later tuning is a separate flow
(`/iterate-evaluator`).

## Get the latest instructions

Both the skill and the CLI on this machine can be months behind. Update both
before anything else, following
[`../../references/startup.md`](../../references/startup.md):

```bash
npx -y skills update design-evaluator -g -y ; npx -y skills update design-evaluator -p -y
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
calibrate agents list < /dev/null   # real read — 401 = not signed in, or key for the wrong deployment
```

If unauthenticated, guide the user:

```bash
calibrate login
```

An API key is created under **Workspace settings → API keys**
(https://calibrate.artpark.ai/workspace-settings?tab=api-keys). No account →
send them to https://calibrate.artpark.ai to sign up.

List existing evaluators so you don't duplicate one — and so the user can reuse
or tune a built-in default instead of authoring from scratch:

```bash
calibrate evaluators list --output-format json < /dev/null
```

The list includes the built-in defaults. If a judge already covers the intent,
present it and ask whether to reuse it (hand to `/build-test-suite`) rather than
create another. If a default is close but its rubric needs adjusting, don't
rebuild it here — defaults are editable, so hand to `/iterate-evaluator` to tune
it. Author from scratch only when no default is close.

## Phase 1: Decide what it judges

Three axes fix the evaluator's shape. Settle all three before writing any
prompt.

- **evaluator-type** — *what* the judge is handed. `--evaluator-type` accepts
  exactly five values:
  - `llm` (the default) — a reply together with the conversation before it.
  - `llm-general` — a standalone input and the output it produced.
  - `conversation` — a whole conversation.
  - `stt` — one transcript.
  - `tts` — synthesized speech.

  **The agent's kind decides this.** An agent that takes one input at a time and
  gives one answer needs `llm-general`; a conversational agent needs `llm`. The
  pairing is enforced: a `general` test case only accepts an `llm-general`
  evaluator, a `response` test case only accepts `llm`. Mixing them is rejected
  at creation. Check the agent's `interaction_type` in
  `calibrate agents list --output-format json` if you're unsure which kind it is.
- **data-type** — the modality the judge reads: `text` (grades a text reply or
  transcript) or `audio` (grades synthesized speech / audio output).
- **evaluator type** — what it judges: `llm` (a reply with its conversation
  history), `llm-general` (a standalone input/output pair), `conversation` (a
  whole conversation), `stt`, `tts`, or `tool-call` (whether the agent called
  the right tool, labelled by a person — it has no judge prompt to write, so
  don't draft one).
- **output-type** — how it scores:
  - `binary` — pass/fail. Uses the default `Correct` / `Wrong` labels unless you
    override them. Best for "did the reply do X?" checks.
  - `rating` — a labeled scale (e.g. 1–5). Requires an `output_config` that
    defines each scale point and its label. Use when a graded judgment is more
    useful than pass/fail.

If `rating`, collect the scale points and a short label for each.

## Phase 2: Write the judge prompt and variables

Draft the `system_prompt`. It may contain `{{variable}}` placeholders — commonly
a single `{{criteria}}` — filled per-test-case from that test's
`variable_values`. This lets one evaluator score many different criteria.

Declare each variable as `{"name", "description", "default"}`.

**Warn the user before proceeding:** variable **names are frozen after v1**.
Later versions can change a variable's description or default, but cannot add,
remove, or rename one. Choose the variable set deliberately now — a good default
is a single `criteria` variable, which keeps the judge reusable across tests.

Show the drafted prompt, variables, and (for rating) the scale, and confirm.
See the `version-param` shape in
[`../../references/config-shapes.md`](../../references/config-shapes.md).

## Phase 3: Choose the judge model

Pick a `judge_model` sized to the expected case volume. Prefer a cheap-enough
model (e.g. a mini model) unless the rubric genuinely needs a stronger one — a
judge runs once per test case, so cost scales with the suite. Model names are
provider-qualified, e.g. `openai/gpt-4.1`.

## Phase 4: Create

Show a summary and confirm before creating:

```
Evaluator summary
  Name:        <name>
  Reads:       a reply and the conversation before it | one input and one answer
               | a whole conversation | a transcript | the audio itself
  Data type:   text | audio
  Output type: binary | rating
  Judge model: <judge_model>
  Variables:   <names>
```

```bash
calibrate evaluators create \
  --name "<name>" \
  --description "<one line on what it judges>" \
  --data-type text \
  --evaluator-type <type> \
  --output-type binary \
  --version-param '{"judge_model":"openai/gpt-4.1","system_prompt":"...{{criteria}}...","variables":[{"name":"criteria","description":"what must hold","default":""}]}' \
  --output-format json < /dev/null
```

Quote every value that can contain a space, `--name` and `--description` above
all. An unquoted description stops at the first space and the rest of it arrives
as flags the command doesn't know.

For a `rating` evaluator, add the scale to `version-param` — an ordered array of
scale points under `scale`, not a `labels` map:
`"output_config": {"scale": [{"value": 1, "name": "..."}, {"value": 5, "name": "..."}]}`.

`--name` must be unique within the workspace. Capture `evaluator_uuid` from the
JSON response — never fabricate it. This creates the evaluator and sets **v1
live**.

## Phase 5: Sanity check + next steps

Read the evaluator back and confirm the prompt actually landed:

```bash
calibrate evaluators get --evaluator-uuid <evaluator_uuid> --output-format json < /dev/null
```

Check `live_version` on the result: `system_prompt` is the prompt you drafted,
`judge_model` is the model you chose, and `variables` holds every variable you
declared. A live v1 is not enough on its own — an evaluator with an empty prompt
is created happily and reports success.

If any of the three is empty or missing, the create didn't carry them. Variable
names are frozen after v1, so there is nothing to repair and no later version
fixes it. The CLI cannot delete an evaluator, so tell the user it came out empty
and ask them to delete it in the Calibrate app, then create it again with the
flags above.

Then report plainly:

```
Evaluator created
  ID:      <evaluator_uuid>
  Name:    <name>
  Live:    v1
```

An unvalidated judge is a guess. Strongly recommend validating it against human
labels before trusting it at scale — a judge that disagrees with people will
quietly skew every eval that uses it.

## Handoffs

- **Validate this judge against human labels** (strongly recommended before
  relying on it) → `/calibrate-evaluator`
- **Add or tune versions later** → `/iterate-evaluator`
- **Attach this evaluator to response test cases** → `/build-test-suite`
- **Run the full first-eval flow** → `/onboard`
