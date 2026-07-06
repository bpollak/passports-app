import asyncio
import json
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class NotificationManager:
    def __init__(self):
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)

    def subscribe(self, location_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers[location_id].append(queue)
        return queue

    def unsubscribe(self, location_id: str, queue: asyncio.Queue):
        subs = self._subscribers.get(location_id, [])
        if queue in subs:
            subs.remove(queue)
        if not subs:
            self._subscribers.pop(location_id, None)

    async def publish(self, location_id: str, event: str, data: dict):
        message = json.dumps({"event": event, "data": data})
        for queue in self._subscribers.get(location_id, []):
            await queue.put(message)

    async def publish_all(self, event: str, data: dict):
        message = json.dumps({"event": event, "data": data})
        for queues in self._subscribers.values():
            for queue in queues:
                await queue.put(message)


notification_manager = NotificationManager()


async def event_generator(location_id: str):
    queue = notification_manager.subscribe(location_id)
    try:
        yield f"event: connected\ndata: {json.dumps({'status': 'connected'})}\n\n"
        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=30.0)
                parsed = json.loads(message)
                yield f"event: {parsed['event']}\ndata: {json.dumps(parsed['data'])}\n\n"
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        notification_manager.unsubscribe(location_id, queue)
