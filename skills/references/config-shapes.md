# Calibrate config shapes

The JSON payloads the `calibrate` CLI accepts. These are the shapes the skills
generate. Always confirm exact keys against the live CLI help
(`calibrate <cmd> --help`) — this is a guide, not the schema of record.

## Test (`tests create` / `tests bulk-create`)

A test runs the agent against a conversation and evaluates the result. Two
top-level modes via `--type`:

- `tool_call` — deterministic: assert the agent calls tool X with args Y. No
  judge model, no cost.
- `response` — quality: an evaluator (LLM judge) scores the reply against
  `criteria`.

One test item (as passed inside the `--tests` array for `bulk-create`):

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

For `tool_call` tests, the expectation is the tool the agent should call; for
`response` tests, `evaluators[].variable_values` fills the judge prompt's
`{{variables}}`. A batch is at most 500 items, names unique within the batch.

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
- An evaluator's type can also be `tool-call` (a person checks the agent called
  the right tool). One with `is_protected` true is locked: it can't be deleted,
  and only its name, description and rubric can change.

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

- `payload` — **required**. Its shape follows the task `--type`, but
  `payload.name` is **always required** and must be unique within the task, and
  `description` is accepted on every type. Other keys by type:
  - `stt`: `predicted_transcript`, `reference_transcript`
  - `tts`: `audio_path` (storage key or `s3://` URI), `text`
  - `llm`: `agent_response`, `chat_history` (turns ending at the user turn);
    optional `evaluator_variables`
  - `llm-general`: `input`, `output`; optional `evaluator_variables`
  - `conversation`: `transcript`; optional `evaluator_variables`
  - A turn is `{role, content}`, plus optional `label` and `versions`. Likewise
    `agent_response`, `input` and `output` take either a string or
    `{content, label?, versions?}`: `content` is what the judge reads,
    `versions` maps a name to another form (a translation, a human rewrite)
    shown to annotators only.
  - For `llm` and `llm-general`, `actual_tool_calls`, `expected_tool_calls` or
    `tool_calls` (each a list of `{tool, arguments?, output?}`) mark the item as
    a tool call for a person to judge (`is_tool_call` is then set on the item).
    Those items are labelled with the `tool-call` evaluator type and no other.
- `metadata` — **optional**, beside `payload`: a list of `{key, value}` strings
  (up to 100) shown next to the item on the labelling form. On update, omit it
  to keep what is stored; an empty list clears it.
- `evaluator_results` — **optional**, beside `payload`: judge scores you already
  have, keyed by evaluator UUID (each linked to the task), as
  `{value, reasoning?, version_number?}`. Omit `version_number` to record against
  the live version. The reply then carries `evaluator_result_count` and
  `evaluator_run_job_id`.
- `annotations` — **optional**. Human labels to seed, keyed by evaluator UUID
  (each must be linked to the task). `value` is a bool for a `binary` evaluator
  or a number for a `rating` one; `reasoning` is optional. Whenever any item
  carries `annotations`, the request must set `--annotator-id <id>` (the
  annotator those labels belong to). Omit `annotations` to leave items unlabeled
  for annotators to fill.
