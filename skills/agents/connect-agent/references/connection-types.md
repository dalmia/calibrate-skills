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

## Choosing

| Have a running service at a URL? | Use |
| --- | --- |
| No | `type=agent` |
| Yes | `type=connection` |

When in doubt default to `type=agent` so the user isn't blocked on standing up
an endpoint they don't have.
