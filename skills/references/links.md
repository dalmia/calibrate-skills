# Give the user the link, every time

Whenever a skill makes something the user can open in Calibrate, end that step
with the address for it. They should never have to go and find it.

This applies to all of it: tests, a labelling task, a test run, a benchmark, an
evaluator (on create and on every update), and an agent.

## Where things live

Take `<app>` from the address the user opens Calibrate at:
`https://calibrate.artpark.ai` on the hosted service, or their own address if
they run their own copy. You asked them for it at sign-in, so you have it.

| What you just made | Address |
|---|---|
| Tests | `<app>/tests` |
| A test run or benchmark | `<app>/tests?tab=runs&runId=<task_id>` |
| A labelling task | `<app>/human-alignment?tab=tasks` |
| An evaluator | `<app>/evaluators/<evaluator_uuid>` |
| An agent | `<app>/agents/<agent_uuid>` |

A link that does not name the workspace still works. Calibrate works out which
workspace the user is in and takes them there, carrying the rest of the address
with it.

## How to write it

One line, after the outcome, saying what they will see. Not a bare address.

> Added 40 tests. See them here: https://calibrate.artpark.ai/tests

> The run finished, 32 of 40 passed. Full results:
> https://calibrate.artpark.ai/tests?tab=runs&runId=b0ee4304-3a53-4074-84cb-c31ac779e7bb

> Updated "Reply correctness" and made it live:
> https://calibrate.artpark.ai/evaluators/3e830208-d7a8-4bb0-a5b8-44edf1179837

Never invent a UUID to put in a link. If the command didn't give you one, say
what happened instead and leave the link out.
