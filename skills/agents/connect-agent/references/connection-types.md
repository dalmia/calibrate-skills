# Agent connection types

How Calibrate connects to the agent under test. The keys you set under
`--config-param` depend on the type. Confirm exact accepted keys against the live
schema: `calibrate agents create --help`.

## `type=agent` — built inside Calibrate (no endpoint)

Calibrate calls a model directly as the agent — use when the user has no running
service to point at.

- **`--type`**: `agent` (the CLI default)
- **Required config keys**: `system_prompt`, `llm.model` (e.g. `openai/gpt-4.1`)
- **Optional config keys**: `stt.provider`, `tts.provider`, `settings.agent_speaks_first`,
  `settings.max_assistant_turns`, `system_tools.end_call`, `data_extraction_fields`
- **Use when**: evaluating a prompt/model choice before any service exists.

```json
{
  "system_prompt": "You are a helpful support agent.",
  "llm": {"model": "openai/gpt-4.1"}
}
```

## `type=connection` — your own HTTP endpoint

Calibrate sends conversations to an HTTP endpoint you host.

- **`--type`**: `connection`
- **Required config keys**: `agent_url` (valid http/https URL)
- **Optional config keys**: `agent_headers` (auth headers), `benchmark_provider`
- **No endpoint yet, but a codebase?** See
  [`expose-endpoint.md`](expose-endpoint.md) — add the `/calibrate/test` route,
  infer auth headers from the code, then come back here.
- **Validation**: URL must be reachable from Calibrate — run
  `verify-connection` after create.
- **Common pitfalls**:
  - Endpoint behind a VPN/firewall — must be publicly reachable.
  - Missing auth header → 401 at verify time; set it in `agent_headers`.

```json
{
  "agent_url": "https://api.example.com/agent",
  "agent_headers": {"Authorization": "Bearer <token>"}
}
```

## `interaction_type` — what the agent is called *with*

**This is a second, independent question, not part of `--type`.** `--type` says
*where the agent lives* (inside Calibrate, or behind your own endpoint);
`interaction_type` says *what Calibrate sends it when it calls*. All four
combinations are valid — an agent built inside Calibrate and a connected one can
each be either kind.

- **`--interaction-type conversation`** (short `-i`; the CLI default) — the agent
  is called with the whole exchange so far:

  ```json
  { "messages": [
      {"role": "assistant", "content": "Hi, how can I help?"},
      {"role": "user", "content": "What's my vaccination schedule?"}
  ] }
  ```

- **`--interaction-type general`** — the agent is called with only the latest
  user text:

  ```json
  { "input": "Summarise this transcript in three bullets." }
  ```

- **Set at creation, and fixed after that.** `calibrate agents update` has no flag
  for it and the API's update body doesn't accept it — changing an agent's kind
  means creating a new agent.
- **Simulations need `conversation`.** A simulation always sends the exchange so
  far, so a `general` agent can't be used with one.
- **Reading it back**: `calibrate agents list --output-format json` returns
  `interaction_type` on every item — when the user reuses an existing agent, take
  it from there instead of asking again.
- **CLI floor**: `--interaction-type` exists from CLI 0.0.41 onward. Omitting it
  keeps today's behavior (`conversation`).

## Choosing

| Have a running service at a URL? | Use |
| --- | --- |
| No | `type=agent` |
| Yes | `type=connection` |

When in doubt default to `type=agent` so the user isn't blocked on standing up
an endpoint they don't have. That table settles `--type` only — the kind of call
the agent takes is the separate question above, and you have to answer both.
