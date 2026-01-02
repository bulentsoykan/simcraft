"""
SimCraft - A Discrete Event Simulation Framework

SimCraft is a production-grade discrete event simulation (DES) framework
designed for academic research, industrial applications, and integration
with optimization algorithms including reinforcement learning.

SimCraft provides a clean, extensible API for building complex simulation
models with hierarchical composition, resource management, and comprehensive
statistics collection.

Example
-------
>>> from simcraft import Simulation, Server, Entity
>>>
>>> class Customer(Entity):
...     pass
>>>
>>> class BankSimulation(Simulation):
...     def __init__(self):
...         super().__init__()
...         self.teller = Server(self, capacity=2, service_time=5.0)
...
...     def on_init(self):
...         self.schedule(self.customer_arrival, delay=0)
...
...     def customer_arrival(self):
...         customer = Customer()
...         self.teller.enqueue(customer)
...         self.schedule(self.customer_arrival, delay=self.rng.exponential(3.0))
>>>
>>> sim = BankSimulation()
>>> sim.run(until=100)
>>> print(sim.teller.stats)

Features
--------
- Event-driven simulation with efficient scheduling
- Hierarchical model composition
- Resource and queue management
- Comprehensive statistics collection
- Activity-based state machines
- Random variate generation
- Optimization and RL integration
- Type hints and full documentation

Author
------
Bulent Soykan

License
-------
MIT License
"""

__version__ = "1.0.0"
__author__ = "SimCraft Contributors"

# Core simulation components
from simcraft.core.simulation import Simulation
from simcraft.core.event import Event
from simcraft.core.entity import Entity
from simcraft.core.clock import Clock

# Resource management
from simcraft.resources.server import Server
from simcraft.resources.queue import Queue
from simcraft.resources.resource import Resource
from simcraft.resources.pool import ResourcePool

# Activity framework
from simcraft.activities.activity import Activity
from simcraft.activities.state_machine import StateMachine, State

# Statistics
from simcraft.statistics.counter import Counter
from simcraft.statistics.tally import Tally
from simcraft.statistics.time_series import TimeSeries
from simcraft.statistics.monitor import Monitor

# Random variates
from simcraft.random.distributions import RandomGenerator
from simcraft.random.streams import RandomStream

# Optimization interfaces
from simcraft.optimization.base import OptimizationInterface
from simcraft.optimization.rl_interface import RLInterface

__all__ = [
    # Version
    "__version__",

    # Core
    "Simulation",
    "Event",
    "Entity",
    "Clock",

    # Resources
    "Server",
    "Queue",
    "Resource",
    "ResourcePool",

    # Activities
    "Activity",
    "StateMachine",
    "State",

    # Statistics
    "Counter",
    "Tally",
    "TimeSeries",
    "Monitor",

    # Random
    "RandomGenerator",
    "RandomStream",

    # Optimization
    "OptimizationInterface",
    "RLInterface",
]
