from __future__ import annotations

import asyncio
import logging
from typing import Optional

import orjson
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, WebSocketException, status

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

    # Verify the run exists before accepting
    ctx = await run_manager.get_any_run(run_id)
    if ctx is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    logger.info("WebSocket client connected to run %s", run_id)

    # Subscribe to the run's event queue
    queue = await run_manager.subscribe(run_id)

    try:
        # Send the current snapshot immediately so the client has a consistent
        # starting state before streaming delta events.
        snapshot = await run_manager.get_any_snapshot(run_id)
        if snapshot:
            initial_event = {
                "type": "snapshot",
                "payload": snapshot.model_dump(),
            }
            await websocket.send_text(orjson.dumps(initial_event).decode())

        # Stream events from the queue
        while True:
            # We poll the queue with a short timeout so we can also check for
            # client-initiated disconnects (receive_text raises on disconnect).
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1.0)
                await websocket.send_text(orjson.dumps(event).decode())

                # If the run has finished, drain remaining events and close
                if event.get("type") == "run.stage" and event.get("payload", {}).get("stage") in (
                    "completed",
                    "error",
                ):
                    # Drain any remaining queued events
                    while not queue.empty():
                        remaining = queue.get_nowait()
                        await websocket.send_text(orjson.dumps(remaining).decode())
                    break

            except asyncio.TimeoutError:
                # No event within timeout window; send a keepalive ping and
                # check whether the run is still active.
                try:
                    await websocket.send_text(orjson.dumps({"type": "ping"}).decode())
                except Exception:
                    break

                # Check if run is done and queue is empty — close gracefully
                updated_ctx = await run_manager.get_run(run_id)
                if updated_ctx and updated_ctx.stage in ("completed", "error"):
                    if queue.empty():
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
        await run_manager.unsubscribe(run_id, queue)
        logger.debug("WebSocket unsubscribed from run %s", run_id)
