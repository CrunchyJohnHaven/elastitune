from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional, Set

from ..config import settings


class RunPubSub:
    """Shared pub/sub broker for search and committee runs."""

    def __init__(self) -> None:
        self.subscribers: Dict[str, Set[asyncio.Queue]] = {}

    async def publish(self, run_id: str, event: dict[str, Any]) -> None:
        queues = self.subscribers.get(run_id, set())
        dead: Set[asyncio.Queue] = set()
        for queue in list(queues):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                dead.add(queue)
        for queue in dead:
            queues.discard(queue)

    async def publish_error(
        self,
        run_id: str,
        *,
        code: str,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        payload: dict[str, Any] = {"code": code, "message": message}
        if details:
            payload["details"] = details
        await self.publish(run_id, {"type": "error", "payload": payload})

    async def publish_invariant(
        self,
        run_id: str,
        *,
        name: str,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        if not settings.emit_invariant_events:
            return
        payload: dict[str, Any] = {"name": name, "message": message}
        if details:
            payload["details"] = details
        await self.publish(run_id, {"type": "dev.invariant", "payload": payload})

    async def subscribe(self, run_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=512)
        self.subscribers.setdefault(run_id, set()).add(queue)
        return queue

    async def unsubscribe(self, run_id: str, queue: asyncio.Queue) -> None:
        self.subscribers.get(run_id, set()).discard(queue)
