# Auto-sync: keeping the skills current

The skills depend on two things that move without anyone here noticing: the API
the `calibrate` command talks to, and the web app people are told to click
around in. There is one workflow per source. Both work the same way — Claude
reads what changed, reads the skills, makes the edits, and opens a pull request
for a person to review. Nothing is merged automatically.

| Source | Workflow | Watches for |
| --- | --- | --- |
| The API | [`sync-from-spec.yml`](workflows/sync-from-spec.yml) | Flags, payload shapes, endpoints the skills hardcode |
| The web app | [`sync-from-frontend.yml`](workflows/sync-from-frontend.yml) | Addresses the skills print, names people are told to click, what the product can do |

---

# The API: `sync-from-spec.yml`

The skills hardcode CLI flags and payload shapes from the Calibrate OpenAPI
spec. They are **prose, not generated**, so they cannot be regenerated from the
spec. Instead, every time the API changes, Claude reads what changed, reads the
skills, and makes the edits the change calls for.

## How it triggers

Same mechanism the docs repo (`calibrate`) already uses: `calibrate-backend`
fires a `repository_dispatch` after it finishes publishing, and each consumer
repo listens for it.

```
calibrate-backend ──(publish done)──► repository_dispatch: sync-api-spec
                                          ├─► calibrate        (regenerates docs  → PR)
                                          └─► calibrate-skills (Claude edits them → PR)
```

The listener here is [`sync-from-spec.yml`](workflows/sync-from-spec.yml). It
also runs weekly (cron fallback) and on manual `workflow_dispatch`.

## What the run does

1. Fetches the published spec and diffs it against
   [`openapi.seen.json`](openapi.seen.json), the copy this repo last acted on.
   Both are rewritten with sorted keys first, so the diff shows real API changes
   rather than however the server ordered its JSON that day.
2. If they match, the run stops there and costs nothing.
3. Otherwise Claude gets the diff, reads the skills, and edits the ones the
   change makes wrong or incomplete. Most spec changes touch nothing.
4. If Claude changed nothing, no pull request opens — and `openapi.seen.json`
   stays where it was, so that change is still in the next run's diff and cannot
   be quietly lost.
5. If Claude did change something, `check_skills.py` runs, the snapshot moves
   forward, one pull request opens on `automated/spec-sync`, and an email goes
   out with the link.

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
- **Secret `CLAUDE_CODE_OAUTH_TOKEN`** — required. Without it the step that
  works out what the skills need cannot run.
- **Secrets `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`** —
  required for the email. Same names and same action as `tests.yml` in the
  `calibrate` repo.
- **Secret `SKILLS_SYNC_TOKEN`** (optional) — a PAT so the pull request triggers
  `skill-check`; one opened by the default `GITHUB_TOKEN` does not start further
  CI runs. Without it the pull request still opens, just without an automatic
  check.

## When the pull request is wrong

Claude wrote it, so treat it as a draft by a colleague rather than a fact. The
pull request body says which files changed and why, and whether the skills are
still installable. Edit the branch and merge it, or close it — closing loses
nothing, because the snapshot only moves forward on merge.

---

# The web app: `sync-from-frontend.yml`

The skills also tell people where to go in the web app: the settings page for
creating an API key, the page for one agent, and the words to look for on
screen. None of that is in the API description, so `sync-from-spec` cannot see
it move. This watches for it.

## How it triggers

`calibrate-frontend` fires a `repository_dispatch` on every push to its `prod`
branch, carrying the commit that shipped.

```
calibrate-frontend ──(push to prod)──► repository_dispatch: frontend-released
                                          └─► calibrate-skills (Claude reads it → PR, or drops it)
```

Add this to `calibrate-frontend` as `.github/workflows/notify-skills.yml`:

```yaml
name: notify-skills

on:
  push:
    branches: [prod]

jobs:
  notify:
    if: github.repository == 'ARTPARK-SAHAI-ORG/calibrate-frontend'
    runs-on: ubuntu-latest
    steps:
      - name: Tell calibrate-skills what shipped
        env:
          TOKEN: ${{ secrets.SKILLS_DISPATCH_TOKEN }}
          SHA: ${{ github.sha }}
        run: |
          curl -fsSL -X POST \
            -H "Authorization: Bearer $TOKEN" \
            -H "Accept: application/vnd.github+json" \
            https://api.github.com/repos/dalmia/calibrate-skills/dispatches \
            -d "{\"event_type\":\"frontend-released\",\"client_payload\":{\"sha\":\"$SHA\"}}"
```

`SKILLS_DISPATCH_TOKEN` is a PAT with `contents: write` on
`dalmia/calibrate-skills`. The default `GITHUB_TOKEN` cannot dispatch across
repos.

## What the run does

1. Reads every commit on `prod` between
   [`frontend-seen.txt`](frontend-seen.txt), the last commit this repo looked
   at, and the one that just shipped: the commit subjects, the files they
   touched, and the diff capped at 1500 lines.
2. Claude checks that against the only four things the skills take from the web
   app — the addresses they print, the names people are told to click, the names
   the app shows for things the skills also say out loud, and what the product
   can or cannot do. **Most releases touch none of it, and dropping them is the
   expected outcome.**
3. Nothing relevant, no pull request opens, and the marker is left alone so that
   stretch of prod is read again next time rather than skipped.
4. Something relevant, one pull request opens on `automated/frontend-sync`, the
   marker moves to the commit just read, and an email goes out with the link.

Run it by hand from the Actions tab to re-check a stretch of prod; the `since`
input takes any commit to compare from.

## Config on this repo

- **Secret `FRONTEND_READ_TOKEN`** — required. A PAT with read access to
  `ARTPARK-SAHAI-ORG/calibrate-frontend`, so the run can read what shipped.
- `CLAUDE_CODE_OAUTH_TOKEN`, the four `MAIL_*` secrets and `SKILLS_SYNC_TOKEN`
  are shared with `sync-from-spec.yml` above.
