"""
Monitor for general-purpose data collection and analysis.

Provides a flexible interface for recording simulation data
and generating reports.
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

from simcraft.statistics.counter import Counter
from simcraft.statistics.tally import Tally
from simcraft.statistics.time_series import TimeSeries

if TYPE_CHECKING:
    from simcraft.core.simulation import Simulation


class Monitor:
    """
    General-purpose data collection and monitoring.

    Provides a unified interface for tracking counters, tallies,
    and time series, with support for data export and reporting.

    Parameters
    ----------
    sim : Simulation
        Parent simulation
    name : str
        Monitor name

    Examples
    --------
    >>> monitor = Monitor(sim, name="performance")
    >>>
    >>> # Add collectors
    >>> monitor.add_counter("arrivals")
    >>> monitor.add_tally("service_time")
    >>> monitor.add_time_series("queue_length")
    >>>
    >>> # Record data
    >>> monitor.counters["arrivals"].increment()
    >>> monitor.tallies["service_time"].observe(5.2)
    >>> monitor.time_series["queue_length"].observe_change(1)
    >>>
    >>> # Get report
    >>> report = monitor.report()
    """

    def __init__(
        self,
        sim: "Simulation",
        name: str = "",
    ) -> None:
        """Initialize monitor."""
        self._sim = sim
        self._name = name or f"Monitor_{id(self)}"

        self._counters: Dict[str, Counter] = {}
        self._tallies: Dict[str, Tally] = {}
        self._time_series: Dict[str, TimeSeries] = {}

        # Custom metrics
        self._custom_metrics: Dict[str, Callable[[], Any]] = {}

        # Event log
        self._events: List[Tuple[float, str, Any]] = []
        self._log_events = False

    @property
    def name(self) -> str:
        """Get monitor name."""
        return self._name

    @property
    def counters(self) -> Dict[str, Counter]:
        """Get all counters."""
        return self._counters

    @property
    def tallies(self) -> Dict[str, Tally]:
        """Get all tallies."""
        return self._tallies

    @property
    def time_series(self) -> Dict[str, TimeSeries]:
        """Get all time series."""
        return self._time_series

    def add_counter(self, name: str) -> Counter:
        """
        Add a counter.

        Parameters
        ----------
        name : str
            Counter name

        Returns
        -------
        Counter
            The created counter
        """
        counter = Counter(name=name, _sim=self._sim)
        self._counters[name] = counter
        return counter

    def add_tally(
        self,
        name: str,
        keep_history: bool = False,
    ) -> Tally:
        """
        Add a tally.

        Parameters
        ----------
        name : str
            Tally name
        keep_history : bool
            Whether to store observations

        Returns
        -------
        Tally
            The created tally
        """
        tally = Tally(name=name, keep_history=keep_history, _sim=self._sim)
        self._tallies[name] = tally
        return tally

    def add_time_series(
        self,
        name: str,
        initial_value: float = 0.0,
        keep_history: bool = False,
    ) -> TimeSeries:
        """
        Add a time series.

        Parameters
        ----------
        name : str
            Time series name
        initial_value : float
            Initial value
        keep_history : bool
            Whether to store history

        Returns
        -------
        TimeSeries
            The created time series
        """
        ts = TimeSeries(
            sim=self._sim,
            name=name,
            initial_value=initial_value,
            keep_history=keep_history,
        )
        self._time_series[name] = ts
        return ts

    def add_custom_metric(
        self,
        name: str,
        calculator: Callable[[], Any],
    ) -> None:
        """
        Add a custom metric.

        Parameters
        ----------
        name : str
            Metric name
        calculator : Callable
            Function that returns the metric value
        """
        self._custom_metrics[name] = calculator

    def get_counter(self, name: str) -> Optional[Counter]:
        """Get counter by name."""
        return self._counters.get(name)

    def get_tally(self, name: str) -> Optional[Tally]:
        """Get tally by name."""
        return self._tallies.get(name)

    def get_time_series(self, name: str) -> Optional[TimeSeries]:
        """Get time series by name."""
        return self._time_series.get(name)

    def enable_event_logging(self) -> None:
        """Enable event logging."""
        self._log_events = True

    def log_event(self, event_type: str, data: Any = None) -> None:
        """
        Log an event.

        Parameters
        ----------
        event_type : str
            Type of event
        data : Any
            Event data
        """
        if self._log_events:
            self._events.append((self._sim.now, event_type, data))

    def get_events(
        self,
        event_type: Optional[str] = None,
    ) -> List[Tuple[float, str, Any]]:
        """
        Get logged events.

        Parameters
        ----------
        event_type : Optional[str]
            Filter by event type

        Returns
        -------
        List[Tuple[float, str, Any]]
            List of (time, type, data) tuples
        """
        if event_type is None:
            return self._events.copy()
        return [(t, e, d) for t, e, d in self._events if e == event_type]

    def report(self) -> Dict[str, Any]:
        """
        Generate a summary report.

        Returns
        -------
        Dict[str, Any]
            Dictionary with all statistics
        """
        report = {
            "simulation_time": self._sim.now,
            "counters": {},
            "tallies": {},
            "time_series": {},
            "custom_metrics": {},
        }

        for name, counter in self._counters.items():
            report["counters"][name] = {
                "value": counter.value,
                "rate": counter.rate,
            }

        for name, tally in self._tallies.items():
            report["tallies"][name] = tally.summary()

        for name, ts in self._time_series.items():
            report["time_series"][name] = ts.summary()

        for name, calculator in self._custom_metrics.items():
            try:
                report["custom_metrics"][name] = calculator()
            except Exception as e:
                report["custom_metrics"][name] = f"Error: {e}"

        return report

    def reset(self) -> None:
        """Reset all statistics."""
        for counter in self._counters.values():
            counter.reset()
        for tally in self._tallies.values():
            tally.reset()
        for ts in self._time_series.values():
            ts.reset()
        self._events.clear()

    def to_json(self, indent: int = 2) -> str:
        """
        Export report as JSON.

        Parameters
        ----------
        indent : int
            JSON indentation

        Returns
        -------
        str
            JSON string
        """
        return json.dumps(self.report(), indent=indent, default=str)

    def to_dataframe(self) -> Any:
        """
        Export time series data as pandas DataFrame.

        Returns
        -------
        pd.DataFrame
            DataFrame with time series data

        Raises
        ------
        ImportError
            If pandas is not available
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required for to_dataframe()")

        data = {}
        for name, ts in self._time_series.items():
            if ts._keep_history:
                history = ts.get_history()
                data[f"{name}_time"] = [t for t, _ in history]
                data[f"{name}_value"] = [v for _, v in history]

        return pd.DataFrame(data)

    def __repr__(self) -> str:
        """Return detailed representation."""
        return (
            f"Monitor(name={self._name!r}, "
            f"counters={len(self._counters)}, "
            f"tallies={len(self._tallies)}, "
            f"time_series={len(self._time_series)})"
        )


class SimulationRecorder:
    """
    Records simulation state at regular intervals.

    Useful for generating time-series plots and animations.

    Parameters
    ----------
    sim : Simulation
        Parent simulation
    interval : float
        Recording interval
    """

    def __init__(
        self,
        sim: "Simulation",
        interval: float = 1.0,
    ) -> None:
        """Initialize recorder."""
        self._sim = sim
        self._interval = interval
        self._records: List[Dict[str, Any]] = []
        self._collectors: Dict[str, Callable[[], Any]] = {}
        self._is_recording = False

    def add_collector(self, name: str, collector: Callable[[], Any]) -> None:
        """
        Add a data collector.

        Parameters
        ----------
        name : str
            Data series name
        collector : Callable
            Function that returns the current value
        """
        self._collectors[name] = collector

    def start(self) -> None:
        """Start recording."""
        self._is_recording = True
        self._schedule_next()

    def stop(self) -> None:
        """Stop recording."""
        self._is_recording = False

    def _schedule_next(self) -> None:
        """Schedule next recording."""
        if self._is_recording:
            self._record()
            self._sim.schedule(self._schedule_next, delay=self._interval)

    def _record(self) -> None:
        """Record current state."""
        record = {"time": self._sim.now}
        for name, collector in self._collectors.items():
            try:
                record[name] = collector()
            except Exception:
                record[name] = None
        self._records.append(record)

    def get_records(self) -> List[Dict[str, Any]]:
        """Get all records."""
        return self._records.copy()

    def to_dataframe(self) -> Any:
        """
        Export records as pandas DataFrame.

        Returns
        -------
        pd.DataFrame
            DataFrame with recorded data
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required for to_dataframe()")

        return pd.DataFrame(self._records)

    def clear(self) -> None:
        """Clear all records."""
        self._records.clear()
