"""
Entity base class for simulation objects.

Entities represent the objects that flow through and interact
within the simulation (e.g., customers, jobs, packets, containers).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type
from enum import Enum, auto
import itertools

if TYPE_CHECKING:
    from simcraft.core.simulation import Simulation


class EntityState(Enum):
    """Standard entity lifecycle states."""

    CREATED = auto()
    ACTIVE = auto()
    WAITING = auto()
    IN_SERVICE = auto()
    BLOCKED = auto()
    COMPLETED = auto()
    DISPOSED = auto()


@dataclass
class Entity:
    """
    Base class for all simulation entities.

    Entities are the objects that flow through and interact within
    the simulation. They maintain their own state, track timing
    information, and can carry arbitrary attributes.

    Attributes
    ----------
    id : Optional[str]
        Custom identifier for the entity
    state : EntityState
        Current lifecycle state
    created_at : float
        Simulation time when entity was created
    attributes : Dict[str, Any]
        Custom attributes dictionary

    Examples
    --------
    >>> class Customer(Entity):
    ...     def __init__(self, priority: int = 0):
    ...         super().__init__()
    ...         self.priority = priority
    ...
    >>> customer = Customer(priority=1)
    >>> customer.set_attribute("vip", True)
    >>> print(customer.index, customer.get_attribute("vip"))
    """

    id: Optional[str] = None
    state: EntityState = EntityState.CREATED
    created_at: float = 0.0
    attributes: Dict[str, Any] = field(default_factory=dict, repr=False)

    # Class-level counter for unique indices
    _counter: itertools.count = field(
        default_factory=lambda: itertools.count(1), repr=False, compare=False
    )
    _index: int = field(default=0, repr=False)

    def __post_init__(self) -> None:
        """Initialize entity with unique index."""
        if self._index == 0:
            # Get unique index from class-specific counter
            entity_class = type(self)
            if not hasattr(entity_class, "_class_counter"):
                entity_class._class_counter = itertools.count(1)
            self._index = next(entity_class._class_counter)

        if self.id is None:
            self.id = f"{type(self).__name__}_{self._index}"

    @property
    def index(self) -> int:
        """Get unique sequence index for this entity."""
        return self._index

    def set_attribute(self, key: str, value: Any) -> None:
        """
        Set a custom attribute.

        Parameters
        ----------
        key : str
            Attribute name
        value : Any
            Attribute value
        """
        self.attributes[key] = value

    def get_attribute(self, key: str, default: Any = None) -> Any:
        """
        Get a custom attribute.

        Parameters
        ----------
        key : str
            Attribute name
        default : Any
            Value to return if attribute not found

        Returns
        -------
        Any
            Attribute value or default
        """
        return self.attributes.get(key, default)

    def has_attribute(self, key: str) -> bool:
        """
        Check if entity has an attribute.

        Parameters
        ----------
        key : str
            Attribute name

        Returns
        -------
        bool
            True if attribute exists
        """
        return key in self.attributes

    def activate(self) -> None:
        """Transition entity to ACTIVE state."""
        self.state = EntityState.ACTIVE

    def wait(self) -> None:
        """Transition entity to WAITING state."""
        self.state = EntityState.WAITING

    def enter_service(self) -> None:
        """Transition entity to IN_SERVICE state."""
        self.state = EntityState.IN_SERVICE

    def block(self) -> None:
        """Transition entity to BLOCKED state."""
        self.state = EntityState.BLOCKED

    def complete(self) -> None:
        """Transition entity to COMPLETED state."""
        self.state = EntityState.COMPLETED

    def dispose(self) -> None:
        """Transition entity to DISPOSED state."""
        self.state = EntityState.DISPOSED

    @property
    def is_active(self) -> bool:
        """Check if entity is in an active processing state."""
        return self.state in (EntityState.ACTIVE, EntityState.IN_SERVICE)

    @property
    def is_waiting(self) -> bool:
        """Check if entity is waiting."""
        return self.state == EntityState.WAITING

    @property
    def is_completed(self) -> bool:
        """Check if entity has completed processing."""
        return self.state == EntityState.COMPLETED

    @property
    def is_disposed(self) -> bool:
        """Check if entity has been disposed."""
        return self.state == EntityState.DISPOSED

    def __eq__(self, other: object) -> bool:
        """Entities are equal if they have the same index."""
        if not isinstance(other, Entity):
            return NotImplemented
        return type(self) == type(other) and self._index == other._index

    def __hash__(self) -> int:
        """Hash based on class and index."""
        return hash((type(self).__name__, self._index))

    def __str__(self) -> str:
        """Return human-readable representation."""
        return f"{type(self).__name__}(id={self.id}, state={self.state.name})"


@dataclass
class TimedEntity(Entity):
    """
    Entity with timing tracking.

    Extends Entity with automatic tracking of entry/exit times
    for different stages of processing.

    Attributes
    ----------
    entry_time : float
        Time when entity entered the system
    start_service_time : float
        Time when entity started being served
    end_service_time : float
        Time when entity finished being served
    exit_time : float
        Time when entity left the system
    """

    entry_time: float = 0.0
    start_service_time: float = 0.0
    end_service_time: float = 0.0
    exit_time: float = 0.0

    # Tracking intermediate times
    _time_stamps: Dict[str, float] = field(default_factory=dict, repr=False)

    def record_entry(self, time: float) -> None:
        """Record system entry time."""
        self.entry_time = time
        self.created_at = time

    def record_service_start(self, time: float) -> None:
        """Record service start time."""
        self.start_service_time = time
        self.enter_service()

    def record_service_end(self, time: float) -> None:
        """Record service end time."""
        self.end_service_time = time

    def record_exit(self, time: float) -> None:
        """Record system exit time."""
        self.exit_time = time
        self.complete()

    def record_timestamp(self, name: str, time: float) -> None:
        """Record a named timestamp."""
        self._time_stamps[name] = time

    def get_timestamp(self, name: str) -> Optional[float]:
        """Get a recorded timestamp."""
        return self._time_stamps.get(name)

    @property
    def waiting_time(self) -> float:
        """Calculate time spent waiting for service."""
        if self.start_service_time == 0:
            return 0.0
        return self.start_service_time - self.entry_time

    @property
    def service_time(self) -> float:
        """Calculate time spent in service."""
        if self.end_service_time == 0:
            return 0.0
        return self.end_service_time - self.start_service_time

    @property
    def flow_time(self) -> float:
        """Calculate total time in system (entry to exit)."""
        if self.exit_time == 0:
            return 0.0
        return self.exit_time - self.entry_time

    @property
    def cycle_time(self) -> float:
        """Alias for flow_time."""
        return self.flow_time


class EntityFactory:
    """
    Factory for creating entities with consistent configuration.

    Examples
    --------
    >>> factory = EntityFactory(Customer, priority=1)
    >>> customer1 = factory.create()
    >>> customer2 = factory.create(vip=True)
    """

    def __init__(
        self,
        entity_class: Type[Entity],
        **default_kwargs: Any,
    ) -> None:
        """
        Initialize factory.

        Parameters
        ----------
        entity_class : Type[Entity]
            Class of entities to create
        **default_kwargs
            Default keyword arguments for entity creation
        """
        self.entity_class = entity_class
        self.default_kwargs = default_kwargs
        self._created_count = 0

    def create(self, **kwargs: Any) -> Entity:
        """
        Create a new entity.

        Parameters
        ----------
        **kwargs
            Override default arguments

        Returns
        -------
        Entity
            New entity instance
        """
        merged_kwargs = {**self.default_kwargs, **kwargs}
        entity = self.entity_class(**merged_kwargs)
        self._created_count += 1
        return entity

    @property
    def created_count(self) -> int:
        """Get number of entities created by this factory."""
        return self._created_count


class EntityPool:
    """
    Pool for reusing entity instances.

    Useful for high-frequency entity creation to reduce
    garbage collection overhead.

    Examples
    --------
    >>> pool = EntityPool(Customer, initial_size=100)
    >>> customer = pool.acquire()
    >>> # ... use customer ...
    >>> pool.release(customer)
    """

    def __init__(
        self,
        entity_class: Type[Entity],
        initial_size: int = 0,
        **default_kwargs: Any,
    ) -> None:
        """
        Initialize pool.

        Parameters
        ----------
        entity_class : Type[Entity]
            Class of entities to pool
        initial_size : int
            Number of entities to pre-create
        **default_kwargs
            Default arguments for entity creation
        """
        self.entity_class = entity_class
        self.default_kwargs = default_kwargs
        self._available: List[Entity] = []
        self._in_use: List[Entity] = []

        for _ in range(initial_size):
            entity = self.entity_class(**default_kwargs)
            self._available.append(entity)

    def acquire(self, **kwargs: Any) -> Entity:
        """
        Get an entity from the pool.

        Parameters
        ----------
        **kwargs
            Override default arguments for new entities

        Returns
        -------
        Entity
            Available entity (either reused or newly created)
        """
        if self._available:
            entity = self._available.pop()
            # Reset entity state
            entity.state = EntityState.CREATED
            for key, value in kwargs.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)
        else:
            merged_kwargs = {**self.default_kwargs, **kwargs}
            entity = self.entity_class(**merged_kwargs)

        self._in_use.append(entity)
        return entity

    def release(self, entity: Entity) -> None:
        """
        Return an entity to the pool.

        Parameters
        ----------
        entity : Entity
            Entity to return
        """
        if entity in self._in_use:
            self._in_use.remove(entity)
            entity.dispose()
            self._available.append(entity)

    @property
    def available_count(self) -> int:
        """Get number of available entities."""
        return len(self._available)

    @property
    def in_use_count(self) -> int:
        """Get number of entities currently in use."""
        return len(self._in_use)

    @property
    def total_count(self) -> int:
        """Get total number of entities in pool."""
        return len(self._available) + len(self._in_use)
