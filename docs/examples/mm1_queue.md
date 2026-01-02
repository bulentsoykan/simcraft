# M/M/1 Queue Example

A classic single-server queueing system with theoretical validation.

## Overview

The M/M/1 queue is the simplest queueing model:

- **M**: Markovian (Poisson) arrivals
- **M**: Markovian (exponential) service times
- **1**: Single server

This example demonstrates:

- Basic event scheduling
- Server resource usage
- Statistics collection (Tally, TimeSeries)
- Comparison with theoretical values

## Queueing Theory Background

For an M/M/1 queue with arrival rate λ and service rate μ:

- **Utilization**: ρ = λ/μ
- **Average queue length**: Lq = ρ² / (1 - ρ)
- **Average wait time**: Wq = ρ / (μ(1 - ρ))
- **Average system time**: W = 1 / (μ(1 - ρ))

The system is stable when ρ < 1.

## Code Walkthrough

### Customer Entity

```python
from dataclasses import dataclass
from simcraft.core.entity import TimedEntity


@dataclass
class Customer(TimedEntity):
    """A customer in the queueing system."""
    priority: int = 0
```

The `TimedEntity` base class provides automatic timing:
- `record_entry(time)`: Mark arrival time
- `record_service_start(time)`: Mark when service begins
- `record_exit(time)`: Mark departure time
- `waiting_time`: Time from entry to service start
- `flow_time`: Total time in system

### Simulation Class

```python
class MM1Queue(Simulation):
    def __init__(
        self,
        arrival_rate: float = 0.8,
        service_rate: float = 1.0,
    ) -> None:
        super().__init__(name="MM1Queue")

        self.arrival_rate = arrival_rate
        self.service_rate = service_rate
        self.rho = arrival_rate / service_rate

        # Create server with exponential service time
        self.server = Server(
            sim=self,
            capacity=1,
            service_time=lambda: self.rng.exponential(1.0 / self.service_rate),
        )

        # Statistics
        self.queue_length = TimeSeries(self, name="QueueLength")
        self.wait_times = Tally(name="WaitTime")
        self.system_times = Tally(name="SystemTime")

        # Set up callbacks
        self.server.on_service_start(self._on_service_start)
        self.server.on_departure(self._on_departure)
```

### Event Handlers

```python
def on_init(self) -> None:
    """Schedule first arrival."""
    self.schedule(self._arrival, delay=0)

def _arrival(self) -> None:
    """Handle customer arrival."""
    customer = Customer()
    customer.record_entry(self.now)

    # Track queue length
    self.queue_length.observe_change(1)

    # Enter server queue
    self.server.enqueue(customer)

    # Schedule next arrival (exponential interarrival)
    interarrival = self.rng.exponential(1.0 / self.arrival_rate)
    self.schedule(self._arrival, delay=interarrival)

def _on_service_start(self, customer: Customer) -> None:
    """Record wait time when service begins."""
    customer.record_service_start(self.now)
    self.wait_times.observe(customer.waiting_time)

def _on_departure(self, customer: Customer) -> None:
    """Record system time when customer leaves."""
    customer.record_exit(self.now)
    self.queue_length.observe_change(-1)
    self.system_times.observe(customer.flow_time)
```

## Running the Example

```python
from simcraft.examples.mm1_queue import MM1Queue

# Create simulation with ρ = 0.8
sim = MM1Queue(arrival_rate=0.8, service_rate=1.0)

# Run for 10,000 time units
sim.run(until=10000)

# Get results
report = sim.report()
print(f"Simulation queue length: {report['simulation_results']['average_queue_length']:.4f}")
print(f"Theoretical queue length: {report['theoretical_values']['average_queue_length']:.4f}")
```

## Sample Output

```
M/M/1 Queue Simulation
============================================================

Parameters:
  arrival_rate: 0.8000
  service_rate: 1.0000
  utilization_rho: 0.8000

Simulation Results:
  simulation_time: 10000.0000
  customers_arrived: 7987
  customers_served: 7986
  average_queue_length: 3.1842
  average_wait_time: 3.9712
  average_system_time: 4.9893
  server_utilization: 0.7992

Theoretical Values:
  average_queue_length: 3.2000
  average_wait_time: 4.0000
  average_system_time: 5.0000

Comparison (Simulation vs Theoretical):
  Queue Length: 3.1842 vs 3.2000
  Wait Time: 3.9712 vs 4.0000
```

## Extending the Example

### M/M/c Queue (Multiple Servers)

```python
# Simply increase server capacity
self.server = Server(
    sim=self,
    capacity=3,  # Three servers
    service_time=lambda: self.rng.exponential(1.0 / self.service_rate),
)
```

### Priority Queue

```python
from simcraft.resources.queue import PriorityQueue

# Use priority queue instead of FIFO
self.server = Server(
    sim=self,
    capacity=1,
    queue=PriorityQueue(),
    service_time=lambda: self.rng.exponential(1.0 / self.service_rate),
)

# Assign priority when creating customers
customer = Customer(priority=self.rng.randint(1, 5))
```

### Warmup Period

```python
sim = MM1Queue(arrival_rate=0.8, service_rate=1.0)

# Run warmup (statistics are reset afterward)
sim.warmup(duration=1000)

# Run main simulation
sim.run(until=10000)
```

## Source Code

The complete source code is in `simcraft/examples/mm1_queue.py`.
