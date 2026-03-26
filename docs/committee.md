# Committee Mode

Committee mode turns a document into a live decision-making exercise.

It models a small buying committee, scores the document from each persona's point of view, and rewrites weak sections until the message is more persuasive.

## Core Idea

The committee loop has four steps:

1. Parse the uploaded document into sections.
2. Generate personas or accept provided personas.
3. Evaluate each section for each persona.
4. Propose rewrites, keep the ones that improve the committee score, and publish the report.

## Persona Generation

Personas come from `backend/committee/personas.py`.

There are three broad paths:

- **Provided personas**: the user uploads a custom persona list.
- **Seed personas**: the app uses built-in role templates for a predictable demo.
- **LLM-assisted personas**: when an LLM is configured, it can help generate a more tailored committee.

When no LLM is available, the system falls back to deterministic heuristics so the workflow still completes.

Useful files:

- [`backend/committee/personas.py`](../backend/committee/personas.py)
- [`backend/committee/industry_profiles.py`](../backend/committee/industry_profiles.py)
- [`backend/committee/runtime.py`](../backend/committee/runtime.py)

## Evaluation And Rewrite Loop

The live committee run is coordinated from `backend/services/run_manager.py` and the committee evaluator/rewrite engine.

The flow is:

1. Parse the document.
2. Build a baseline score.
3. Publish a persona batch to the client.
4. Select a section and a rewrite parameter.
5. Evaluate the candidate version.
6. Keep the change if it improves score and does not violate the do-no-harm floor.

Relevant files:

- [`backend/committee/evaluator.py`](../backend/committee/evaluator.py)
- [`backend/committee/rewrite_engine.py`](../backend/committee/rewrite_engine.py)
- [`backend/committee/reporting.py`](../backend/committee/reporting.py)
- [`backend/api/routes_committee.py`](../backend/api/routes_committee.py)
- [`backend/services/run_manager.py`](../backend/services/run_manager.py)

## Scoring Model

Committee scoring is intentionally simple to explain in a demo:

- each persona gets a per-section score
- the app rolls those scores into a committee view
- the run tracks baseline, current, and best scores
- rewrites are accepted or rejected based on the resulting committee posture

The exposed evaluation modes are:

- `full_committee`
- `adversarial`
- `champion_only`

## What The UI Shows

The committee UI shows:

- the parsed document
- persona cards and objections
- the live rewrite log
- score changes over time
- the final report and export payload

The WebSocket event stream is shared with the rest of the app, which makes the live run feel consistent with search mode.

## Demo Notes

Committee mode works best when the document has a clear business message:

- a proposal
- an executive brief
- a sales deck
- a project summary

The most convincing demo path is to show:

1. A skeptical persona reacting to the first draft.
2. A rewrite that addresses the objection.
3. The score improvement.
4. The export or report output at the end.

## Related Documentation

- [docs/api-reference.md](api-reference.md)
- [docs/demo-narrative.md](demo-narrative.md)
- [docs/research.md](research.md)
