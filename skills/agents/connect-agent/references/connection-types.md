# Agent connection types

How Calibrate connects to the agent under test. The keys you set under
`--config-param` depend on the type. Confirm exact accepted keys against the live
schema: `calibrate agents create --help`.

## Internal-LLM agent (no endpoint)

Calibrate calls a model directly as the agent — use when the user has no running
service to point at. Provide the model, system prompt, and (optionally) the tool
schema in `config-param`; do not set an endpoint.

- **Required**: `model` (e.g. `openai/gpt-4.1`), `system_prompt`
- **Optional**: `tools` (JSON tool schema), `temperature`
- **Use when**: evaluating a prompt/model choice before any service exists.

## External chat/API agent (endpoint)

Calibrate sends conversations to an HTTP endpoint you host.

- **Required**: `agent_url` (valid http/https URL)
- **Optional**: `agent_headers` (auth), `model`, `system_prompt`, `timeout`
- **No endpoint yet, but a codebase?** See
  [`expose-endpoint.md`](expose-endpoint.md) — add the `/calibrate/test` route,
  infer `headers` from the code, then come back here.
- **Validation**: URL must be reachable from Calibrate — run
  `verify-connection` after create.
- **Common pitfalls**:
  - Endpoint behind a VPN/firewall — must be publicly reachable.
  - Missing auth header → 401 at verify time; set it in `headers`.
  - Endpoint slower than the timeout → increase `timeout`.

## Choosing

| Have a running service at a URL? | Use |
| --- | --- |
| No | internal-LLM agent |
| Yes | external chat/API agent |

Both are the same `agents create` call — the difference is whether
`config-param` carries an `endpoint`. When in doubt default to internal-LLM mode
so the user isn't blocked on standing up an endpoint they don't have.
