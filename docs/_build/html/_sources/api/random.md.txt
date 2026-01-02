# Random Module

Random variate generation and stream management for reproducible simulations.

## RandomGenerator

Primary random number generator with 20+ distributions.

```{eval-rst}
.. autoclass:: simcraft.RandomGenerator
   :members:
   :undoc-members:
   :show-inheritance:
```

## Stream Management

Named streams with checkpointing for variance reduction techniques.

```{eval-rst}
.. autoclass:: simcraft.random.streams.RandomStream
   :members:
   :undoc-members:
```

```{eval-rst}
.. autoclass:: simcraft.random.streams.StreamManager
   :members:
   :undoc-members:
```

```{eval-rst}
.. autoclass:: simcraft.random.streams.CommonRandomNumbers
   :members:
   :undoc-members:
```

## Alternative Generators

```{eval-rst}
.. autoclass:: simcraft.random.distributions.LCG
   :members:
   :undoc-members:
```
