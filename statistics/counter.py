"""
Counter for counting discrete events.

Simple counter with rate calculation and reset capabilities.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from simcraft.core.simulation import Simulation


@dataclass
class Counter:
    """
    Counter for discrete events.

    Tracks the number of occurrences and calculates rates.

    Parameters
    ----------
    sim : Optional[Simulation]
        Parent simulation for rate calculations
    name : str
        Counter name

    Examples
    --------
    >>> counter = Counter(sim, name="arrivals")
    >>> counter.increment()
    >>> counter.increment(5)
    >>> print(counter.value)
    6
    >>> print(counter.rate)  # per time unit
    """

    name: str = ""
    _value: int = field(default=0, repr=False)
    _start_time: float = field(default=0.0, repr=False)
    _sim: Optional["Simulation"] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Initialize counter."""
        if self._sim:
            self._start_time = self._sim.now

    @property
    def value(self) -> int:
        """Get current count."""
        return self._value

    @property
    def elapsed_time(self) -> float:
        """Get elapsed time since start/reset."""
        if self._sim is None:
            return 0.0
        return self._sim.now - self._start_time

    @property
    def rate(self) -> float:
        """Get rate (count per time unit)."""
        elapsed = self.elapsed_time
        if elapsed == 0:
            return 0.0
        return self._value / elapsed

    def increment(self, amount: int = 1) -> int:
        """
        Increment the counter.

        Parameters
        ----------
        amount : int
            Amount to increment by

        Returns
        -------
        int
            New counter value
        """
        self._value += amount
        return self._value

    def decrement(self, amount: int = 1) -> int:
        """
        Decrement the counter.

        Parameters
        ----------
        amount : int
            Amount to decrement by

        Returns
        -------
        int
            New counter value
        """
        self._value -= amount
        return self._value

    def reset(self) -> None:
        """Reset counter to zero."""
        self._value = 0
        if self._sim:
            self._start_time = self._sim.now

    def __int__(self) -> int:
        """Convert to int."""
        return self._value

    def __repr__(self) -> str:
        """Return detailed representation."""
        return f"Counter(name={self.name!r}, value={self._value}, rate={self.rate:.4f})"


class WindowedCounter:
    """
    Counter that tracks values over a sliding time window.

    Useful for calculating rates over recent time periods.

    Parameters
    ----------
    sim : Simulation
        Parent simulation
    window_size : float
        Size of sliding window in time units
    name : str
        Counter name

    Examples
    --------
    >>> counter = WindowedCounter(sim, window_size=60.0, name="arrivals_per_hour")
    >>> counter.increment()
    >>> # ... time passes ...
    >>> print(counter.window_rate)  # Rate over last 60 time units
    """

    def __init__(
        self,
        sim: "Simulation",
        window_size: float,
        name: str = "",
    ) -> None:
        """Initialize windowed counter."""
        self._sim = sim
        self._window_size = window_size
        self._name = name or f"WindowedCounter_{id(self)}"

        self._events: list = []  # List of (time, amount)
        self._total = 0

    @property
    def name(self) -> str:
        """Get counter name."""
        return self._name

    @property
    def window_size(self) -> float:
        """Get window size."""
        return self._window_size

    def _prune_old_events(self) -> None:
        """Remove events outside the window."""
        cutoff = self._sim.now - self._window_size
        while self._events and self._events[0][0] < cutoff:
            _, amount = self._events.pop(0)
            self._total -= amount

    def increment(self, amount: int = 1) -> None:
        """
        Increment the counter.

        Parameters
        ----------
        amount : int
            Amount to increment by
        """
        self._prune_old_events()
        self._events.append((self._sim.now, amount))
        self._total += amount

    @property
    def window_count(self) -> int:
        """Get count within the window."""
        self._prune_old_events()
        return self._total

    @property
    def window_rate(self) -> float:
        """Get rate within the window (count per time unit)."""
        self._prune_old_events()
        if self._window_size == 0:
            return 0.0
        return self._total / self._window_size

    def reset(self) -> None:
        """Reset the counter."""
        self._events.clear()
        self._total = 0

    def __repr__(self) -> str:
        """Return detailed representation."""
        return (
            f"WindowedCounter(name={self._name!r}, "
            f"window={self._window_size}, count={self.window_count})"
        )
