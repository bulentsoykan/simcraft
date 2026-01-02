# Statistics Module

Data collection and analysis components for simulation output.

## Counter

Event counting with rate calculation.

```{eval-rst}
.. autoclass:: simcraft.Counter
   :members:
   :undoc-members:
   :show-inheritance:
```

```{eval-rst}
.. autoclass:: simcraft.statistics.counter.WindowedCounter
   :members:
   :undoc-members:
   :show-inheritance:
```

## Tally

Discrete observation collector with statistical analysis using Welford's algorithm.

```{eval-rst}
.. autoclass:: simcraft.Tally
   :members:
   :undoc-members:
   :show-inheritance:
```

```{eval-rst}
.. autoclass:: simcraft.statistics.tally.BatchTally
   :members:
   :undoc-members:
   :show-inheritance:
```

## TimeSeries

Time-weighted statistics collection (equivalent to O2DES HourCounter).

```{eval-rst}
.. autoclass:: simcraft.TimeSeries
   :members:
   :undoc-members:
   :show-inheritance:
```

```{eval-rst}
.. autoclass:: simcraft.statistics.time_series.CapacityTimeSeries
   :members:
   :undoc-members:
   :show-inheritance:
```

## Monitor

Unified data collection with multiple metric types.

```{eval-rst}
.. autoclass:: simcraft.Monitor
   :members:
   :undoc-members:
   :show-inheritance:
```

```{eval-rst}
.. autoclass:: simcraft.statistics.monitor.SimulationRecorder
   :members:
   :undoc-members:
   :show-inheritance:
```
