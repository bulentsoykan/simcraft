"""
Resource component for simulation.

Resources represent limited items that can be acquired and released,
such as operators, machines, or transportation vehicles.
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
    TypeVar,
    Tuple,
)
from collections import deque
from enum import Enum, auto

if TYPE_CHECKING:
    from simcraft.core.simulation import Simulation
    from simcraft.core.entity import Entity

T = TypeVar("T")


class ResourceState(Enum):
    """Resource states."""

    AVAILABLE = auto()
    ALLOCATED = auto()
    DOWN = auto()


@dataclass
class ResourceStats:
    """
    Statistics for resource usage.

    Attributes
    ----------
    acquisitions : int
        Total number of successful acquisitions
    releases : int
        Total number of releases
    timeouts : int
        Number of acquisition timeouts
    total_busy_time : float
        Total time resources were in use
    total_idle_time : float
        Total time resources were available
    """

    acquisitions: int = 0
    releases: int = 0
    timeouts: int = 0
    total_busy_time: float = 0.0
    total_idle_time: float = 0.0
    total_wait_time: float = 0.0
    _area_allocated: float = 0.0
    _last_change_time: float = 0.0
    _current_allocated: int = 0
    _capacity: int = 1

    def record_acquisition(self, time: float, wait_time: float = 0.0) -> None:
        """Record a resource acquisition."""
        self._update_area(time)
        self.acquisitions += 1
        self._current_allocated += 1
        self.total_wait_time += wait_time

    def record_release(self, time: float, hold_time: float) -> None:
        """Record a resource release."""
        self._update_area(time)
        self.releases += 1
        self._current_allocated -= 1
        self.total_busy_time += hold_time

    def _update_area(self, time: float) -> None:
        """Update time-weighted allocation area."""
        duration = time - self._last_change_time
        self._area_allocated += self._current_allocated * duration
        self._last_change_time = time

    @property
    def utilization(self) -> float:
        """Get average resource utilization."""
        if self._last_change_time == 0 or self._capacity == 0:
            return 0.0
        return self._area_allocated / (self._last_change_time * self._capacity)

    @property
    def average_hold_time(self) -> float:
        """Get average hold time."""
        if self.releases == 0:
            return 0.0
        return self.total_busy_time / self.releases

    @property
    def average_wait_time(self) -> float:
        """Get average wait time for acquisition."""
        if self.acquisitions == 0:
            return 0.0
        return self.total_wait_time / self.acquisitions

    def reset(self) -> None:
        """Reset all statistics."""
        self.acquisitions = 0
        self.releases = 0
        self.timeouts = 0
        self.total_busy_time = 0.0
        self.total_idle_time = 0.0
        self.total_wait_time = 0.0
        self._area_allocated = 0.0
        self._last_change_time = 0.0


@dataclass
class AcquisitionRequest(Generic[T]):
    """Request to acquire a resource."""

    requester: T
    quantity: int
    request_time: float
    priority: int = 0
    timeout: Optional[float] = None
    callback: Optional[Callable[["Resource", T], None]] = None

    def __lt__(self, other: "AcquisitionRequest") -> bool:
        """Compare by priority then request time."""
        if self.priority != other.priority:
            return self.priority > other.priority  # Higher priority first
        return self.request_time < other.request_time


class Resource:
    """
    Limited resource with acquire/release semantics.

    A Resource represents a limited item (or pool of items) that
    entities can acquire and later release. Supports priority-based
    waiting and timeouts.

    Parameters
    ----------
    sim : Simulation
        Parent simulation
    capacity : int
        Number of resource units
    name : str
        Optional resource name

    Examples
    --------
    >>> operator = Resource(sim, capacity=1, name="Operator")
    >>>
    >>> # Immediate acquisition
    >>> if operator.acquire(job):
    ...     # Use resource
    ...     operator.release(job)
    >>>
    >>> # Request with callback
    >>> def on_acquired(resource, job):
    ...     sim.schedule(release_op, delay=5.0, args=(job,))
    >>> operator.request(job, callback=on_acquired)
    """

    def __init__(
        self,
        sim: "Simulation",
        capacity: int = 1,
        name: str = "",
    ) -> None:
        """Initialize resource."""
        self._sim = sim
        self._capacity = capacity
        self._name = name or f"Resource_{id(self)}"

        self._available = capacity
        self._allocated: Dict[int, Tuple[T, int, float]] = {}  # id -> (entity, qty, time)
        self._waiting: List[AcquisitionRequest] = []

        self._stats = ResourceStats()
        self._stats._capacity = capacity

        self._is_down = False

    @property
    def name(self) -> str:
        """Get resource name."""
        return self._name

    @property
    def capacity(self) -> int:
        """Get total capacity."""
        return self._capacity

    @property
    def available(self) -> int:
        """Get available units."""
        if self._is_down:
            return 0
        return self._available

    @property
    def allocated(self) -> int:
        """Get allocated units."""
        return self._capacity - self._available

    @property
    def waiting_count(self) -> int:
        """Get number of waiting requests."""
        return len(self._waiting)

    @property
    def stats(self) -> ResourceStats:
        """Get resource statistics."""
        return self._stats

    @property
    def is_available(self) -> bool:
        """Check if any units are available."""
        return self.available > 0

    def acquire(
        self,
        requester: T,
        quantity: int = 1,
    ) -> bool:
        """
        Immediately acquire resource units.

        Parameters
        ----------
        requester : T
            Entity requesting the resource
        quantity : int
            Number of units to acquire

        Returns
        -------
        bool
            True if acquisition succeeded, False otherwise
        """
        if self._is_down or quantity > self._available:
            return False

        self._available -= quantity
        self._allocated[id(requester)] = (requester, quantity, self._sim.now)
        self._stats.record_acquisition(self._sim.now, 0.0)

        return True

    def release(self, holder: T) -> bool:
        """
        Release resource units.

        Parameters
        ----------
        holder : T
            Entity currently holding the resource

        Returns
        -------
        bool
            True if release succeeded, False if entity wasn't holding
        """
        record = self._allocated.pop(id(holder), None)
        if record is None:
            return False

        entity, quantity, acquire_time = record
        hold_time = self._sim.now - acquire_time

        self._available += quantity
        self._stats.record_release(self._sim.now, hold_time)

        # Process waiting requests
        self._process_waiting()

        return True

    def request(
        self,
        requester: T,
        quantity: int = 1,
        priority: int = 0,
        timeout: Optional[float] = None,
        callback: Optional[Callable[["Resource", T], None]] = None,
    ) -> bool:
        """
        Request resource units (may wait if not available).

        Parameters
        ----------
        requester : T
            Entity requesting the resource
        quantity : int
            Number of units to request
        priority : int
            Request priority (higher = processed first)
        timeout : Optional[float]
            Maximum wait time (None = wait indefinitely)
        callback : Optional[Callable]
            Function to call when acquired

        Returns
        -------
        bool
            True if immediately acquired, False if waiting
        """
        if self._is_down:
            return False

        # Try immediate acquisition
        if quantity <= self._available:
            self.acquire(requester, quantity)
            if callback:
                callback(self, requester)
            return True

        # Queue the request
        request = AcquisitionRequest(
            requester=requester,
            quantity=quantity,
            request_time=self._sim.now,
            priority=priority,
            timeout=timeout,
            callback=callback,
        )

        # Insert in priority order
        import bisect

        bisect.insort(self._waiting, request)

        # Schedule timeout if specified
        if timeout is not None:
            self._sim.schedule(
                self._handle_timeout,
                delay=timeout,
                args=(request,),
                tag=f"{self._name}_timeout",
            )

        return False

    def _process_waiting(self) -> None:
        """Process waiting requests."""
        while self._waiting:
            request = self._waiting[0]

            if request.quantity > self._available:
                break  # Cannot satisfy this request

            self._waiting.pop(0)
            wait_time = self._sim.now - request.request_time

            self._available -= request.quantity
            self._allocated[id(request.requester)] = (
                request.requester,
                request.quantity,
                self._sim.now,
            )
            self._stats.record_acquisition(self._sim.now, wait_time)

            if request.callback:
                request.callback(self, request.requester)

    def _handle_timeout(self, request: AcquisitionRequest) -> None:
        """Handle request timeout."""
        if request in self._waiting:
            self._waiting.remove(request)
            self._stats.timeouts += 1

    def cancel_request(self, requester: T) -> bool:
        """
        Cancel a pending request.

        Parameters
        ----------
        requester : T
            Entity that made the request

        Returns
        -------
        bool
            True if request was found and cancelled
        """
        for i, request in enumerate(self._waiting):
            if id(request.requester) == id(requester):
                self._waiting.pop(i)
                return True
        return False

    def shutdown(self) -> None:
        """Shut down the resource."""
        self._is_down = True

    def restart(self) -> None:
        """Restart the resource."""
        self._is_down = False
        self._process_waiting()

    def reset_stats(self) -> None:
        """Reset statistics."""
        self._stats.reset()
        self._stats._capacity = self._capacity

    def __repr__(self) -> str:
        """Return detailed representation."""
        return (
            f"Resource(name={self._name!r}, "
            f"available={self.available}/{self._capacity}, "
            f"waiting={self.waiting_count})"
        )


class PreemptiveResource(Resource):
    """
    Resource with preemption support.

    Lower priority holders can be preempted by higher priority requests.

    Parameters
    ----------
    sim : Simulation
        Parent simulation
    capacity : int
        Number of resource units
    name : str
        Optional resource name

    Examples
    --------
    >>> machine = PreemptiveResource(sim, capacity=1)
    >>> machine.acquire(low_priority_job, priority=1)
    >>> machine.acquire(high_priority_job, priority=10)  # Preempts
    """

    def __init__(
        self,
        sim: "Simulation",
        capacity: int = 1,
        name: str = "",
    ) -> None:
        """Initialize preemptive resource."""
        super().__init__(sim, capacity, name)
        self._priorities: Dict[int, int] = {}  # id -> priority
        self._on_preempt: Optional[Callable[[T], None]] = None

    def acquire(
        self,
        requester: T,
        quantity: int = 1,
        priority: int = 0,
    ) -> bool:
        """
        Acquire resource units, possibly preempting lower priority holders.

        Parameters
        ----------
        requester : T
            Entity requesting the resource
        quantity : int
            Number of units to acquire
        priority : int
            Priority level

        Returns
        -------
        bool
            True if acquisition succeeded
        """
        # Try normal acquisition
        if super().acquire(requester, quantity):
            self._priorities[id(requester)] = priority
            return True

        # Try preemption
        if quantity <= self._capacity:
            preempted = self._try_preempt(quantity, priority)
            if preempted:
                self._priorities[id(requester)] = priority
                return super().acquire(requester, quantity)

        return False

    def _try_preempt(self, needed: int, priority: int) -> List[T]:
        """
        Try to preempt lower priority holders.

        Returns list of preempted entities.
        """
        preempted = []
        freed = 0

        # Sort allocations by priority (lowest first)
        allocations = [
            (self._priorities.get(id_, 0), id_, record)
            for id_, record in self._allocated.items()
        ]
        allocations.sort()

        for alloc_priority, id_, (entity, qty, _) in allocations:
            if alloc_priority >= priority:
                break  # No more lower priority holders

            if freed >= needed:
                break  # Have enough

            # Preempt this holder
            super().release(entity)
            self._priorities.pop(id_, None)
            preempted.append(entity)
            freed += qty

            if self._on_preempt:
                self._on_preempt(entity)

        return preempted if freed >= needed else []

    def release(self, holder: T) -> bool:
        """Release resource and clean up priority tracking."""
        self._priorities.pop(id(holder), None)
        return super().release(holder)

    def on_preempt(self, callback: Callable[[T], None]) -> None:
        """Set callback for preemption events."""
        self._on_preempt = callback
