"""
Resource pool for managing collections of individual resources.

Useful when resources are distinguishable (e.g., specific machines,
operators with different skills, AGVs with different locations).
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
    Iterator,
)
from enum import Enum, auto

if TYPE_CHECKING:
    from simcraft.core.simulation import Simulation

T = TypeVar("T")
R = TypeVar("R")


class PoolSelectionPolicy(Enum):
    """Policies for selecting resources from pool."""

    FIRST_AVAILABLE = auto()
    ROUND_ROBIN = auto()
    LEAST_UTILIZED = auto()
    CUSTOM = auto()


@dataclass
class PooledResource(Generic[R]):
    """
    Wrapper for a resource in a pool.

    Attributes
    ----------
    resource : R
        The actual resource object
    id : str
        Unique identifier
    is_available : bool
        Whether resource is currently available
    allocations : int
        Number of times this resource has been allocated
    total_busy_time : float
        Total time this resource has been allocated
    """

    resource: R
    id: str
    is_available: bool = True
    allocations: int = 0
    total_busy_time: float = 0.0
    _allocated_at: Optional[float] = None
    _allocated_to: Optional[Any] = None


@dataclass
class PoolStats:
    """
    Statistics for resource pool.

    Attributes
    ----------
    total_acquisitions : int
        Total successful acquisitions
    total_releases : int
        Total releases
    failed_acquisitions : int
        Failed acquisition attempts
    """

    total_acquisitions: int = 0
    total_releases: int = 0
    failed_acquisitions: int = 0
    total_wait_time: float = 0.0
    _waiting_count: int = 0

    @property
    def success_rate(self) -> float:
        """Get acquisition success rate."""
        total = self.total_acquisitions + self.failed_acquisitions
        if total == 0:
            return 0.0
        return self.total_acquisitions / total


class ResourcePool(Generic[R]):
    """
    Pool of individual, distinguishable resources.

    Unlike a simple capacity-based Resource, ResourcePool manages
    individual resource objects that can be selected based on
    various policies (first available, round-robin, least utilized,
    or custom selection function).

    Parameters
    ----------
    sim : Simulation
        Parent simulation
    name : str
        Pool name
    selection_policy : PoolSelectionPolicy
        Policy for selecting resources

    Examples
    --------
    >>> class AGV:
    ...     def __init__(self, id: str, location: tuple):
    ...         self.id = id
    ...         self.location = location
    ...
    >>> pool = ResourcePool(sim, name="AGVPool")
    >>> pool.add_resource(AGV("AGV1", (0, 0)), id="AGV1")
    >>> pool.add_resource(AGV("AGV2", (10, 0)), id="AGV2")
    >>>
    >>> # Custom selection: nearest AGV
    >>> def nearest_to(target):
    ...     def selector(available):
    ...         return min(available, key=lambda r: distance(r.location, target))
    ...     return selector
    >>>
    >>> agv = pool.acquire(job, selector=nearest_to((5, 5)))
    """

    def __init__(
        self,
        sim: "Simulation",
        name: str = "",
        selection_policy: PoolSelectionPolicy = PoolSelectionPolicy.FIRST_AVAILABLE,
    ) -> None:
        """Initialize resource pool."""
        self._sim = sim
        self._name = name or f"Pool_{id(self)}"
        self._policy = selection_policy

        self._resources: Dict[str, PooledResource[R]] = {}
        self._round_robin_index = 0
        self._stats = PoolStats()

        # Waiting queue: list of (requester, callback, selector)
        self._waiting: List[tuple] = []

        # Custom selector function
        self._custom_selector: Optional[Callable[[List[R]], R]] = None

    @property
    def name(self) -> str:
        """Get pool name."""
        return self._name

    @property
    def size(self) -> int:
        """Get total number of resources in pool."""
        return len(self._resources)

    @property
    def available_count(self) -> int:
        """Get number of available resources."""
        return sum(1 for r in self._resources.values() if r.is_available)

    @property
    def allocated_count(self) -> int:
        """Get number of allocated resources."""
        return self.size - self.available_count

    @property
    def stats(self) -> PoolStats:
        """Get pool statistics."""
        return self._stats

    @property
    def is_empty(self) -> bool:
        """Check if pool has no resources."""
        return len(self._resources) == 0

    @property
    def has_available(self) -> bool:
        """Check if any resources are available."""
        return self.available_count > 0

    def add_resource(self, resource: R, id: Optional[str] = None) -> str:
        """
        Add a resource to the pool.

        Parameters
        ----------
        resource : R
            Resource to add
        id : Optional[str]
            Unique identifier (generated if not provided)

        Returns
        -------
        str
            Resource identifier
        """
        if id is None:
            id = f"Resource_{len(self._resources) + 1}"

        if id in self._resources:
            raise ValueError(f"Resource with id '{id}' already exists")

        self._resources[id] = PooledResource(resource=resource, id=id)
        return id

    def remove_resource(self, id: str) -> Optional[R]:
        """
        Remove a resource from the pool.

        Parameters
        ----------
        id : str
            Resource identifier

        Returns
        -------
        Optional[R]
            The removed resource, or None if not found
        """
        pooled = self._resources.pop(id, None)
        if pooled:
            return pooled.resource
        return None

    def get_resource(self, id: str) -> Optional[R]:
        """
        Get a resource by ID.

        Parameters
        ----------
        id : str
            Resource identifier

        Returns
        -------
        Optional[R]
            The resource, or None if not found
        """
        pooled = self._resources.get(id)
        return pooled.resource if pooled else None

    def _select_resource(
        self,
        selector: Optional[Callable[[List[R]], R]] = None,
    ) -> Optional[PooledResource[R]]:
        """Select a resource based on policy or custom selector."""
        available = [r for r in self._resources.values() if r.is_available]

        if not available:
            return None

        if selector is not None:
            # Custom selector
            resources = [r.resource for r in available]
            selected = selector(resources)
            for pooled in available:
                if pooled.resource is selected:
                    return pooled
            return None

        if self._policy == PoolSelectionPolicy.FIRST_AVAILABLE:
            return available[0]

        elif self._policy == PoolSelectionPolicy.ROUND_ROBIN:
            self._round_robin_index = self._round_robin_index % len(available)
            result = available[self._round_robin_index]
            self._round_robin_index += 1
            return result

        elif self._policy == PoolSelectionPolicy.LEAST_UTILIZED:
            return min(available, key=lambda r: r.allocations)

        elif self._policy == PoolSelectionPolicy.CUSTOM:
            if self._custom_selector:
                resources = [r.resource for r in available]
                selected = self._custom_selector(resources)
                for pooled in available:
                    if pooled.resource is selected:
                        return pooled
            return available[0]

        return available[0]

    def acquire(
        self,
        requester: Any,
        selector: Optional[Callable[[List[R]], R]] = None,
    ) -> Optional[R]:
        """
        Acquire a resource from the pool.

        Parameters
        ----------
        requester : Any
            Entity requesting the resource
        selector : Optional[Callable]
            Custom function to select from available resources

        Returns
        -------
        Optional[R]
            Selected resource, or None if none available
        """
        pooled = self._select_resource(selector)

        if pooled is None:
            self._stats.failed_acquisitions += 1
            return None

        pooled.is_available = False
        pooled.allocations += 1
        pooled._allocated_at = self._sim.now
        pooled._allocated_to = requester

        self._stats.total_acquisitions += 1

        return pooled.resource

    def request(
        self,
        requester: Any,
        callback: Callable[[R], None],
        selector: Optional[Callable[[List[R]], R]] = None,
    ) -> bool:
        """
        Request a resource (wait if not available).

        Parameters
        ----------
        requester : Any
            Entity requesting the resource
        callback : Callable
            Function to call when resource is acquired
        selector : Optional[Callable]
            Custom selection function

        Returns
        -------
        bool
            True if immediately acquired, False if waiting
        """
        resource = self.acquire(requester, selector)

        if resource is not None:
            callback(resource)
            return True

        # Add to waiting queue
        self._waiting.append((requester, callback, selector, self._sim.now))
        return False

    def release(self, resource: R) -> bool:
        """
        Release a resource back to the pool.

        Parameters
        ----------
        resource : R
            Resource to release

        Returns
        -------
        bool
            True if successfully released
        """
        for pooled in self._resources.values():
            if pooled.resource is resource:
                if pooled.is_available:
                    return False  # Already available

                pooled.is_available = True

                if pooled._allocated_at is not None:
                    hold_time = self._sim.now - pooled._allocated_at
                    pooled.total_busy_time += hold_time

                pooled._allocated_at = None
                pooled._allocated_to = None

                self._stats.total_releases += 1

                # Process waiting requests
                self._process_waiting()

                return True

        return False

    def _process_waiting(self) -> None:
        """Process waiting requests."""
        if not self._waiting or not self.has_available:
            return

        # Process in order
        i = 0
        while i < len(self._waiting) and self.has_available:
            requester, callback, selector, request_time = self._waiting[i]

            resource = self.acquire(requester, selector)
            if resource is not None:
                self._waiting.pop(i)
                wait_time = self._sim.now - request_time
                self._stats.total_wait_time += wait_time
                callback(resource)
            else:
                i += 1

    def set_selection_policy(
        self,
        policy: PoolSelectionPolicy,
        custom_selector: Optional[Callable[[List[R]], R]] = None,
    ) -> None:
        """
        Set resource selection policy.

        Parameters
        ----------
        policy : PoolSelectionPolicy
            Selection policy
        custom_selector : Optional[Callable]
            Custom selector for CUSTOM policy
        """
        self._policy = policy
        self._custom_selector = custom_selector

    def get_available(self) -> List[R]:
        """
        Get list of available resources.

        Returns
        -------
        List[R]
            Available resources
        """
        return [r.resource for r in self._resources.values() if r.is_available]

    def get_allocated(self) -> List[R]:
        """
        Get list of allocated resources.

        Returns
        -------
        List[R]
            Allocated resources
        """
        return [r.resource for r in self._resources.values() if not r.is_available]

    def get_utilization(self, resource_id: str) -> float:
        """
        Get utilization for a specific resource.

        Parameters
        ----------
        resource_id : str
            Resource identifier

        Returns
        -------
        float
            Utilization ratio (0-1)
        """
        pooled = self._resources.get(resource_id)
        if pooled is None or self._sim.now == 0:
            return 0.0

        busy_time = pooled.total_busy_time
        if not pooled.is_available and pooled._allocated_at:
            busy_time += self._sim.now - pooled._allocated_at

        return busy_time / self._sim.now

    def get_average_utilization(self) -> float:
        """
        Get average utilization across all resources.

        Returns
        -------
        float
            Average utilization ratio
        """
        if not self._resources:
            return 0.0

        total = sum(self.get_utilization(id) for id in self._resources)
        return total / len(self._resources)

    def reset_stats(self) -> None:
        """Reset all statistics."""
        self._stats = PoolStats()
        for pooled in self._resources.values():
            pooled.allocations = 0
            pooled.total_busy_time = 0.0

    def __iter__(self) -> Iterator[R]:
        """Iterate over all resources."""
        return (r.resource for r in self._resources.values())

    def __len__(self) -> int:
        """Get total number of resources."""
        return len(self._resources)

    def __repr__(self) -> str:
        """Return detailed representation."""
        return (
            f"ResourcePool(name={self._name!r}, "
            f"size={self.size}, available={self.available_count}, "
            f"waiting={len(self._waiting)})"
        )
