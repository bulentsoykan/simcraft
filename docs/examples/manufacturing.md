# Manufacturing Example

A semiconductor fabrication simulation with multi-step routing and quality constraints.

## Overview

This example models a semiconductor fab inspired by the Winter Simulation Conference (WSC) 2023 challenge. It demonstrates:

- Multi-step production routes
- Quality Time (QT) constraints between steps
- Lot-based batch processing
- Multiple workstations with tool capacity
- Work-in-progress (WIP) monitoring
- Constraint breach detection

## The Manufacturing Process

```
Lot Release → Step 1 → Step 2 → ... → Step N → Completion
                 │         │
                 └── QT ───┘  (Quality Time constraint)
```

**Key concepts:**

- **Lot**: A batch of wafers moving through the fab
- **Step**: A processing operation at a workstation
- **Workstation**: A group of parallel tools performing the same operation
- **Quality Time (QT)**: Maximum allowed time between certain steps

## Code Walkthrough

### Domain Entities

```python
@dataclass
class ProductType:
    """Definition of a product's manufacturing route."""
    name: str
    steps: List[Step]
    qt_constraints: List[QTConstraint]

@dataclass
class Lot(TimedEntity):
    """A lot (batch) moving through the fab."""
    lot_id: str
    product_type: ProductType
    quantity: int = 25  # wafers per lot
    current_step: int = 0
    qt_breach: bool = False
```

### Workstation with Tools

```python
class Workstation:
    """A workstation with multiple parallel tools."""

    def __init__(self, sim, name: str, num_tools: int, process_time: float):
        self.server = Server(
            sim=sim,
            capacity=num_tools,
            service_time=lambda: sim.rng.exponential(process_time),
            name=name,
        )
        self.wip = TimeSeries(sim, name=f"{name}_WIP")
```

### Quality Time Constraints

```python
@dataclass
class QTConstraint:
    """Quality time constraint between steps."""
    from_step: int
    to_step: int
    max_time: float

def check_qt_constraint(self, lot: Lot) -> bool:
    """Check if lot has violated any QT constraints."""
    for qt in lot.product_type.qt_constraints:
        if lot.current_step == qt.to_step:
            elapsed = self.now - lot.step_times[qt.from_step]
            if elapsed > qt.max_time:
                return True  # Breach!
    return False
```

### Lot Flow

```python
def on_init(self):
    """Start lot releases."""
    self.schedule(self.release_lot, delay=0)

def release_lot(self):
    """Release a new lot into the fab."""
    lot = Lot(
        lot_id=f"LOT-{self.lots_released}",
        product_type=self.product_types[0],
    )
    lot.record_entry(self.now)
    self.lots_released += 1

    # Start processing at first workstation
    self.process_step(lot)

    # Schedule next release
    self.schedule(self.release_lot, delay=self.release_interval)

def process_step(self, lot: Lot):
    """Process lot at current step."""
    step = lot.product_type.steps[lot.current_step]
    workstation = self.workstations[step.workstation]

    # Track WIP
    workstation.wip.observe_change(1)

    # Enter workstation queue
    workstation.server.enqueue(lot)

def on_step_complete(self, lot: Lot):
    """Handle step completion."""
    # Check QT constraint
    if self.check_qt_constraint(lot):
        lot.qt_breach = True
        self.breaches += 1

    # Update WIP
    workstation.wip.observe_change(-1)

    # Move to next step or complete
    lot.current_step += 1
    if lot.current_step < len(lot.product_type.steps):
        self.process_step(lot)
    else:
        self.complete_lot(lot)
```

## Running the Example

```python
from simcraft.examples.manufacturing import ManufacturingSimulation

# Create simulation
sim = ManufacturingSimulation(
    num_workstations=5,
    tools_per_workstation=3,
    release_interval=10.0,
)

# Run for one week (168 hours)
sim.run(until=168 * 60)  # in minutes

# Print results
sim.report()
```

## Sample Output

```
Manufacturing Simulation Results
============================================================

Production Metrics:
  Lots released: 1008
  Lots completed: 987
  QT breaches: 23 (2.3%)

Cycle Time:
  Average: 142.3 minutes
  Min: 98.7 minutes
  Max: 312.5 minutes

Workstation Utilization:
  WS-1: 78.2%
  WS-2: 82.5%
  WS-3: 71.3%
  WS-4: 85.1%
  WS-5: 69.8%

Bottleneck: WS-4 (highest utilization)
```

## Key Patterns Demonstrated

### Multi-Step Routing

Lots follow a predefined sequence of steps, each at a specific workstation.

### Time Constraints

Quality Time (QT) constraints enforce maximum elapsed time between steps. Violations are tracked as breaches.

### Parallel Resources

Each workstation has multiple tools (parallel servers) that can process lots simultaneously.

### WIP Tracking

Work-in-progress is tracked at each workstation using TimeSeries statistics.

## Extensions

### Priority Dispatching

```python
# Prioritize lots close to QT breach
def get_priority(lot: Lot) -> float:
    remaining_qt = self.get_remaining_qt(lot)
    return -remaining_qt  # Lower remaining time = higher priority
```

### Machine Breakdowns

```python
def schedule_breakdown(self, workstation):
    """Schedule random machine breakdown."""
    mtbf = self.rng.exponential(1000)  # Mean time between failures
    self.schedule(
        self.machine_failure,
        delay=mtbf,
        args=(workstation,)
    )

def machine_failure(self, workstation):
    """Handle machine failure."""
    workstation.server.set_down()
    repair_time = self.rng.exponential(30)
    self.schedule(
        self.machine_repair,
        delay=repair_time,
        args=(workstation,)
    )
```

### Multiple Product Types

```python
product_a = ProductType(
    name="ProductA",
    steps=[Step("WS-1"), Step("WS-2"), Step("WS-3")],
    qt_constraints=[QTConstraint(0, 2, max_time=60)]
)

product_b = ProductType(
    name="ProductB",
    steps=[Step("WS-1"), Step("WS-3"), Step("WS-4"), Step("WS-5")],
    qt_constraints=[QTConstraint(1, 3, max_time=90)]
)
```

## Source Code

The complete source code is in `simcraft/examples/manufacturing.py`.
