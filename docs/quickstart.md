# Quick Start

This guide will help you get started with SimCraft by building a simple M/M/1 queue simulation.

## Hello World

The simplest SimCraft simulation schedules events and runs until a specified time:

```python
import simcraft

class HelloWorld(simcraft.Simulation):
    def on_init(self):
        """Called when simulation starts."""
        self.schedule(self.say_hello, delay=1.0)

    def say_hello(self):
        print(f"Hello at time {self.now}!")
        if self.now < 4.0:
            self.schedule(self.say_hello, delay=1.0)

sim = HelloWorld()
sim.run(until=5.0)
```

Output:
```
Hello at time 1.0!
Hello at time 2.0!
Hello at time 3.0!
Hello at time 4.0!
```

## Core Concepts

### Simulation

The `Simulation` class is the main container for your model. Override `on_init()` to set up initial events:

```python
class MySimulation(simcraft.Simulation):
    def on_init(self):
        # Schedule initial events here
        self.schedule(self.first_event, delay=0.0)
```

### Scheduling Events

Use `schedule()` to add events to the simulation:

```python
# Schedule with delay from current time
self.schedule(self.my_event, delay=5.0)

# Schedule at absolute time
self.schedule(self.my_event, at=10.0)

# Pass arguments to the event
self.schedule(self.process, delay=1.0, args=(entity,))
```

### Random Numbers

Use the built-in random number generator for reproducibility:

```python
# Exponential inter-arrival times
delay = self.rng.exponential(mean=2.0)

# Normal service times
service_time = self.rng.normal(mean=1.0, std=0.2)

# Random choice
item = self.rng.choice(['A', 'B', 'C'])
```

## M/M/1 Queue Example

Here's a complete M/M/1 queue simulation with statistics collection:

```python
import simcraft

class MM1Queue(simcraft.Simulation):
    def __init__(self, arrival_rate: float, service_rate: float):
        super().__init__()
        self.arrival_rate = arrival_rate
        self.service_rate = service_rate

        # Resources
        self.server = simcraft.Server(capacity=1)

        # Statistics
        self.wait_times = simcraft.Tally()
        self.queue_length = simcraft.TimeSeries()

    def on_init(self):
        # Start arrivals
        self.schedule(self.arrival, delay=0.0)

        # Set up callbacks
        self.server.on_arrival(self.on_customer_arrival)
        self.server.on_departure(self.on_customer_departure)

    def arrival(self):
        # Create customer entity
        customer = simcraft.TimedEntity()
        customer.record_entry(self.now)

        # Enter server queue
        self.server.enqueue(customer)
        self.queue_length.observe_change(1, self.now)

        # Schedule next arrival
        inter_arrival = self.rng.exponential(1.0 / self.arrival_rate)
        self.schedule(self.arrival, delay=inter_arrival)

    def on_customer_arrival(self, customer):
        # Customer starts service
        customer.record_service_start(self.now)
        self.wait_times.observe(customer.waiting_time)

        # Schedule service completion
        service_time = self.rng.exponential(1.0 / self.service_rate)
        self.schedule(self.complete_service, delay=service_time, args=(customer,))

    def complete_service(self, customer):
        customer.record_exit(self.now)
        self.server.depart(customer)
        self.queue_length.observe_change(-1, self.now)

    def on_customer_departure(self, customer):
        pass  # Could collect more statistics here

    def report(self):
        rho = self.arrival_rate / self.service_rate
        print(f"Utilization: {self.server.stats.utilization:.3f} (theory: {rho:.3f})")
        print(f"Avg Wait: {self.wait_times.mean:.3f}")
        print(f"Avg Queue: {self.queue_length.average_value:.3f}")

# Run simulation
sim = MM1Queue(arrival_rate=0.8, service_rate=1.0)
sim.run(until=10000)
sim.report()
```

## Next Steps

- Explore the [Tutorials](tutorials/index) for in-depth guides
- See [Examples](examples/index) for complete simulation models
- Browse the [API Reference](api/index) for detailed documentation
