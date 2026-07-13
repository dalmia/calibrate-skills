# Expose a Calibrate endpoint from a codebase

Use this when the user has an agent **codebase** but no HTTP endpoint Calibrate
can reach yet — you add the endpoint for them, infer its auth from the code, and
only then collect the one thing the code can't tell you: where it's deployed.

Skip all of this when the user already has a live URL — go straight to
`agents create` with their `endpoint`.

## The connection contract

Calibrate needs one HTTP route that follows a fixed contract:

- **Request** — Calibrate sends `POST` with the conversation history as a
  `messages` array in OpenAI chat format:

  ```json
  { "messages": [
      {"role": "assistant", "content": "Hi, how can I help?"},
      {"role": "user", "content": "What's my vaccination schedule?"}
  ] }
  ```

  An optional `model` field is added only when benchmarking across models; ignore
  it unless the agent switches models from that input.

- **Response** — the route returns JSON with **at least one** of `response` (the
  agent's text reply) or `tool_calls` (an array of `{tool, arguments}`, each
  optionally carrying an `output`):

  ```json
  { "response": "Your next vaccination is at 14 weeks — OPV and DPT.",
    "tool_calls": [
      {"tool": "get_schedule", "arguments": {"child_age_weeks": 14}}
    ] }
  ```

## Inspect first — don't assume greenfield

Before editing anything, find out whether a Calibrate-style route **already
exists**, so you don't add a duplicate or step on working wiring. Search the
codebase for the tell-tale signs of the contract:

```bash
grep -rniE "/calibrate|calibrate.?test|\"?tool_calls\"?|\"?messages\"?\s*[:=]" \
  --include=*.py --include=*.js --include=*.ts --include=*.go .
```

Also list the app's POST routes (`@app.post`, `app.post(`, `router.POST`,
`methods=["POST"]`) and read any that look agent-facing. Then classify:

| What you find | What to do |
| --- | --- |
| **No route** matching the contract | Add one — go to **Add the route**. |
| A route that **already conforms** (POST, reads a `messages` array, returns `response` and/or `tool_calls`) | **Don't touch the code.** Use its path as the endpoint and go straight to auth inference + create/verify. |
| A route that's **present but mis-wired** | Report the exact mismatch, propose a targeted fix — don't bolt on a second route. |

When a route is present but wrong, check it against the contract point by point
and name what's off:

- Wrong method (GET instead of POST), or wrong path than the user expects.
- Reads the body as something other than a `messages` array (e.g. a single
  `prompt` / `text` field, or query params).
- Returns the reply under the wrong key (`reply`, `output`, `text`,
  `choices[0]...`) instead of `response`, or emits neither `response` nor
  `tool_calls`.
- Drops tool calls the agent makes, or returns them in a non-contract shape
  (not an array of `{tool, arguments}`).

Show the user the offending lines and the minimal edit to bring them into line,
then let them apply it. `verify-connection` (Phase 3) is the backstop that
confirms whichever path you took actually works.

## Add the route

Pull the model call out of the request handler into a reusable function, then
expose a thin Calibrate route that calls it directly with `body["messages"]`.
Match the codebase's framework and style — the shape below is FastAPI; adapt for
Flask, Express, Next.js route handlers, etc.

**Before** — the model call is buried in the handler:

```python
def inference(x1, x2, x3):
    messages = build_messages(x1, x2, x3)
    response = client.chat.completions.create(messages=messages)  # buried
    return transform(response)
```

**After** — the model call is shared, and a Calibrate route reuses it:

```python
def llm_inference(messages):
    """Core model call — reused by both the agent and Calibrate."""
    response = client.chat.completions.create(messages=messages)
    return response.choices[0].message.content

def inference(x1, x2, x3):
    messages = build_messages(x1, x2, x3)
    return transform(llm_inference(messages))   # same call, now shared

@app.post("/calibrate/test")                     # the endpoint you connect
def calibrate_test(body):
    return {"response": llm_inference(body["messages"])}
```

If the agent emits tool calls, return them too:
`{"response": ..., "tool_calls": [{"tool": name, "arguments": {...}}]}`.

Show the user the diff and let them apply/deploy it. Calibrate can only reach a
**publicly deployed** URL, so the route must ship before you verify.

## Infer auth from the code — don't ask blindly

Read the existing routes/middleware to decide what `headers` (if any) the new
route needs. **Do not ask "are there any headers?"** — infer, then confirm only
what you genuinely can't resolve.

Look for:

- **Header/scheme** — auth middleware or per-route guards reading
  `Authorization`, `X-API-Key`, `X-Api-Token`, cookies, or a custom header.
  Framework signals: FastAPI `Depends(...)` / `Security(...)`, Flask
  `@requires_auth` / `before_request`, Express `app.use(authMiddleware)`,
  `passport`, `verifyToken`. The **name and scheme** (`Bearer`, raw key) are
  almost always derivable from code.
- **Secret value** — the env var or secret store the check reads
  (`os.environ["API_KEY"]`, `process.env.AGENT_TOKEN`, a vault client). The code
  gives you the *name*, not the *value*.

Decision table:

| What the code shows | What to do |
| --- | --- |
| No auth on any route / the route is intentionally public | Create the agent with **no** `headers`. Don't ask. State: "No auth header — the endpoint is open in the code." |
| A header + scheme, secret from an env var | Set `headers` to `{"<Header>": "<scheme> <value>"}`. Ask **only** for the secret value (the code can't resolve it), then confirm before create. |
| Auth present but ambiguous (custom/opaque middleware) | Show the user the exact code you found and ask them to confirm the header name + value. Don't guess. |

Never invent a header the code doesn't require, and never leave off one it does.
Treat a discovered secret value as sensitive: put it straight into
`--config-param` for the create call; don't echo it back in summaries or logs.

## What to actually ask the user

After inspecting the code you should only need:

1. **Deploy base URL** — where the route is/will be hosted (the code can't know
   this). The endpoint is `<base-url>/calibrate/test` (or wherever you added it).
2. **Any secret value** the code references but can't resolve — and only that.

Then hand back to Phase 2 of the skill with `endpoint` set to the full URL and
`headers` set from inference (or omitted entirely when there is no auth).
