import asyncio
from typing import Dict, List, Any

# Simple in-process pub/sub for per-build activity events
_subscribers: Dict[str, List[asyncio.Queue]] = {}


def subscribe(build_id: str) -> asyncio.Queue:
    """Subscribe to activity events for a build. Returns an asyncio.Queue that receives events."""
    q: asyncio.Queue = asyncio.Queue(maxsize=1000)
    _subscribers.setdefault(build_id, []).append(q)
    return q


def unsubscribe(build_id: str, q: asyncio.Queue) -> None:
    """Unsubscribe a queue from a build's event stream."""
    subscribers = _subscribers.get(build_id)
    if not subscribers:
        return
    try:
        subscribers.remove(q)
    except ValueError:
        pass
    if not subscribers:
        _subscribers.pop(build_id, None)


def publish(build_id: str, event: Dict[str, Any]) -> None:
    """Publish an activity event to all subscribers of a build."""
    for q in list(_subscribers.get(build_id, [])):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            # Drop oldest item and try once more to avoid blocking
            try:
                q.get_nowait()
            except Exception:
                pass
            try:
                q.put_nowait(event)
            except Exception:
                pass
