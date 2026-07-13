---
name: import-dataset
description: Import an existing dataset (local CSV/TSV, JSON/JSONL, or a
  HuggingFace dataset) into Calibrate as test cases via bulk upload. Use when the
  user says "import a dataset", "import from HuggingFace", "load my CSV as tests",
  "convert my dataset into tests", or "bulk import test cases".
argument-hint: "[path-or-dataset-name]"
---

# Import a dataset as tests

Turn rows of an existing dataset into Calibrate test cases and bulk-upload them.
Drives the `calibrate tests bulk-create` command. Ask at each step; if
`$ARGUMENTS` already carries a path or HuggingFace dataset name, pre-fill it and
skip that question.

See [`../../references/agent-mode.md`](../../references/agent-mode.md) for how to
read command output (TOON/JSON) and
[`../../references/config-shapes.md`](../../references/config-shapes.md) for the
exact test-item shape. Keep what you *say* to the user plain — see
[`../../references/voice.md`](../../references/voice.md).

## Phase 0: Setup check

```bash
calibrate whoami
```

If unauthenticated, guide the user:

```bash
calibrate login
```

An API key is created under **Workspace settings → API keys**
(https://calibrate.artpark.ai/workspace-settings?tab=api-keys). No account →
send them to https://calibrate.artpark.ai to sign up.

## Phase 1: Pick the target agent

Every imported test can be linked to one or more agents (`--agent-uuids`). Ask
which agent these cases belong to, or whether to import them unlinked.

```bash
calibrate agents list --output-format json
```

Present a numbered list; capture the chosen `agent_uuid`(s). If none exists yet
and the user wants a link, hand off to `/connect-agent` first. Linking is
optional — omit `--agent-uuids` to link none.

## Phase 2: Locate and inspect the dataset

Find the source from `$ARGUMENTS` or by asking. Supported sources:

- **Local CSV/TSV** — read the header and a few rows.
- **Local JSON/JSONL** — read the first few records.
- **HuggingFace dataset** — load via the `datasets` library if available:

```bash
python -c "import datasets; print('ok')" 2>/dev/null && echo "datasets available"
```

```python
from datasets import load_dataset
ds = load_dataset("<name>", split="train")
print(ds.column_names)
print(ds[0])
```

If `datasets` is not installed, offer to `pip install datasets` or ask the user
to export the split to CSV/JSONL first.

Read enough rows to learn the column names and shapes. Report the columns back
to the user before mapping — never guess the schema blind.

## Phase 3: Map columns to test fields

Decide how each source column becomes a Calibrate test item. See
[`../../references/config-shapes.md`](../../references/config-shapes.md) for the
item shape. You must settle:

- **`--type`** — `tool_call` (assert the agent calls tool X with args Y) or
  `response` (an LLM judge scores the reply against `criteria`). Pick per the
  dataset's expectation column.
- **`conversation_history`** — which column(s) become the ordered turns. Each
  turn is `{"role": "user"|"assistant"|"tool", "content": "..."}`. A single
  prompt column becomes one `user` turn; a transcript column must be parsed into
  turns.
- **The expectation** — for `response` tests, which column supplies the judge
  `criteria`; for `tool_call` tests, which column names the expected tool/args.

If the mapping is ambiguous (unclear which column is the prompt vs. the
expected answer, or whether rows are tool calls or free-text replies), **ask —
don't guess silently.**

For `response` items, each evaluator needs an `evaluator_uuid` plus its
`variable_values` (e.g. `criteria`). If no suitable evaluator exists, hand off
to `/design-evaluator` to create one, then come back with its UUID.

## Phase 4: Transform rows into the items array

Convert rows to the JSON items array. Requirements:

- **Unique names within each batch.** Generate them deterministically, e.g.
  `<dataset-slug>-<row-index>`. Confirm no collisions.
- **500-item cap per request.** Chunk the full set into slices of ≤500 and issue
  one `bulk-create` per chunk. **Never silently truncate** — if the dataset has
  more rows than one request allows, that is exactly why you chunk.
- **Track skips.** If a row is malformed, missing the mapped columns, or
  otherwise unmappable, drop it and record which rows and why. Report the count.

A small transform snippet is fine, for example:

```python
import json, csv
rows = list(csv.DictReader(open("<path>")))
slug = "<dataset-slug>"
items, skipped = [], []
for i, r in enumerate(rows):
    prompt = (r.get("<prompt-col>") or "").strip()
    if not prompt:
        skipped.append(i); continue
    items.append({
        "name": f"{slug}-{i}",
        "conversation_history": [{"role": "user", "content": prompt}],
        # response tests: add "evaluators": [{"evaluator_uuid": "<uuid>",
        #   "variable_values": {"criteria": r["<criteria-col>"]}}]
    })
chunks = [items[i:i+500] for i in range(0, len(items), 500)]
print(len(items), "items,", len(chunks), "chunks,", len(skipped), "skipped")
for n, c in enumerate(chunks):
    json.dump(c, open(f"chunk-{n}.json", "w"))
```

Show the user the item count, chunk count, and skipped rows before uploading.

## Phase 5: Upload each chunk

For each chunk, run `bulk-create` and collect the created `test_uuid`s:

```bash
calibrate tests bulk-create \
  --type <tool_call|response> \
  --tests "$(cat chunk-0.json)" \
  --agent-uuids '["<agent_uuid>"]' \
  --language <lang> \
  --output-format json
```

Omit `--agent-uuids` to link none; omit `--language` to leave
`config.settings.language` unset. If a chunk fails, surface the structured error
(validation, duplicate name, auth), fix that chunk's payload, and retry it —
don't proceed as if it succeeded. Never fabricate a `test_uuid`.

## Phase 6: Verify and report

```bash
calibrate tests list --output-format json
```

Reconcile the results:

```
Import summary
  Source rows:   <n>
  Imported:      <created> across <chunks> request(s)
  Skipped:       <count>  (<reasons>)
  Linked agents: <uuids or "none">
```

Report imported vs. source row count and every dropped row with its reason. If
the numbers don't match and nothing was skipped, investigate — don't paper over
it.

## Handoffs

- **Response cases need a judge** → `/design-evaluator`
- **Author cases by hand instead** → `/build-test-suite`
- **Run the imported tests** → `/run-tests`
- **Full first-eval flow** → `/onboard`
