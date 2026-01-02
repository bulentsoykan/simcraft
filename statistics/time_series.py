"""
TimeSeries for time-weighted statistics.

Equivalent to HourCounter in O2DES, tracks values that change
over time and calculates time-weighted statistics.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional, Tuple

if TYPE_CHECKING:
    from simcraft.core.simulation import Simulation


class TimeSeries:
    """
    Time-weighted statistics collector (HourCounter equivalent).

    Tracks a value that changes over time and calculates
    time-weighted statistics like average count, utilization,
    and average duration.

    Parameters
    ----------
    sim : Simulation
        Parent simulation for time tracking
    name : str
        Time series name
    initial_value : float
        Initial value
    keep_history : bool
        Whether to store value history

    Examples
    --------
    >>> ts = TimeSeries(sim, name="queue_length")
    >>> ts.observe_change(1)   # Entity enters queue
    >>> ts.observe_change(1)   # Another entity
    >>> # ... time passes ...
    >>> ts.observe_change(-1)  # Entity leaves
    >>> print(ts.average_value)  # Time-weighted average
    >>> print(ts.average_duration)  # Average time per entry
    """

    def __init__(
        self,
        sim: "Simulation",
        name: str = "",
        initial_value: float = 0.0,
        keep_history: bool = False,
    ) -> None:
        """Initialize time series."""
        self._sim = sim
        self._name = name or f"TimeSeries_{id(self)}"
        self._keep_history = keep_history

        # Current state
        self._current_value = initial_value
        self._last_change_time = sim.now

        # Cumulative statistics
        self._cumulative_value = 0.0  # Time-weighted integral
        self._total_increments = 0.0
        self._total_decrements = 0.0
        self._increment_count = 0
        self._decrement_count = 0
        self._start_time = sim.now

        # Min/max tracking
        self._min_value = initial_value
        self._max_value = initial_value

        # Optional history
        self._history: List[Tuple[float, float]] = []
        if keep_history:
            self._history.append((sim.now, initial_value))

    @property
    def name(self) -> str:
        """Get time series name."""
        return self._name

    @property
    def current_value(self) -> float:
        """Get current value."""
        return self._current_value

    @property
    def elapsed_time(self) -> float:
        """Get total elapsed time."""
        return self._sim.now - self._start_time

    @property
    def cumulative_value(self) -> float:
        """Get cumulative time-weighted value."""
        self._update_cumulative()
        return self._cumulative_value

    @property
    def average_value(self) -> float:
        """Get time-weighted average value (average count)."""
        elapsed = self.elapsed_time
        if elapsed == 0:
            return self._current_value
        return self.cumulative_value / elapsed

    @property
    def average_duration(self) -> float:
        """
        Get average duration per entry.

        For counting values (queue length), this gives
        the average time an item spends in the system.
        """
        if self._decrement_count == 0:
            return 0.0
        return self.cumulative_value / self._decrement_count

    @property
    def min_value(self) -> float:
        """Get minimum observed value."""
        return self._min_value

    @property
    def max_value(self) -> float:
        """Get maximum observed value."""
        return self._max_value

    @property
    def increment_rate(self) -> float:
        """Get increment rate (per time unit)."""
        elapsed = self.elapsed_time
        if elapsed == 0:
            return 0.0
        return self._total_increments / elapsed

    @property
    def decrement_rate(self) -> float:
        """Get decrement rate (per time unit)."""
        elapsed = self.elapsed_time
        if elapsed == 0:
            return 0.0
        return self._total_decrements / elapsed

    @property
    def increment_count(self) -> int:
        """Get number of increments."""
        return self._increment_count

    @property
    def decrement_count(self) -> int:
        """Get number of decrements."""
        return self._decrement_count

    @property
    def utilization(self) -> float:
        """
        Get utilization ratio (fraction of time value > 0).

        For capacity tracking, this gives the busy ratio.
        """
        # This is an approximation using average_value
        if self._max_value <= 0:
            return 0.0
        return min(1.0, self.average_value / self._max_value)

    def _update_cumulative(self) -> None:
        """Update cumulative value to current time."""
        duration = self._sim.now - self._last_change_time
        if duration > 0:
            self._cumulative_value += self._current_value * duration
            self._last_change_time = self._sim.now

    def observe_change(self, delta: float) -> float:
        """
        Observe a change in value.

        Parameters
        ----------
        delta : float
            Change amount (positive or negative)

        Returns
        -------
        float
            New value after change
        """
        self._update_cumulative()

        self._current_value += delta

        # Track increments/decrements
        if delta > 0:
            self._total_increments += delta
            self._increment_count += 1
        elif delta < 0:
            self._total_decrements += abs(delta)
            self._decrement_count += 1

        # Update min/max
        self._min_value = min(self._min_value, self._current_value)
        self._max_value = max(self._max_value, self._current_value)

        # Record history
        if self._keep_history:
            self._history.append((self._sim.now, self._current_value))

        return self._current_value

    def observe_value(self, value: float) -> None:
        """
        Set value directly (observe absolute value).

        Parameters
        ----------
        value : float
            New value
        """
        delta = value - self._current_value
        if delta != 0:
            self.observe_change(delta)

    def histogram(
        self,
        bins: int = 10,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
    ) -> List[Tuple[float, float, float]]:
        """
        Calculate time-weighted histogram from history.

        Parameters
        ----------
        bins : int
            Number of bins
        min_val : Optional[float]
            Minimum bin value
        max_val : Optional[float]
            Maximum bin value

        Returns
        -------
        List[Tuple[float, float, float]]
            List of (bin_start, bin_end, time_fraction)

        Raises
        ------
        ValueError
            If history not kept
        """
        if not self._keep_history or len(self._history) < 2:
            raise ValueError("Histogram requires keep_history=True and observations")

        if min_val is None:
            min_val = self._min_value
        if max_val is None:
            max_val = self._max_value

        if min_val == max_val:
            return [(min_val, max_val, 1.0)]

        bin_width = (max_val - min_val) / bins
        bin_times = [0.0] * bins

        for i in range(len(self._history) - 1):
            t1, v1 = self._history[i]
            t2, _ = self._history[i + 1]
            duration = t2 - t1

            # Find bin for this value
            bin_idx = int((v1 - min_val) / bin_width)
            bin_idx = max(0, min(bins - 1, bin_idx))
            bin_times[bin_idx] += duration

        total_time = sum(bin_times)
        if total_time == 0:
            return []

        result = []
        for i in range(bins):
            start = min_val + i * bin_width
            end = start + bin_width
            fraction = bin_times[i] / total_time
            result.append((start, end, fraction))

        return result

    def percentile(self, p: float) -> float:
        """
        Calculate time-weighted percentile from history.

        Parameters
        ----------
        p : float
            Percentile (0-100)

        Returns
        -------
        float
            Percentile value
        """
        if not self._keep_history or len(self._history) < 2:
            raise ValueError("Percentile requires keep_history=True")

        # Create time-weighted value distribution
        weighted_values = []
        for i in range(len(self._history) - 1):
            t1, v1 = self._history[i]
            t2, _ = self._history[i + 1]
            duration = t2 - t1
            weighted_values.append((v1, duration))

        # Sort by value
        weighted_values.sort(key=lambda x: x[0])

        # Find percentile
        total_time = sum(d for _, d in weighted_values)
        target = total_time * p / 100

        cumulative = 0.0
        for value, duration in weighted_values:
            cumulative += duration
            if cumulative >= target:
                return value

        return weighted_values[-1][0] if weighted_values else 0.0

    def get_history(self) -> List[Tuple[float, float]]:
        """
        Get value history.

        Returns
        -------
        List[Tuple[float, float]]
            List of (time, value) tuples
        """
        return self._history.copy()

    def reset(self, initial_value: float = 0.0) -> None:
        """
        Reset statistics.

        Parameters
        ----------
        initial_value : float
            New initial value
        """
        self._current_value = initial_value
        self._last_change_time = self._sim.now
        self._cumulative_value = 0.0
        self._total_increments = 0.0
        self._total_decrements = 0.0
        self._increment_count = 0
        self._decrement_count = 0
        self._start_time = self._sim.now
        self._min_value = initial_value
        self._max_value = initial_value
        self._history.clear()
        if self._keep_history:
            self._history.append((self._sim.now, initial_value))

    def summary(self) -> dict:
        """
        Get summary statistics.

        Returns
        -------
        dict
            Dictionary of statistics
        """
        return {
            "current_value": self._current_value,
            "average_value": self.average_value,
            "average_duration": self.average_duration,
            "min_value": self._min_value,
            "max_value": self._max_value,
            "elapsed_time": self.elapsed_time,
            "increment_count": self._increment_count,
            "decrement_count": self._decrement_count,
            "utilization": self.utilization,
        }

    def __repr__(self) -> str:
        """Return detailed representation."""
        return (
            f"TimeSeries(name={self._name!r}, "
            f"current={self._current_value}, "
            f"average={self.average_value:.4f})"
        )


class CapacityTimeSeries(TimeSeries):
    """
    TimeSeries specialized for capacity tracking.

    Tracks busy/idle states for a resource with fixed capacity.

    Parameters
    ----------
    sim : Simulation
        Parent simulation
    capacity : int
        Total capacity
    name : str
        Time series name
    """

    def __init__(
        self,
        sim: "Simulation",
        capacity: int,
        name: str = "",
    ) -> None:
        """Initialize capacity time series."""
        super().__init__(sim, name=name, initial_value=0.0)
        self._capacity = capacity

    @property
    def capacity(self) -> int:
        """Get total capacity."""
        return self._capacity

    @property
    def available(self) -> int:
        """Get available capacity."""
        return max(0, self._capacity - int(self._current_value))

    @property
    def utilization(self) -> float:
        """Get utilization ratio."""
        if self._capacity == 0:
            return 0.0
        return self.average_value / self._capacity

    @property
    def is_busy(self) -> bool:
        """Check if all capacity is in use."""
        return self._current_value >= self._capacity

    @property
    def is_idle(self) -> bool:
        """Check if no capacity is in use."""
        return self._current_value == 0

    def acquire(self, amount: int = 1) -> bool:
        """
        Acquire capacity.

        Parameters
        ----------
        amount : int
            Amount to acquire

        Returns
        -------
        bool
            True if successful
        """
        if self._current_value + amount > self._capacity:
            return False
        self.observe_change(amount)
        return True

    def release(self, amount: int = 1) -> bool:
        """
        Release capacity.

        Parameters
        ----------
        amount : int
            Amount to release

        Returns
        -------
        bool
            True if successful
        """
        if self._current_value - amount < 0:
            return False
        self.observe_change(-amount)
        return True
