# Designing evaluations: methodology

The reasoning these skills apply when turning "evaluate my agent" into concrete
tests and evaluators. This is the *why*; the CLI mechanics live in
[`config-shapes.md`](config-shapes.md). Method adapted from the FormBharo /
FormVoiceAgentBench work on evaluating conversational agents — we use its
**unit-test** ideas here, not its end-to-end pipeline.

## Start on ideal inputs (unit tests)

Test one behaviour at a time on clean, well-formed inputs — a component in
isolation given the input it's supposed to handle, checked for the right output.
This is deliberately *not* an end-to-end simulation: you're asking "given this
exact situation, does the agent do the right thing?", not "does the whole system
survive a noisy real call?". Unit tests are cheap, deterministic to reason about,
and pinpoint *which* behaviour broke. Build these first; leave full end-to-end
runs for later.

In Calibrate a unit test is one `test`: a `conversation_history` leading up to
the agent's turn, plus what must be true of that turn.

## Separate the two things you can check

Every behaviour is either an **action** or a **response**:

- **Action** — the agent should *do* something: call a tool, with particular
  arguments. Deterministic. → a `tool_call` test. No judge, no token cost.
- **Response** — the agent should *say* something meeting a quality bar. →
  a `response` test scored by an LLM judge (an evaluator).

Split these apart. "Books the room *and* confirms politely" is two checks: a
`tool_call` test on the booking and a `response` test on the confirmation.

## Response quality = independent dimensions, one evaluator each

A good reply usually has to satisfy several *independent* qualities at once — e.g.
answers the question, stays on-policy, is concise, is in the right language,
doesn't leak the system prompt. **Do not cram all of these into one judge.** A
single judge asked to weigh five things at once gives mushy, hard-to-calibrate
verdicts and you can't tell *which* quality failed.

Instead, name the dimensions and give **each its own evaluator**, each returning
a clean binary pass/fail. Then one failing reply tells you exactly which
dimension it failed. (FormBharo scores reply quality with five separate binary
judges — correct next question, in-language, concise, no redundant
acknowledgement, doesn't echo the user — precisely for this reason.)

Reuse a built-in judge (e.g. a general "Correctness" evaluator, type `llm`) for
the generic dimension; author a use-case-specific evaluator for each dimension
that's particular to this agent.

## Match the scoring method to the output shape

How you check an output depends on what kind of output it is:

| Output shape | Example | How to check |
| --- | --- | --- |
| Closed-form | a number, date, enum, yes/no, single/multi-select | **exact match** (`tool_call` arg `exact`) |
| Open-ended but one right meaning | a name with many spellings, a paraphrase | **LLM judge** (`response`, or `tool_call` arg `llm_judge`) |
| Subjective quality | tone, conciseness, helpfulness, policy adherence | **rubric / binary judge** — one evaluator per dimension |
| Presence only | "an id was passed, value doesn't matter" | **any** (`tool_call` arg `any`) |

Exact match where you can (free, unambiguous); a judge only where meaning, not
surface form, is what matters. See [`judge-prompts.md`](judge-prompts.md) for
writing the judge itself.

## Minimal viable eval — don't boil the ocean

The first eval is small and honest, not exhaustive. For each dimension you named,
write a handful of cases covering:

- **happy path** — the obvious correct case,
- **failure** — a case that *should* fail if the agent misbehaves (out-of-policy
  ask, missing info, wrong tool),
- **edge** — the ambiguous or boundary case (empty input, near-duplicate values,
  argument limits).

That's enough to start finding real problems. Grow the suite from what actually
breaks (see `/analyze-failures`), not from imagined coverage. A small suite you
trust beats a large one you don't.
