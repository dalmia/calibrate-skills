# Reading `calibrate` CLI output (agent mode)

All these skills drive the `calibrate` CLI. When a coding agent or CI job runs
it, the CLI switches to **agent mode** automatically (it detects `CLAUDE_CODE`,
`CURSOR_AGENT`, and similar). Two things change that matter when parsing output:

- **Output defaults to TOON** — a compact, token-efficient JSON-like format.
  Force a format per command with `--output-format`:
  - `--output-format json` — parse this when you need to extract a field
    (`uuid`, `task_id`, `job_uuid`) reliably. An agent's id comes back as
    `uuid`, not `agent_uuid`; `agent_uuid` is only ever a flag name.
  - `toon` (default), `yaml`, `table`, `pretty` — for display.
- **Errors are structured** — failures come back as a machine-parseable object,
  not prose. Branch on it: distinguish auth failures (re-run `calibrate login`)
  from validation errors (fix the payload) from not-found (wrong UUID).

## Conventions used across the skills

- **Always add `--output-format json`** on any command whose result you need to
  read a field out of (creates, run launches, status polls).
- **Always add `--no-interactive`** on every command you run, not just in CI.
  It stops the CLI opening a prompt, a form, or the explorer when you aren't
  there to answer.
- **Ask for less than the whole result.** A run of a hundred-odd tests comes
  back as about a megabyte of text, nearly all of it the agent's answers and the
  judge's reasoning. Reading all of that on every poll is slow and buys you
  nothing. `--jq` works everywhere. `--compact` and `--only-failed` exist only on
  `agent-tests get-run` and `agent-tests get-benchmark`, and they do different
  things on each: see those skills. Pull the full text once at the end, for the
  cases you're going to show.
- **Never fabricate a field.** If a command fails or omits a field, report the
  error — do not invent a UUID, score, or status.
- **Toggle agent mode by hand** only if needed: `--agent-mode` /
  `--agent-mode=false`.

## Polling pattern (runs, benchmarks, evaluator jobs)

Launch commands return a `task_id` / `job_uuid`; results come from a separate
`get-*` command. There are two status sets, and they do not agree on the word
for finished:

- **Test runs and benchmarks** (`task_id`): `queued`, `in_progress`,
  `cancelled`, `done`, `failed`. A finished run says `done`, never `completed`.
  `cancelled` is final too: someone stopped it, so stop polling.
- **Evaluator runs** (`job_uuid`): `queued`, `in_progress`, `completed`,
  `failed`. Here a finished job does say `completed`.

Back off between polls, report progress to the user, and never block silently.
