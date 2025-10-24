"""
Standardized agent protocol models.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum


class MessageType(str, Enum):
    COMMAND = "command"
    RESULT = "result"
    EVENT = "event"
    ERROR = "error"


@dataclass
class Command:
    name: str
    payload: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None


@dataclass
class Result:
    ok: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    correlation_id: Optional[str] = None


@dataclass
class Event:
    type: str
    data: Dict[str, Any] = field(default_factory=dict)
