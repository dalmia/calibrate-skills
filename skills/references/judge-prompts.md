# Writing a good judge prompt

An evaluator is only as good as its prompt. These are the rules for writing the
`system_prompt` of an LLM judge (used by `/design-evaluator` and
`/iterate-evaluator`). Adapted from hamelsmu's *write-judge-prompt* skill
(https://github.com/hamelsmu/evals-skills, MIT).

## One judge, one question

A judge should decide **one** thing. If you're tempted to write "…and also
checks that it's polite and in Spanish", that's three judges, not one — split
them (see [`methodology.md`](methodology.md), independent dimensions). A judge
scoring several qualities at once produces verdicts you can't calibrate or act
on.

## Prefer binary

Default to a `binary` (pass/fail) judge. Binary verdicts are easy for the model
to give consistently, easy to check against human labels, and easy to act on.
Reach for a `rating` scale only when a graded judgment genuinely drives a
decision (e.g. surfacing the worst 10% for review) — and expect it to be harder
to calibrate.

## Define the bar concretely

State exactly what **passes** and what **fails**, in observable terms. Vague
rubrics ("the reply is good") produce coin-flip judges. Anchor it:

- what the reply must contain / do to pass,
- what makes it fail,
- what is explicitly *out of scope* for this judge (handled by another
  dimension) — so it doesn't penalise things it shouldn't.

## Give the judge the right context

An evaluator of type `llm` receives the reply **and its conversation history** —
so the prompt can refer to the prior turns ("relative to what the user just
asked…"). If your judge needs the history to decide, that's the type to use;
`llm-general` sees only a standalone input/output pair and can't reason about the
conversation.

## Handle the boundary with examples

For anything ambiguous, put one or two short examples in the prompt: a borderline
case that should pass and one that should fail, each with a one-line why.
Boundary examples move a judge's agreement more than extra adjectives do.

## Keep it reusable with a `{{criteria}}` variable

Put the specific thing being checked in a `{{criteria}}` placeholder filled
per-test-case, and keep the surrounding prompt about *how* to judge. One
well-written evaluator then scores many different criteria across your suite. See
the `version-param` shape in [`config-shapes.md`](config-shapes.md).

## A prompt is a guess until it's calibrated

However careful the wording, you don't know the judge agrees with people until
you measure it. Validate against human labels before trusting it at scale →
`/calibrate-evaluator`.
