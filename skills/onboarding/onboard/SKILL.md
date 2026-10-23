---
name: onboard
description: Guided end-to-end setup for a first Calibrate evaluation — connect an
  agent, build tests, run them, and (optionally) calibrate the judge against
  humans. Orchestrates the feature skills. Use when the user says "get started",
  "onboard me", "set up Calibrate", "evaluate my agent" (and they have no tests
  yet), or "run my first eval". Prefer run-tests when the user already has
  tests set up.
argument-hint: "[what-you-want-to-evaluate]"
---

# Calibrate onboarding

Take a first-time user from nothing to a trustworthy evaluation. This skill is an
**orchestrator**: each phase delegates to a feature skill and produces a real
Calibrate object. Persist progress to `.calibrate/onboard.md` (copy the bundled
[`assets/onboard.md`](assets/onboard.md) on first use) so a session can resume at
the first incomplete phase.

Loose inspiration: the local `calibrate-guide` intake flow — phased, resumable,
adaptive. This version targets the cloud API primitives.

This is a first-time user's first contact with Calibrate, so voice matters most
here — keep what you *say* plain and jargon-free. See
[`../../references/voice.md`](../../references/voice.md).
When you finish a step, give the user the address for everything you set up along the way, as
[`../../references/links.md`](../../references/links.md) sets out.

## Get the latest instructions

Both the skill and the CLI on this machine can be months behind. Update both
before anything else, following
[`../../references/startup.md`](../../references/startup.md):

```bash
npx -y skills update onboard -g -y ; npx -y skills update onboard -p -y
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

## Operating principle: match the user's pace

Match rigor to the user's expertise:

- **Novice / unspecified** — walk the phases in order, use defaults, run the
  setup check, don't over-ask.
- **Expert / explicit** — honor their choices, compress or skip phases they've
  already answered, let them dictate. Defaults are a fallback, not a mandate.

Compress a phase when the user already gave you the answer in passing. The phase
list is structure, not a script.

## Setup check (before any run)

From the project root, run the bundled stdlib gate — it needs nothing installed:

```bash
uv run --no-project /path/to/skills/onboarding/onboard/scripts/validate.py \
  --state .calibrate/onboard.md
```

It exits non-zero and lists what's missing when a required phase is unfilled.
Default-on for novices; an expert may skip it.

## Setup (first use in a project)

```bash
mkdir -p .calibrate
cp /path/to/skills/onboarding/onboard/assets/onboard.md .calibrate/onboard.md
```

Confirm the CLI is installed, then auth, once. `npx skills add` installs only
the instructions, not the `calibrate` command itself — if it's missing, have the user
`brew install dalmia/tap/calibrate` before continuing:

```bash
command -v calibrate >/dev/null || echo "calibrate CLI not installed — brew install dalmia/tap/calibrate"
calibrate agents list   # real read — 401 (not signed in / wrong deployment) → calibrate login
```

Before that first login, confirm which Calibrate the user is on — the hosted
service at https://calibrate.artpark.ai, or a self-hosted deployment. A key from
one won't validate against the other. For self-hosted, find their deployment's
API host and point the CLI at it *before* logging in:
`calibrate configure --no-interactive --server-url https://<their-calibrate-api-host>`,
then `calibrate login`. See [`calibrate-resources`](../../overview/calibrate-resources/SKILL.md)
→ *Which Calibrate* for the details and the API-host-vs-web-address gotcha.

## Phase 1 — Describe your agent

Ask what the agent does, who uses it, and where it fails today. Also settle
which kind it is — ask it in their words ("does it go back and forth with a
person, or take one instruction and give one answer?"), never by the field name.
That answer sets `interaction_type` at creation and can never be changed
afterwards, and it decides which test and evaluator types are allowed later.
Write a short summary into **Phase 1** of `.calibrate/onboard.md`. Then delegate:

→ **`/connect-agent`** — register + `verify-connection`. Record the resulting
`agent_uuid` in the state file. Don't proceed until the connection verifies.
An agent built inside Calibrate has no connection to check; `/connect-agent`
Phase 3 says what to check instead.

## Phase 2 — Decide how answers are graded

Do this before writing any test: each judged test needs its judge attached when
it is created. Never pick a judge for the user, not even an existing one.

→ **`/design-evaluator`**. Its Phase 1 explains to the user what a judge is,
suggests qualities to check based on Phase 1 here, and lets them pick one or
more or add their own. Write the qualities they chose into **Phase 2**, and
record the `evaluator_uuid`(s).

Skip this phase only if every test will check which action the agent took
(`tool_call`).

## Phase 3 — Turn goals into tests

Turn the goal into a falsifiable claim ("when the user gives an ORD-\d+ id, the
agent calls `check_order` with that id"). Write it into **Phase 3**. Then:

→ **`/build-test-suite`** (or **`/import-dataset`** if they already have a
dataset). Name the test type per case as you go: `tool_call` = deterministic and
free; `response`, `conversation` and `general` all need a judge. Phase 1's answer
fixes the choice — a back-and-forth agent takes `response` or `conversation`
cases, a one-instruction-one-answer agent takes `general` ones. Attach the
judges chosen in Phase 2, one per quality, to each judged case. Record the
`test_uuids`.

## Phase 4 — Run

→ **`/run-tests`** — link tests to the agent, run, poll, and read results.
Present **failures first**. Record the `task_id` and outcome in **Phase 4**.

## Phase 5 — Check the evaluator against people (offer, don't force)

Only if the user cares whether the automated scores are trustworthy (they mention
"can I trust this", human review, or high-stakes decisions):

→ **`/calibrate-evaluator`** — measure human↔judge agreement and tune until the
judge matches humans. This is the step that makes the eval *Calibrate*, not just
a test runner. Offer it; don't impose it.

## Phase 6 — Scale + CI

→ **`/benchmark-models`** — compare models across the linked tests.

If the user mentions PRs, CI, releases, or "before we ship", propose wiring
`calibrate agent-tests run` into CI in agent mode (`--agent-mode --no-interactive
--output-format json`), pinned to one cheap model in CI with the full matrix run
locally. Don't force it — only when the signal is there.

## Iterate

Evaluation is a loop, not a line. After Phase 4, expect one of:

- **Expand the test set** — a defect surfaced or coverage is thin → back to
  Phase 3 (`/build-test-suite`), re-run.
- **Tune the hypothesis** — the bar is too loose/strict → edit Phase 3, re-run.
- **Add a model** — → Phase 6 (`/benchmark-models`).
- **Tune the judge** — agreement too low → `/iterate-evaluator` +
  `/calibrate-evaluator`.

Each pass appends to **Phase 4 — Runs** in the state file so prior baselines stay
inspectable. Stop when the user has shipped, wired it into CI, or says they're
done.
