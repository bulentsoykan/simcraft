"""
Simulation clock for time management.

The Clock class provides centralized time tracking for the simulation,
supporting various time units and warmup period handling.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class TimeUnit(Enum):
    """Enumeration of supported time units."""

    SECONDS = "seconds"
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"

    def to_hours(self, value: float) -> float:
        """Convert value in this unit to hours."""
        multipliers = {
            TimeUnit.SECONDS: 1 / 3600,
            TimeUnit.MINUTES: 1 / 60,
            TimeUnit.HOURS: 1.0,
            TimeUnit.DAYS: 24.0,
        }
        return value * multipliers[self]

    def from_hours(self, hours: float) -> float:
        """Convert hours to this time unit."""
        divisors = {
            TimeUnit.SECONDS: 1 / 3600,
            TimeUnit.MINUTES: 1 / 60,
            TimeUnit.HOURS: 1.0,
            TimeUnit.DAYS: 24.0,
        }
        return hours / divisors[self]


@dataclass
class Clock:
    """
    Simulation clock for centralized time management.

    The clock tracks the current simulation time, warmup status,
    and provides utilities for time conversion and formatting.

    Attributes
    ----------
    now : float
        Current simulation time in the base time unit (hours by default)
    time_unit : TimeUnit
        The base time unit for the simulation
    start_datetime : Optional[datetime]
        Optional real-world start time for datetime mapping
    warmup_end : float
        Time at which warmup period ends (statistics start being collected)
    is_warmed_up : bool
        Whether the simulation has completed its warmup period

    Examples
    --------
    >>> clock = Clock()
    >>> clock.advance(1.5)  # Advance 1.5 hours
    >>> print(clock.now)
    1.5
    >>> print(clock.now_in(TimeUnit.MINUTES))
    90.0
    """

    now: float = 0.0
    time_unit: TimeUnit = TimeUnit.HOURS
    start_datetime: Optional[datetime] = None
    warmup_end: float = 0.0
    _initial_time: float = field(default=0.0, repr=False)

    def __post_init__(self) -> None:
        """Initialize internal state."""
        self._initial_time = self.now

    @property
    def is_warmed_up(self) -> bool:
        """Check if simulation has passed warmup period."""
        return self.now >= self.warmup_end

    @property
    def elapsed(self) -> float:
        """Get total elapsed simulation time."""
        return self.now - self._initial_time

    @property
    def elapsed_since_warmup(self) -> float:
        """Get elapsed time since warmup ended."""
        if not self.is_warmed_up:
            return 0.0
        return self.now - self.warmup_end

    def advance(self, delta: float) -> None:
        """
        Advance the clock by a time delta.

        Parameters
        ----------
        delta : float
            Time to advance in base time units
        """
        if delta < 0:
            raise ValueError("Cannot advance clock by negative time")
        self.now += delta

    def advance_to(self, time: float) -> None:
        """
        Advance the clock to a specific time.

        Parameters
        ----------
        time : float
            Target time in base time units

        Raises
        ------
        ValueError
            If target time is before current time
        """
        if time < self.now:
            raise ValueError(f"Cannot move clock backwards from {self.now} to {time}")
        self.now = time

    def now_in(self, unit: TimeUnit) -> float:
        """
        Get current time in specified units.

        Parameters
        ----------
        unit : TimeUnit
            Target time unit

        Returns
        -------
        float
            Current time converted to specified unit
        """
        hours = self.time_unit.to_hours(self.now)
        return unit.from_hours(hours)

    def convert(self, value: float, from_unit: TimeUnit, to_unit: TimeUnit) -> float:
        """
        Convert time value between units.

        Parameters
        ----------
        value : float
            Time value to convert
        from_unit : TimeUnit
            Source time unit
        to_unit : TimeUnit
            Target time unit

        Returns
        -------
        float
            Converted time value
        """
        hours = from_unit.to_hours(value)
        return to_unit.from_hours(hours)

    @property
    def datetime_now(self) -> Optional[datetime]:
        """
        Get current simulation time as real-world datetime.

        Returns None if start_datetime is not set.
        """
        if self.start_datetime is None:
            return None
        hours = self.time_unit.to_hours(self.now)
        return self.start_datetime + timedelta(hours=hours)

    def set_warmup(self, duration: float) -> None:
        """
        Set warmup period duration from current time.

        Parameters
        ----------
        duration : float
            Warmup duration in base time units
        """
        self.warmup_end = self.now + duration

    def reset(self) -> None:
        """Reset clock to initial state."""
        self.now = self._initial_time
        self.warmup_end = 0.0

    def __str__(self) -> str:
        """Return string representation of current time."""
        if self.start_datetime:
            return f"Clock(now={self.now:.4f} {self.time_unit.value}, datetime={self.datetime_now})"
        return f"Clock(now={self.now:.4f} {self.time_unit.value})"

    def __repr__(self) -> str:
        """Return detailed representation."""
        return (
            f"Clock(now={self.now}, time_unit={self.time_unit}, "
            f"warmup_end={self.warmup_end}, is_warmed_up={self.is_warmed_up})"
        )
