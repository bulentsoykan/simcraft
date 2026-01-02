"""
Tally for collecting discrete observations.

Collects individual observations and provides statistical summaries.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional, Tuple

if TYPE_CHECKING:
    from simcraft.core.simulation import Simulation


@dataclass
class Tally:
    """
    Collects discrete observations and calculates statistics.

    Efficiently calculates running statistics without storing
    all observations (unless keep_history is True).

    Parameters
    ----------
    sim : Optional[Simulation]
        Parent simulation
    name : str
        Tally name
    keep_history : bool
        Whether to store all observations

    Examples
    --------
    >>> tally = Tally(name="service_time")
    >>> for time in service_times:
    ...     tally.observe(time)
    >>> print(tally.mean, tally.std)
    """

    name: str = ""
    keep_history: bool = False
    _sim: Optional["Simulation"] = field(default=None, repr=False)

    # Running statistics (Welford's algorithm)
    _count: int = field(default=0, repr=False)
    _mean: float = field(default=0.0, repr=False)
    _m2: float = field(default=0.0, repr=False)  # Sum of squared deviations
    _min: float = field(default=float("inf"), repr=False)
    _max: float = field(default=float("-inf"), repr=False)
    _sum: float = field(default=0.0, repr=False)

    # Optional history
    _history: List[Tuple[float, float]] = field(default_factory=list, repr=False)

    @property
    def count(self) -> int:
        """Get number of observations."""
        return self._count

    @property
    def sum(self) -> float:
        """Get sum of observations."""
        return self._sum

    @property
    def mean(self) -> float:
        """Get mean of observations."""
        return self._mean

    @property
    def variance(self) -> float:
        """Get sample variance."""
        if self._count < 2:
            return 0.0
        return self._m2 / (self._count - 1)

    @property
    def std(self) -> float:
        """Get sample standard deviation."""
        return math.sqrt(self.variance)

    @property
    def min(self) -> float:
        """Get minimum observation."""
        if self._count == 0:
            return 0.0
        return self._min

    @property
    def max(self) -> float:
        """Get maximum observation."""
        if self._count == 0:
            return 0.0
        return self._max

    @property
    def range(self) -> float:
        """Get range (max - min)."""
        if self._count == 0:
            return 0.0
        return self._max - self._min

    def observe(self, value: float) -> None:
        """
        Record an observation.

        Parameters
        ----------
        value : float
            Observed value
        """
        self._count += 1
        self._sum += value

        # Welford's online algorithm for variance
        delta = value - self._mean
        self._mean += delta / self._count
        delta2 = value - self._mean
        self._m2 += delta * delta2

        # Update min/max
        self._min = min(self._min, value)
        self._max = max(self._max, value)

        # Store history if requested
        if self.keep_history:
            time = self._sim.now if self._sim else 0.0
            self._history.append((time, value))

    def observe_batch(self, values: List[float]) -> None:
        """
        Record multiple observations.

        Parameters
        ----------
        values : List[float]
            Observed values
        """
        for value in values:
            self.observe(value)

    def percentile(self, p: float) -> float:
        """
        Calculate percentile from stored history.

        Parameters
        ----------
        p : float
            Percentile (0-100)

        Returns
        -------
        float
            Percentile value

        Raises
        ------
        ValueError
            If history not kept or empty
        """
        if not self.keep_history or not self._history:
            raise ValueError("Percentile requires keep_history=True and observations")

        values = sorted(v for _, v in self._history)
        k = (len(values) - 1) * p / 100
        f = math.floor(k)
        c = math.ceil(k)

        if f == c:
            return values[int(k)]

        return values[int(f)] * (c - k) + values[int(c)] * (k - f)

    def confidence_interval(self, confidence: float = 0.95) -> Tuple[float, float]:
        """
        Calculate confidence interval for the mean.

        Parameters
        ----------
        confidence : float
            Confidence level (e.g., 0.95 for 95%)

        Returns
        -------
        Tuple[float, float]
            (lower, upper) confidence bounds
        """
        if self._count < 2:
            return (self._mean, self._mean)

        # t-distribution critical value approximation
        # Using normal approximation for large samples
        import math

        alpha = 1 - confidence
        if self._count >= 30:
            # Normal approximation
            z = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}.get(confidence, 1.96)
        else:
            # Rough t-distribution approximation
            z = 2.0 + 0.5 * (30 - self._count) / 30

        se = self.std / math.sqrt(self._count)
        margin = z * se

        return (self._mean - margin, self._mean + margin)

    def get_history(self) -> List[Tuple[float, float]]:
        """
        Get observation history.

        Returns
        -------
        List[Tuple[float, float]]
            List of (time, value) tuples
        """
        return self._history.copy()

    def reset(self) -> None:
        """Reset all statistics."""
        self._count = 0
        self._mean = 0.0
        self._m2 = 0.0
        self._min = float("inf")
        self._max = float("-inf")
        self._sum = 0.0
        self._history.clear()

    def summary(self) -> dict:
        """
        Get summary statistics.

        Returns
        -------
        dict
            Dictionary of statistics
        """
        return {
            "count": self._count,
            "mean": self.mean,
            "std": self.std,
            "min": self.min,
            "max": self.max,
            "sum": self._sum,
        }

    def __repr__(self) -> str:
        """Return detailed representation."""
        return (
            f"Tally(name={self.name!r}, count={self._count}, "
            f"mean={self.mean:.4f}, std={self.std:.4f})"
        )


class BatchTally(Tally):
    """
    Tally that groups observations into batches for analysis.

    Useful for batch means analysis and detecting initialization bias.

    Parameters
    ----------
    batch_size : int
        Number of observations per batch
    name : str
        Tally name
    """

    def __init__(
        self,
        batch_size: int = 100,
        name: str = "",
        sim: Optional["Simulation"] = None,
    ) -> None:
        """Initialize batch tally."""
        super().__init__(name=name, _sim=sim)
        self._batch_size = batch_size
        self._current_batch: List[float] = []
        self._batch_means: List[float] = []

    @property
    def batch_count(self) -> int:
        """Get number of completed batches."""
        return len(self._batch_means)

    @property
    def batch_means(self) -> List[float]:
        """Get list of batch means."""
        return self._batch_means.copy()

    def observe(self, value: float) -> None:
        """Record an observation."""
        super().observe(value)
        self._current_batch.append(value)

        if len(self._current_batch) >= self._batch_size:
            batch_mean = sum(self._current_batch) / len(self._current_batch)
            self._batch_means.append(batch_mean)
            self._current_batch.clear()

    def batch_variance(self) -> float:
        """
        Calculate variance of batch means.

        Useful for estimating variance of the overall mean.
        """
        if len(self._batch_means) < 2:
            return 0.0

        mean_of_means = sum(self._batch_means) / len(self._batch_means)
        ss = sum((m - mean_of_means) ** 2 for m in self._batch_means)
        return ss / (len(self._batch_means) - 1)

    def reset(self) -> None:
        """Reset all statistics."""
        super().reset()
        self._current_batch.clear()
        self._batch_means.clear()
