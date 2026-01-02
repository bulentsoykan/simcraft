"""
Logging utilities for simulation.

Provides structured logging for simulation events and debugging.
"""

from __future__ import annotations
import logging
import sys
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from simcraft.core.simulation import Simulation


def setup_logging(
    level: int = logging.INFO,
    format_string: Optional[str] = None,
    filename: Optional[str] = None,
) -> None:
    """
    Set up logging for simulation.

    Parameters
    ----------
    level : int
        Logging level
    format_string : Optional[str]
        Custom format string
    filename : Optional[str]
        Log file path
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    handlers = []

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(logging.Formatter(format_string))
    handlers.append(console)

    # File handler
    if filename:
        file_handler = logging.FileHandler(filename)
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(format_string))
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(level=level, handlers=handlers, format=format_string)


class SimulationLogger:
    """
    Logger for simulation events.

    Provides structured logging with simulation time stamps.

    Parameters
    ----------
    sim : Simulation
        Parent simulation
    name : str
        Logger name
    level : int
        Logging level

    Examples
    --------
    >>> logger = SimulationLogger(sim, "MyModel")
    >>> logger.info("Customer arrived")
    >>> logger.debug("Queue length: %d", queue.length)
    """

    def __init__(
        self,
        sim: "Simulation",
        name: str = "",
        level: int = logging.INFO,
    ) -> None:
        """Initialize logger."""
        self._sim = sim
        self._name = name or "Simulation"
        self._logger = logging.getLogger(f"simcraft.{self._name}")
        self._logger.setLevel(level)

    def _format_message(self, message: str) -> str:
        """Add simulation time to message."""
        return f"[t={self._sim.now:.4f}] {message}"

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log debug message."""
        self._logger.debug(self._format_message(message), *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log info message."""
        self._logger.info(self._format_message(message), *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log warning message."""
        self._logger.warning(self._format_message(message), *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log error message."""
        self._logger.error(self._format_message(message), *args, **kwargs)

    def event(
        self,
        event_type: str,
        entity_id: Optional[str] = None,
        **details: Any,
    ) -> None:
        """
        Log a structured simulation event.

        Parameters
        ----------
        event_type : str
            Type of event (e.g., "arrival", "departure")
        entity_id : Optional[str]
            Entity identifier
        **details
            Additional event details
        """
        parts = [f"[t={self._sim.now:.4f}]", event_type]

        if entity_id:
            parts.append(f"entity={entity_id}")

        for key, value in details.items():
            parts.append(f"{key}={value}")

        self._logger.info(" ".join(parts))

    def set_level(self, level: int) -> None:
        """Set logging level."""
        self._logger.setLevel(level)
