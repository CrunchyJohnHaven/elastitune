import asyncio
import random
import time
from typing import List
from ..models.contracts import PersonaViewModel, PersonaRuntime
from ..models.runtime import RunContext


async def run_persona_simulator(ctx: RunContext, run_manager):
    """Simulate personas searching over time."""
    rng = random.Random()

    while not ctx.cancel_flag.is_set():
        try:
            await asyncio.sleep(rng.uniform(1.0, 3.0))

            if ctx.cancel_flag.is_set():
                break

            # Pick 1-3 personas to simulate searching
            active_count = rng.randint(1, min(3, len(ctx.personas)))
            active_personas = rng.sample(ctx.personas, active_count)

            now = time.time()
            updated = []

            for p in active_personas:
                # Set to searching
                p.state = 'searching'
                p.pulseUntil = now + 1.5

                # Pick a query
                if p.queries:
                    p.lastQuery = rng.choice(p.queries)

                # Simulate result based on current improvement
                improvement_factor = max(0, ctx.metrics.improvementPct / 100.0)
                success_prob = 0.4 + improvement_factor * 0.3

                roll = rng.random()
                if roll < success_prob:
                    p.state = 'success'
                    p.successes += 1
                    p.lastResultRank = rng.randint(1, 3)
                elif roll < success_prob + 0.25:
                    p.state = 'partial'
                    p.partials += 1
                    p.lastResultRank = rng.randint(4, 10)
                else:
                    p.state = 'failure'
                    p.failures += 1
                    p.lastResultRank = None

                p.totalSearches += 1
                if p.totalSearches > 0:
                    p.successRate = round(p.successes / p.totalSearches, 3)

                updated.append(p)

            # Compute overall persona success rate
            total_searches = sum(p.totalSearches for p in ctx.personas)
            total_successes = sum(p.successes for p in ctx.personas)
            if total_searches > 0:
                ctx.metrics.personaSuccessRate = round(total_successes / total_searches, 3)

            # Send persona batch update
            await run_manager.publish(ctx.run_id, {
                "type": "persona.batch",
                "payload": {
                    "runId": ctx.run_id,
                    "personas": [p.model_dump() for p in updated]
                }
            })

            # After a short time, reset searching personas to idle/state
            await asyncio.sleep(rng.uniform(0.8, 1.5))

            for p in updated:
                if p.state == 'searching':
                    p.state = 'idle'

            # Handle "reacting" when experiment is accepted
            # (This is triggered by the optimizer loop)

        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(2.0)
            continue
