"""
Statistics and monitoring for simulation.

This module provides components for collecting and analyzing
simulation performance data:
- Counter: Count events
- Tally: Collect discrete observations
- TimeSeries: Time-weighted statistics (HourCounter equivalent)
- Monitor: General purpose data collector
"""

from simcraft.statistics.counter import Counter
from simcraft.statistics.tally import Tally
from simcraft.statistics.time_series import TimeSeries
from simcraft.statistics.monitor import Monitor

__all__ = ["Counter", "Tally", "TimeSeries", "Monitor"]
