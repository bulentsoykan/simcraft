"""
Manufacturing simulation model (based on WSC 2023 challenge).

Simulates a semiconductor fabrication facility with:
- Multiple workstations with tool capacity
- Multi-step production processes
- Quality time (QT) constraints
- Lot-based processing
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum, auto

from simcraft.core.simulation import Simulation, SimulationConfig
from simcraft.core.entity import TimedEntity, EntityState
from simcraft.resources.queue import Queue, PriorityQueue
from simcraft.statistics.time_series import TimeSeries
from simcraft.statistics.tally import Tally
from simcraft.statistics.counter import Counter


class LotState(Enum):
    """States for a manufacturing lot."""

    WAITING = auto()
    IN_SYSTEM = auto()
    BREACH = auto()
    DEPART = auto()
    EXIT = auto()


@dataclass
class Step:
    """
    A processing step in manufacturing.

    Attributes
    ----------
    id : str
        Step identifier
    workstation_id : str
        Workstation where step is performed
    stage_delay : float
        Setup/staging time
    run_delay : float
        Processing time
    """

    id: str
    workstation_id: str
    stage_delay: float
    run_delay: float


@dataclass
class QTLoop:
    """
    Quality time constraint between steps.

    If a lot takes longer than qt_limit between start_step
    and end_step, it breaches the QT constraint.

    Attributes
    ----------
    id : str
        QT loop identifier
    start_step_id : str
        Starting step
    end_step_id : str
        Ending step
    qt_limit : float
        Maximum allowed time
    """

    id: str
    start_step_id: str
    end_step_id: str
    qt_limit: float


@dataclass
class ProductType:
    """
    A type of product with its processing route.

    Attributes
    ----------
    id : str
        Product type identifier
    steps : List[Step]
        Ordered processing steps
    qt_loops : List[QTLoop]
        QT constraints for this product
    lot_count : int
        Number of lots to create
    """

    id: str
    steps: List[Step] = field(default_factory=list)
    qt_loops: List[QTLoop] = field(default_factory=list)
    lot_count: int = 1


@dataclass
class Lot(TimedEntity):
    """
    A manufacturing lot.

    Attributes
    ----------
    product_type : ProductType
        Type of product
    current_step_index : int
        Current position in route
    running_qt_loops : Dict
        Active QT constraints (id -> start_time)
    state : LotState
        Current lot state
    """

    product_type: Optional[ProductType] = None
    current_step_index: int = 0
    running_qt_loops: Dict[str, float] = field(default_factory=dict)
    lot_state: LotState = LotState.WAITING
    breached: bool = False

    @property
    def current_step(self) -> Optional[Step]:
        """Get current processing step."""
        if self.product_type is None:
            return None
        if self.current_step_index >= len(self.product_type.steps):
            return None
        return self.product_type.steps[self.current_step_index]

    @property
    def remaining_steps(self) -> int:
        """Get number of remaining steps."""
        if self.product_type is None:
            return 0
        return len(self.product_type.steps) - self.current_step_index

    def advance_step(self) -> bool:
        """Move to next step. Returns True if more steps remain."""
        self.current_step_index += 1
        return self.remaining_steps > 0


@dataclass
class Workstation:
    """
    A manufacturing workstation.

    Attributes
    ----------
    id : str
        Workstation identifier
    num_tools : int
        Number of parallel tools
    available_tools : int
        Currently available tools
    pending_lots : List[Lot]
        Lots waiting to process
    wip : List[Lot]
        Lots currently processing
    """

    id: str
    num_tools: int
    available_tools: int = 0
    pending_lots: List[Lot] = field(default_factory=list)
    wip: List[Lot] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Initialize available tools."""
        self.available_tools = self.num_tools

    @property
    def utilization(self) -> float:
        """Get current utilization."""
        if self.num_tools == 0:
            return 0.0
        return len(self.wip) / self.num_tools


class ManufacturingSimulation(Simulation):
    """
    Manufacturing job shop simulation.

    Based on the WSC 2023 simulation challenge for semiconductor
    fabrication optimization.

    Parameters
    ----------
    workstations : Dict[str, Workstation]
        Workstations by ID
    product_types : List[ProductType]
        Product types to manufacture
    arrival_interval : float
        Time between lot arrivals (minutes)
    config : Optional[SimulationConfig]
        Simulation configuration

    Examples
    --------
    >>> # Create workstations
    >>> ws = {
    ...     "WS1": Workstation(id="WS1", num_tools=2),
    ...     "WS2": Workstation(id="WS2", num_tools=1),
    ... }
    >>>
    >>> # Create product type
    >>> steps = [
    ...     Step("S1", "WS1", stage_delay=0.1, run_delay=1.0),
    ...     Step("S2", "WS2", stage_delay=0.1, run_delay=0.5),
    ... ]
    >>> product = ProductType(id="P1", steps=steps, lot_count=100)
    >>>
    >>> # Run simulation
    >>> sim = ManufacturingSimulation(ws, [product], arrival_interval=2.0)
    >>> sim.run(until=1000)
    >>> print(sim.report())
    """

    def __init__(
        self,
        workstations: Dict[str, Workstation],
        product_types: List[ProductType],
        arrival_interval: float = 1.0,
        config: Optional[SimulationConfig] = None,
    ) -> None:
        """Initialize manufacturing simulation."""
        super().__init__(config=config, name="ManufacturingSim")

        self.workstations = workstations
        self.product_types = product_types
        self.arrival_interval = arrival_interval

        # Statistics
        self.lots_arrived = Counter(name="lots_arrived", _sim=self)
        self.lots_completed = Counter(name="lots_completed", _sim=self)
        self.lots_breached = Counter(name="lots_breached", _sim=self)

        self.cycle_times = Tally(name="cycle_time", keep_history=True, _sim=self)
        self.wip_level = TimeSeries(self, name="wip", keep_history=True)

        self.workstation_stats: Dict[str, TimeSeries] = {}
        for ws_id in workstations:
            self.workstation_stats[ws_id] = TimeSeries(
                self, name=f"WS_{ws_id}_util", keep_history=True
            )

        # Lot queues
        self.lots: List[Lot] = []

    def on_init(self) -> None:
        """Schedule initial lot arrivals."""
        for product_type in self.product_types:
            for i in range(product_type.lot_count):
                delay = i * self.arrival_interval
                self.schedule(self._arrive, delay=delay, args=(product_type,))

    def _arrive(self, product_type: ProductType) -> None:
        """Handle lot arrival."""
        lot = Lot(product_type=product_type)
        lot.record_entry(self.now)
        lot.lot_state = LotState.IN_SYSTEM

        self.lots.append(lot)
        self.lots_arrived.increment()
        self.wip_level.observe_change(1)

        # Start processing
        self._attempt_to_stage(lot)

    def _attempt_to_stage(self, lot: Lot) -> None:
        """Try to move lot to its workstation."""
        step = lot.current_step
        if step is None:
            return

        workstation = self.workstations.get(step.workstation_id)
        if workstation is None:
            return

        # Add to pending queue
        workstation.pending_lots.append(lot)

        # Check and start QT loops
        self._check_qt_start(lot)

        # Schedule staging
        self.schedule(self._start_step, delay=step.stage_delay, args=(lot, workstation))

    def _check_qt_start(self, lot: Lot) -> None:
        """Check if any QT loops should start at this step."""
        step = lot.current_step
        if step is None or lot.product_type is None:
            return

        for qt_loop in lot.product_type.qt_loops:
            if qt_loop.start_step_id == step.id:
                lot.running_qt_loops[qt_loop.id] = self.now

    def _start_step(self, lot: Lot, workstation: Workstation) -> None:
        """Start processing a lot."""
        if lot not in workstation.pending_lots:
            return

        if workstation.available_tools <= 0:
            return

        # Move from pending to WIP
        workstation.pending_lots.remove(lot)
        workstation.wip.append(lot)
        workstation.available_tools -= 1

        # Update statistics
        self.workstation_stats[workstation.id].observe_change(1)

        lot.record_service_start(self.now)

        # Schedule completion
        step = lot.current_step
        if step:
            self.schedule(
                self._complete_step,
                delay=step.run_delay,
                args=(lot, workstation),
            )

    def _complete_step(self, lot: Lot, workstation: Workstation) -> None:
        """Complete processing at current step."""
        if lot not in workstation.wip:
            return

        # Free the tool
        workstation.wip.remove(lot)
        workstation.available_tools += 1

        # Update statistics
        self.workstation_stats[workstation.id].observe_change(-1)

        # Check QT violations
        self._check_qt_end(lot)

        # Move to next step or complete
        if lot.advance_step():
            self._attempt_to_stage(lot)
        else:
            self._depart(lot)

        # Try to start waiting lots
        self._try_start_pending(workstation)

    def _check_qt_end(self, lot: Lot) -> None:
        """Check if any QT loops end at this step."""
        step = lot.current_step
        if step is None or lot.product_type is None:
            return

        for qt_loop in lot.product_type.qt_loops:
            if qt_loop.end_step_id == step.id:
                if qt_loop.id in lot.running_qt_loops:
                    start_time = lot.running_qt_loops.pop(qt_loop.id)
                    elapsed = self.now - start_time

                    if elapsed > qt_loop.qt_limit:
                        lot.breached = True
                        lot.lot_state = LotState.BREACH
                        self.lots_breached.increment()

    def _try_start_pending(self, workstation: Workstation) -> None:
        """Try to start pending lots at workstation."""
        while workstation.pending_lots and workstation.available_tools > 0:
            lot = workstation.pending_lots[0]
            self._start_step(lot, workstation)

    def _depart(self, lot: Lot) -> None:
        """Lot completes all processing."""
        lot.record_exit(self.now)
        lot.lot_state = LotState.DEPART

        self.lots_completed.increment()
        self.wip_level.observe_change(-1)
        self.cycle_times.observe(lot.flow_time)

    def report(self) -> dict:
        """Generate summary report."""
        completed = self.lots_completed.value
        breached = self.lots_breached.value
        breach_rate = breached / completed if completed > 0 else 0

        ws_utils = {}
        for ws_id, ts in self.workstation_stats.items():
            ws = self.workstations[ws_id]
            if ws.num_tools > 0 and self.now > 0:
                ws_utils[ws_id] = ts.average_value / ws.num_tools
            else:
                ws_utils[ws_id] = 0.0

        return {
            "simulation_time": self.now,
            "lots_arrived": self.lots_arrived.value,
            "lots_completed": completed,
            "lots_breached": breached,
            "breach_rate": breach_rate,
            "average_cycle_time": self.cycle_times.mean,
            "average_wip": self.wip_level.average_value,
            "workstation_utilization": ws_utils,
        }


def run_manufacturing_example() -> None:
    """Run manufacturing simulation example."""
    print("=" * 60)
    print("Manufacturing Simulation (WSC 2023 Style)")
    print("=" * 60)

    # Create workstations
    workstations = {
        "WS1": Workstation(id="WS1", num_tools=3),
        "WS2": Workstation(id="WS2", num_tools=2),
        "WS3": Workstation(id="WS3", num_tools=2),
    }

    # Create product type with steps
    steps = [
        Step("S1", "WS1", stage_delay=0.5, run_delay=2.0),
        Step("S2", "WS2", stage_delay=0.3, run_delay=1.5),
        Step("S3", "WS3", stage_delay=0.3, run_delay=1.0),
        Step("S4", "WS1", stage_delay=0.2, run_delay=1.0),
    ]

    # QT constraint: must complete S2 within 5 minutes of starting S1
    qt_loops = [
        QTLoop(id="QT1", start_step_id="S1", end_step_id="S3", qt_limit=10.0)
    ]

    product = ProductType(
        id="Product_A",
        steps=steps,
        qt_loops=qt_loops,
        lot_count=500,
    )

    # Create and run simulation
    sim = ManufacturingSimulation(
        workstations=workstations,
        product_types=[product],
        arrival_interval=1.5,
    )

    sim.run(until=1000)

    # Print results
    report = sim.report()

    print(f"\nSimulation Time: {report['simulation_time']:.2f} minutes")
    print(f"\nLot Statistics:")
    print(f"  Arrived: {report['lots_arrived']}")
    print(f"  Completed: {report['lots_completed']}")
    print(f"  Breached: {report['lots_breached']}")
    print(f"  Breach Rate: {report['breach_rate']:.2%}")

    print(f"\nPerformance Metrics:")
    print(f"  Average Cycle Time: {report['average_cycle_time']:.2f} minutes")
    print(f"  Average WIP: {report['average_wip']:.2f} lots")

    print(f"\nWorkstation Utilization:")
    for ws_id, util in report["workstation_utilization"].items():
        print(f"  {ws_id}: {util:.2%}")


if __name__ == "__main__":
    run_manufacturing_example()
