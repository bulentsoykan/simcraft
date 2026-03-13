# ABOUTME: Animation event types and dataclass for visualization recording.
# ABOUTME: Defines the event structure captured during simulation playback.

"""Animation event types for visualization."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class EventType(Enum):
    """Types of animation events."""

    ENTITY_CREATED = "entity_created"
    ENTER_QUEUE = "enter_queue"
    START_SERVICE = "start_service"
    DEPART = "depart"
    BALK = "balk"


@dataclass
class AnimationEvent:
    """
    A recorded event for animation playback.

    Attributes
    ----------
    time : float
        Simulation time when the event occurred.
    event_type : EventType
        Type of event.
    entity_id : str
        ID of the entity involved.
    location : Optional[str]
        Location (server or queue name) where event occurred.
    entity_type : Optional[str]
        Type name of the entity (for entity_created events).
    """

    time: float
    event_type: EventType
    entity_id: str
    location: Optional[str] = None
    entity_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert event to dictionary for JSON export.

        Uses compact keys to reduce file size.
        """
        d: Dict[str, Any] = {
            "t": self.time,
            "type": self.event_type.value,
            "entity": self.entity_id,
        }
        if self.location is not None:
            d["loc"] = self.location
        if self.entity_type is not None:
            d["entity_type"] = self.entity_type
        return d
