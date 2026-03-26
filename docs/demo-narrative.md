# Suggested Human Demo Narrative

Use this script when presenting ElastiTune to sales, engineering, or internal leadership.

## 1. Open With The Problem

Tell the audience that search tuning is usually slow, subjective, and hard to explain.

Then explain that ElastiTune turns the work into a live optimization demo with two modes:

- **Search mode** for relevance tuning
- **Committee mode** for document persuasion and rewrite workflows

## 2. Show Search Mode First

Recommended flow:

1. Connect to a benchmark or live Elasticsearch index.
2. Point out the detected cluster summary.
3. Start a run.
4. Call attention to the live telemetry bar and experiment feed.
5. Show how the score changes as the optimizer keeps or rejects experiments.
6. Open the report when the run completes.

What to emphasize:

- The app shows why a change was kept.
- The score is live, not a static screenshot.
- The report is generated from the run itself.

## 3. Explain The Happy Path

The happy path is short and easy to remember:

1. Connect.
2. Run.
3. Review.
4. Export.

That sequence is the same mental model in both modes, which helps the product feel simple even when the internals are sophisticated.

## 4. Switch To Committee Mode

Use committee mode when the audience wants to see a more boardroom-oriented story.

Walk through:

1. Upload a proposal or brief.
2. Show the generated personas.
3. Start the committee run.
4. Read one or two objections out loud.
5. Show how a rewrite addresses the concern.
6. Highlight the improved score and final export.

What to emphasize:

- Personas make feedback feel concrete.
- The rewrite loop is visible and explainable.
- The app helps teams improve language, not just numbers.

## 5. Suggested Talk Track

Use short lines like these:

- "This is the baseline."
- "This is the experiment we kept."
- "Here is why the committee objected."
- "Here is the revision that moved the score."
- "This is the report we can hand to a stakeholder."

## 6. Closing

End by pointing to the docs and the benchmark harness so the audience can see that the demo is repeatable.

Good closing line:

- "ElastiTune is not just a search toy. It is a repeatable workflow for proving relevance and document quality improvements."
