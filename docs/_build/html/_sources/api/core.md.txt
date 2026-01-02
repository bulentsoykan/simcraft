# Core Module

The core module contains the fundamental building blocks for discrete event simulation.

## Simulation

The main simulation engine with event scheduling and hierarchical composition.

```{eval-rst}
.. autoclass:: simcraft.Simulation
   :members:
   :undoc-members:
   :show-inheritance:
```

```{eval-rst}
.. autoclass:: simcraft.core.simulation.SimulationConfig
   :members:
   :undoc-members:
```

```{eval-rst}
.. autoclass:: simcraft.core.simulation.SimulationState
   :members:
   :undoc-members:
```

## Event

Event management and scheduling.

```{eval-rst}
.. autoclass:: simcraft.core.event.Event
   :members:
   :undoc-members:
   :show-inheritance:
```

```{eval-rst}
.. autoclass:: simcraft.core.event.ConditionalEvent
   :members:
   :undoc-members:
   :show-inheritance:
```

```{eval-rst}
.. autoclass:: simcraft.core.event.EventList
   :members:
   :undoc-members:
```

## Entity

Simulation entities with lifecycle tracking.

```{eval-rst}
.. autoclass:: simcraft.Entity
   :members:
   :undoc-members:
   :show-inheritance:
```

```{eval-rst}
.. autoclass:: simcraft.TimedEntity
   :members:
   :undoc-members:
   :show-inheritance:
```

```{eval-rst}
.. autoclass:: simcraft.core.entity.EntityState
   :members:
   :undoc-members:
```

```{eval-rst}
.. autoclass:: simcraft.core.entity.EntityFactory
   :members:
   :undoc-members:
```

```{eval-rst}
.. autoclass:: simcraft.core.entity.EntityPool
   :members:
   :undoc-members:
```

## Clock

Simulation time management.

```{eval-rst}
.. autoclass:: simcraft.core.clock.Clock
   :members:
   :undoc-members:
```

```{eval-rst}
.. autoclass:: simcraft.core.clock.TimeUnit
   :members:
   :undoc-members:
```
