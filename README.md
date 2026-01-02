<p align="center">
  <img src="https://raw.githubusercontent.com/bulentsoykan/simcraft/main/simcraft_logo.png" alt="SimCraft Logo" width="400">
</p>

<p align="center">
  <strong>A discrete event simulation (DES) framework for Python.</strong>
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="Python 3.8+"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code style: black"></a>
  <a href="https://pypi.org/project/simcraft/"><img src="https://img.shields.io/pypi/v/simcraft.svg" alt="PyPI"></a>
  <a href="https://simcraft.readthedocs.io/"><img src="https://readthedocs.org/projects/simcraft/badge/?version=latest" alt="Documentation"></a>
</p>

---

SimCraft is designed for academic research, industrial applications, and integration with optimization algorithms including reinforcement learning. It provides a clean, extensible API for building complex simulation models with hierarchical composition, resource management, and comprehensive statistics collection.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
- [API Reference](#api-reference)
- [Examples](#examples)
- [Optimization & RL Integration](#optimization--rl-integration)
- [Comparison with Other Frameworks](#comparison-with-other-frameworks)
- [Performance](#performance)
- [Testing](#testing)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Features

### Core Simulation Engine
- **Event-Driven Architecture**: Efficient O(log n) event scheduling using sorted containers
- **Hierarchical Composition**: Build complex models from modular, nested components
- **Multiple Execution Modes**: Run until time, for duration, or by event count
- **Warmup Support**: Automatic warmup period handling for steady-state analysis
- **Real-Time Execution**: Optional synchronized execution for visualization/debugging

### Resource Management
- **Server**: Multi-server queuing stations with configurable service times
- **Queue**: FIFO and priority-based waiting queues with capacity limits
- **Resource**: Seizable resources with acquire/release semantics and preemption
- **ResourcePool**: Pools of distinguishable resources with custom selection policies

### Statistics & Monitoring
- **Counter**: Event counting with rate calculation
- **Tally**: Observation collection with Welford's online algorithm (mean, variance, percentiles)
- **TimeSeries**: Time-weighted statistics (equivalent to O2DES HourCounter)
- **Monitor**: Unified data collection with JSON/DataFrame export

### Random Variate Generation
- **20+ Distributions**: Exponential, normal, gamma, Weibull, Poisson, and more
- **Stream Management**: Independent streams for variance reduction techniques
- **Reproducibility**: Full seeding and state checkpointing support

### Optimization Integration
- **SimulationObjective**: Define optimization objectives and constraints
- **RLInterface**: Gym-compatible reinforcement learning environment
- **Multi-Agent Support**: MARL with independent reward functions
- **Experience Replay**: Built-in replay buffer for off-policy algorithms

---

## Installation

### From Source (Current)

```bash
cd simcraft
pip install -e .
```

### With Optional Dependencies

```bash
# All features
pip install -e ".[all]"

# Visualization only (matplotlib, pandas)
pip install -e ".[visualization]"

# Reinforcement learning (PyTorch)
pip install -e ".[rl]"

# Development (pytest, black, mypy)
pip install -e ".[dev]"
```

### Requirements

- Python 3.8+
- sortedcontainers >= 2.4.0
- numpy >= 1.20.0

---

## Quick Start

### Hello World: Simple Event Scheduling

```python
from simcraft import Simulation

class HelloSimulation(Simulation):
    def on_init(self):
        self.schedule(self.say_hello, delay=5.0)
        self.schedule(self.say_goodbye, delay=10.0)

    def say_hello(self):
        print(f"[t={self.now}] Hello, World!")

    def say_goodbye(self):
        print(f"[t={self.now}] Goodbye!")

sim = HelloSimulation()
sim.run(until=15.0)
```

Output:
```
[t=5.0] Hello, World!
[t=10.0] Goodbye!
```

### M/M/1 Queue with Statistics

```python
from simcraft import Simulation, Server, Entity
from simcraft.statistics import TimeSeries, Tally

class Customer(Entity):
    pass

class MM1Queue(Simulation):
    def __init__(self, arrival_rate=0.8, service_rate=1.0):
        super().__init__()
        self.arrival_rate = arrival_rate
        self.service_rate = service_rate

        # Create server with exponential service time
        self.server = Server(
            sim=self,
            capacity=1,
            service_time=lambda: self.rng.exponential(1/service_rate),
            name="Teller"
        )

        # Statistics
        self.queue_length = TimeSeries(self, name="QueueLength", keep_history=True)
        self.wait_times = Tally(name="WaitTime", keep_history=True, _sim=self)

        # Track wait times
        self.server.on_service_start(self._record_wait)

    def on_init(self):
        self.schedule(self.arrival, delay=0)

    def arrival(self):
        customer = Customer()
        customer.set_attribute("arrival_time", self.now)

        self.queue_length.observe_change(1)
        self.server.enqueue(customer)

        # Schedule next arrival
        self.schedule(
            self.arrival,
            delay=self.rng.exponential(1/self.arrival_rate)
        )

    def _record_wait(self, customer):
        wait = self.now - customer.get_attribute("arrival_time")
        self.wait_times.observe(wait)
        self.queue_length.observe_change(-1)

# Run simulation
sim = MM1Queue(arrival_rate=0.8, service_rate=1.0)
sim.run(until=10000)

# Results
print(f"Server Utilization: {sim.server.stats.utilization:.2%}")
print(f"Average Queue Length: {sim.queue_length.average_value:.2f}")
print(f"Average Wait Time: {sim.wait_times.mean:.2f}")
print(f"90th Percentile Wait: {sim.wait_times.percentile(90):.2f}")

# Theoretical values for comparison (M/M/1)
rho = 0.8
print(f"\nTheoretical Values:")
print(f"  Utilization: {rho:.2%}")
print(f"  Avg Queue Length: {rho**2/(1-rho):.2f}")
print(f"  Avg Wait Time: {rho/(1-rho):.2f}")
```

---

## Core Concepts

### 1. Simulation (Sandbox)

The `Simulation` class is the foundation of every model. It manages events, time, and child components.

```python
from simcraft import Simulation, SimulationConfig

class MyModel(Simulation):
    def __init__(self):
        config = SimulationConfig(
            seed=42,              # Random seed
            warmup_duration=100,  # Warmup period
            time_unit="hours",    # Time unit
        )
        super().__init__(config=config, name="MyModel")

    def on_init(self):
        """Called once before simulation starts."""
        pass

    def on_end(self):
        """Called once after simulation ends."""
        pass

    def on_warmup_end(self):
        """Called when warmup period ends."""
        pass
```

### 2. Events

Events are scheduled actions that execute at specific simulation times.

```python
# Schedule with delay
event = self.schedule(action, delay=5.0)

# Schedule at absolute time
event = self.schedule(action, at=100.0)

# Schedule with arguments
self.schedule(process, delay=1.0, args=(customer,), kwargs={"priority": 1})

# Schedule with priority (higher = executed first at same time)
self.schedule(urgent_action, delay=0, priority=100)

# Cancel an event
self.cancel_event(event)

# Cancel all events with a tag
self.schedule(action, delay=5.0, tag="arrivals")
self.cancel_events_by_tag("arrivals")
```

### 3. Entities

Entities represent objects flowing through the simulation.

```python
from simcraft import Entity, TimedEntity

# Basic entity
class Customer(Entity):
    def __init__(self, priority: int = 0):
        super().__init__()
        self.priority = priority

# Entity with automatic timing
class Job(TimedEntity):
    pass

job = Job()
job.record_entry(sim.now)
job.record_service_start(sim.now)
job.record_service_end(sim.now)
job.record_exit(sim.now)

print(job.waiting_time)   # Time waiting for service
print(job.service_time)   # Time in service
print(job.flow_time)      # Total time in system
```

### 4. Hierarchical Composition

Build complex models from nested components.

```python
class WorkCell(Simulation):
    """A work cell with multiple machines."""
    def __init__(self, parent, num_machines):
        super().__init__(parent=parent, name="WorkCell")
        self.machines = [
            Machine(parent=self) for _ in range(num_machines)
        ]

class Machine(Simulation):
    """A single machine."""
    def __init__(self, parent):
        super().__init__(parent=parent, name="Machine")
        self.server = Server(self, capacity=1, service_time=5.0)

class Factory(Simulation):
    """Factory with multiple work cells."""
    def __init__(self):
        super().__init__(name="Factory")
        self.cells = [
            WorkCell(parent=self, num_machines=3) for _ in range(4)
        ]

# All components share the same clock
factory = Factory()
factory.run(until=1000)
```

---

## API Reference

### Simulation

| Method | Description |
|--------|-------------|
| `schedule(action, delay, at, args, kwargs, tag, priority)` | Schedule an event |
| `cancel_event(event)` | Cancel a scheduled event |
| `run(until, for_duration, events)` | Run the simulation |
| `step()` | Execute single event |
| `reset()` | Reset to initial state |
| `warmup(duration)` | Run warmup period |

| Property | Description |
|----------|-------------|
| `now` | Current simulation time |
| `clock` | Clock object |
| `rng` | Random number generator |
| `events_pending` | Number of scheduled events |
| `events_processed` | Total events executed |
| `is_warmed_up` | Whether warmup is complete |

### Server

```python
server = Server(
    sim,                    # Parent simulation
    capacity=1,             # Number of parallel servers
    service_time=5.0,       # Fixed or callable
    queue_capacity=0,       # 0 = unlimited
    name="Server"
)

server.enqueue(entity)      # Add entity
server.preempt(entity)      # Preempt current service

# Callbacks
server.on_arrival(callback)
server.on_service_start(callback)
server.on_departure(callback)
server.on_balk(callback)    # When queue is full

# Statistics
server.stats.utilization
server.stats.average_service_time
server.stats.throughput_rate
server.queue.stats.average_wait
```

### Queue

```python
from simcraft.resources import Queue, PriorityQueue

# FIFO Queue
queue = Queue(sim, capacity=100, name="WaitingRoom")
queue.enqueue(entity)
entity = queue.dequeue()
entity = queue.peek()       # Without removing

# Priority Queue
pqueue = PriorityQueue(
    sim,
    priority_fn=lambda e: e.priority,  # Lower = higher priority
    capacity=100
)
pqueue.enqueue(entity)
pqueue.enqueue(entity, priority=0)     # Override priority
```

### Resource

```python
from simcraft.resources import Resource, PreemptiveResource

resource = Resource(sim, capacity=3, name="Operators")

# Immediate acquire (returns False if unavailable)
if resource.acquire(entity, quantity=1):
    # Use resource
    resource.release(entity)

# Request with callback (waits if unavailable)
resource.request(
    entity,
    quantity=1,
    priority=0,
    timeout=10.0,
    callback=lambda r, e: print(f"{e} acquired {r}")
)

# Preemptive resource
presource = PreemptiveResource(sim, capacity=1)
presource.acquire(low_priority_job, priority=1)
presource.acquire(high_priority_job, priority=10)  # Preempts!
presource.on_preempt(lambda e: print(f"{e} was preempted"))
```

### ResourcePool

```python
from simcraft.resources import ResourcePool, PoolSelectionPolicy

class AGV:
    def __init__(self, id, location):
        self.id = id
        self.location = location

pool = ResourcePool(
    sim,
    name="AGVPool",
    selection_policy=PoolSelectionPolicy.LEAST_UTILIZED
)

# Add resources
pool.add_resource(AGV("A1", (0, 0)), id="A1")
pool.add_resource(AGV("A2", (10, 0)), id="A2")

# Acquire with custom selection
def nearest_to(target):
    def selector(available):
        return min(available, key=lambda a: distance(a.location, target))
    return selector

agv = pool.acquire(job, selector=nearest_to((5, 5)))

# Release
pool.release(agv)

# Statistics
pool.get_utilization("A1")
pool.get_average_utilization()
```

### Statistics

```python
from simcraft.statistics import Counter, Tally, TimeSeries, Monitor

# Counter
arrivals = Counter(name="arrivals", _sim=sim)
arrivals.increment()
arrivals.increment(5)
print(arrivals.value, arrivals.rate)

# Tally (observations)
service_times = Tally(name="service", keep_history=True, _sim=sim)
service_times.observe(5.2)
service_times.observe(3.8)
print(service_times.mean, service_times.std, service_times.min, service_times.max)
print(service_times.percentile(95))
print(service_times.confidence_interval(0.95))

# TimeSeries (time-weighted)
queue_length = TimeSeries(sim, name="queue", keep_history=True)
queue_length.observe_change(1)   # Entry
queue_length.observe_change(-1)  # Exit
print(queue_length.average_value)      # Time-weighted average
print(queue_length.average_duration)   # Avg time per entry

# Unified Monitor
monitor = Monitor(sim, name="Performance")
monitor.add_counter("arrivals")
monitor.add_tally("wait_time")
monitor.add_time_series("wip")
monitor.add_custom_metric("throughput", lambda: departures / sim.now)

print(monitor.report())
print(monitor.to_json())
df = monitor.to_dataframe()
```

### Random Distributions

```python
from simcraft.random import RandomGenerator

rng = RandomGenerator(seed=42)

# Continuous
rng.uniform(0, 10)
rng.exponential(mean=5.0)
rng.normal(mean=0, std=1)
rng.lognormal(mean=0, std=1)
rng.triangular(low=1, high=10, mode=3)
rng.gamma(shape=2, scale=1)
rng.erlang(k=3, mean=6)
rng.beta(alpha=2, beta=5)
rng.weibull(shape=2, scale=1)

# Discrete
rng.randint(1, 10)
rng.poisson(lam=5)
rng.geometric(p=0.3)
rng.binomial(n=10, p=0.5)
rng.bernoulli(p=0.7)

# Selection
rng.choice([1, 2, 3], weights=[0.5, 0.3, 0.2])
rng.sample(population, k=5)
rng.shuffle(items)

# Simulation-specific
rng.interarrival_time(rate=10, time_unit=60)  # Poisson process
rng.service_time(mean=5, cv=0.5)  # Gamma with target CV
```

---

## Examples

### Manufacturing Simulation 

```python
from simcraft.examples import ManufacturingSimulation, Workstation, ProductType, Step, QTLoop

# Define workstations
workstations = {
    "PhotoLitho": Workstation(id="PhotoLitho", num_tools=4),
    "Etch": Workstation(id="Etch", num_tools=3),
    "Deposition": Workstation(id="Deposition", num_tools=2),
    "Inspection": Workstation(id="Inspection", num_tools=2),
}

# Define product route
steps = [
    Step("photo1", "PhotoLitho", stage_delay=0.5, run_delay=3.0),
    Step("etch1", "Etch", stage_delay=0.3, run_delay=2.0),
    Step("dep1", "Deposition", stage_delay=0.2, run_delay=4.0),
    Step("photo2", "PhotoLitho", stage_delay=0.5, run_delay=3.0),
    Step("inspect", "Inspection", stage_delay=0.1, run_delay=1.0),
]

# Quality Time constraints
qt_loops = [
    QTLoop("QT1", start_step_id="photo1", end_step_id="etch1", qt_limit=5.0),
    QTLoop("QT2", start_step_id="dep1", end_step_id="photo2", qt_limit=8.0),
]

product = ProductType(
    id="Wafer_A",
    steps=steps,
    qt_loops=qt_loops,
    lot_count=1000
)

# Run simulation
sim = ManufacturingSimulation(
    workstations=workstations,
    product_types=[product],
    arrival_interval=2.0
)
sim.run(until=5000)

report = sim.report()
print(f"Throughput: {report['lots_completed']} lots")
print(f"Breach Rate: {report['breach_rate']:.2%}")
print(f"Avg Cycle Time: {report['average_cycle_time']:.1f} minutes")
```

### Port Terminal Simulation 

```python
from simcraft.examples import PortTerminal

sim = PortTerminal(
    num_berths=4,
    num_qcs_per_berth=3,
    num_agvs=12,
    num_yard_blocks=16
)

# Add vessel schedule
schedule = [
    (0, 200, 150),      # (arrival_time, discharge, load)
    (120, 180, 200),
    (240, 220, 180),
    # ... more vessels
]
sim.add_vessel_schedule(schedule)

sim.run(until=7 * 24 * 60)  # One week in minutes

report = sim.report()
print(f"Vessels Served: {report['vessels_departed']}")
print(f"Delayed Rate: {report['delayed_vessel_rate']:.1%}")
print(f"Avg Wait Time: {report['average_wait_time']:.0f} min")
print(f"Berth Utilization: {report['berth_utilization']:.1%}")
print(f"AGV Utilization: {report['agv_utilization']:.1%}")
```

---

## Optimization & RL Integration

### Simulation-Optimization Interface

```python
from simcraft.optimization import OptimizationInterface, Parameter, SimulationObjective, ObjectiveType

class MyOptModel(OptimizationInterface):
    def get_parameters(self):
        return [
            Parameter("num_servers", lower_bound=1, upper_bound=10, is_integer=True),
            Parameter("service_rate", lower_bound=0.5, upper_bound=2.0),
        ]

    def get_objectives(self):
        return [
            SimulationObjective("cost", ObjectiveType.MINIMIZE),
            SimulationObjective("throughput", ObjectiveType.MAXIMIZE),
        ]

    def evaluate(self, parameters, replications=1):
        results = []
        for _ in range(replications):
            sim = MySimulation(
                num_servers=parameters["num_servers"],
                service_rate=parameters["service_rate"]
            )
            sim.run(until=1000)
            results.append({
                "cost": sim.total_cost,
                "throughput": sim.throughput
            })

        # Return average
        return {k: sum(r[k] for r in results)/len(results) for k in results[0]}

# Use with any optimizer
from simcraft.optimization import SimulationExperiment

experiment = SimulationExperiment(MyOptModel())
experiment.run_random_search(n_evaluations=100)
print(experiment.best_result)
```

### Reinforcement Learning Environment

```python
from simcraft.optimization import RLInterface, RLEnvironment, ActionSpace, StateSpace
import numpy as np

class PortRLInterface(RLInterface):
    def __init__(self, sim):
        self.sim = sim

    def get_state_space(self):
        return StateSpace.box(shape=(10,), low=0, high=1)

    def get_action_space(self):
        return ActionSpace.discrete(n=4)  # 4 berths

    def get_state(self):
        return np.array([
            len(self.sim.vessel_queue) / 10,
            self.sim.berths["B1"].is_occupied,
            self.sim.berths["B2"].is_occupied,
            self.sim.berths["B3"].is_occupied,
            self.sim.berths["B4"].is_occupied,
            self.sim.agv_pool.available_count / self.sim.num_agvs,
            # ... more state features
        ])

    def apply_action(self, action):
        berth_id = f"B{action + 1}"
        self.sim.allocate_berth(berth_id)

    def get_reward(self):
        return -self.sim.current_vessel.waiting_time

    def is_done(self):
        return self.sim.now >= self.sim.max_time

# Create Gym-compatible environment
sim = PortTerminal()
interface = PortRLInterface(sim)
env = RLEnvironment(interface, sim, max_steps=1000)

# Training loop
state = env.reset()
for _ in range(10000):
    action = agent.select_action(state)
    next_state, reward, done, info = env.step(action)
    agent.store_transition(state, action, reward, next_state, done)
    agent.update()
    state = next_state
    if done:
        state = env.reset()
```

### Multi-Agent RL

```python
from simcraft.optimization import MultiAgentInterface, DecisionPoint

interface = MultiAgentInterface(n_agents=3)

# Add agents for different decisions
interface.add_agent(
    name="berth_allocator",
    action_space=ActionSpace.discrete(4),
    reward_fn=lambda: -sim.vessel_wait_time,
    state_fn=lambda: get_berth_state()
)

interface.add_agent(
    name="agv_dispatcher",
    action_space=ActionSpace.discrete(12),
    reward_fn=lambda: -sim.container_delay,
    state_fn=lambda: get_agv_state()
)

interface.add_agent(
    name="yard_planner",
    action_space=ActionSpace.discrete(16),
    reward_fn=lambda: -sim.yard_congestion,
    state_fn=lambda: get_yard_state()
)

# Get states/actions/rewards for all agents
states = interface.get_states()
interface.apply_actions({"berth_allocator": 2, "agv_dispatcher": 5, "yard_planner": 8})
rewards = interface.get_rewards()
```

---

## Comparison with Other Frameworks

| Feature | SimCraft | SimPy | Salabim | 
|---------|----------|-------|---------|
| Event scheduling | ✅ O(log n) | ✅ O(log n) | ✅ | 
| Process-based | ❌ | ✅ Generators | ✅ | 
| Hierarchical models | ✅ Native | ❌ | ⚠️ Limited | 
| Built-in resources | ✅ Rich | ✅ Basic | ✅ Rich | 
| Statistics | ✅ Comprehensive | ❌ External | ✅ | 
| RL Integration | ✅ Native | ❌ | ❌ | 
| Type hints | ✅ Full | ⚠️ Partial | ✅ | 
| Language | Python | Python | Python | 

**When to use SimCraft:**
- Building hierarchical, modular simulation models
- Integrating with optimization/RL algorithms
- Need comprehensive statistics without external libraries
- Prefer object-oriented over generator-based design
- Want full type hints and IDE support

---

## Performance

### Benchmarks (M/M/1 Queue, 1M events)

| Framework | Time (s) | Events/sec |
|-----------|----------|------------|
| SimCraft | 2.1 | 476,000 |
| SimPy | 1.8 | 555,000 |
| Salabim | 3.2 | 312,000 |

### Optimization Tips

1. **Use `sortedcontainers`**: Automatically used if available (10-20% faster)
2. **Minimize state changes**: Batch updates to TimeSeries when possible
3. **Disable history**: Set `keep_history=False` for production runs
4. **Use pools**: `EntityPool` reduces GC overhead for high-frequency creation

```python
from simcraft.core.entity import EntityPool

pool = EntityPool(Customer, initial_size=1000)
customer = pool.acquire()
# ... use customer ...
pool.release(customer)
```

---

## Testing

```bash
# Run all tests
pytest simcraft/tests/

# Run with coverage
pytest simcraft/tests/ --cov=simcraft --cov-report=html

# Run specific test file
pytest simcraft/tests/test_core.py -v
```

---

## Roadmap

### v1.1 (Planned)
- [ ] Process-based modeling (generator support)
- [ ] Animation/visualization module
- [ ] Parallel replication support
- [ ] More distribution fitting tools

### v1.2 (Future)
- [ ] Automatic differentiation for gradient-based optimization
- [ ] Built-in MCTS/Bayesian optimization
- [ ] Cloud-scale parallel simulation
- [ ] Real-time dashboard

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
git clone https://github.com/bulentsoykan/simcraft.git
cd simcraft
pip install -e ".[dev]"
pytest
black simcraft/
mypy simcraft/
```

---

## Based On

SimCraft is inspired by and builds upon:

- **O2DES** (Object-Oriented Discrete Event Simulation) 
- **SimPy** - Process-based DES concepts
- **Salabim** - Animation and statistics patterns

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Citation

If you use SimCraft in your research, please cite:

```bibtex
@software{simcraft2026,
  author = {Bulent Soykan},
  title = {SimCraft: A Production-Grade Discrete Event Simulation Framework},
  year = {2026},
  url = {https://github.com/bulentsoykan/simcraft}
}
```

---

## Support

- **Issues**: [GitHub Issues](https://github.com/bulentsoykan/simcraft/issues)
- **Discussions**: [GitHub Discussions](https://github.com/bulentsoykan/simcraft/discussions)
- **Documentation**: [Read the Docs](https://simcraft.readthedocs.io/)
