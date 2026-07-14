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
  "output_config": {"labels": {"1": "Wrong", "2": "Correct"}}
}
```

- `data-type`: `text` or `audio` (modality the judge reads).
- `output-type`: `binary` (Correct/Wrong) or `rating` (a labeled scale — set
  `output_config`).
- Variable names are **frozen after v1** — later versions may change a
  variable's description/default but cannot add, remove, or rename one.

## Agent (`agents create --config-param`)

See [`agents/connect-agent/references/connection-types.md`](../agents/connect-agent/references/connection-types.md).
Internal-LLM agents carry `model` + `system_prompt` (+ optional `tools`);
external agents carry `agent_url` (+ optional `agent_headers`, `timeout`).

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
