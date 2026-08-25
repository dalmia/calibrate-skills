# Auto-sync: keeping the skills aligned with the API

The skills hardcode CLI flags and payload shapes from the Calibrate OpenAPI
spec. They are **prose, not generated**, so they cannot be regenerated from the
spec — but they are **drift-checked** against it. When the backend publishes a
spec change that breaks something a skill documents, a PR is opened with a drift
report.

## How it triggers

Same mechanism the docs repo (`calibrate`) already uses: `calibrate-backend`
fires a `repository_dispatch` after it finishes publishing, and each consumer
repo listens for it.

```
calibrate-backend ──(publish done)──► repository_dispatch: sync-api-spec
                                          ├─► calibrate        (regenerates docs → PR)
                                          └─► calibrate-skills (drift-checks       → PR)
```

The listener here is [`sync-from-spec.yml`](workflows/sync-from-spec.yml). It
also runs weekly (cron fallback) and on manual `workflow_dispatch`.

## What the backend needs to add

In `calibrate-backend`, in the job/step that runs after publishing succeeds,
add `calibrate-skills` as a dispatch target (alongside the existing `calibrate`
one). One step per consumer:

```yaml
- name: Notify calibrate-skills of the new spec
  run: |
    curl -fsSL -X POST \
      -H "Authorization: Bearer ${{ secrets.DISPATCH_PAT }}" \
      -H "Accept: application/vnd.github+json" \
      https://api.github.com/repos/dalmia/calibrate-skills/dispatches \
      -d '{"event_type":"sync-api-spec","client_payload":{"spec_url":"<published-openapi-url>"}}'
```

- `DISPATCH_PAT` — a PAT (or GitHub App token) with `contents: write` on
  `dalmia/calibrate-skills`. The default `GITHUB_TOKEN` cannot dispatch across
  repos.
- `client_payload.spec_url` — optional. If omitted, the workflow falls back to
  the repo variable `OPENAPI_SPEC_URL`.

## Config on this repo

- **Variable `OPENAPI_SPEC_URL`** — public URL of the published `openapi.json`
  (the API's `/openapi` endpoint or the hosted docs spec). Used when the
  dispatch carries no `spec_url`.
- **Secret `SKILLS_SYNC_TOKEN`** (optional) — a PAT so the drift PR triggers
  `skill-check`; PRs opened by the default `GITHUB_TOKEN` do not start further
  CI runs. Without it the PR still opens, just without an automatic check.

## Extending the guard

The check is only as good as its declared dependencies. When a skill starts
relying on a new operation or payload field, add it to `REQUIRED_OPERATIONS` /
`REQUIRED_SCHEMA_FIELDS` in [`scripts/check_spec_drift.py`](../scripts/check_spec_drift.py).
CLI-flag-level drift (a renamed `--flag`) is best caught by a complementary job
that diffs `calibrate <cmd> --help`; add it if flag churn becomes a problem.
