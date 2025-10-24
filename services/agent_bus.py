"""
Simple in-memory pub/sub bus for agent communication.
"""
from __future__ import annotations
from typing import Callable, Dict, List
from collections import defaultdict


class AgentBus:
    def __init__(self) -> None:
        self._subs: Dict[str, List[Callable]] = defaultdict(list)

    def subscribe(self, topic: str, handler: Callable) -> None:
        self._subs[topic].append(handler)

    def publish(self, topic: str, message) -> None:
        for h in list(self._subs.get(topic, [])):
            try:
                h(message)
            except Exception:
                # Best-effort bus
                pass

# Singleton
bus = AgentBus()
