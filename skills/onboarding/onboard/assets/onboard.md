# Calibrate onboarding state

> Resumable state for `/onboard`. Fill the prose under each phase (not the italic
> blurb, not the TODO marker). Resume at the first phase still on TODO. New to the
> terms? See the Glossary at the bottom.

## Phase 1 — System under test

*What the agent does, who uses it, where it fails today.*

<!-- TODO: describe the system under test. -->

**agent_uuid:** <!-- filled by /connect-agent -->

## Phase 2 — Hypothesis + tests

*One falsifiable claim you will measure, and the test cases that check it.*

<!-- TODO: state the hypothesis. -->

**test_uuids:** <!-- filled by /build-test-suite or /import-dataset -->

## Phase 3 — Evaluators

*Any response-quality judges these tests need. Skip if every case is tool_call.*

<!-- TODO: list evaluators, or write "none — all tool_call". -->

**evaluator_uuids:** <!-- filled by /design-evaluator -->

## Phase 4 — Runs

*Every run: task_id, models, outcome. One line per iteration.*

<!-- TODO: track runs. -->

## Phase 5 — Judge calibration

*Human↔judge agreement result, if you ran /calibrate-evaluator.*

<!-- TODO: agreement numbers + whether the judge is trusted. -->

---

## Glossary

1. **Agent** — the system under test; an endpoint or an internal-LLM config.
2. **Test** — one conversation the agent processes, plus what passes/fails.
3. **Evaluator** — the versioned judge that decides pass/fail. `tool_call`
   (deterministic) or `response` (LLM judge against `criteria`).
4. **Judge model** — the LLM an evaluator delegates to.
5. **Agent-test** — a test linked to an agent and run against it.
6. **Benchmark** — one run across multiple models to compare them.
7. **Annotation task** — items labeled by humans (and the judge) to measure
   agreement.
8. **Agreement** — how often labels match: human↔human is the ceiling,
   human↔judge is the score that decides whether to trust the judge.
