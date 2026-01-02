"""
Classic M/M/1 queueing model.

A simple single-server queue with Poisson arrivals and
exponential service times.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from simcraft.core.simulation import Simulation, SimulationConfig
from simcraft.core.entity import TimedEntity
from simcraft.resources.server import Server
from simcraft.statistics.time_series import TimeSeries
from simcraft.statistics.tally import Tally
from simcraft.statistics.monitor import Monitor


@dataclass
class Customer(TimedEntity):
    """A customer in the queueing system."""

    priority: int = 0


class MM1Queue(Simulation):
    """
    M/M/1 single-server queueing system.

    A classic queueing model with:
    - Poisson arrivals (exponential interarrival times)
    - Single server
    - Exponential service times
    - FIFO queue discipline

    Parameters
    ----------
    arrival_rate : float
        Average customers per time unit (lambda)
    service_rate : float
        Average customers served per time unit (mu)
    config : Optional[SimulationConfig]
        Simulation configuration

    Attributes
    ----------
    server : Server
        The single server
    queue_length : TimeSeries
        Queue length over time
    wait_times : Tally
        Customer waiting times
    system_times : Tally
        Customer total time in system

    Examples
    --------
    >>> sim = MM1Queue(arrival_rate=0.8, service_rate=1.0)
    >>> sim.run(until=1000)
    >>> print(f"Average queue length: {sim.queue_length.average_value:.2f}")
    >>> print(f"Average wait time: {sim.wait_times.mean:.2f}")
    >>> print(f"Server utilization: {sim.server.stats.utilization:.2%}")
    """

    def __init__(
        self,
        arrival_rate: float = 0.8,
        service_rate: float = 1.0,
        config: Optional[SimulationConfig] = None,
    ) -> None:
        """Initialize M/M/1 queue."""
        super().__init__(config=config, name="MM1Queue")

        # Parameters
        self.arrival_rate = arrival_rate
        self.service_rate = service_rate

        # Theoretical values
        self.rho = arrival_rate / service_rate  # Utilization

        # Server
        self.server = Server(
            sim=self,
            capacity=1,
            service_time=lambda: self.rng.exponential(1.0 / self.service_rate),
            name="Server",
        )

        # Statistics
        self.queue_length = TimeSeries(self, name="QueueLength", keep_history=True)
        self.wait_times = Tally(name="WaitTime", keep_history=True, _sim=self)
        self.system_times = Tally(name="SystemTime", keep_history=True, _sim=self)

        # Counters
        self.customers_arrived = 0
        self.customers_served = 0

        # Set up callbacks
        self.server.on_arrival(self._on_arrival)
        self.server.on_service_start(self._on_service_start)
        self.server.on_departure(self._on_departure)

    def on_init(self) -> None:
        """Schedule first arrival."""
        self.schedule(self._arrival, delay=0)

    def _arrival(self) -> None:
        """Handle customer arrival."""
        customer = Customer()
        customer.record_entry(self.now)
        self.customers_arrived += 1

        # Update queue length
        self.queue_length.observe_change(1)

        # Enter server
        self.server.enqueue(customer)

        # Schedule next arrival
        interarrival = self.rng.exponential(1.0 / self.arrival_rate)
        self.schedule(self._arrival, delay=interarrival)

    def _on_arrival(self, customer: Customer) -> None:
        """Called when customer enters server."""
        pass

    def _on_service_start(self, customer: Customer) -> None:
        """Called when service starts."""
        customer.record_service_start(self.now)
        self.wait_times.observe(customer.waiting_time)

    def _on_departure(self, customer: Customer) -> None:
        """Called when customer departs."""
        customer.record_exit(self.now)
        self.customers_served += 1

        # Update queue length
        self.queue_length.observe_change(-1)

        # Record system time
        self.system_times.observe(customer.flow_time)

    @property
    def theoretical_queue_length(self) -> float:
        """Get theoretical average queue length (L_q)."""
        if self.rho >= 1:
            return float("inf")
        return (self.rho ** 2) / (1 - self.rho)

    @property
    def theoretical_system_length(self) -> float:
        """Get theoretical average number in system (L)."""
        if self.rho >= 1:
            return float("inf")
        return self.rho / (1 - self.rho)

    @property
    def theoretical_wait_time(self) -> float:
        """Get theoretical average wait time (W_q)."""
        if self.rho >= 1:
            return float("inf")
        return self.rho / (self.service_rate * (1 - self.rho))

    @property
    def theoretical_system_time(self) -> float:
        """Get theoretical average time in system (W)."""
        if self.rho >= 1:
            return float("inf")
        return 1 / (self.service_rate * (1 - self.rho))

    def report(self) -> dict:
        """Generate summary report."""
        return {
            "parameters": {
                "arrival_rate": self.arrival_rate,
                "service_rate": self.service_rate,
                "utilization_rho": self.rho,
            },
            "simulation_results": {
                "simulation_time": self.now,
                "customers_arrived": self.customers_arrived,
                "customers_served": self.customers_served,
                "average_queue_length": self.queue_length.average_value,
                "average_wait_time": self.wait_times.mean,
                "average_system_time": self.system_times.mean,
                "server_utilization": self.server.stats.utilization,
            },
            "theoretical_values": {
                "average_queue_length": self.theoretical_queue_length,
                "average_wait_time": self.theoretical_wait_time,
                "average_system_time": self.theoretical_system_time,
            },
        }


def run_mm1_example() -> None:
    """Run M/M/1 queue example."""
    print("=" * 60)
    print("M/M/1 Queue Simulation")
    print("=" * 60)

    # Create simulation
    sim = MM1Queue(arrival_rate=0.8, service_rate=1.0)

    # Run simulation
    sim.run(until=10000)

    # Print results
    report = sim.report()

    print("\nParameters:")
    for key, value in report["parameters"].items():
        print(f"  {key}: {value:.4f}")

    print("\nSimulation Results:")
    for key, value in report["simulation_results"].items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")

    print("\nTheoretical Values:")
    for key, value in report["theoretical_values"].items():
        print(f"  {key}: {value:.4f}")

    print("\nComparison (Simulation vs Theoretical):")
    print(
        f"  Queue Length: {report['simulation_results']['average_queue_length']:.4f} "
        f"vs {report['theoretical_values']['average_queue_length']:.4f}"
    )
    print(
        f"  Wait Time: {report['simulation_results']['average_wait_time']:.4f} "
        f"vs {report['theoretical_values']['average_wait_time']:.4f}"
    )


if __name__ == "__main__":
    run_mm1_example()
