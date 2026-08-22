# Calibrate config shapes

The JSON payloads the `calibrate` CLI accepts. These are the shapes the skills
generate. Always confirm exact keys against the live CLI help
(`calibrate <cmd> --help`) — this is a guide, not the schema of record.

## Test (`tests create` / `tests bulk-create`)

A test feeds the agent an input and evaluates what comes back. Four types via
`--type`:

- `response` — a judge scores the agent's reply against the conversation
  before it.
- `conversation` — a judge scores the whole conversation.
- `tool_call` — deterministic: assert the agent calls tool X with args Y. No
  judge model, no cost.
- `general` — a judge scores one standalone input and the output it produced,
  with no conversation involved (summarizing, extracting, classifying).

Which types fit depends on the agent. Every agent carries an
`interaction_type`, returned on each item of
`calibrate agents list --output-format json`:

- `conversation` — called with the exchange so far, `{"messages": [...]}`.
  Takes `response`, `conversation` and `tool_call` tests.
- `general` — called with one plain input, `{"input": "..."}`. Takes `general`
  and `tool_call` tests.

Linking a test to an agent of the other kind is rejected by the backend.

### Single test (`tests create --config-param`)

```json
{
  "history": [
    {"role": "user", "content": "I want a refund for order ORD-42"}
  ],
  "evaluation": {"type": "response"},
  "settings": {"language": "en"}
}
```

- `history` — the conversation up to the agent's turn: ordered
  `{role, content}` items, `role` one of `user`, `assistant`, `tool`. A `tool`
  message also carries `tool_call_id` and `name`. Required for `response` and
  `conversation`, and for a `tool_call` test aimed at a conversation agent.
- `input` — a standalone prompt, a plain string with no conversation around it.
  Required for `general`, and for a `tool_call` test aimed at a general agent.
- A `tool_call` test carries **exactly one** of `history` or `input`, and which
  one it carries decides which kind of agent it can be linked to.
- `evaluation` — **required**. `{"type": ...}`, matching the test's `--type`.
  For `tool_call` it also carries `tool_calls`:
  `[{"tool": "issue_refund", "arguments": {"order_id": "ORD-42"},
  "accept_any_arguments": false}]` (`accept_any_arguments` optional).
- `settings` — optional, e.g. `{"language": "en"}`.

### Bulk row (`tests bulk-create --tests`)

Bulk rows use **different key names** from the single-test config: the
conversation is `conversation_history` here and `history` there. Don't carry one
name into the other command.

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

- `name` — **required**, unique within the batch.
- `conversation_history` — ordered `{role, content}` turns. Required for
  `response` and `conversation` batches, and for `tool_call` batches aimed at a
  conversation agent.
- `input` — a standalone prompt string. Required for `general` batches, and for
  `tool_call` batches aimed at a general agent.
- `evaluators` — `[{evaluator_uuid, variable_values}]`; `variable_values` fills
  the judge prompt's `{{variables}}`. Used by `response`, `conversation` and
  `general`; **not** used by `tool_call`.
- `tool_calls` — the expected calls. Required for `tool_call` batches.
- `inputs` — optional extra request fields for that one row, overriding the
  agent's defaults per key.

`--type` applies to every row, so one batch is all one type. A batch is at most
500 rows, names unique within the batch.

An evaluator's own type has to match the test: a `general` test takes only an
`llm-general` evaluator (judges one input/output pair), a `response` test takes
an `llm` one (judges a reply together with the conversation before it). Mixing
them is rejected.

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
