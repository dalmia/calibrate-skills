# Give the user the link, every time

Whenever a skill makes something the user can open in Calibrate, end that step
with the address for it. They should never have to go and find it.

This applies to all of it: tests, a labelling task, a test run, a benchmark, an
evaluator (on create and on every update), and an agent.

## The two parts of an address

`<app>` is the address the user opens Calibrate at:
`https://calibrate.artpark.ai` on the hosted service, or their own address if
they run their own copy. You asked them for it at sign-in, so you have it.

`<workspace_uuid>` is the workspace their API key belongs to. Ask for it once,
the first time you need a link, and reuse it for the rest of the session:

```bash
calibrate workspace current --output-format json
```

It comes back as `{"uuid": "...", "name": "..."}`. Read `uuid` from it, and
never make one up. The command arrived in CLI 0.0.84; on an older one it isn't
there, but every skill upgrades the CLI before it runs, so that should not
happen.

If you still cannot get it, leave that part out and link `<app>/tests` instead
of `<app>/<workspace_uuid>/tests`. That still opens, but it opens whichever
workspace the user looked at last, so it lands in the wrong place for anyone
who works across two. Prefer the full address every time.

## Where things live

| What you just made | Address |
|---|---|
| Tests | `<app>/<workspace_uuid>/tests` |
| A test run or benchmark | `<app>/<workspace_uuid>/tests?tab=runs&runId=<task_id>` |
| A labelling task | `<app>/<workspace_uuid>/human-alignment?tab=tasks` |
| An evaluator | `<app>/<workspace_uuid>/evaluators/<evaluator_uuid>` |
| An agent | `<app>/<workspace_uuid>/agents/<agent_uuid>` |

## How to write it

One line, after the outcome, saying what they will see. Not a bare address.

> Added 40 tests. See them here:
> https://calibrate.artpark.ai/8f3c1a2b-4d5e-4a1b-9c7d-2e5f8a1b3c4d/tests

> The run finished, 32 of 40 passed. Full results:
> https://calibrate.artpark.ai/8f3c1a2b-4d5e-4a1b-9c7d-2e5f8a1b3c4d/tests?tab=runs&runId=b0ee4304-3a53-4074-84cb-c31ac779e7bb

> Updated "Reply correctness" and made it live:
> https://calibrate.artpark.ai/8f3c1a2b-4d5e-4a1b-9c7d-2e5f8a1b3c4d/evaluators/3e830208-d7a8-4bb0-a5b8-44edf1179837

Never invent a UUID to put in a link. If the command didn't give you one, say
what happened instead and leave the link out.
