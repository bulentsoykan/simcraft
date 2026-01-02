"""
Server component for simulation.

Servers represent processing stations that serve entities with
configurable capacity, service time distributions, and queue policies.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    TypeVar,
    Union,
)
from enum import Enum, auto

from simcraft.resources.queue import Queue, PriorityQueue

if TYPE_CHECKING:
    from simcraft.core.simulation import Simulation
    from simcraft.core.entity import Entity

T = TypeVar("T")


class ServerState(Enum):
    """Server operational states."""

    IDLE = auto()
    BUSY = auto()
    BLOCKED = auto()
    DOWN = auto()


@dataclass
class ServerStats:
    """
    Statistics for server performance.

    Attributes
    ----------
    arrivals : int
        Total entities that arrived at the server
    departures : int
        Total entities that completed service
    balked : int
        Entities that left without service (queue full)
    busy_time : float
        Total time server was busy
    idle_time : float
        Total time server was idle
    blocked_time : float
        Total time server was blocked
    down_time : float
        Total time server was down
    """

    arrivals: int = 0
    departures: int = 0
    balked: int = 0
    busy_time: float = 0.0
    idle_time: float = 0.0
    blocked_time: float = 0.0
    down_time: float = 0.0
    total_service_time: float = 0.0
    _last_state_change: float = 0.0
    _current_state: ServerState = ServerState.IDLE
    _busy_count: int = 0

    def record_state_change(self, time: float, new_state: ServerState) -> None:
        """Record a state change."""
        duration = time - self._last_state_change
        if self._current_state == ServerState.IDLE:
            self.idle_time += duration
        elif self._current_state == ServerState.BUSY:
            self.busy_time += duration
        elif self._current_state == ServerState.BLOCKED:
            self.blocked_time += duration
        elif self._current_state == ServerState.DOWN:
            self.down_time += duration

        self._current_state = new_state
        self._last_state_change = time

    @property
    def utilization(self) -> float:
        """Get server utilization (busy time / total active time)."""
        active_time = self.busy_time + self.idle_time
        if active_time == 0:
            return 0.0
        return self.busy_time / active_time

    @property
    def average_service_time(self) -> float:
        """Get average service time."""
        if self.departures == 0:
            return 0.0
        return self.total_service_time / self.departures

    @property
    def throughput_rate(self) -> float:
        """Get throughput rate (departures per time unit)."""
        total_time = self.busy_time + self.idle_time + self.blocked_time + self.down_time
        if total_time == 0:
            return 0.0
        return self.departures / total_time

    def reset(self) -> None:
        """Reset all statistics."""
        self.arrivals = 0
        self.departures = 0
        self.balked = 0
        self.busy_time = 0.0
        self.idle_time = 0.0
        self.blocked_time = 0.0
        self.down_time = 0.0
        self.total_service_time = 0.0
        self._last_state_change = 0.0


@dataclass
class ServiceRecord(Generic[T]):
    """Record of an entity being served."""

    entity: T
    start_time: float
    service_time: float
    server_index: int = 0

    @property
    def end_time(self) -> float:
        """Get scheduled end time."""
        return self.start_time + self.service_time


class Server(Generic[T]):
    """
    Multi-server processing station.

    A Server models a processing station with one or more parallel
    servers (capacity), a waiting queue, and configurable service
    time distributions.

    Parameters
    ----------
    sim : Simulation
        Parent simulation
    capacity : int
        Number of parallel servers
    service_time : Union[float, Callable[[], float]]
        Fixed service time or function returning random service time
    queue_capacity : int
        Maximum queue length (0 = unlimited)
    name : str
        Optional name for the server

    Examples
    --------
    >>> def service_time():
    ...     return sim.rng.exponential(5.0)
    ...
    >>> server = Server(sim, capacity=2, service_time=service_time)
    >>> server.enqueue(customer)
    >>> server.on_departure(lambda c: print(f"{c.id} departed"))
    """

    def __init__(
        self,
        sim: "Simulation",
        capacity: int = 1,
        service_time: Union[float, Callable[[], float]] = 1.0,
        queue_capacity: int = 0,
        name: str = "",
    ) -> None:
        """Initialize server."""
        self._sim = sim
        self._capacity = capacity
        self._service_time = service_time
        self._name = name or f"Server_{id(self)}"

        # Queue for waiting entities
        self._queue: Queue[T] = Queue(sim, capacity=queue_capacity)

        # Currently being served
        self._in_service: List[ServiceRecord[T]] = []

        # State tracking
        self._state = ServerState.IDLE
        self._stats = ServerStats()
        self._is_down = False

        # Callbacks
        self._on_arrival: Optional[Callable[[T], None]] = None
        self._on_service_start: Optional[Callable[[T], None]] = None
        self._on_departure: Optional[Callable[[T], None]] = None
        self._on_balk: Optional[Callable[[T], None]] = None

    @property
    def name(self) -> str:
        """Get server name."""
        return self._name

    @property
    def capacity(self) -> int:
        """Get server capacity."""
        return self._capacity

    @property
    def available_capacity(self) -> int:
        """Get number of available servers."""
        return self._capacity - len(self._in_service)

    @property
    def is_idle(self) -> bool:
        """Check if all servers are idle."""
        return len(self._in_service) == 0

    @property
    def is_busy(self) -> bool:
        """Check if all servers are busy."""
        return self.available_capacity == 0

    @property
    def queue_length(self) -> int:
        """Get current queue length."""
        return len(self._queue)

    @property
    def in_service_count(self) -> int:
        """Get number of entities in service."""
        return len(self._in_service)

    @property
    def total_in_system(self) -> int:
        """Get total entities (queue + in service)."""
        return self.queue_length + self.in_service_count

    @property
    def stats(self) -> ServerStats:
        """Get server statistics."""
        return self._stats

    @property
    def queue(self) -> Queue[T]:
        """Get the waiting queue."""
        return self._queue

    @property
    def state(self) -> ServerState:
        """Get current server state."""
        return self._state

    def _get_service_time(self) -> float:
        """Get service time value."""
        if callable(self._service_time):
            return self._service_time()
        return self._service_time

    def _update_state(self) -> None:
        """Update server state based on occupancy."""
        if self._is_down:
            new_state = ServerState.DOWN
        elif len(self._in_service) == 0:
            new_state = ServerState.IDLE
        else:
            new_state = ServerState.BUSY

        if new_state != self._state:
            self._stats.record_state_change(self._sim.now, new_state)
            self._state = new_state

    def enqueue(self, entity: T) -> bool:
        """
        Add an entity to the server.

        The entity will be served immediately if capacity is available,
        otherwise it will wait in the queue.

        Parameters
        ----------
        entity : T
            Entity to process

        Returns
        -------
        bool
            True if entity was accepted, False if queue is full
        """
        if self._is_down:
            return False

        self._stats.arrivals += 1

        if self._on_arrival:
            self._on_arrival(entity)

        # Try to start service immediately
        if self.available_capacity > 0:
            self._start_service(entity)
            return True

        # Queue if space available
        if self._queue.enqueue(entity):
            return True

        # Balk - queue is full
        self._stats.balked += 1
        if self._on_balk:
            self._on_balk(entity)
        return False

    def _start_service(self, entity: T) -> None:
        """Start serving an entity."""
        service_time = self._get_service_time()
        server_index = len(self._in_service)

        record = ServiceRecord(
            entity=entity,
            start_time=self._sim.now,
            service_time=service_time,
            server_index=server_index,
        )

        self._in_service.append(record)

        if self._on_service_start:
            self._on_service_start(entity)

        # Schedule departure
        self._sim.schedule(
            self._complete_service,
            delay=service_time,
            args=(record,),
            tag=f"{self._name}_departure",
        )

        self._update_state()

    def _complete_service(self, record: ServiceRecord[T]) -> None:
        """Complete service for an entity."""
        if record not in self._in_service:
            return  # Already removed (e.g., due to preemption)

        self._in_service.remove(record)
        entity = record.entity

        # Update statistics
        self._stats.departures += 1
        self._stats.total_service_time += record.service_time

        if self._on_departure:
            self._on_departure(entity)

        # Start next entity from queue
        if not self._queue.is_empty:
            next_entity = self._queue.dequeue()
            if next_entity is not None:
                self._start_service(next_entity)

        self._update_state()

    def preempt(self, entity: T) -> Optional[T]:
        """
        Preempt service for highest-priority entity.

        Parameters
        ----------
        entity : T
            Entity requesting preemption

        Returns
        -------
        Optional[T]
            The preempted entity, or None if no preemption occurred
        """
        if not self._in_service:
            # No one to preempt, start service
            self._start_service(entity)
            return None

        # Find entity to preempt (last started)
        record = self._in_service.pop()
        preempted_entity = record.entity

        # Re-queue preempted entity at front
        self._queue._items.appendleft(preempted_entity)
        self._queue._entry_times[id(preempted_entity)] = self._sim.now

        # Start new entity
        self._start_service(entity)

        return preempted_entity

    def shutdown(self) -> None:
        """Shut down the server."""
        self._is_down = True
        self._update_state()

    def restart(self) -> None:
        """Restart the server."""
        self._is_down = False
        self._update_state()

        # Start any queued entities
        while self.available_capacity > 0 and not self._queue.is_empty:
            next_entity = self._queue.dequeue()
            if next_entity is not None:
                self._start_service(next_entity)

    def on_arrival(self, callback: Callable[[T], None]) -> None:
        """Set callback for entity arrivals."""
        self._on_arrival = callback

    def on_service_start(self, callback: Callable[[T], None]) -> None:
        """Set callback for service start."""
        self._on_service_start = callback

    def on_departure(self, callback: Callable[[T], None]) -> None:
        """Set callback for entity departures."""
        self._on_departure = callback

    def on_balk(self, callback: Callable[[T], None]) -> None:
        """Set callback for balking entities."""
        self._on_balk = callback

    def reset_stats(self) -> None:
        """Reset server and queue statistics."""
        self._stats.reset()
        self._queue.reset_stats()

    def get_entities_in_service(self) -> List[T]:
        """Get list of entities currently in service."""
        return [record.entity for record in self._in_service]

    def __repr__(self) -> str:
        """Return detailed representation."""
        return (
            f"Server(name={self._name!r}, capacity={self._capacity}, "
            f"in_service={self.in_service_count}, queue={self.queue_length}, "
            f"state={self._state.name})"
        )


class MultiStageServer(Generic[T]):
    """
    Multi-stage processing server.

    Entities flow through a sequence of processing stages,
    each with its own service time and optional queue.

    Parameters
    ----------
    sim : Simulation
        Parent simulation
    stage_configs : List[Dict]
        Configuration for each stage with keys:
        - capacity: int
        - service_time: float or Callable
        - queue_capacity: int (optional)
    name : str
        Optional name

    Examples
    --------
    >>> stages = [
    ...     {"capacity": 1, "service_time": 5.0},
    ...     {"capacity": 2, "service_time": 3.0},
    ... ]
    >>> server = MultiStageServer(sim, stages)
    >>> server.enqueue(job)
    """

    def __init__(
        self,
        sim: "Simulation",
        stage_configs: List[Dict[str, Any]],
        name: str = "",
    ) -> None:
        """Initialize multi-stage server."""
        self._sim = sim
        self._name = name or f"MultiStageServer_{id(self)}"

        self._stages: List[Server[T]] = []
        for i, config in enumerate(stage_configs):
            stage = Server(
                sim=sim,
                capacity=config.get("capacity", 1),
                service_time=config.get("service_time", 1.0),
                queue_capacity=config.get("queue_capacity", 0),
                name=f"{self._name}_Stage{i + 1}",
            )
            self._stages.append(stage)

        # Connect stages
        for i in range(len(self._stages) - 1):
            self._stages[i].on_departure(self._stages[i + 1].enqueue)

        # Final stage callback
        self._on_completion: Optional[Callable[[T], None]] = None

    @property
    def num_stages(self) -> int:
        """Get number of stages."""
        return len(self._stages)

    def enqueue(self, entity: T) -> bool:
        """
        Add entity to first stage.

        Parameters
        ----------
        entity : T
            Entity to process

        Returns
        -------
        bool
            True if accepted
        """
        return self._stages[0].enqueue(entity)

    def on_completion(self, callback: Callable[[T], None]) -> None:
        """Set callback for entity completion of all stages."""
        self._on_completion = callback
        self._stages[-1].on_departure(callback)

    def get_stage(self, index: int) -> Server[T]:
        """
        Get a specific stage.

        Parameters
        ----------
        index : int
            Stage index (0-based)

        Returns
        -------
        Server[T]
            The stage server
        """
        return self._stages[index]

    def __repr__(self) -> str:
        """Return detailed representation."""
        return f"MultiStageServer(name={self._name!r}, stages={self.num_stages})"
