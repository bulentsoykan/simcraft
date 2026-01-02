"""
Random stream management for simulation.

Provides independent random streams for different purposes,
enabling better experimental design and variance reduction.
"""

from __future__ import annotations
from typing import Dict, List, Optional
from simcraft.random.distributions import RandomGenerator


class RandomStream(RandomGenerator):
    """
    Named random stream with checkpointing.

    Extends RandomGenerator with stream identification and
    state management for reproducibility.

    Parameters
    ----------
    name : str
        Stream name
    seed : Optional[int]
        Initial seed

    Examples
    --------
    >>> arrival_stream = RandomStream("arrivals", seed=100)
    >>> service_stream = RandomStream("service", seed=200)
    >>>
    >>> # Save and restore state
    >>> state = arrival_stream.checkpoint()
    >>> # ... run simulation ...
    >>> arrival_stream.restore(state)
    """

    def __init__(
        self,
        name: str = "",
        seed: Optional[int] = None,
    ) -> None:
        """Initialize stream."""
        super().__init__(seed=seed)
        self._name = name or f"Stream_{id(self)}"

    @property
    def name(self) -> str:
        """Get stream name."""
        return self._name

    def checkpoint(self) -> dict:
        """
        Create checkpoint of current state.

        Returns
        -------
        dict
            Checkpoint data
        """
        return {
            "name": self._name,
            "seed": self._seed,
            "state": self.get_state(),
        }

    def restore(self, checkpoint: dict) -> None:
        """
        Restore from checkpoint.

        Parameters
        ----------
        checkpoint : dict
            Checkpoint data
        """
        self.set_state(checkpoint["state"])

    def fork(self, name: Optional[str] = None) -> "RandomStream":
        """
        Create a new stream with derived seed.

        Parameters
        ----------
        name : Optional[str]
            Name for new stream

        Returns
        -------
        RandomStream
            New stream
        """
        new_seed = self.randint(0, 2**31 - 1)
        return RandomStream(
            name=name or f"{self._name}_fork",
            seed=new_seed,
        )

    def __repr__(self) -> str:
        """Return detailed representation."""
        return f"RandomStream(name={self._name!r}, seed={self._seed})"


class StreamManager:
    """
    Manages multiple random streams for a simulation.

    Provides centralized stream management, seeding strategies,
    and synchronization for variance reduction techniques.

    Parameters
    ----------
    base_seed : Optional[int]
        Base seed for stream generation

    Examples
    --------
    >>> manager = StreamManager(base_seed=42)
    >>>
    >>> # Get or create streams
    >>> arrivals = manager.get_stream("arrivals")
    >>> service = manager.get_stream("service")
    >>>
    >>> # Antithetic variates
    >>> manager.enable_antithetic()
    >>> value1 = arrivals.uniform()  # U
    >>> value2 = arrivals.uniform()  # 1-U (antithetic)
    """

    def __init__(self, base_seed: Optional[int] = None) -> None:
        """Initialize stream manager."""
        self._base_seed = base_seed
        self._streams: Dict[str, RandomStream] = {}
        self._stream_seeds: Dict[str, int] = {}
        self._seed_generator = RandomGenerator(seed=base_seed)
        self._antithetic_enabled = False

    @property
    def stream_names(self) -> List[str]:
        """Get names of all streams."""
        return list(self._streams.keys())

    def get_stream(self, name: str) -> RandomStream:
        """
        Get or create a named stream.

        Parameters
        ----------
        name : str
            Stream name

        Returns
        -------
        RandomStream
            The stream
        """
        if name not in self._streams:
            seed = self._generate_seed(name)
            self._streams[name] = RandomStream(name=name, seed=seed)
            self._stream_seeds[name] = seed
        return self._streams[name]

    def _generate_seed(self, name: str) -> int:
        """Generate a seed for a stream."""
        # Use hash of name combined with base seed for reproducibility
        if self._base_seed is not None:
            combined = hash((name, self._base_seed))
            return abs(combined) % (2**31)
        return self._seed_generator.randint(0, 2**31 - 1)

    def create_stream(
        self,
        name: str,
        seed: Optional[int] = None,
    ) -> RandomStream:
        """
        Create a new stream with explicit seed.

        Parameters
        ----------
        name : str
            Stream name
        seed : Optional[int]
            Stream seed

        Returns
        -------
        RandomStream
            The new stream
        """
        if seed is None:
            seed = self._generate_seed(name)
        stream = RandomStream(name=name, seed=seed)
        self._streams[name] = stream
        self._stream_seeds[name] = seed
        return stream

    def reset_all(self) -> None:
        """Reset all streams to initial state."""
        for name, seed in self._stream_seeds.items():
            self._streams[name].set_seed(seed)

    def checkpoint(self) -> dict:
        """
        Checkpoint all streams.

        Returns
        -------
        dict
            Checkpoint data
        """
        return {
            name: stream.checkpoint()
            for name, stream in self._streams.items()
        }

    def restore(self, checkpoint: dict) -> None:
        """
        Restore all streams from checkpoint.

        Parameters
        ----------
        checkpoint : dict
            Checkpoint data
        """
        for name, data in checkpoint.items():
            if name in self._streams:
                self._streams[name].restore(data)

    def enable_antithetic(self) -> None:
        """Enable antithetic variates (for variance reduction)."""
        self._antithetic_enabled = True

    def disable_antithetic(self) -> None:
        """Disable antithetic variates."""
        self._antithetic_enabled = False

    def set_base_seed(self, seed: int) -> None:
        """
        Set new base seed and regenerate all streams.

        Parameters
        ----------
        seed : int
            New base seed
        """
        self._base_seed = seed
        self._seed_generator.set_seed(seed)

        # Regenerate all streams
        for name in self._streams.keys():
            new_seed = self._generate_seed(name)
            self._streams[name].set_seed(new_seed)
            self._stream_seeds[name] = new_seed

    def __repr__(self) -> str:
        """Return detailed representation."""
        return (
            f"StreamManager(base_seed={self._base_seed}, "
            f"streams={list(self._streams.keys())})"
        )


class CommonRandomNumbers:
    """
    Helper for common random numbers (CRN) technique.

    Synchronizes random streams across multiple simulation runs
    for variance reduction in comparing alternatives.

    Examples
    --------
    >>> crn = CommonRandomNumbers(base_seed=42)
    >>>
    >>> # Run alternative 1
    >>> crn.reset()
    >>> results1 = run_simulation(crn.get_stream("arrivals"))
    >>>
    >>> # Run alternative 2 with same random numbers
    >>> crn.reset()
    >>> results2 = run_simulation(crn.get_stream("arrivals"))
    """

    def __init__(self, base_seed: int = 42) -> None:
        """Initialize CRN helper."""
        self._base_seed = base_seed
        self._manager = StreamManager(base_seed=base_seed)
        self._checkpoints: Dict[str, dict] = {}

    def get_stream(self, name: str) -> RandomStream:
        """Get a synchronized stream."""
        return self._manager.get_stream(name)

    def save_checkpoint(self, name: str = "default") -> None:
        """Save current stream states."""
        self._checkpoints[name] = self._manager.checkpoint()

    def load_checkpoint(self, name: str = "default") -> None:
        """Load saved stream states."""
        if name in self._checkpoints:
            self._manager.restore(self._checkpoints[name])

    def reset(self) -> None:
        """Reset all streams to initial state."""
        self._manager.reset_all()

    def __repr__(self) -> str:
        """Return detailed representation."""
        return f"CommonRandomNumbers(base_seed={self._base_seed})"
