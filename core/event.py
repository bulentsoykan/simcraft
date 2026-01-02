"""
Event class for discrete event simulation.

Events are the fundamental unit of simulation execution.
Each event represents a state change that occurs at a specific time.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Optional, Tuple
from functools import total_ordering

if TYPE_CHECKING:
    from simcraft.core.simulation import Simulation


@total_ordering
@dataclass
class Event:
    """
    A discrete event scheduled for future execution.

    Events are ordered by their scheduled time, with ties broken by
    their sequence index to ensure deterministic execution order.

    Attributes
    ----------
    scheduled_time : float
        The simulation time at which this event should be executed
    action : Callable
        The function to call when the event is executed
    args : tuple
        Positional arguments to pass to the action
    kwargs : dict
        Keyword arguments to pass to the action
    owner : Simulation
        The simulation that scheduled this event
    index : int
        Unique sequence number for tie-breaking
    tag : str
        Optional tag for event identification and filtering
    priority : int
        Priority level (higher = executed first at same time)
    cancelled : bool
        Whether this event has been cancelled

    Examples
    --------
    >>> def handle_arrival(customer_id: int):
    ...     print(f"Customer {customer_id} arrived")
    ...
    >>> event = Event(
    ...     scheduled_time=10.0,
    ...     action=handle_arrival,
    ...     args=(1,),
    ...     index=0
    ... )
    >>> event.invoke()
    Customer 1 arrived
    """

    scheduled_time: float
    action: Callable[..., Any]
    args: Tuple[Any, ...] = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    owner: Optional["Simulation"] = None
    index: int = 0
    tag: str = ""
    priority: int = 0
    cancelled: bool = False

    def invoke(self) -> Any:
        """
        Execute the event action.

        Returns
        -------
        Any
            The return value of the action, if any

        Notes
        -----
        Cancelled events will not execute and return None.
        """
        if self.cancelled:
            return None
        return self.action(*self.args, **self.kwargs)

    def cancel(self) -> None:
        """
        Cancel this event.

        The event will remain in the event list but will not
        execute when its scheduled time is reached.
        """
        self.cancelled = True

    def __eq__(self, other: object) -> bool:
        """Check equality based on time, priority, and index."""
        if not isinstance(other, Event):
            return NotImplemented
        return (
            self.scheduled_time == other.scheduled_time
            and self.priority == other.priority
            and self.index == other.index
        )

    def __lt__(self, other: object) -> bool:
        """
        Compare events for ordering.

        Events are ordered by:
        1. Scheduled time (ascending)
        2. Priority (descending - higher priority first)
        3. Index (ascending - first scheduled first)
        """
        if not isinstance(other, Event):
            return NotImplemented

        if self.scheduled_time != other.scheduled_time:
            return self.scheduled_time < other.scheduled_time

        if self.priority != other.priority:
            return self.priority > other.priority  # Higher priority first

        return self.index < other.index

    def __hash__(self) -> int:
        """Hash based on unique identifiers."""
        return hash((self.scheduled_time, self.priority, self.index, id(self)))

    def __str__(self) -> str:
        """Return human-readable representation."""
        action_name = getattr(self.action, "__name__", repr(self.action))
        status = " [CANCELLED]" if self.cancelled else ""
        tag_str = f" [{self.tag}]" if self.tag else ""
        return f"Event(t={self.scheduled_time:.4f}, {action_name}{tag_str}{status})"

    def __repr__(self) -> str:
        """Return detailed representation."""
        return (
            f"Event(scheduled_time={self.scheduled_time}, "
            f"action={self.action.__name__ if hasattr(self.action, '__name__') else self.action}, "
            f"index={self.index}, priority={self.priority}, "
            f"cancelled={self.cancelled})"
        )


@dataclass
class ConditionalEvent:
    """
    An event that executes only when a condition is met.

    Useful for events that depend on system state.

    Attributes
    ----------
    condition : Callable[[], bool]
        Function that returns True when event should execute
    action : Callable
        The function to call when condition is met
    check_interval : float
        How often to check the condition
    max_attempts : int
        Maximum number of condition checks (0 = unlimited)
    """

    condition: Callable[[], bool]
    action: Callable[..., Any]
    args: Tuple[Any, ...] = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    check_interval: float = 0.1
    max_attempts: int = 0
    _attempt_count: int = field(default=0, repr=False)

    def check_and_execute(self) -> bool:
        """
        Check condition and execute if met.

        Returns
        -------
        bool
            True if condition was met and action executed
        """
        self._attempt_count += 1
        if self.condition():
            self.action(*self.args, **self.kwargs)
            return True

        if self.max_attempts > 0 and self._attempt_count >= self.max_attempts:
            return True  # Stop checking

        return False


class EventList:
    """
    Efficient container for managing scheduled events.

    Uses sortedcontainers.SortedList for O(log n) insertion
    and O(1) minimum extraction.

    Examples
    --------
    >>> events = EventList()
    >>> events.add(Event(scheduled_time=5.0, action=lambda: None, index=0))
    >>> events.add(Event(scheduled_time=3.0, action=lambda: None, index=1))
    >>> next_event = events.pop_next()
    >>> print(next_event.scheduled_time)
    3.0
    """

    def __init__(self) -> None:
        """Initialize empty event list."""
        try:
            from sortedcontainers import SortedList

            self._events: Any = SortedList()
        except ImportError:
            import heapq

            self._events = []
            self._use_heap = True
        else:
            self._use_heap = False

    def add(self, event: Event) -> None:
        """
        Add an event to the list.

        Parameters
        ----------
        event : Event
            The event to schedule
        """
        if self._use_heap:
            import heapq

            heapq.heappush(self._events, event)
        else:
            self._events.add(event)

    def pop_next(self) -> Optional[Event]:
        """
        Remove and return the next event.

        Returns
        -------
        Optional[Event]
            The next event to execute, or None if list is empty
        """
        if not self._events:
            return None

        if self._use_heap:
            import heapq

            return heapq.heappop(self._events)
        else:
            return self._events.pop(0)

    def peek_next(self) -> Optional[Event]:
        """
        Return the next event without removing it.

        Returns
        -------
        Optional[Event]
            The next event, or None if list is empty
        """
        if not self._events:
            return None
        return self._events[0]

    def remove(self, event: Event) -> bool:
        """
        Remove a specific event from the list.

        Parameters
        ----------
        event : Event
            The event to remove

        Returns
        -------
        bool
            True if event was found and removed
        """
        try:
            if self._use_heap:
                self._events.remove(event)
                import heapq

                heapq.heapify(self._events)
            else:
                self._events.remove(event)
            return True
        except ValueError:
            return False

    def clear(self) -> None:
        """Remove all events from the list."""
        if self._use_heap:
            self._events = []
        else:
            self._events.clear()

    def __len__(self) -> int:
        """Return number of events in the list."""
        return len(self._events)

    def __bool__(self) -> bool:
        """Return True if list is not empty."""
        return bool(self._events)

    def __iter__(self):
        """Iterate over events in scheduled order."""
        return iter(sorted(self._events) if self._use_heap else self._events)
