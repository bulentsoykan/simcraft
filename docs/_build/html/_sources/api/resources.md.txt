# Resources Module

Resource management components for modeling limited resources, servers, and queues.

## Server

Multi-server processing stations with automatic queue management.

```{eval-rst}
.. autoclass:: simcraft.Server
   :members:
   :undoc-members:
   :show-inheritance:
```

```{eval-rst}
.. autoclass:: simcraft.resources.server.ServerStats
   :members:
   :undoc-members:
```

```{eval-rst}
.. autoclass:: simcraft.resources.server.ServerState
   :members:
   :undoc-members:
```

```{eval-rst}
.. autoclass:: simcraft.resources.server.MultiStageServer
   :members:
   :undoc-members:
   :show-inheritance:
```

## Queue

FIFO and priority queues with statistics collection.

```{eval-rst}
.. autoclass:: simcraft.Queue
   :members:
   :undoc-members:
   :show-inheritance:
```

```{eval-rst}
.. autoclass:: simcraft.resources.queue.QueueStats
   :members:
   :undoc-members:
```

```{eval-rst}
.. autoclass:: simcraft.resources.queue.PriorityQueue
   :members:
   :undoc-members:
   :show-inheritance:
```

## Resource

Seizable resources with acquire/release semantics.

```{eval-rst}
.. autoclass:: simcraft.Resource
   :members:
   :undoc-members:
   :show-inheritance:
```

```{eval-rst}
.. autoclass:: simcraft.resources.resource.ResourceStats
   :members:
   :undoc-members:
```

```{eval-rst}
.. autoclass:: simcraft.resources.resource.ResourceState
   :members:
   :undoc-members:
```

```{eval-rst}
.. autoclass:: simcraft.resources.resource.PreemptiveResource
   :members:
   :undoc-members:
   :show-inheritance:
```

## Resource Pool

Pools of distinguishable resources.

```{eval-rst}
.. autoclass:: simcraft.ResourcePool
   :members:
   :undoc-members:
   :show-inheritance:
```

```{eval-rst}
.. autoclass:: simcraft.resources.pool.PooledResource
   :members:
   :undoc-members:
```

```{eval-rst}
.. autoclass:: simcraft.resources.pool.PoolStats
   :members:
   :undoc-members:
```

```{eval-rst}
.. autoclass:: simcraft.resources.pool.PoolSelectionPolicy
   :members:
   :undoc-members:
```
