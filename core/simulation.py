"""
Main simulation engine.

The Simulation class is the core of the SimCraft framework,
providing event scheduling, execution, and hierarchical composition.
"""

from __future__ import annotations
import time as wall_time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from enum import Enum, auto
import logging

from simcraft.core.clock import Clock, TimeUnit
from simcraft.core.event import Event, EventList
from simcraft.core.entity import Entity


class SimulationState(Enum):
    """Simulation lifecycle states."""

    CREATED = auto()
    INITIALIZED = auto()
    RUNNING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    TERMINATED = auto()


@dataclass
class SimulationConfig:
    """
    Configuration for simulation execution.

    Attributes
    ----------
    time_unit : TimeUnit
        Base time unit for the simulation
    seed : Optional[int]
        Random seed for reproducibility
    warmup_duration : float
        Duration of warmup period
    max_events : int
        Maximum number of events to process (0 = unlimited)
    real_time_factor : float
        Factor for real-time execution (0 = as fast as possible)
    log_level : int
        Logging verbosity level
    collect_trace : bool
        Whether to collect event execution trace
    """

    time_unit: TimeUnit = TimeUnit.HOURS
    seed: Optional[int] = None
    warmup_duration: float = 0.0
    max_events: int = 0
    real_time_factor: float = 0.0
    log_level: int = logging.WARNING
    collect_trace: bool = False


class Simulation:
    """
    Core discrete event simulation engine.

    The Simulation class provides the fundamental infrastructure for
    discrete event simulation including event scheduling, time advancement,
    hierarchical model composition, and execution control.

    Features
    --------
    - Efficient event scheduling with priority support
    - Hierarchical model composition (parent-child sandboxes)
    - Multiple execution modes (run until, run for, step)
    - Warmup period handling
    - Real-time execution support
    - Event tracing and debugging

    Examples
    --------
    Basic simulation:

    >>> class BankSimulation(Simulation):
    ...     def __init__(self):
    ...         super().__init__()
    ...         self.customers_served = 0
    ...
    ...     def on_init(self):
    ...         self.schedule(self.customer_arrival, delay=0)
    ...
    ...     def customer_arrival(self):
    ...         self.customers_served += 1
    ...         self.schedule(self.customer_arrival,
    ...                       delay=self.rng.exponential(5.0))
    ...
    >>> sim = BankSimulation()
    >>> sim.run(until=100)
    >>> print(f"Served {sim.customers_served} customers")

    Hierarchical composition:

    >>> class Server(Simulation):
    ...     def __init__(self, parent: Simulation):
    ...         super().__init__(parent=parent)
    ...
    >>> class System(Simulation):
    ...     def __init__(self):
    ...         super().__init__()
    ...         self.server1 = Server(parent=self)
    ...         self.server2 = Server(parent=self)
    """

    def __init__(
        self,
        parent: Optional[Simulation] = None,
        config: Optional[SimulationConfig] = None,
        name: str = "",
    ) -> None:
        """
        Initialize simulation.

        Parameters
        ----------
        parent : Optional[Simulation]
            Parent simulation for hierarchical composition
        config : Optional[SimulationConfig]
            Simulation configuration
        name : str
            Optional name for the simulation
        """
        self._parent = parent
        self._children: List[Simulation] = []
        self._config = config or SimulationConfig()
        self._name = name or type(self).__name__

        # State management
        self._state = SimulationState.CREATED
        self._is_root = parent is None

        # Event management
        self._events = EventList()
        self._event_count = 0
        self._processed_count = 0

        # Clock - root owns, children reference parent's
        if self._is_root:
            self._clock = Clock(time_unit=self._config.time_unit)
        else:
            parent._children.append(self)

        # Random number generation
        self._init_rng()

        # Statistics and monitoring
        self._monitors: Dict[str, Any] = {}
        self._trace: List[Tuple[float, str, str]] = []

        # Logging
        self._logger = logging.getLogger(f"simcraft.{self._name}")
        self._logger.setLevel(self._config.log_level)

    def _init_rng(self) -> None:
        """Initialize random number generator."""
        from simcraft.random.distributions import RandomGenerator

        self._rng = RandomGenerator(seed=self._config.seed)

    @property
    def clock(self) -> Clock:
        """Get the simulation clock."""
        if self._is_root:
            return self._clock
        return self._parent.clock

    @property
    def now(self) -> float:
        """Get current simulation time."""
        return self.clock.now

    @property
    def rng(self) -> "RandomGenerator":
        """Get random number generator."""
        return self._rng

    @property
    def name(self) -> str:
        """Get simulation name."""
        return self._name

    @property
    def state(self) -> SimulationState:
        """Get current simulation state."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Check if simulation is currently running."""
        return self._state == SimulationState.RUNNING

    @property
    def is_warmed_up(self) -> bool:
        """Check if warmup period has completed."""
        return self.clock.is_warmed_up

    @property
    def parent(self) -> Optional["Simulation"]:
        """Get parent simulation."""
        return self._parent

    @property
    def root(self) -> "Simulation":
        """Get root simulation."""
        if self._is_root:
            return self
        return self._parent.root

    @property
    def events_pending(self) -> int:
        """Get number of pending events."""
        return len(self._events)

    @property
    def events_processed(self) -> int:
        """Get number of processed events."""
        return self._processed_count

    def schedule(
        self,
        action: Callable[..., Any],
        delay: float = 0.0,
        at: Optional[float] = None,
        args: Tuple[Any, ...] = (),
        kwargs: Optional[Dict[str, Any]] = None,
        tag: str = "",
        priority: int = 0,
    ) -> Event:
        """
        Schedule an event for future execution.

        Parameters
        ----------
        action : Callable
            Function to execute
        delay : float
            Time delay from current time (ignored if 'at' is specified)
        at : Optional[float]
            Absolute simulation time for execution
        args : tuple
            Positional arguments for the action
        kwargs : dict
            Keyword arguments for the action
        tag : str
            Optional tag for event identification
        priority : int
            Priority level (higher = executed first at same time)

        Returns
        -------
        Event
            The scheduled event (can be used for cancellation)

        Examples
        --------
        >>> sim.schedule(process_arrival, delay=5.0)
        >>> sim.schedule(process_arrival, at=sim.now + 5.0)
        >>> sim.schedule(process_arrival, delay=0, priority=10)  # High priority
        """
        if at is not None:
            scheduled_time = at
        else:
            scheduled_time = self.now + delay

        if scheduled_time < self.now:
            self._logger.warning(
                f"Scheduling event in the past: {scheduled_time} < {self.now}"
            )

        self._event_count += 1
        event = Event(
            scheduled_time=scheduled_time,
            action=action,
            args=args,
            kwargs=kwargs or {},
            owner=self,
            index=self._event_count,
            tag=tag,
            priority=priority,
        )

        # Add to root's event list
        self.root._events.add(event)

        self._logger.debug(f"Scheduled: {event}")
        return event

    def cancel_event(self, event: Event) -> bool:
        """
        Cancel a scheduled event.

        Parameters
        ----------
        event : Event
            The event to cancel

        Returns
        -------
        bool
            True if event was successfully cancelled
        """
        event.cancel()
        self._logger.debug(f"Cancelled: {event}")
        return True

    def cancel_events_by_tag(self, tag: str) -> int:
        """
        Cancel all events with a specific tag.

        Parameters
        ----------
        tag : str
            Tag to match

        Returns
        -------
        int
            Number of events cancelled
        """
        count = 0
        for event in self.root._events:
            if event.tag == tag and not event.cancelled:
                event.cancel()
                count += 1
        return count

    def run(
        self,
        until: Optional[float] = None,
        for_duration: Optional[float] = None,
        events: Optional[int] = None,
    ) -> "Simulation":
        """
        Run the simulation.

        Parameters
        ----------
        until : Optional[float]
            Run until this simulation time
        for_duration : Optional[float]
            Run for this duration from current time
        events : Optional[int]
            Run for this many events

        Returns
        -------
        Simulation
            Self for method chaining

        Examples
        --------
        >>> sim.run(until=100)  # Run until time 100
        >>> sim.run(for_duration=50)  # Run for 50 time units
        >>> sim.run(events=1000)  # Run 1000 events
        >>> sim.run()  # Run until no more events
        """
        if not self._is_root:
            raise RuntimeError("Only root simulation can be run directly")

        self._initialize()

        stop_time = None
        if until is not None:
            stop_time = until
        elif for_duration is not None:
            stop_time = self.now + for_duration

        max_events = events or self._config.max_events or 0

        self._state = SimulationState.RUNNING
        self._logger.info(f"Simulation started at time {self.now}")

        try:
            self._execute_loop(stop_time=stop_time, max_events=max_events)
        except KeyboardInterrupt:
            self._logger.info("Simulation interrupted by user")
            self._state = SimulationState.PAUSED
        except Exception as e:
            self._logger.error(f"Simulation error: {e}")
            self._state = SimulationState.TERMINATED
            raise

        if self._state == SimulationState.RUNNING:
            self._state = SimulationState.COMPLETED

        self._finalize()
        self._logger.info(
            f"Simulation ended at time {self.now} "
            f"({self._processed_count} events processed)"
        )

        return self

    def _initialize(self) -> None:
        """Initialize simulation before running."""
        if self._state == SimulationState.CREATED:
            # Set warmup
            if self._config.warmup_duration > 0:
                self.clock.set_warmup(self._config.warmup_duration)

            # Call initialization hooks
            self.on_init()
            for child in self._children:
                child._initialize()

            self._state = SimulationState.INITIALIZED

    def _finalize(self) -> None:
        """Finalize simulation after running."""
        self.on_end()
        for child in self._children:
            child._finalize()

    def _execute_loop(
        self,
        stop_time: Optional[float],
        max_events: int,
    ) -> None:
        """
        Main event processing loop.

        Parameters
        ----------
        stop_time : Optional[float]
            Time at which to stop
        max_events : int
            Maximum events to process (0 = unlimited)
        """
        event_count = 0
        real_time_start = wall_time.time()

        while self._events:
            event = self._events.peek_next()
            if event is None:
                break

            # Check stop conditions
            if stop_time is not None and event.scheduled_time > stop_time:
                self.clock.advance_to(stop_time)
                break

            if max_events > 0 and event_count >= max_events:
                break

            # Pop and process event
            event = self._events.pop_next()

            # Handle real-time execution
            if self._config.real_time_factor > 0:
                self._sync_real_time(
                    event.scheduled_time, real_time_start, self._config.real_time_factor
                )

            # Advance clock
            self.clock.advance_to(event.scheduled_time)

            # Execute event
            if not event.cancelled:
                self._execute_event(event)
                event_count += 1
                self._processed_count += 1

    def _execute_event(self, event: Event) -> None:
        """
        Execute a single event.

        Parameters
        ----------
        event : Event
            The event to execute
        """
        if self._config.collect_trace:
            action_name = getattr(event.action, "__name__", str(event.action))
            self._trace.append((self.now, action_name, event.tag))

        self._logger.debug(f"Executing at {self.now}: {event}")

        try:
            event.invoke()
        except Exception as e:
            self._logger.error(f"Error executing event {event}: {e}")
            raise

    def _sync_real_time(
        self, sim_time: float, real_start: float, factor: float
    ) -> None:
        """Synchronize with wall clock for real-time execution."""
        expected_real_time = real_start + (sim_time - self.now) / factor
        current_real_time = wall_time.time()
        if current_real_time < expected_real_time:
            wall_time.sleep(expected_real_time - current_real_time)

    def step(self) -> bool:
        """
        Execute a single event.

        Returns
        -------
        bool
            True if an event was processed, False if no events remain
        """
        if not self._is_root:
            return self.root.step()

        if self._state == SimulationState.CREATED:
            self._initialize()

        event = self._events.pop_next()
        if event is None:
            return False

        self.clock.advance_to(event.scheduled_time)

        if not event.cancelled:
            self._execute_event(event)
            self._processed_count += 1

        return True

    def warmup(self, duration: Optional[float] = None) -> "Simulation":
        """
        Run warmup period.

        Parameters
        ----------
        duration : Optional[float]
            Warmup duration (uses config value if not specified)

        Returns
        -------
        Simulation
            Self for method chaining
        """
        warmup_time = duration or self._config.warmup_duration
        if warmup_time > 0:
            self.clock.set_warmup(warmup_time)
            self.run(for_duration=warmup_time)
        return self

    def reset(self) -> "Simulation":
        """
        Reset simulation to initial state.

        Returns
        -------
        Simulation
            Self for method chaining
        """
        self._events.clear()
        self.clock.reset()
        self._processed_count = 0
        self._event_count = 0
        self._state = SimulationState.CREATED
        self._trace.clear()

        # Reset children
        for child in self._children:
            child.reset()

        # Reinitialize RNG
        self._init_rng()

        self._logger.info("Simulation reset")
        return self

    def on_init(self) -> None:
        """
        Hook called during initialization.

        Override this method to set up initial events and state.
        """
        pass

    def on_end(self) -> None:
        """
        Hook called when simulation ends.

        Override this method for cleanup and result collection.
        """
        pass

    def on_warmup_end(self) -> None:
        """
        Hook called when warmup period ends.

        Override this method to reset statistics after warmup.
        """
        pass

    def add_monitor(self, name: str, monitor: Any) -> None:
        """
        Register a monitor/statistics collector.

        Parameters
        ----------
        name : str
            Monitor name for retrieval
        monitor : Any
            Monitor instance
        """
        self._monitors[name] = monitor

    def get_monitor(self, name: str) -> Any:
        """
        Get a registered monitor.

        Parameters
        ----------
        name : str
            Monitor name

        Returns
        -------
        Any
            Monitor instance or None
        """
        return self._monitors.get(name)

    def get_trace(self) -> List[Tuple[float, str, str]]:
        """
        Get event execution trace.

        Returns
        -------
        List[Tuple[float, str, str]]
            List of (time, action_name, tag) tuples
        """
        return self._trace.copy()

    def __repr__(self) -> str:
        """Return detailed representation."""
        return (
            f"{type(self).__name__}("
            f"name={self._name!r}, "
            f"time={self.now:.4f}, "
            f"state={self._state.name}, "
            f"events_pending={self.events_pending}, "
            f"events_processed={self._processed_count}"
            f")"
        )

    def __str__(self) -> str:
        """Return human-readable representation."""
        return f"{self._name} @ t={self.now:.4f}"
