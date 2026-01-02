"""
Activity component for modeling time-based operations.

Activities represent operations that take time, such as processing,
transportation, or service. They support capacity constraints,
external resource synchronization, and various lifecycle callbacks.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Deque,
    Dict,
    Generic,
    List,
    Optional,
    Set,
    TypeVar,
)
from collections import deque
from enum import Enum, auto

if TYPE_CHECKING:
    from simcraft.core.simulation import Simulation
    from simcraft.core.entity import Entity

T = TypeVar("T")


class ActivityState(Enum):
    """States for activity lifecycle."""

    PENDING = auto()  # Waiting to start
    READY_TO_START = auto()  # Can start if capacity available
    PROCESSING = auto()  # Currently executing
    COMPLETED = auto()  # Processing done, not yet departed
    READY_TO_FINISH = auto()  # Can finish (external sync)
    READY_TO_DEPART = auto()  # Completed, can depart


@dataclass
class ActivityStats:
    """
    Statistics for activity performance.

    Attributes
    ----------
    entries : int
        Total entities that entered the activity
    completions : int
        Total entities that completed
    departures : int
        Total entities that departed
    total_processing_time : float
        Sum of all processing times
    total_wait_time : float
        Sum of all wait times
    """

    entries: int = 0
    completions: int = 0
    departures: int = 0
    total_processing_time: float = 0.0
    total_wait_time: float = 0.0
    _area_processing: float = 0.0
    _area_waiting: float = 0.0
    _last_change_time: float = 0.0
    _current_processing: int = 0
    _current_waiting: int = 0

    def record_entry(self, time: float) -> None:
        """Record entity entering waiting state."""
        self._update_area(time)
        self.entries += 1
        self._current_waiting += 1

    def record_start(self, time: float, wait_time: float) -> None:
        """Record entity starting processing."""
        self._update_area(time)
        self._current_waiting -= 1
        self._current_processing += 1
        self.total_wait_time += wait_time

    def record_completion(self, time: float, processing_time: float) -> None:
        """Record entity completing processing."""
        self._update_area(time)
        self.completions += 1
        self.total_processing_time += processing_time

    def record_departure(self, time: float) -> None:
        """Record entity departing."""
        self._update_area(time)
        self._current_processing -= 1
        self.departures += 1

    def _update_area(self, time: float) -> None:
        """Update time-weighted areas."""
        duration = time - self._last_change_time
        self._area_processing += self._current_processing * duration
        self._area_waiting += self._current_waiting * duration
        self._last_change_time = time

    @property
    def average_processing(self) -> float:
        """Get time-average number in processing."""
        if self._last_change_time == 0:
            return 0.0
        return self._area_processing / self._last_change_time

    @property
    def average_waiting(self) -> float:
        """Get time-average number waiting."""
        if self._last_change_time == 0:
            return 0.0
        return self._area_waiting / self._last_change_time

    @property
    def average_processing_time(self) -> float:
        """Get average processing time per entity."""
        if self.completions == 0:
            return 0.0
        return self.total_processing_time / self.completions

    @property
    def average_wait_time(self) -> float:
        """Get average wait time per entity."""
        if self.completions == 0:
            return 0.0
        return self.total_wait_time / self.completions


@dataclass
class ActivityRecord(Generic[T]):
    """Record for an entity in an activity."""

    entity: T
    state: ActivityState
    entry_time: float
    start_time: Optional[float] = None
    completion_time: Optional[float] = None


class Activity(Generic[T]):
    """
    Time-based activity with capacity and resource synchronization.

    Activities model operations that take time, with support for:
    - Capacity constraints
    - External resource requirements
    - State-based lifecycle management
    - Statistics collection

    The activity lifecycle is:
    1. PENDING: Entity is waiting to start
    2. READY_TO_START: Resources available, can start
    3. PROCESSING: Currently being processed
    4. COMPLETED: Processing done
    5. READY_TO_FINISH: Can depart (external signal)
    6. READY_TO_DEPART: Ready to leave

    Parameters
    ----------
    sim : Simulation
        Parent simulation
    capacity : int
        Maximum concurrent entities
    processing_time : Union[float, Callable[[T], float]]
        Fixed time or function returning processing time
    need_external_start : bool
        Whether external signal needed to start
    need_external_finish : bool
        Whether external signal needed to finish
    name : str
        Activity name

    Examples
    --------
    >>> def processing_time(job):
    ...     return job.size * 0.1
    ...
    >>> activity = Activity(
    ...     sim,
    ...     capacity=2,
    ...     processing_time=processing_time,
    ...     name="Assembly"
    ... )
    >>>
    >>> activity.on_departure(lambda job: output_queue.enqueue(job))
    >>> activity.request_to_start(job)
    """

    def __init__(
        self,
        sim: "Simulation",
        capacity: int = 1,
        processing_time: Any = 1.0,
        need_external_start: bool = False,
        need_external_finish: bool = False,
        name: str = "",
    ) -> None:
        """Initialize activity."""
        self._sim = sim
        self._capacity = capacity
        self._processing_time = processing_time
        self._need_external_start = need_external_start
        self._need_external_finish = need_external_finish
        self._name = name or f"Activity_{id(self)}"

        # Entity tracking by state
        self._pending: Deque[ActivityRecord[T]] = deque()
        self._ready_to_start: Deque[ActivityRecord[T]] = deque()
        self._processing: List[ActivityRecord[T]] = []
        self._completed: List[ActivityRecord[T]] = []
        self._ready_to_finish: List[ActivityRecord[T]] = []
        self._ready_to_depart: Deque[ActivityRecord[T]] = deque()

        self._stats = ActivityStats()

        # Callbacks
        self._on_start: Optional[Callable[[T], None]] = None
        self._on_complete: Optional[Callable[[T], None]] = None
        self._on_depart: Optional[Callable[[T], None]] = None

    @property
    def name(self) -> str:
        """Get activity name."""
        return self._name

    @property
    def capacity(self) -> int:
        """Get activity capacity."""
        return self._capacity

    @property
    def stats(self) -> ActivityStats:
        """Get activity statistics."""
        return self._stats

    @property
    def occupancy(self) -> int:
        """Get current occupancy (processing + completed + ready_to_finish)."""
        return (
            len(self._processing)
            + len(self._completed)
            + len(self._ready_to_finish)
            + len(self._ready_to_depart)
        )

    @property
    def available_capacity(self) -> int:
        """Get available capacity."""
        return max(0, self._capacity - self.occupancy)

    @property
    def pending_count(self) -> int:
        """Get number of pending entities."""
        return len(self._pending) + len(self._ready_to_start)

    @property
    def processing_count(self) -> int:
        """Get number of entities in processing."""
        return len(self._processing)

    def _get_processing_time(self, entity: T) -> float:
        """Get processing time for an entity."""
        if callable(self._processing_time):
            return self._processing_time(entity)
        return float(self._processing_time)

    def _find_record(self, entity: T) -> Optional[ActivityRecord[T]]:
        """Find record for an entity."""
        for collection in [
            self._pending,
            self._ready_to_start,
            self._processing,
            self._completed,
            self._ready_to_finish,
            self._ready_to_depart,
        ]:
            for record in collection:
                if record.entity is entity:
                    return record
        return None

    def request_to_start(self, entity: T) -> None:
        """
        Request an entity to start the activity.

        Parameters
        ----------
        entity : T
            Entity requesting to start
        """
        record = ActivityRecord(
            entity=entity,
            state=ActivityState.PENDING,
            entry_time=self._sim.now,
        )

        if self._need_external_start:
            self._pending.append(record)
            self._stats.record_entry(self._sim.now)
        else:
            self._ready_to_start.append(record)
            self._stats.record_entry(self._sim.now)
            self._attempt_to_start()

    def try_start(self, entity: T) -> bool:
        """
        External signal that entity can start.

        Parameters
        ----------
        entity : T
            Entity to start

        Returns
        -------
        bool
            True if entity was found and can start
        """
        for record in list(self._pending):
            if record.entity is entity:
                self._pending.remove(record)
                record.state = ActivityState.READY_TO_START
                self._ready_to_start.append(record)
                self._attempt_to_start()
                return True
        return False

    def _attempt_to_start(self) -> None:
        """Attempt to start entities that are ready."""
        while self._ready_to_start and self.available_capacity > 0:
            record = self._ready_to_start.popleft()
            self._start(record)

    def _start(self, record: ActivityRecord[T]) -> None:
        """Start processing an entity."""
        record.state = ActivityState.PROCESSING
        record.start_time = self._sim.now

        wait_time = self._sim.now - record.entry_time
        self._stats.record_start(self._sim.now, wait_time)

        self._processing.append(record)

        if self._on_start:
            self._on_start(record.entity)

        # Schedule completion
        processing_time = self._get_processing_time(record.entity)
        self._sim.schedule(
            self._complete,
            delay=processing_time,
            args=(record,),
            tag=f"{self._name}_complete",
        )

    def _complete(self, record: ActivityRecord[T]) -> None:
        """Complete processing for an entity."""
        if record not in self._processing:
            return  # Already removed

        self._processing.remove(record)
        record.state = ActivityState.COMPLETED
        record.completion_time = self._sim.now

        processing_time = self._sim.now - (record.start_time or record.entry_time)
        self._stats.record_completion(self._sim.now, processing_time)

        if self._on_complete:
            self._on_complete(record.entity)

        if self._need_external_finish:
            self._completed.append(record)
        else:
            self._ready_to_finish.append(record)
            self._attempt_to_finish()

    def try_finish(self, entity: T) -> bool:
        """
        External signal that entity can finish.

        Parameters
        ----------
        entity : T
            Entity to finish

        Returns
        -------
        bool
            True if entity was found and can finish
        """
        for record in list(self._completed):
            if record.entity is entity:
                self._completed.remove(record)
                record.state = ActivityState.READY_TO_FINISH
                self._ready_to_finish.append(record)
                self._attempt_to_finish()
                return True
        return False

    def _attempt_to_finish(self) -> None:
        """Attempt to finish entities that are ready."""
        while self._ready_to_finish:
            record = self._ready_to_finish.pop(0)
            self._finish(record)

    def _finish(self, record: ActivityRecord[T]) -> None:
        """Finish an entity and allow departure."""
        record.state = ActivityState.READY_TO_DEPART
        self._ready_to_depart.append(record)
        self._depart(record)

    def _depart(self, record: ActivityRecord[T]) -> None:
        """Entity departs from the activity."""
        if record in self._ready_to_depart:
            self._ready_to_depart.remove(record)

        self._stats.record_departure(self._sim.now)

        if self._on_depart:
            self._on_depart(record.entity)

        # Try to start more
        self._attempt_to_start()

    def get_pending(self) -> List[T]:
        """Get list of pending entities."""
        return [r.entity for r in self._pending]

    def get_processing(self) -> List[T]:
        """Get list of entities in processing."""
        return [r.entity for r in self._processing]

    def get_completed(self) -> List[T]:
        """Get list of completed entities."""
        return [r.entity for r in self._completed]

    def on_start(self, callback: Callable[[T], None]) -> None:
        """Set callback for processing start."""
        self._on_start = callback

    def on_complete(self, callback: Callable[[T], None]) -> None:
        """Set callback for processing complete."""
        self._on_complete = callback

    def on_departure(self, callback: Callable[[T], None]) -> None:
        """Set callback for entity departure."""
        self._on_depart = callback

    def reset_stats(self) -> None:
        """Reset activity statistics."""
        self._stats = ActivityStats()

    def __repr__(self) -> str:
        """Return detailed representation."""
        return (
            f"Activity(name={self._name!r}, capacity={self._capacity}, "
            f"pending={self.pending_count}, processing={self.processing_count}, "
            f"occupancy={self.occupancy})"
        )


class ParallelActivity(Generic[T]):
    """
    Parallel activities with shared waiting queue.

    Useful for modeling parallel processing stations that
    share a common input queue.

    Parameters
    ----------
    sim : Simulation
        Parent simulation
    num_parallel : int
        Number of parallel activities
    processing_time : Any
        Processing time per activity

    Examples
    --------
    >>> parallel = ParallelActivity(sim, num_parallel=3, processing_time=5.0)
    >>> parallel.request_to_start(job)  # Goes to first available
    """

    def __init__(
        self,
        sim: "Simulation",
        num_parallel: int,
        processing_time: Any = 1.0,
        name: str = "",
    ) -> None:
        """Initialize parallel activities."""
        self._sim = sim
        self._name = name or f"ParallelActivity_{id(self)}"

        self._activities: List[Activity[T]] = []
        for i in range(num_parallel):
            activity = Activity(
                sim=sim,
                capacity=1,
                processing_time=processing_time,
                name=f"{self._name}_{i + 1}",
            )
            self._activities.append(activity)

        self._pending: Deque[T] = deque()
        self._on_depart: Optional[Callable[[T], None]] = None

        # Connect departures
        for activity in self._activities:
            activity.on_departure(self._handle_departure)

    def request_to_start(self, entity: T) -> None:
        """
        Request entity to start on any available activity.

        Parameters
        ----------
        entity : T
            Entity to process
        """
        # Find available activity
        for activity in self._activities:
            if activity.available_capacity > 0:
                activity.request_to_start(entity)
                return

        # Queue if all busy
        self._pending.append(entity)

    def _handle_departure(self, entity: T) -> None:
        """Handle departure from any activity."""
        # Start next pending
        if self._pending:
            next_entity = self._pending.popleft()
            self.request_to_start(next_entity)

        if self._on_depart:
            self._on_depart(entity)

    def on_departure(self, callback: Callable[[T], None]) -> None:
        """Set callback for entity departure."""
        self._on_depart = callback

    @property
    def total_capacity(self) -> int:
        """Get total capacity across all activities."""
        return len(self._activities)

    @property
    def available_capacity(self) -> int:
        """Get total available capacity."""
        return sum(a.available_capacity for a in self._activities)

    @property
    def pending_count(self) -> int:
        """Get number of entities waiting."""
        return len(self._pending) + sum(a.pending_count for a in self._activities)

    def __repr__(self) -> str:
        """Return detailed representation."""
        return (
            f"ParallelActivity(name={self._name!r}, "
            f"parallel={len(self._activities)}, "
            f"pending={self.pending_count})"
        )
