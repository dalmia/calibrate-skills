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
- **Non-interactive runs** (CI, unattended): pass `--no-interactive` to disable
  prompts, the explorer auto-launch, and TUI forms.
- **Never fabricate a field.** If a command fails or omits a field, report the
  error — do not invent a UUID, score, or status.
- **Toggle agent mode by hand** only if needed: `--agent-mode` /
  `--agent-mode=false`.

## Polling pattern (runs, benchmarks, evaluator jobs)

Launch commands return a `task_id` / `job_uuid`; results come from a separate
`get-*` command. Poll it until the status is terminal (`completed` / `failed`),
backing off between polls. Report progress to the user; never block silently.
