# Calibrate config shapes

The JSON payloads the `calibrate` CLI accepts. These are the shapes the skills
generate. Always confirm exact keys against the live CLI help
(`calibrate <cmd> --help`) — this is a guide, not the schema of record.

## Test (`tests create` / `tests bulk-create`)

A test runs the agent against a conversation and evaluates the result. Three
modes via `--type`:

- `response` — quality: an evaluator (LLM judge, type `llm`) scores the reply
  against `criteria`.
- `tool_call` — deterministic: assert the agent calls tool X with args Y. No
  judge model, no cost.
- `conversation` — quality: an evaluator (type `conversation`) scores the whole
  multi-turn exchange.

### bulk-create item shape

Items in the `--tests` array for `bulk-create` carry the expectation at the top
level of the item (the shape differs from single `create`, below).

A **`response`** item — the reply is graded by linked evaluators:

```json
{
  "name": "refund-within-window",
  "conversation_history": [
    {"role": "user", "content": "I want a refund for order ORD-42"}
  ],
  "evaluators": [
    {
      "evaluator_uuid": "<uuid>",
      "variable_values": {"criteria": "The reply must cite the 30-day refund window"}
    }
  ]
}
```

A **`tool_call`** item — expected calls go in `tool_calls` (sibling to
`conversation_history`), each argument checked by a **match type**:

```json
{
  "name": "book-room-101",
  "conversation_history": [
    {"role": "user", "content": "Book room 101 for tomorrow"}
  ],
  "tool_calls": [
    {
      "tool": "book_room",
      "arguments": {
        "room": {"match_type": "exact", "value": "101"},
        "date": {"match_type": "llm_judge", "criteria": "tomorrow's date"},
        "note": {"match_type": "any"}
      },
      "accept_any_arguments": false
    }
  ]
}
```

Match types (per argument):

- `{"match_type": "exact", "value": <any>}` — must equal `value`. Use for
  closed-form args (ids, numbers, dates, enums).
- `{"match_type": "llm_judge", "criteria": "..."}` — a judge decides if the
  passed value satisfies `criteria`. Use where meaning, not surface form,
  matters.
- `{"match_type": "any"}` — only checks the argument was passed at all.
- `accept_any_arguments: true` on a call ignores argument checking entirely —
  asserts only that the tool was called.

A batch is at most 500 items, names unique within the batch. `conversation_history`
turns are `{role, content}` with `role` one of `user`, `assistant`, `tool` (a
`tool` message also carries `tool_call_id` and `name`).

### single `create` shape

`tests create` uses `--config-param` with three top-level keys — `history`,
`evaluation` (`{"type": ...}`, matching `--type`; `tool_call` puts its
`tool_calls` list here), and optional `settings` — with evaluators passed
separately via `--evaluators`. Prefer `bulk-create` for more than a couple of
cases.

## Evaluator version (`evaluators create --version-param`)

An evaluator is a versioned judge. A version is one prompt + model + rubric:

```json
{
  "judge_model": "openai/gpt-4.1",
  "system_prompt": "You are grading whether {{criteria}} holds. Respond ...",
  "variables": [{"name": "criteria", "description": "what must hold", "default": ""}],
  "output_config": {"scale": [{"value": 1, "name": "Wrong"}, {"value": 2, "name": "Correct"}]}
}
```

- `evaluator-type` (`-e`): what the judge reads. **Must match the test that uses
  it.** Defaults to `llm`.
  - `llm` — a reply *with its conversation history* → for **`response`** tests
    (conversational bots). The default and the usual choice.
  - `conversation` — a full conversation → for **`conversation`** tests.
  - `stt` — one transcript; `tts` — synthesized audio (`data-type audio`).
  - `llm-general` — a standalone input/output pair, no history. **Not accepted
    for `response` tests** — don't reach for it just because it sounds general.
- `data-type`: `text` or `audio` (modality the judge reads).
- `output-type`: `binary` (Correct/Wrong) or `rating` (a labeled scale — set
  `output_config`).
- `output_config` is `{"scale": [{value, name, description?, color?}, ...]}` — an
  ordered array of scale points, **not** a `labels` map. `value` is a boolean for
  a `binary` evaluator, a number for a `rating` one.
- Variable names are **frozen after v1** — later versions may change a
  variable's description/default but cannot add, remove, or rename one.
- Evaluators are either **built-in defaults** or **custom** ones you authored —
  both are editable the same way (add a version with `evaluators create-version`).
  In list/get output, `is_default` flags which kind it is.

## Agent (`agents create --config-param`)

See [`agents/connect-agent/references/connection-types.md`](../agents/connect-agent/references/connection-types.md).
`type=agent` (built inside Calibrate) carries `system_prompt` + `llm.model` (+ optional `stt`, `tts`, `settings`);
`type=connection` (your own HTTP endpoint) carries `agent_url` (+ optional `agent_headers`, `benchmark_provider`).

## Annotation item (`annotation-tasks add-items --items`)

`--items` is an array of `AnnotationItemPayload`. Each item has two keys:

```json
{
  "payload": {"name": "item-1", "...": "shape depends on task --type"},
  "annotations": {
    "<evaluator_uuid>": {"value": true, "reasoning": "meets the bar"}
  }
}
```

- `payload` — **required**. Its shape follows the task `--type`
  (`conversation`, `stt`, `tts`, …), but `payload.name` is **always required**
  and must be unique within the task.
- `annotations` — **optional**. Human labels to seed, keyed by evaluator UUID
  (each must be linked to the task). `value` is a bool for a `binary` evaluator
  or a number for a `rating` one; `reasoning` is optional. Whenever any item
  carries `annotations`, the request must set `--annotator-id <id>` (the
  annotator those labels belong to). Omit `annotations` to leave items unlabeled
  for annotators to fill.
