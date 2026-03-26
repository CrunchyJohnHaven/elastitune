from __future__ import annotations

import asyncio
import logging
from typing import Optional

import orjson
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from ..services.run_manager import RunManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/runs/{run_id}")
async def ws_run_events(websocket: WebSocket, run_id: str) -> None:
    """
    WebSocket endpoint for live run updates.

    On connect:
      1. Accept the connection.
      2. Send the current run snapshot immediately.
      3. Subscribe to the run's event queue.
      4. Forward every event to the client until disconnect or run completion.

    On disconnect: unsubscribe cleanly.
    """
    run_manager: RunManager = websocket.app.state.run_manager

    # Accept both active runs and persisted completed runs.
    snapshot = await run_manager.get_any_snapshot(run_id)
    ctx = await run_manager.get_any_run(run_id)
    if snapshot is None and ctx is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    logger.info("WebSocket client connected to run %s", run_id)

    try:
        # Send the current snapshot immediately so the client has a consistent
        # starting state before streaming delta events.
        if snapshot:
            sanitized_snapshot = (
                snapshot.sanitize_for_client()
                if hasattr(snapshot, "sanitize_for_client")
                else snapshot
            )
            initial_event = {
                "type": "snapshot",
                "payload": sanitized_snapshot.model_dump(),
            }
            await websocket.send_text(orjson.dumps(initial_event).decode())

        initial_stage = getattr(snapshot, "stage", None)
        if initial_stage in ("completed", "error"):
            await websocket.send_text(
                orjson.dumps(
                    {
                        "type": "run.complete",
                        "payload": {"runId": run_id, "stage": initial_stage},
                    }
                ).decode()
            )
            await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
            return

        # Subscribe to the run's event queue only for active runs.
        queue = await run_manager.subscribe(run_id)

        # Stream events from the queue
        while True:
            # We poll the queue with a short timeout so we can also check for
            # client-initiated disconnects (receive_text raises on disconnect).
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1.0)
                await websocket.send_text(orjson.dumps(event).decode())

                # If the run has finished, drain remaining events and close
                if event.get("type") == "run.stage" and event.get("payload", {}).get(
                    "stage"
                ) in (
                    "completed",
                    "error",
                ):
                    # Drain any remaining queued events
                    while not queue.empty():
                        remaining = queue.get_nowait()
                        await websocket.send_text(orjson.dumps(remaining).decode())
                    await websocket.send_text(
                        orjson.dumps(
                            {
                                "type": "run.complete",
                                "payload": {
                                    "runId": run_id,
                                    "stage": event.get("payload", {}).get(
                                        "stage", "completed"
                                    ),
                                },
                            }
                        ).decode()
                    )
                    break

            except asyncio.TimeoutError:
                # No event within timeout window; send a keepalive ping and
                # check whether the run is still active.
                try:
                    await websocket.send_text(orjson.dumps({"type": "ping"}).decode())
                except Exception:
                    break

                # Check if run is done and queue is empty — close gracefully
                updated_snapshot = await run_manager.get_any_snapshot(run_id)
                updated_stage: Optional[str] = getattr(updated_snapshot, "stage", None)
                if updated_stage in ("completed", "error"):
                    if queue.empty():
                        await websocket.send_text(
                            orjson.dumps(
                                {
                                    "type": "run.complete",
                                    "payload": {
                                        "runId": run_id,
                                        "stage": updated_stage,
                                    },
                                }
                            ).decode()
                        )
                        break

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected from run %s", run_id)
    except Exception as exc:
        logger.warning("WebSocket error for run %s: %s", run_id, exc)
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass
    finally:
        if "queue" in locals():
            await run_manager.unsubscribe(run_id, queue)
        logger.debug("WebSocket unsubscribed from run %s", run_id)
