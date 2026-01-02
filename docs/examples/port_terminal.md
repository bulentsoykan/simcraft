# Port Terminal Example

A container port terminal simulation with resource allocation and RL integration.

## Overview

This example models a container port terminal inspired by the Winter Simulation Conference (WSC) 2025 challenge. It demonstrates:

- Multiple resource types (berths, quay cranes, AGVs, yard blocks)
- Complex entity lifecycles (vessels, containers)
- Decision points for optimization
- RL integration patterns
- Multi-resource coordination

## Terminal Operations

```
Vessel Arrival → Berthing → Discharge Containers → Load Containers → Departure
                    │              │                     │
                    └── Berth ─────┴── QC + AGV + Yard ──┘
```

**Key resources:**

- **Berths**: Locations where vessels dock
- **Quay Cranes (QC)**: Load/unload containers from vessels
- **AGVs**: Transport containers between quay and yard
- **Yard Blocks**: Storage areas for containers

## Code Walkthrough

### Domain Entities

```python
@dataclass
class Vessel(TimedEntity):
    """A container vessel."""
    vessel_id: str
    containers_to_discharge: int
    containers_to_load: int
    berth: Optional[int] = None

@dataclass
class Container(TimedEntity):
    """A container being handled."""
    container_id: str
    vessel: Vessel
    operation: str  # "discharge" or "load"
    yard_block: Optional[int] = None
```

### Resource Setup

```python
class PortTerminal(Simulation):
    def __init__(
        self,
        num_berths: int = 4,
        num_quay_cranes: int = 8,
        num_agvs: int = 20,
        num_yard_blocks: int = 6,
    ):
        super().__init__()

        # Berths - distinguishable resources
        self.berths = ResourcePool(
            sim=self,
            resources=[f"Berth-{i}" for i in range(num_berths)],
        )

        # Quay cranes - can be assigned to berths
        self.quay_cranes = ResourcePool(
            sim=self,
            resources=[f"QC-{i}" for i in range(num_quay_cranes)],
        )

        # AGVs - shared transport fleet
        self.agvs = ResourcePool(
            sim=self,
            resources=[f"AGV-{i}" for i in range(num_agvs)],
        )

        # Yard blocks - container storage
        self.yard_blocks = [
            YardBlock(f"YB-{i}", capacity=500)
            for i in range(num_yard_blocks)
        ]
```

### Vessel Lifecycle

```python
def on_init(self):
    """Schedule vessel arrivals."""
    self.schedule(self.vessel_arrival, delay=0)

def vessel_arrival(self):
    """Handle vessel arrival."""
    vessel = self.create_vessel()
    vessel.record_entry(self.now)

    # Request berth allocation (decision point)
    berth = self.decision_maker.allocate_berth(vessel, self.berths)

    if berth:
        self.berth_vessel(vessel, berth)
    else:
        self.vessel_queue.enqueue(vessel)

    # Schedule next arrival
    self.schedule(
        self.vessel_arrival,
        delay=self.rng.exponential(self.inter_arrival_time)
    )

def berth_vessel(self, vessel: Vessel, berth: str):
    """Berth a vessel and start operations."""
    vessel.berth = berth
    self.berths.acquire(vessel, resource_id=berth)

    # Allocate quay cranes (decision point)
    num_cranes = self.decision_maker.allocate_cranes(vessel)
    self.assigned_cranes[vessel] = []

    for _ in range(num_cranes):
        crane = self.quay_cranes.acquire(vessel)
        self.assigned_cranes[vessel].append(crane)

    # Start discharge operations
    self.start_discharge(vessel)
```

### Container Handling

```python
def start_discharge(self, vessel: Vessel):
    """Start discharging containers from vessel."""
    for i in range(vessel.containers_to_discharge):
        container = Container(
            container_id=f"{vessel.vessel_id}-D{i}",
            vessel=vessel,
            operation="discharge",
        )
        self.schedule(
            self.discharge_container,
            delay=i * 0.1,  # Staggered start
            args=(container,)
        )

def discharge_container(self, container: Container):
    """Discharge a single container."""
    # Use quay crane
    crane = self.get_available_crane(container.vessel)
    crane_time = self.rng.uniform(2, 4)  # minutes

    self.schedule(
        self.container_lifted,
        delay=crane_time,
        args=(container,)
    )

def container_lifted(self, container: Container):
    """Container lifted from vessel, needs AGV transport."""
    # Request AGV
    agv = self.agvs.acquire(container)

    # Select yard block (decision point)
    yard_block = self.decision_maker.select_yard_block(container)
    container.yard_block = yard_block

    # Transport to yard
    transport_time = self.get_transport_time(container.vessel.berth, yard_block)
    self.schedule(
        self.container_stored,
        delay=transport_time,
        args=(container, agv)
    )

def container_stored(self, container: Container, agv):
    """Container stored in yard."""
    self.agvs.release(agv)
    self.yard_blocks[container.yard_block].store(container)
    container.record_exit(self.now)

    self.containers_discharged += 1
    self.check_vessel_complete(container.vessel)
```

### Decision Maker Interface

```python
class PortDecisionMaker:
    """Decision maker for port operations (pluggable for RL)."""

    def allocate_berth(self, vessel: Vessel, berths: ResourcePool) -> Optional[str]:
        """Decide which berth to assign to vessel."""
        available = berths.get_available()
        if not available:
            return None
        # Default: first available
        return available[0]

    def allocate_cranes(self, vessel: Vessel) -> int:
        """Decide how many cranes to assign."""
        # Default: 2 cranes per vessel
        return min(2, self.available_cranes())

    def select_yard_block(self, container: Container) -> int:
        """Decide which yard block for container."""
        # Default: least utilized block
        return min(range(len(self.yard_blocks)),
                   key=lambda i: self.yard_blocks[i].utilization)
```

## RL Integration

Replace the decision maker with an RL agent:

```python
class RLPortDecisionMaker(PortDecisionMaker, RLInterface):
    """RL-based decision maker for port operations."""

    def get_state(self) -> np.ndarray:
        """Return current port state."""
        return np.array([
            self.berths.utilization,
            self.quay_cranes.utilization,
            self.agvs.utilization,
            len(self.vessel_queue),
            *[yb.utilization for yb in self.yard_blocks],
        ])

    def get_action_space(self) -> ActionSpace:
        """Define action space."""
        return ActionSpace(
            space_type="multi_discrete",
            nvec=[
                self.num_berths + 1,  # berth selection (0 = wait)
                4,                     # num cranes (1-4)
                self.num_yard_blocks,  # yard block
            ]
        )

    def apply_action(self, action: np.ndarray):
        """Apply RL agent's decision."""
        berth_action, crane_action, yard_action = action
        self.pending_decisions = {
            "berth": berth_action,
            "cranes": crane_action + 1,
            "yard": yard_action,
        }
```

## Running the Example

```python
from simcraft.examples.port_terminal import PortTerminal

# Create simulation
sim = PortTerminal(
    num_berths=4,
    num_quay_cranes=8,
    num_agvs=20,
    num_yard_blocks=6,
)

# Run for one week
sim.run(until=7 * 24 * 60)  # minutes

# Print results
sim.report()
```

## Sample Output

```
Port Terminal Simulation Results
============================================================

Vessel Statistics:
  Vessels arrived: 42
  Vessels served: 40
  Vessels in queue: 2
  Average wait time: 45.3 minutes
  Average turnaround: 8.2 hours

Container Statistics:
  Containers discharged: 12,450
  Containers loaded: 11,890
  Average handling time: 4.2 minutes

Resource Utilization:
  Berths: 82.5%
  Quay Cranes: 71.3%
  AGVs: 68.9%
  Yard Blocks: 45.2% - 67.8%
```

## Key Patterns

### Multiple Resource Types

The simulation coordinates berths, cranes, AGVs, and yard blocks - each with different characteristics.

### Decision Points

Key decisions (berth allocation, crane assignment, yard block selection) are isolated for easy RL integration.

### Complex Entity Lifecycle

Vessels go through multiple stages: arrival → queue → berthing → discharge → load → departure.

### Resource Pools

Distinguishable resources (berths, cranes) are managed via `ResourcePool` with custom selection policies.

## Source Code

The complete source code is in `simcraft/examples/port_terminal.py`.
