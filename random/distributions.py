"""
Random variate generators for simulation.

Provides a comprehensive set of probability distributions
commonly used in discrete event simulation.
"""

from __future__ import annotations
import math
import random
from typing import Any, List, Optional, Sequence, Tuple, TypeVar

T = TypeVar("T")


class RandomGenerator:
    """
    Random variate generator with common distributions.

    Wraps Python's random module with additional distributions
    and seeding capabilities for reproducible simulations.

    Parameters
    ----------
    seed : Optional[int]
        Random seed for reproducibility

    Examples
    --------
    >>> rng = RandomGenerator(seed=42)
    >>> service_time = rng.exponential(5.0)
    >>> batch_size = rng.poisson(10)
    >>> priority = rng.choice([1, 2, 3], weights=[0.5, 0.3, 0.2])
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        """Initialize generator."""
        self._rng = random.Random(seed)
        self._seed = seed

    @property
    def seed(self) -> Optional[int]:
        """Get initial seed."""
        return self._seed

    def set_seed(self, seed: int) -> None:
        """
        Set new seed.

        Parameters
        ----------
        seed : int
            New seed value
        """
        self._seed = seed
        self._rng.seed(seed)

    def get_state(self) -> tuple:
        """Get current RNG state for checkpointing."""
        return self._rng.getstate()

    def set_state(self, state: tuple) -> None:
        """Restore RNG state from checkpoint."""
        self._rng.setstate(state)

    # Continuous distributions

    def uniform(self, a: float = 0.0, b: float = 1.0) -> float:
        """
        Uniform distribution U(a, b).

        Parameters
        ----------
        a : float
            Lower bound
        b : float
            Upper bound

        Returns
        -------
        float
            Random value in [a, b]
        """
        return self._rng.uniform(a, b)

    def exponential(self, mean: float) -> float:
        """
        Exponential distribution.

        Parameters
        ----------
        mean : float
            Mean (1/rate)

        Returns
        -------
        float
            Random exponential value
        """
        if mean <= 0:
            raise ValueError("Mean must be positive")
        return self._rng.expovariate(1.0 / mean)

    def normal(self, mean: float = 0.0, std: float = 1.0) -> float:
        """
        Normal (Gaussian) distribution.

        Parameters
        ----------
        mean : float
            Mean
        std : float
            Standard deviation

        Returns
        -------
        float
            Random normal value
        """
        return self._rng.gauss(mean, std)

    def lognormal(self, mean: float, std: float) -> float:
        """
        Log-normal distribution.

        Parameters
        ----------
        mean : float
            Mean of underlying normal
        std : float
            Standard deviation of underlying normal

        Returns
        -------
        float
            Random log-normal value
        """
        return self._rng.lognormvariate(mean, std)

    def triangular(
        self,
        low: float,
        high: float,
        mode: Optional[float] = None,
    ) -> float:
        """
        Triangular distribution.

        Parameters
        ----------
        low : float
            Minimum value
        high : float
            Maximum value
        mode : Optional[float]
            Most likely value (default: midpoint)

        Returns
        -------
        float
            Random triangular value
        """
        if mode is None:
            mode = (low + high) / 2
        return self._rng.triangular(low, high, mode)

    def gamma(self, shape: float, scale: float) -> float:
        """
        Gamma distribution.

        Parameters
        ----------
        shape : float
            Shape parameter (k)
        scale : float
            Scale parameter (theta)

        Returns
        -------
        float
            Random gamma value
        """
        return self._rng.gammavariate(shape, scale)

    def erlang(self, k: int, mean: float) -> float:
        """
        Erlang distribution (integer shape gamma).

        Parameters
        ----------
        k : int
            Shape parameter (number of phases)
        mean : float
            Mean of distribution

        Returns
        -------
        float
            Random Erlang value
        """
        scale = mean / k
        return self.gamma(k, scale)

    def beta(self, alpha: float, beta: float) -> float:
        """
        Beta distribution.

        Parameters
        ----------
        alpha : float
            Alpha parameter
        beta : float
            Beta parameter

        Returns
        -------
        float
            Random beta value in [0, 1]
        """
        return self._rng.betavariate(alpha, beta)

    def weibull(self, shape: float, scale: float) -> float:
        """
        Weibull distribution.

        Parameters
        ----------
        shape : float
            Shape parameter (k)
        scale : float
            Scale parameter (lambda)

        Returns
        -------
        float
            Random Weibull value
        """
        return scale * self._rng.weibullvariate(1.0, shape)

    def pareto(self, alpha: float, xm: float = 1.0) -> float:
        """
        Pareto distribution.

        Parameters
        ----------
        alpha : float
            Shape parameter
        xm : float
            Scale parameter (minimum value)

        Returns
        -------
        float
            Random Pareto value
        """
        return xm * self._rng.paretovariate(alpha)

    # Discrete distributions

    def randint(self, a: int, b: int) -> int:
        """
        Uniform integer distribution.

        Parameters
        ----------
        a : int
            Lower bound (inclusive)
        b : int
            Upper bound (inclusive)

        Returns
        -------
        int
            Random integer in [a, b]
        """
        return self._rng.randint(a, b)

    def poisson(self, lam: float) -> int:
        """
        Poisson distribution.

        Parameters
        ----------
        lam : float
            Rate parameter (expected value)

        Returns
        -------
        int
            Random Poisson value
        """
        # Use inverse transform method
        if lam <= 0:
            return 0

        L = math.exp(-lam)
        k = 0
        p = 1.0

        while p > L:
            k += 1
            p *= self._rng.random()

        return k - 1

    def geometric(self, p: float) -> int:
        """
        Geometric distribution (number of trials until first success).

        Parameters
        ----------
        p : float
            Success probability

        Returns
        -------
        int
            Number of trials (>= 1)
        """
        if p <= 0 or p > 1:
            raise ValueError("p must be in (0, 1]")
        return int(math.ceil(math.log(1 - self._rng.random()) / math.log(1 - p)))

    def binomial(self, n: int, p: float) -> int:
        """
        Binomial distribution.

        Parameters
        ----------
        n : int
            Number of trials
        p : float
            Success probability

        Returns
        -------
        int
            Number of successes
        """
        successes = 0
        for _ in range(n):
            if self._rng.random() < p:
                successes += 1
        return successes

    def negative_binomial(self, r: int, p: float) -> int:
        """
        Negative binomial distribution.

        Number of failures before r successes.

        Parameters
        ----------
        r : int
            Number of successes required
        p : float
            Success probability

        Returns
        -------
        int
            Number of failures
        """
        failures = 0
        successes = 0
        while successes < r:
            if self._rng.random() < p:
                successes += 1
            else:
                failures += 1
        return failures

    # Selection and sampling

    def choice(
        self,
        population: Sequence[T],
        weights: Optional[Sequence[float]] = None,
    ) -> T:
        """
        Random selection from population.

        Parameters
        ----------
        population : Sequence[T]
            Items to choose from
        weights : Optional[Sequence[float]]
            Selection weights

        Returns
        -------
        T
            Selected item
        """
        if weights is None:
            return self._rng.choice(population)
        return self._rng.choices(population, weights=weights, k=1)[0]

    def choices(
        self,
        population: Sequence[T],
        weights: Optional[Sequence[float]] = None,
        k: int = 1,
    ) -> List[T]:
        """
        Random selection with replacement.

        Parameters
        ----------
        population : Sequence[T]
            Items to choose from
        weights : Optional[Sequence[float]]
            Selection weights
        k : int
            Number of selections

        Returns
        -------
        List[T]
            Selected items
        """
        return self._rng.choices(population, weights=weights, k=k)

    def sample(self, population: Sequence[T], k: int) -> List[T]:
        """
        Random sample without replacement.

        Parameters
        ----------
        population : Sequence[T]
            Items to sample from
        k : int
            Sample size

        Returns
        -------
        List[T]
            Sampled items
        """
        return self._rng.sample(population, k)

    def shuffle(self, x: List[T]) -> None:
        """
        Shuffle list in place.

        Parameters
        ----------
        x : List[T]
            List to shuffle
        """
        self._rng.shuffle(x)

    def shuffled(self, x: Sequence[T]) -> List[T]:
        """
        Return shuffled copy.

        Parameters
        ----------
        x : Sequence[T]
            Sequence to shuffle

        Returns
        -------
        List[T]
            Shuffled copy
        """
        result = list(x)
        self._rng.shuffle(result)
        return result

    # Empirical distributions

    def empirical(
        self,
        values: Sequence[float],
        probabilities: Sequence[float],
    ) -> float:
        """
        Empirical discrete distribution.

        Parameters
        ----------
        values : Sequence[float]
            Possible values
        probabilities : Sequence[float]
            Probabilities (must sum to 1)

        Returns
        -------
        float
            Selected value
        """
        return self.choice(values, weights=probabilities)

    def empirical_continuous(
        self,
        breakpoints: Sequence[float],
        probabilities: Sequence[float],
    ) -> float:
        """
        Empirical continuous distribution (piecewise linear).

        Parameters
        ----------
        breakpoints : Sequence[float]
            Breakpoint values
        probabilities : Sequence[float]
            Cumulative probabilities at breakpoints

        Returns
        -------
        float
            Interpolated value
        """
        u = self._rng.random()

        for i in range(len(probabilities) - 1):
            if u <= probabilities[i + 1]:
                # Linear interpolation
                p_range = probabilities[i + 1] - probabilities[i]
                if p_range == 0:
                    return breakpoints[i]
                t = (u - probabilities[i]) / p_range
                return breakpoints[i] + t * (breakpoints[i + 1] - breakpoints[i])

        return breakpoints[-1]

    # Special simulation distributions

    def interarrival_time(
        self,
        rate: float,
        time_unit: float = 1.0,
    ) -> float:
        """
        Generate interarrival time for Poisson process.

        Parameters
        ----------
        rate : float
            Arrival rate per time unit
        time_unit : float
            Time unit scale

        Returns
        -------
        float
            Time until next arrival
        """
        mean = time_unit / rate
        return self.exponential(mean)

    def service_time(
        self,
        mean: float,
        cv: float = 1.0,
    ) -> float:
        """
        Generate service time with specified coefficient of variation.

        Uses gamma distribution to achieve target CV.

        Parameters
        ----------
        mean : float
            Mean service time
        cv : float
            Coefficient of variation (std/mean, default 1.0 = exponential)

        Returns
        -------
        float
            Service time
        """
        if cv <= 0:
            return mean

        if cv == 1.0:
            return self.exponential(mean)

        # Gamma distribution with shape k = 1/cv^2
        shape = 1.0 / (cv * cv)
        scale = mean / shape
        return self.gamma(shape, scale)

    def bernoulli(self, p: float) -> bool:
        """
        Bernoulli trial.

        Parameters
        ----------
        p : float
            Success probability

        Returns
        -------
        bool
            True with probability p
        """
        return self._rng.random() < p

    def __repr__(self) -> str:
        """Return detailed representation."""
        return f"RandomGenerator(seed={self._seed})"


class LCG:
    """
    Linear Congruential Generator (for compatibility).

    Implements the LCG from the WSC challenges for reproducibility.

    Parameters
    ----------
    seed : int
        Initial seed

    Examples
    --------
    >>> lcg = LCG(seed=12345)
    >>> value = lcg.uniform()
    """

    # LCG parameters (same as WSC challenges)
    MULTIPLIER = 1103515245
    INCREMENT = 12345
    MODULUS = 2**31

    def __init__(self, seed: int) -> None:
        """Initialize LCG."""
        self._state = seed

    @property
    def state(self) -> int:
        """Get current state."""
        return self._state

    def _next(self) -> int:
        """Generate next value."""
        self._state = (
            self._state * self.MULTIPLIER + self.INCREMENT
        ) % self.MODULUS
        return self._state

    def uniform(self) -> float:
        """Generate uniform [0, 1)."""
        return self._next() / self.MODULUS

    def exponential(self, mean: float) -> float:
        """Generate exponential with given mean."""
        u = self.uniform()
        if u == 0:
            u = 1e-10
        return -mean * math.log(u)

    def __repr__(self) -> str:
        """Return detailed representation."""
        return f"LCG(state={self._state})"
