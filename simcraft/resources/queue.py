"""
Queue implementations for simulation.

Provides FIFO and priority-based queues with statistics collection.
"""

from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Deque,
    Generic,
    Iterator,
    List,
    Optional,
    TypeVar,
)
import heapq

if TYPE_CHECKING:
    from simcraft.core.simulation import Simulation
    from simcraft.core.entity import Entity

T = TypeVar("T")


@dataclass
class QueueEntry(Generic[T]):
    """Wrapper for queue items with entry metadata."""

    item: T
    entry_time: float


@dataclass
class QueueStats:
    """
    Statistics for queue performance.

    Attributes
    ----------
    entries : int
        Total number of entities that entered the queue
    exits : int
        Total number of entities that left the queue
    max_length : int
        Maximum queue length observed
    total_wait_time : float
        Sum of all waiting times
    area : float
        Time-weighted queue length integral
    """

    entries: int = 0
    exits: int = 0
    max_length: int = 0
    total_wait_time: float = 0.0
    area: float = 0.0
    _last_change_time: float = 0.0
    _current_length: int = 0

    def record_entry(self, time: float) -> None:
        """Record an entry to the queue."""
        self._update_area(time)
        self.entries += 1
        self._current_length += 1
        self.max_length = max(self.max_length, self._current_length)

    def record_exit(self, time: float, wait_time: float) -> None:
        """Record an exit from the queue."""
        self._update_area(time)
        self.exits += 1
        self._current_length -= 1
        self.total_wait_time += wait_time

    def _update_area(self, time: float) -> None:
        """Update time-weighted area."""
        duration = time - self._last_change_time
        self.area += self._current_length * duration
        self._last_change_time = time

    @property
    def average_length(self) -> float:
        """Get time-average queue length."""
        if self._last_change_time == 0:
            return 0.0
        return self.area / self._last_change_time

    @property
    def average_wait(self) -> float:
        """Get average waiting time."""
        if self.exits == 0:
            return 0.0
        return self.total_wait_time / self.exits

    @property
    def current_length(self) -> int:
        """Get current queue length."""
        return self._current_length

    def reset(self) -> None:
        """Reset all statistics."""
        self.entries = 0
        self.exits = 0
        self.max_length = 0
        self.total_wait_time = 0.0
        self.area = 0.0
        self._last_change_time = 0.0
        self._current_length = 0


class Queue(Generic[T]):
    """
    FIFO queue with statistics collection.

    A basic first-in-first-out queue that tracks entry times
    and collects performance statistics.

    Parameters
    ----------
    sim : Simulation
        Parent simulation for time tracking
    capacity : int
        Maximum queue capacity (0 = unlimited)
    name : str
        Optional name for the queue

    Examples
    --------
    >>> queue = Queue(sim, capacity=10, name="WaitingRoom")
    >>> queue.enqueue(customer)
    >>> if not queue.is_empty:
    ...     next_customer = queue.dequeue()
    >>> print(queue.stats.average_wait)
    """

    def __init__(
        self,
        sim: "Simulation",
        capacity: int = 0,
        name: str = "",
    ) -> None:
        """Initialize queue."""
        self._sim = sim
        self._capacity = capacity
        self._name = name or f"Queue_{id(self)}"

        self._entries: Deque[QueueEntry[T]] = deque()
        self._stats = QueueStats()

        # Callbacks
        self._on_enqueue: Optional[Callable[[T], None]] = None
        self._on_dequeue: Optional[Callable[[T], None]] = None

    @property
    def name(self) -> str:
        """Get queue name."""
        return self._name

    @property
    def stats(self) -> QueueStats:
        """Get queue statistics."""
        return self._stats

    @property
    def capacity(self) -> int:
        """Get queue capacity (0 = unlimited)."""
        return self._capacity

    @property
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self._entries) == 0

    @property
    def is_full(self) -> bool:
        """Check if queue is at capacity."""
        if self._capacity == 0:
            return False
        return len(self._entries) >= self._capacity

    def __len__(self) -> int:
        """Get current queue length."""
        return len(self._entries)

    def enqueue(self, item: T) -> bool:
        """
        Add item to the queue.

        Parameters
        ----------
        item : T
            Item to add

        Returns
        -------
        bool
            True if item was added, False if queue is full
        """
        if self.is_full:
            return False

        entry = QueueEntry(item=item, entry_time=self._sim.now)
        self._entries.append(entry)
        self._stats.record_entry(self._sim.now)

        if self._on_enqueue:
            self._on_enqueue(item)

        return True

    def dequeue(self) -> Optional[T]:
        """
        Remove and return the first item.

        Returns
        -------
        Optional[T]
            First item or None if queue is empty
        """
        if self.is_empty:
            return None

        entry = self._entries.popleft()
        wait_time = self._sim.now - entry.entry_time

        self._stats.record_exit(self._sim.now, wait_time)

        if self._on_dequeue:
            self._on_dequeue(entry.item)

        return entry.item

    def peek(self) -> Optional[T]:
        """
        Return the first item without removing it.

        Returns
        -------
        Optional[T]
            First item or None if queue is empty
        """
        if self.is_empty:
            return None
        return self._entries[0].item

    def remove(self, item: T) -> bool:
        """
        Remove a specific item from the queue.

        Parameters
        ----------
        item : T
            Item to remove

        Returns
        -------
        bool
            True if item was found and removed
        """
        for entry in self._entries:
            if entry.item is item or entry.item == item:
                self._entries.remove(entry)
                wait_time = self._sim.now - entry.entry_time
                self._stats.record_exit(self._sim.now, wait_time)
                return True
        return False

    def clear(self) -> List[T]:
        """
        Remove all items from the queue.

        Returns
        -------
        List[T]
            List of removed items
        """
        items = list(self._items)
        for item in items:
            self.dequeue()
        return items

    def contains(self, item: T) -> bool:
        """Check if item is in the queue."""
        return any(entry.item is item or entry.item == item for entry in self._entries)

    def on_enqueue(self, callback: Callable[[T], None]) -> None:
        """Set callback for enqueue events."""
        self._on_enqueue = callback

    def on_dequeue(self, callback: Callable[[T], None]) -> None:
        """Set callback for dequeue events."""
        self._on_dequeue = callback

    def reset_stats(self) -> None:
        """Reset statistics (keep items)."""
        self._stats.reset()
        self._stats._current_length = len(self._entries)

    def __iter__(self) -> Iterator[T]:
        """Iterate over items in queue order."""
        return (entry.item for entry in self._entries)

    def __repr__(self) -> str:
        """Return detailed representation."""
        return (
            f"Queue(name={self._name!r}, length={len(self)}, "
            f"capacity={self._capacity})"
        )


@dataclass(order=True)
class PriorityItem(Generic[T]):
    """Wrapper for priority queue items."""

    priority: float
    index: int = field(compare=True)
    item: T = field(compare=False)
    entry_time: float = field(compare=False, default=0.0)


class PriorityQueue(Generic[T]):
    """
    Priority queue with statistics collection.

    Items are dequeued in order of priority (lower value = higher priority).

    Parameters
    ----------
    sim : Simulation
        Parent simulation for time tracking
    priority_fn : Optional[Callable[[T], float]]
        Function to extract priority from items (default uses 0)
    capacity : int
        Maximum queue capacity (0 = unlimited)
    name : str
        Optional name for the queue

    Examples
    --------
    >>> queue = PriorityQueue(sim, priority_fn=lambda x: x.priority)
    >>> queue.enqueue(high_priority_job)
    >>> queue.enqueue(low_priority_job)
    >>> next_job = queue.dequeue()  # Returns high_priority_job
    """

    def __init__(
        self,
        sim: "Simulation",
        priority_fn: Optional[Callable[[T], float]] = None,
        capacity: int = 0,
        name: str = "",
    ) -> None:
        """Initialize priority queue."""
        self._sim = sim
        self._priority_fn = priority_fn or (lambda x: 0.0)
        self._capacity = capacity
        self._name = name or f"PriorityQueue_{id(self)}"

        self._heap: List[PriorityItem[T]] = []
        self._counter = 0
        self._stats = QueueStats()

    @property
    def name(self) -> str:
        """Get queue name."""
        return self._name

    @property
    def stats(self) -> QueueStats:
        """Get queue statistics."""
        return self._stats

    @property
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self._heap) == 0

    @property
    def is_full(self) -> bool:
        """Check if queue is at capacity."""
        if self._capacity == 0:
            return False
        return len(self._heap) >= self._capacity

    def __len__(self) -> int:
        """Get current queue length."""
        return len(self._heap)

    def enqueue(self, item: T, priority: Optional[float] = None) -> bool:
        """
        Add item to the queue.

        Parameters
        ----------
        item : T
            Item to add
        priority : Optional[float]
            Override priority (uses priority_fn if not specified)

        Returns
        -------
        bool
            True if item was added, False if queue is full
        """
        if self.is_full:
            return False

        if priority is None:
            priority = self._priority_fn(item)

        self._counter += 1
        entry = PriorityItem(
            priority=priority,
            index=self._counter,
            item=item,
            entry_time=self._sim.now,
        )

        heapq.heappush(self._heap, entry)
        self._stats.record_entry(self._sim.now)

        return True

    def dequeue(self) -> Optional[T]:
        """
        Remove and return the highest priority item.

        Returns
        -------
        Optional[T]
            Highest priority item or None if empty
        """
        if self.is_empty:
            return None

        entry = heapq.heappop(self._heap)

        wait_time = self._sim.now - entry.entry_time
        self._stats.record_exit(self._sim.now, wait_time)

        return entry.item

    def peek(self) -> Optional[T]:
        """
        Return the highest priority item without removing it.

        Returns
        -------
        Optional[T]
            Highest priority item or None if empty
        """
        if self.is_empty:
            return None
        return self._heap[0].item

    def _find_entry(self, item: T) -> Optional[PriorityItem[T]]:
        """Find the first entry matching the item."""
        for entry in self._heap:
            if entry.item is item or entry.item == item:
                return entry
        return None

    def remove(self, item: T) -> bool:
        """
        Remove a specific item from the queue.

        Parameters
        ----------
        item : T
            Item to remove

        Returns
        -------
        bool
            True if item was found and removed
        """
        entry = self._find_entry(item)
        if entry is None:
            return False

        self._heap.remove(entry)
        heapq.heapify(self._heap)

        wait_time = self._sim.now - entry.entry_time
        self._stats.record_exit(self._sim.now, wait_time)

        return True

    def update_priority(self, item: T, new_priority: float) -> bool:
        """
        Update the priority of an item.

        Parameters
        ----------
        item : T
            Item to update
        new_priority : float
            New priority value

        Returns
        -------
        bool
            True if item was found and updated
        """
        entry = self._find_entry(item)
        if entry is None:
            return False

        self._heap.remove(entry)

        self._counter += 1
        new_entry = PriorityItem(
            priority=new_priority,
            index=self._counter,
            item=item,
            entry_time=entry.entry_time,
        )

        heapq.heappush(self._heap, new_entry)

        return True

    def __repr__(self) -> str:
        """Return detailed representation."""
        return (
            f"PriorityQueue(name={self._name!r}, length={len(self)}, "
            f"capacity={self._capacity})"
        )
