import asyncio
import time
import random
from datetime import datetime, timezone
from typing import Optional, List
import logging

from ..models.contracts import SearchProfile, ExperimentRecord, SearchProfileChange
from ..models.runtime import RunContext
from .evaluator import Evaluator
from .optimizer_search_space import generate_mutations, pick_mutation

logger = logging.getLogger(__name__)

KEEP_THRESHOLD = 0.003


async def run_optimizer_loop(ctx: RunContext, run_manager, evaluator: Evaluator):
    """Main optimizer loop. Runs experiments until cancelled or max reached."""

    # Initial baseline evaluation
    try:
        if ctx.mode == 'demo':
            baseline_score, _ = await evaluator.evaluate_demo(ctx.current_profile, ctx.eval_set)
        else:
            baseline_score, _ = await evaluator.evaluate(ctx.current_profile, ctx.eval_set)

        ctx._best_score = baseline_score
        ctx.metrics.baselineScore = baseline_score
        ctx.metrics.bestScore = baseline_score
        ctx.metrics.currentScore = baseline_score
        if ctx.metrics.scoreTimeline is None:
            ctx.metrics.scoreTimeline = []
        ctx.metrics.scoreTimeline.append({"t": 0.0, "score": baseline_score})

    except Exception as e:
        logger.error(f"Baseline evaluation failed: {e}")
        ctx.stage = 'error'
        await run_manager.publish(ctx.run_id, {
            "type": "error",
            "payload": {"code": "BASELINE_FAILED", "message": str(e)}
        })
        return

    ctx.stage = 'running'
    await run_manager.publish(ctx.run_id, {
        "type": "run.stage",
        "payload": {"runId": ctx.run_id, "stage": "running", "message": "Optimization started"}
    })

    recently_reverted = []
    experiment_id = 0
    plateau_count = 0
    rng = random.Random()
    start_time = time.time()

    while not ctx.cancel_flag.is_set():
        # Check limits
        if experiment_id >= ctx.max_experiments:
            break

        elapsed = time.time() - start_time
        if elapsed > ctx.duration_minutes * 60:
            break

        # Check plateau
        if ctx.auto_stop_on_plateau and plateau_count >= 8:
            break

        # Generate mutations
        history_paths = [e.change.path for e in ctx.experiments[-10:]]
        mutations = generate_mutations(ctx.current_profile, ctx.experiments, recently_reverted[-5:])

        if not mutations:
            await asyncio.sleep(1.0)
            continue

        # Pick a mutation
        mutation = pick_mutation(mutations, rng)
        if not mutation:
            await asyncio.sleep(1.0)
            continue

        candidate_profile, change = mutation

        # Build hypothesis text
        hypothesis = _make_hypothesis(change, ctx.mode)

        # Evaluate candidate
        eval_start = time.time()
        try:
            if ctx.mode == 'demo':
                candidate_score, failures_after = await evaluator.evaluate_demo(candidate_profile, ctx.eval_set)
                # Add small delay to simulate work
                await asyncio.sleep(rng.uniform(1.5, 3.5))
            else:
                candidate_score, failures_after = await evaluator.evaluate(candidate_profile, ctx.eval_set)

            _, failures_before = [], []
        except Exception as e:
            logger.warning(f"Experiment {experiment_id} failed: {e}")
            await asyncio.sleep(2.0)
            continue

        eval_duration_ms = int((time.time() - eval_start) * 1000)

        # Keep or revert
        delta = candidate_score - ctx._best_score
        if delta > KEEP_THRESHOLD:
            decision = 'kept'
            ctx.current_profile = candidate_profile
            ctx.best_profile = candidate_profile.model_copy(deep=True)
            ctx._best_score = candidate_score
            plateau_count = 0
        else:
            decision = 'reverted'
            recently_reverted.append(change.path)
            if len(recently_reverted) > 10:
                recently_reverted.pop(0)
            plateau_count += 1

        experiment_id += 1

        record = ExperimentRecord(
            experimentId=experiment_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            hypothesis=hypothesis,
            change=change,
            baselineScore=ctx._best_score if decision == 'kept' else ctx._best_score,
            candidateScore=candidate_score,
            deltaAbsolute=round(delta, 6),
            deltaPercent=round((delta / max(ctx._best_score, 0.001)) * 100, 2),
            decision=decision,
            durationMs=eval_duration_ms,
            queryFailuresBefore=failures_before[:3],
            queryFailuresAfter=failures_after[:3],
        )

        ctx.experiments.append(record)
        ctx.metrics.experimentsRun = experiment_id
        ctx.metrics.improvementsKept = sum(1 for e in ctx.experiments if e.decision == 'kept')
        ctx.metrics.currentScore = candidate_score if decision == 'kept' else ctx._best_score
        ctx.metrics.bestScore = ctx._best_score

        elapsed = time.time() - start_time
        ctx.metrics.elapsedSeconds = elapsed
        ctx.metrics.scoreTimeline.append({"t": elapsed, "score": ctx._best_score})

        # Compute improvement pct
        if ctx.metrics.baselineScore > 0:
            ctx.metrics.improvementPct = round(
                ((ctx._best_score - ctx.metrics.baselineScore) / ctx.metrics.baselineScore) * 100, 2
            )

        # Publish experiment
        await run_manager.publish(ctx.run_id, {
            "type": "experiment.completed",
            "payload": record.model_dump()
        })

        # Small pause between experiments
        if ctx.mode != 'demo':
            await asyncio.sleep(0.5)

    # Done
    if not ctx.cancel_flag.is_set():
        ctx.stage = 'completed'
        ctx.completed_at = datetime.now(timezone.utc).isoformat()

        # Generate report
        from ..services.report_service import ReportService
        try:
            report = ReportService().generate(ctx)
            ctx.report = report
            await run_manager.publish(ctx.run_id, {
                "type": "report.ready",
                "payload": report.model_dump()
            })
        except Exception as e:
            logger.error(f"Report generation failed: {e}")

        await run_manager.publish(ctx.run_id, {
            "type": "run.stage",
            "payload": {"runId": ctx.run_id, "stage": "completed"}
        })


def _make_hypothesis(change: SearchProfileChange, mode: str) -> str:
    """Generate a hypothesis string for a mutation."""
    hypotheses = {
        "multiMatchType": f"Switching to {change.after} matching should improve recall for complex queries",
        "minimumShouldMatch": f"Adjusting minimum_should_match to {change.after} should reduce noise while keeping precision",
        "tieBreaker": f"Setting tie_breaker to {change.after} should improve ranking across multiple fields",
        "phraseBoost": f"Adding phrase boost of {change.after} should reward exact phrase matches",
        "fuzziness": f"Enabling fuzziness {change.after} should improve recall for misspelled queries",
        "fusionMethod": f"Switching to {change.after} fusion should better balance lexical and vector scores",
        "lexicalWeight": f"Rebalancing lexical/vector weights should improve hybrid retrieval",
        "rrfRankConstant": f"Adjusting RRF rank constant to {change.after} should improve rank fusion stability",
        "knnK": f"Increasing kNN k to {change.after} should improve vector recall",
        "numCandidates": f"Expanding numCandidates to {change.after} should improve vector retrieval quality",
    }

    path = change.path
    if "boost" in path:
        field = change.label.split(" boost")[0]
        return f"Stronger weighting for {field} should improve precision for exact lookups"

    base_path = path.split("[")[0]
    return hypotheses.get(base_path, f"Adjusting {change.label} should improve search quality")
