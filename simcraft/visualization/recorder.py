# ABOUTME: Records simulation events for visualization playback.
# ABOUTME: Wraps server callbacks to capture entity flow events.

"""Visualization recorder for capturing simulation events."""

from __future__ import annotations
import json
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Set, TypeVar

from simcraft.visualization.events import AnimationEvent, EventType

if TYPE_CHECKING:
    from simcraft.core.simulation import Simulation
    from simcraft.resources.server import Server

T = TypeVar("T")


class VisualizationRecorder:
    """
    Records simulation events for visualization playback.

    The recorder wraps server callbacks to capture arrival, service start,
    departure, and balk events. These events can then be exported to JSON
    for playback in a visualization viewer.

    Parameters
    ----------
    sim : Simulation
        The simulation to record.

    Examples
    --------
    >>> sim = Simulation()
    >>> recorder = VisualizationRecorder(sim)
    >>> server = Server(sim, capacity=1, service_time=5.0, name="Teller")
    >>> recorder.track_server(server)
    >>> # ... run simulation ...
    >>> recorder.save("animation.json")
    """

    VERSION = "1.0"

    def __init__(self, sim: "Simulation") -> None:
        """Initialize the recorder."""
        self._sim = sim
        self._events: List[AnimationEvent] = []
        self._components: Dict[str, Dict[str, Any]] = {}
        self._seen_entities: Set[str] = set()

    @property
    def events(self) -> List[AnimationEvent]:
        """Get the list of recorded events."""
        return self._events

    @property
    def components(self) -> Dict[str, Dict[str, Any]]:
        """Get the registered components."""
        return self._components

    def track_server(self, server: "Server", name: Optional[str] = None) -> None:
        """
        Register a server for event recording.

        Wraps server callbacks to capture arrival, service_start,
        departure, and balk events.

        Parameters
        ----------
        server : Server
            The server to track.
        name : Optional[str]
            Custom name for the server. Defaults to server.name.
        """
        name = name or server.name
        self._components[name] = {
            "type": "server",
            "capacity": server.capacity,
        }
        self._components[f"{name}.queue"] = {
            "type": "queue",
            "capacity": server.queue.capacity if hasattr(server.queue, 'capacity') else 0,
        }
        self._wrap_server_callbacks(server, name)

    def _wrap_server_callbacks(self, server: "Server", name: str) -> None:
        """Chain recorder callbacks after existing user callbacks."""
        # Capture existing callbacks
        existing_arrival = server._on_arrival
        existing_service_start = server._on_service_start
        existing_departure = server._on_departure
        existing_balk = server._on_balk

        def wrapped_arrival(entity: T) -> None:
            # Call user's callback first
            if existing_arrival:
                existing_arrival(entity)
            # Record entity creation if first time seen
            self._record_entity_created(entity)
            # Determine if entity goes to queue or directly to service
            # We check server state AFTER the arrival callback runs
            # The entity will either be in service or in queue at this point
            if server.available_capacity == 0:
                # Server was full, so entity must be queued
                self._record_event(
                    EventType.ENTER_QUEUE,
                    self._get_entity_id(entity),
                    f"{name}.queue",
                )

        def wrapped_service_start(entity: T) -> None:
            # Call user's callback first
            if existing_service_start:
                existing_service_start(entity)
            # Record service start
            self._record_event(
                EventType.START_SERVICE,
                self._get_entity_id(entity),
                name,
            )

        def wrapped_departure(entity: T) -> None:
            # Call user's callback first
            if existing_departure:
                existing_departure(entity)
            # Record departure
            self._record_event(
                EventType.DEPART,
                self._get_entity_id(entity),
                name,
            )

        def wrapped_balk(entity: T) -> None:
            # Call user's callback first
            if existing_balk:
                existing_balk(entity)
            # Record entity creation if first time seen
            self._record_entity_created(entity)
            # Record balk
            self._record_event(
                EventType.BALK,
                self._get_entity_id(entity),
                name,
            )

        # Install wrapped callbacks
        server.on_arrival(wrapped_arrival)
        server.on_service_start(wrapped_service_start)
        server.on_departure(wrapped_departure)
        server.on_balk(wrapped_balk)

    def _get_entity_id(self, entity: Any) -> str:
        """Get the ID of an entity."""
        if hasattr(entity, "id"):
            return str(entity.id)
        return str(id(entity))

    def _get_entity_type(self, entity: Any) -> str:
        """Get the type name of an entity."""
        return type(entity).__name__

    def _record_entity_created(self, entity: Any) -> None:
        """Record entity creation if not already seen."""
        entity_id = self._get_entity_id(entity)
        if entity_id not in self._seen_entities:
            self._seen_entities.add(entity_id)
            event = AnimationEvent(
                time=self._sim.now,
                event_type=EventType.ENTITY_CREATED,
                entity_id=entity_id,
                entity_type=self._get_entity_type(entity),
            )
            self._events.append(event)

    def _record_event(
        self,
        event_type: EventType,
        entity_id: str,
        location: str,
    ) -> None:
        """Record an animation event."""
        event = AnimationEvent(
            time=self._sim.now,
            event_type=event_type,
            entity_id=entity_id,
            location=location,
        )
        self._events.append(event)

    def to_dict(self) -> Dict[str, Any]:
        """
        Export recorder state to dictionary.

        Returns
        -------
        Dict[str, Any]
            Dictionary with version, simulation metadata, components, and events.
        """
        # Sort events by time for export
        sorted_events = sorted(self._events, key=lambda e: e.time)

        return {
            "version": self.VERSION,
            "simulation": {
                "name": self._sim.name,
                "duration": self._sim.now,
            },
            "components": self._components,
            "events": [e.to_dict() for e in sorted_events],
        }

    def to_json(self, indent: int = 2) -> str:
        """
        Export recorder state to JSON string.

        Parameters
        ----------
        indent : int
            JSON indentation level.

        Returns
        -------
        str
            JSON string representation.
        """
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, path: str) -> None:
        """
        Write JSON to file.

        Parameters
        ----------
        path : str
            Output file path.
        """
        with open(path, "w") as f:
            f.write(self.to_json())
