---
name: calibrate-resources
description: Orientation for evaluating agents with Calibrate — the primitives
  (agents, tests, agent-tests, evaluators, annotation tasks, traces), the CLI,
  auth, and which skill to reach for. Load when the user asks "what is
  Calibrate", "how do I evaluate with Calibrate", "what can Calibrate do", or
  seems unsure where to start.
---

# Calibrate: resources and orientation

Calibrate is an evaluation platform for AI agents. You connect an agent, define
test cases, run them, and — its signature move — **calibrate the LLM judges
against human labels** so the automated scores are trustworthy. These skills
drive the `calibrate` CLI against the public API.

## Get the latest instructions

Both the skill and the CLI on this machine can be months behind. Update both
before anything else, following
[`../../references/startup.md`](../../references/startup.md):

```bash
npx -y skills update calibrate-resources -g -y ; npx -y skills update calibrate-resources -p -y
```

```bash
have=$(calibrate version 2>/dev/null | head -1 | awk '{print $2}')
want=$(curl -fsS https://api.github.com/repos/dalmia/calibrate-cli/releases/latest 2>/dev/null | sed -n 's/.*"tag_name": *"v\{0,1\}\([^"]*\)".*/\1/p' | head -1)
if [ -n "$want" ] && [ "$have" != "$want" ]; then
  if command -v brew >/dev/null 2>&1; then
    brew update >/dev/null 2>&1
    brew install dalmia/tap/calibrate >/dev/null 2>&1 || brew upgrade dalmia/tap/calibrate >/dev/null 2>&1
  else
    arch=$(uname -m); case "$arch" in aarch64|arm64) arch=arm64 ;; *) arch=x86_64 ;; esac
    case "$(uname -s)" in
      Linux)  os=Linux;   bin=calibrate ;;
      Darwin) os=Darwin;  bin=calibrate ;;
      *)      os=Windows; bin=calibrate.exe ;;
    esac
    dest=$(command -v calibrate || echo "$HOME/.local/bin/$bin")
    tmp=$(mktemp -d)
    if [ "$os" = Windows ]; then
      curl -fsSL -o "$tmp/c.zip" "https://github.com/dalmia/calibrate-cli/releases/download/v${want}/calibrate-cli_${os}_${arch}.zip" && unzip -oq "$tmp/c.zip" -d "$tmp"
    else
      curl -fsSL "https://github.com/dalmia/calibrate-cli/releases/download/v${want}/calibrate-cli_${os}_${arch}.tar.gz" | tar xz -C "$tmp"
    fi
    if [ -f "$tmp/$bin" ]; then
      mkdir -p "$(dirname "$dest")"
      chmod +x "$tmp/$bin"
      cp "$tmp/$bin" "$dest"
    fi
    rm -rf "$tmp"
  fi
fi
calibrate version 2>/dev/null | head -1 || echo "calibrate is not installed"
```

Then re-read this `SKILL.md` from the path you loaded it from and follow that
copy: what is in your context is the version from before the update, and the
steps below may have changed.

Do all of this silently. `startup.md` names the one case worth telling the user
about.

## Setup

```bash
brew install dalmia/tap/calibrate    # install the CLI
calibrate login                      # authenticate (API key from workspace settings)
calibrate agents list                # confirm auth with a real call
```

**Confirm the *key works* with a real read, not `whoami`.** `calibrate whoami`
prints the resolved server URL and the configured key's source — useful for
checking *which* host and key are in play — but it never calls the server, so it
can't tell you the key is actually valid. For that, use a real read like
`calibrate agents list`: a `401` there means not signed in, or a key for the
wrong deployment (see *Which Calibrate* below).

API key: **Workspace settings → API keys**
(https://calibrate.artpark.ai/workspace-settings?tab=api-keys).

### Which Calibrate — hosted or self-hosted

A key only validates against the deployment it was created in: a key from a
self-hosted Calibrate will 401 against the hosted service, and vice versa. This
is the most common "my API key doesn't work" cause. **Before `calibrate login`,
confirm which deployment the user is on** (see [`voice.md`](../../references/voice.md)
for how to ask):

Two different URLs are in play — keep them apart:

- **Web address** (frontend) — what the user opens in a browser to sign in and
  create their key, e.g. `https://calibrate.artpark.ai`.
- **API host** (backend) — what the CLI talks to, and the *only* thing
  `--server-url` accepts, e.g. `https://api.calibrate.artpark.ai`.

They are **not** the same host, and there is no fixed rule mapping one to the
other — hosted uses an `api.` prefix, but a self-hosted app at
`calibrate.example.org` might call `calibrate-backend.example.org`. So **never
pass the web address to `--server-url`** and never guess the API host from the
web address by pattern.

- **Hosted at https://calibrate.artpark.ai** — the CLI already defaults to the
  hosted API host, so plain `calibrate login` works; nothing extra to do.
- **Self-hosted** — the user's team runs its own Calibrate. Point the CLI at
  their **API host** once with `configure` (it persists to
  `~/.config/calibrate/config.yaml`), then have them log in — the key is then
  validated against, and every later command reaches, their backend with no
  repeated flags:

  ```bash
  calibrate configure --no-interactive --server-url https://<their-calibrate-api-host>
  calibrate login        # then have the user log in / paste their key
  calibrate agents list  # verify: empty list (200) = success; 401 = key not valid there
  ```

  **Order matters: `configure` the host *before* `login`.** Do the `configure`
  step yourself once you've found the host (it's just the URL, not a secret); the
  key is the user's to enter. Resolution is flag > env > config, so a one-off
  `--server-url …` or `CALIBRATE_SERVER_URL` still overrides per call, and
  `calibrate whoami` shows the resolved URL and where it came from — use it to
  confirm the host landed.

  **Finding the API host is your job, not the user's — do it silently.** Ask
  them only for the web address they open (that is all a non-technical user
  reliably knows), tell them you'll take it from there, then work it out without
  narrating. Don't hand-write the search each time — run the helper:

  ```bash
  scripts/find-backend.sh <web-address>   # best guess on stdout, alternates on stderr
  host=$(scripts/find-backend.sh <web-address>)   # capture it directly
  ```

  It fetches the app and its JS (where the backend host is compiled in — a
  Next.js app proxies `/api/*` same-origin, so it isn't visible in the top-level
  network tab) and prints the likely API host, preferring one on the front end's
  own parent domain. Take the top hit; if it looks wrong, the stderr list and
  whoever set the deployment up are your fallbacks. Do **not** report back that
  "the web address isn't the one I need" — that turns your own request into a
  bait-and-switch. The user hears the outcome ("logged you in against your
  deployment"), never the front-end/back-end gap. If they happen to know the
  API/backend URL, take it directly. Once `configure` has set the host, the key
  is stored by `login` and the host by config, so plain commands (no flag) reach
  their deployment from then on.

### Linking to something in the web app

Web addresses for a specific page start with the workspace ID, as in
`<web-address>/<workspace_uuid>/tests` or
`<web-address>/<workspace_uuid>/agents/<agent_uuid>`. Get the ID with
`GET <api-host>/organizations/current` (header `X-API-Key`); it returns
`uuid` and `name` for the workspace the key belongs to. Fetch it once and reuse
it. If the call fails, skip the link rather than sending a broken one. When you
hand the user a link, give just the address, never the lookup.

See
[`../../references/agent-mode.md`](../../references/agent-mode.md) for output
formats and [`../../references/config-shapes.md`](../../references/config-shapes.md)
for payload shapes. Keep what you *say* to the user plain — see
[`../../references/voice.md`](../../references/voice.md).

## The six primitives

| Primitive | What it is | CLI group | Skill |
| --- | --- | --- | --- |
| **Agent** | The agent you're testing (endpoint or internal-LLM), of one of two fixed kinds — `conversation` or `general` | `agents` | `/connect-agent` |
| **Test** | One case + evaluators — `response`, `conversation`, `tool_call` or `general` | `tests` | `/build-test-suite`, `/import-dataset` |
| **Agent-test** | Linking tests to an agent and running them | `agent-tests` | `/run-tests`, `/benchmark-models` |
| **Evaluator** | A versioned LLM/audio judge (binary or rating) | `evaluators` | `/design-evaluator`, `/iterate-evaluator` |
| **Annotation task** | Human labels + human↔judge agreement | `annotation-tasks` | `/calibrate-evaluator` |
| **Trace** | One real turn the agent handled in production — what it was given, what it produced, and the tools it called | `traces` | `/send-traces` |

## Typical flow

1. `/connect-agent` — register + verify the agent.
2. `/send-traces` — if the agent already runs in production, send real turns so
   actual failures become test cases (feeds `/build-test-suite`).
3. `/build-test-suite` (or `/import-dataset`) — author test cases.
4. `/design-evaluator` — if any test judges response quality.
5. `/run-tests` — run and read pass/fail.
6. `/calibrate-evaluator` — prove the judge agrees with humans before trusting it.
7. `/benchmark-models` — compare models once the harness is trustworthy.
8. `/iterate-evaluator` — tune the judge and reset its live version.

`/onboard` runs this whole flow interactively for a first-time user.

## Not in the public API

Calibrate's public API covers tests, evaluators, traces, and annotation-based
judge calibration. There is **no** persona/simulation, dashboard, or report
resource — don't offer skills for those here.
