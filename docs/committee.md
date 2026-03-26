# Committee Mode

Committee mode simulates the internal buying group that often reviews a proposal, pitch deck, or solution brief.

## What personas are

Personas are structured buyer roles. They have:

- a title and decision role,
- authority weight,
- priorities and concerns,
- likely objections,
- and a current score while the run is active.

The frontend renders them in the committee canvas, rails, and final report.

## How personas are generated

Persona generation lives in [backend/committee/personas.py](../backend/committee/personas.py).

The generator follows three paths:

- `provided_personas` from the request take precedence.
- Seed personas can be used when the run should feel deterministic or demo-friendly.
- Otherwise the heuristics derive personas from the parsed document, the detected industry profile, and the available LLM configuration.

When an LLM is available, the persona generator can use it for richer role descriptions. When it is not, the heuristics fall back to stable, deterministic buyer roles.

## How the committee loop works

The committee loop is coordinated by [backend/api/routes_committee.py](../backend/api/routes_committee.py) and [backend/services/run_manager.py](../backend/services/run_manager.py).

At a high level:

1. The uploaded document is parsed into sections by [backend/committee/document_parser.py](../backend/committee/document_parser.py).
2. Personas are built or normalized.
3. The evaluator scores each persona against each section.
4. The rewrite engine proposes improvements to the weakest sections.
5. The report and export payload summarize the strongest narrative and the remaining objections.

The scoring and rollup logic lives in [backend/committee/evaluator.py](../backend/committee/evaluator.py). The final report and export payload are built in [backend/committee/reporting.py](../backend/committee/reporting.py).

## What the UI shows

- `CommitteeRunScreen` streams the live consensus loop.
- `CommitteeTopBar` shows elapsed time, consensus, and rewrite counts.
- `CommitteeRightRail` shows the persona list, selected persona detail, and score timeline.
- `CommitteeReportScreen` shows the final diff, persona reactions, and rewrite log.

## Why this mode exists

Committee mode gives teams a structured way to test whether a document works for different stakeholders, not just whether it sounds polished. It is especially useful for proposal reviews, enablement briefings, and executive narratives where one weak objection can derail the whole message.
