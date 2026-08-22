---
name: send-traces
description: Send an agent's real production turns into Calibrate as traces, by
  adding the send call to the user's own code and confirming one lands. Use when
  the user says "send traces", "log my agent's real conversations", "instrument
  my agent", "record production traffic", "capture what my agent does in
  production", or "I want to see real traffic in Calibrate".
argument-hint: "[agent-name-or-uuid]"
---

# Send traces from a running agent

A trace is a record of one real thing the agent handled in production: what it
was given, and what it produced. Sending them puts real traffic in Calibrate, so
the user can see what their agent actually does and later turn real failures
into test cases. Drives `calibrate traces create`.

See [`../../references/agent-mode.md`](../../references/agent-mode.md) for how to
read command output (TOON/JSON). Keep what you *say* to the user plain — see
[`../../references/voice.md`](../../references/voice.md).

## Phase 0: Setup check

First confirm the CLI itself is installed — `npx skills add` installs only the
instructions, not the `calibrate` command itself:

```bash
command -v calibrate >/dev/null || echo "calibrate CLI not installed"
```

If it's missing, stop and have the user install it, then re-run:

```bash
brew install dalmia/tap/calibrate
```

(No account yet? https://calibrate.artpark.ai). Only once the command is present,
check auth:

```bash
calibrate agents list   # real read — 401 = not signed in, or key for the wrong deployment
```

If unauthenticated, first confirm which Calibrate the user is on — the hosted
service at https://calibrate.artpark.ai, or a self-hosted deployment. A key only
works against the deployment it came from, so this determines how they log in:

```bash
calibrate login                                                            # hosted
# self-hosted: point the CLI at their backend once, then log in
calibrate configure --no-interactive --server-url https://<their-api-host>
calibrate login
```

For self-hosted, find the URL of their deployment's API host — often not the
same as the web address they visit (see
[`../../overview/calibrate-resources/SKILL.md`](../../overview/calibrate-resources/SKILL.md)
→ *Which Calibrate*). An API key is created under **Workspace settings → API
keys** (https://calibrate.artpark.ai/workspace-settings?tab=api-keys) on hosted,
or the equivalent settings page on their deployment.

Then resolve which agent these traces belong to:

```bash
calibrate agents list --output-format json
```

Match `$ARGUMENTS` against the listing if it carries a name or id; otherwise
present a numbered list and ask which agent this code is. No agent yet →
`/connect-agent` first. Keep two things from the chosen item: `agent_uuid`, and
`interaction_type` — that decides the shape of `input` below. **Read it from the
listing; never ask the user.**

- `conversation` → `input` is an array of turns, oldest first, up to the reply
  being reported. Each turn is `{"role": ..., "content": ...}`; `content` may be
  omitted on a turn that only carried tool calls. At most 500 turns, 50000
  characters per string.
- `general` → `input` is a plain string: the standalone prompt.

## Phase 1: Find where to put the call

Inspect before editing — the same discipline as
[`expose-endpoint.md`](../../agents/connect-agent/references/expose-endpoint.md).
Never assume the codebase is empty.

```bash
grep -rniE "traces|X-API-Key|calibrate" --include=*.py --include=*.js \
  --include=*.ts --include=*.go .
```

| What you find | What to do |
| --- | --- |
| Nothing sending traces | Add the call — Phase 2. |
| A send already there and correct | **Don't add a second one.** Skip to Phase 3 and confirm one lands. |
| A send there but wrong — wrong agent id, tool results dropped, blocks the reply, errors not swallowed | Show the offending lines and the minimal fix. Don't bolt on a second call. |

When you do need to add one, find two places and read them properly:

1. **Where the reply leaves the agent** — the last point that has both what came
   in and what went out. Usually the request handler, or the function that
   returns the model's text.
2. **Where tool results come back** — the tool-dispatch loop. Both what the tool
   was called with *and* what it returned have to reach the send call, so if the
   return value is thrown away today, that's part of the edit.

If the code already carries its own ids for the conversation and the last user
message, pass them through (Phase 2). If it doesn't, don't invent an id scheme.

## Phase 2: Add the call

Show a diff in the codebase's own language and let the user apply it. Two things
the code must get right:

- **It must never break the agent.** Sending a trace is not part of answering the
  person, so a failure to send must be swallowed, and the person must not wait
  for it: background task, fire-and-forget thread, queue — whatever is idiomatic
  there. Do not wrap the reply path in anything that can raise.
- **Capture what each tool returned**, not just that it ran:
  `{"tool": "get_schedule", "arguments": {"child_age_weeks": 14},
  "output": {"weeks": 14, "vaccines": ["OPV", "DPT"]}}`.

The whole accepted set of fields — anything else is rejected:

- `agent_id` — required, the agent from Phase 0.
- `input` — required, the shape for this agent's kind (Phase 0).
- `output` — required, an object with at least one of:
  - `response` — the reply text; omit on a turn that only made tool calls.
  - `tool_calls` — up to 50 × `{tool, arguments, output}`. `tool` required;
    `arguments` omitted when there were none; `output` is whatever the tool
    returned (any JSON value), omitted when the code doesn't record it.
- `conversation_id` — optional, their own id; the same id on every turn of one
  conversation ties them together.
- `message_id` — optional, their own id for the last user message, kept for
  reference only.
- `metadata` — optional, a list of up to 100 `{"key": ..., "value": ...}` pairs,
  both strings — **not** a plain object. Prefer OpenTelemetry `gen_ai.*` key
  names where they fit.

The code needs two things from Calibrate: the backend host to post to, and a
workspace API key for the `X-API-Key` header (**Workspace settings → API keys**).
Both belong in the codebase's own environment config, never written into the
source — set them the way that codebase already handles secrets.

Python (adapt to the codebase's HTTP client and framework):

```python
def send_trace(messages, reply, tool_calls, conversation_id):
    try:
        httpx.post(
            f"{os.environ['CALIBRATE_URL']}/traces",     # the backend host
            headers={"X-API-Key": os.environ["CALIBRATE_API_KEY"]},
            json={
                "agent_id": AGENT_ID,
                "input": messages,          # array of turns for this agent
                "output": {"response": reply, "tool_calls": tool_calls},
                "conversation_id": conversation_id,
            },
            timeout=5,
        )
    except Exception:
        pass                                # never break the reply path
```

Called off the reply path — `asyncio.create_task(...)`, a `ThreadPoolExecutor`,
or FastAPI's `BackgroundTasks` — never awaited before returning to the user.

JavaScript / TypeScript:

```js
function sendTrace({ messages, reply, toolCalls, conversationId }) {
  fetch(`${process.env.CALIBRATE_URL}/traces`, {
    method: "POST",
    headers: { "X-API-Key": process.env.CALIBRATE_API_KEY,
               "Content-Type": "application/json" },
    body: JSON.stringify({
      agent_id: AGENT_ID,
      input: messages,
      output: { response: reply, tool_calls: toolCalls },
      conversation_id: conversationId,
    }),
  }).catch(() => {});          // not awaited, never breaks the reply
}
```

For a `general` agent the only change is `input`: the prompt string in place of
the array of turns. Show the user only the shape that matches their agent.

## Phase 3: Check one landed

Don't declare success until a real one has gone through. Send one from the
terminal against the same agent:

```bash
calibrate traces create --agent-id <agent_uuid> \
  --input '<json: array of turns, or a plain string>' \
  --output-param '{"response": "...", "tool_calls": [{"tool": "...", "arguments": {}, "output": {}}]}' \
  --output-format json
```

Add `--conversation-id`, `--message-id` or `--metadata '[{"key": "...", "value":
"..."}]'` only if the codebase actually carries them.

(`-i` is the short form of `--input`.) Report plainly whether it landed. On
failure read the structured error and fix it — a rejected field, the wrong input
shape for this agent's kind, a stale key — rather than moving on. Then have the
user run their own agent once and confirm that turn shows up too; only that
proves the code edit works.

## Phase 4: Summary + next steps

```
Traces flowing
  Agent: <name>
  Dashboard: https://calibrate.artpark.ai/agents/<agent_uuid>
```

Where this goes next:

- Real failures you spot in the traces become test cases → `/build-test-suite`
- Run those tests against the agent → `/run-tests`
