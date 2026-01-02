# Building Your First Simulation

This tutorial walks you through building a complete discrete event simulation from scratch.

## What You'll Learn

- Creating a `Simulation` subclass
- Scheduling and handling events
- Creating and tracking entities
- Using resources (servers and queues)
- Collecting statistics
- Running and analyzing results

## The Scenario

We'll build a simple bank simulation where:
- Customers arrive randomly
- They wait in a queue if all tellers are busy
- They get served by a teller
- We track wait times and teller utilization

## Step 1: Create the Simulation Class

Start by creating a new file `bank_simulation.py`:

```python
import simcraft

class BankSimulation(simcraft.Simulation):
    """A simple bank with customers and tellers."""

    def __init__(self, num_tellers: int = 2, arrival_rate: float = 1.0):
        super().__init__()
        self.arrival_rate = arrival_rate

        # Create a server with multiple tellers
        self.tellers = simcraft.Server(capacity=num_tellers)

        # Statistics
        self.wait_times = simcraft.Tally()
        self.customers_served = simcraft.Counter()

    def on_init(self):
        """Called when simulation starts."""
        # Schedule first customer arrival
        self.schedule(self.customer_arrival, delay=0.0)

        # Set up callbacks for server events
        self.tellers.on_service_start(self.on_service_start)
        self.tellers.on_departure(self.on_service_complete)
```

## Step 2: Handle Customer Arrivals

Add the arrival event handler:

```python
    def customer_arrival(self):
        """Handle a customer arriving at the bank."""
        # Create a new customer entity
        customer = simcraft.TimedEntity()
        customer.record_entry(self.now)

        # Customer joins the teller queue
        self.tellers.enqueue(customer)

        # Schedule next customer arrival
        inter_arrival = self.rng.exponential(1.0 / self.arrival_rate)
        self.schedule(self.customer_arrival, delay=inter_arrival)
```

## Step 3: Handle Service Events

Add the service event handlers:

```python
    def on_service_start(self, customer):
        """Called when a customer starts being served."""
        customer.record_service_start(self.now)
        self.wait_times.observe(customer.waiting_time)

        # Schedule service completion
        service_time = self.rng.exponential(mean=2.0)
        self.schedule(self.service_complete, delay=service_time, args=(customer,))

    def service_complete(self, customer):
        """Handle service completion."""
        customer.record_exit(self.now)
        self.tellers.depart(customer)

    def on_service_complete(self, customer):
        """Called after customer departs."""
        self.customers_served.increment()
```

## Step 4: Add Reporting

Add a method to report results:

```python
    def report(self):
        """Print simulation results."""
        print("\n=== Bank Simulation Results ===")
        print(f"Simulation time: {self.now:.1f}")
        print(f"Customers served: {self.customers_served.value}")
        print(f"Teller utilization: {self.tellers.stats.utilization:.1%}")
        print(f"Average wait time: {self.wait_times.mean:.2f}")
        print(f"Max wait time: {self.wait_times.max:.2f}")
        if self.wait_times.count >= 2:
            print(f"Wait time std dev: {self.wait_times.std:.2f}")
```

## Step 5: Run the Simulation

Add a main block to run the simulation:

```python
if __name__ == "__main__":
    # Create simulation with 2 tellers, 1.5 customers/minute
    sim = BankSimulation(num_tellers=2, arrival_rate=1.5)

    # Run for 480 minutes (8 hours)
    sim.run(until=480)

    # Print results
    sim.report()
```

## Complete Code

Here's the complete simulation:

```python
import simcraft


class BankSimulation(simcraft.Simulation):
    """A simple bank with customers and tellers."""

    def __init__(self, num_tellers: int = 2, arrival_rate: float = 1.0):
        super().__init__()
        self.arrival_rate = arrival_rate

        # Create a server with multiple tellers
        self.tellers = simcraft.Server(capacity=num_tellers)

        # Statistics
        self.wait_times = simcraft.Tally()
        self.customers_served = simcraft.Counter()

    def on_init(self):
        """Called when simulation starts."""
        self.schedule(self.customer_arrival, delay=0.0)
        self.tellers.on_service_start(self.on_service_start)
        self.tellers.on_departure(self.on_service_complete)

    def customer_arrival(self):
        """Handle a customer arriving at the bank."""
        customer = simcraft.TimedEntity()
        customer.record_entry(self.now)
        self.tellers.enqueue(customer)

        inter_arrival = self.rng.exponential(1.0 / self.arrival_rate)
        self.schedule(self.customer_arrival, delay=inter_arrival)

    def on_service_start(self, customer):
        """Called when a customer starts being served."""
        customer.record_service_start(self.now)
        self.wait_times.observe(customer.waiting_time)

        service_time = self.rng.exponential(mean=2.0)
        self.schedule(self.service_complete, delay=service_time, args=(customer,))

    def service_complete(self, customer):
        """Handle service completion."""
        customer.record_exit(self.now)
        self.tellers.depart(customer)

    def on_service_complete(self, customer):
        """Called after customer departs."""
        self.customers_served.increment()

    def report(self):
        """Print simulation results."""
        print("\n=== Bank Simulation Results ===")
        print(f"Simulation time: {self.now:.1f}")
        print(f"Customers served: {self.customers_served.value}")
        print(f"Teller utilization: {self.tellers.stats.utilization:.1%}")
        print(f"Average wait time: {self.wait_times.mean:.2f}")
        print(f"Max wait time: {self.wait_times.max:.2f}")


if __name__ == "__main__":
    sim = BankSimulation(num_tellers=2, arrival_rate=1.5)
    sim.run(until=480)
    sim.report()
```

## Running the Simulation

Save the file and run it:

```bash
python bank_simulation.py
```

Example output:
```
=== Bank Simulation Results ===
Simulation time: 480.0
Customers served: 712
Teller utilization: 74.2%
Average wait time: 1.84
Max wait time: 12.37
```

## Experimentation

Try modifying the simulation:

1. **Change the number of tellers**: How does utilization change with 1, 2, or 3 tellers?
2. **Vary arrival rate**: What happens when customers arrive faster?
3. **Add warmup**: Use `sim.warmup(60)` before `sim.run()` to exclude startup transients

## Next Steps

- See the [M/M/1 Queue Example](../examples/mm1_queue) for theoretical validation
- Learn about [RL Integration](rl_integration) for optimization
- Explore more [Examples](../examples/index)
