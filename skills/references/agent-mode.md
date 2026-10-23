# Reading `calibrate` CLI output (agent mode)

All these skills drive the `calibrate` CLI. When a coding agent or CI job runs
it, the CLI switches to **agent mode** automatically (it detects `CLAUDE_CODE`,
`CURSOR_AGENT`, and similar). Two things change that matter when parsing output:

- **Output defaults to TOON** — a compact, token-efficient JSON-like format.
  Force a format per command with `--output-format`:
  - `--output-format json` — parse this when you need to extract a field
    (`agent_uuid`, `task_id`, `job_uuid`) reliably.
  - `toon` (default), `yaml`, `table`, `pretty` — for display.
- **Errors are structured** — failures come back as a machine-parseable object,
  not prose. Branch on it: distinguish auth failures (re-run `calibrate login`)
  from validation errors (fix the payload) from not-found (wrong UUID).

## Conventions used across the skills

- **Always add `--output-format json`** on any command whose result you need to
  read a field out of (creates, run launches, status polls).
- **End every command with `< /dev/null`.** The CLI reads standard input before
  it sends its request, so a command run with an input stream nobody writes to
  and nobody closes just sits there: nothing printed, nothing sent, no exit, for
  as long as you leave it. It looks exactly like a slow server, and
  `--no-interactive` does not stop it. The same `get-run` that sat for two and a
  half minutes returned in one second with `< /dev/null` on the end. The one
  exception is `calibrate login`, which needs the input stream because the user
  pastes their key into it.
- **Always add `--no-interactive`** on every command you run, not just in CI.
  It stops the CLI opening a prompt, a form, or the explorer when you aren't
  there to answer.
- **Ask for less than the whole result.** A run of a hundred-odd tests comes
  back as about a megabyte of text, nearly all of it the agent's answers and the
  judge's reasoning. Reading all of that on every poll is slow and buys you
  nothing: use `--compact`, `--only-failed` or `--jq`, and pull the full text
  once at the end for the cases you're going to show.
- **Never fabricate a field.** If a command fails or omits a field, report the
  error — do not invent a UUID, score, or status.
- **Toggle agent mode by hand** only if needed: `--agent-mode` /
  `--agent-mode=false`.

## Polling pattern (runs, benchmarks, evaluator jobs)

Launch commands return a `task_id` / `job_uuid`; results come from a separate
`get-*` command. Poll it until the status is final: `done` or `failed`. A
finished run says `done`, not `completed`. Back off between polls, report
progress to the user, and never block silently.
