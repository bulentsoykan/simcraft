"""
Port terminal simulation model (based on WSC 2025 challenge).

Simulates a container port terminal with:
- Vessel arrivals and berthing
- Quay cranes for loading/unloading
- AGVs for container transport
- Yard cranes for stacking
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple
from enum import Enum, auto
import math

from simcraft.core.simulation import Simulation, SimulationConfig
from simcraft.core.entity import TimedEntity
from simcraft.resources.pool import ResourcePool
from simcraft.resources.queue import Queue
from simcraft.statistics.time_series import TimeSeries
from simcraft.statistics.tally import Tally
from simcraft.statistics.counter import Counter


class VesselState(Enum):
    """Vessel lifecycle states."""

    WAITING = auto()
    BERTHING = auto()
    DISCHARGING = auto()
    LOADING = auto()
    DEPARTING = auto()
    DEPARTED = auto()


@dataclass
class Container(TimedEntity):
    """
    A shipping container.

    Attributes
    ----------
    is_discharge : bool
        True if being unloaded, False if being loaded
    vessel_id : str
        Associated vessel
    yard_block : Optional[str]
        Yard block location
    """

    is_discharge: bool = True
    vessel_id: str = ""
    yard_block: Optional[str] = None


@dataclass
class Vessel(TimedEntity):
    """
    A container vessel.

    Attributes
    ----------
    discharge_count : int
        Containers to unload
    load_count : int
        Containers to load
    arrival_time : float
        Scheduled arrival
    berth_id : Optional[str]
        Assigned berth
    state : VesselState
        Current state
    """

    discharge_count: int = 0
    load_count: int = 0
    arrival_time: float = 0.0
    berth_id: Optional[str] = None
    state: VesselState = VesselState.WAITING
    discharged: int = 0
    loaded: int = 0

    @property
    def total_containers(self) -> int:
        """Total containers to handle."""
        return self.discharge_count + self.load_count

    @property
    def is_complete(self) -> bool:
        """Check if all cargo operations complete."""
        return (
            self.discharged >= self.discharge_count
            and self.loaded >= self.load_count
        )


@dataclass
class Berth:
    """
    A vessel berth.

    Attributes
    ----------
    id : str
        Berth identifier
    num_qcs : int
        Number of quay cranes
    vessel : Optional[Vessel]
        Currently berthed vessel
    """

    id: str
    num_qcs: int = 3
    vessel: Optional[Vessel] = None

    @property
    def is_occupied(self) -> bool:
        """Check if berth is occupied."""
        return self.vessel is not None


@dataclass
class QuayCrane:
    """
    A quay crane for loading/unloading.

    Attributes
    ----------
    id : str
        Crane identifier
    berth_id : str
        Associated berth
    cycle_time : float
        Time per container move
    """

    id: str
    berth_id: str
    cycle_time: float = 2.0  # minutes per container


@dataclass
class AGV:
    """
    Automated Guided Vehicle.

    Attributes
    ----------
    id : str
        Vehicle identifier
    position : Tuple[float, float]
        Current (x, y) position
    speed : float
        Speed in units per minute
    is_loaded : bool
        Whether carrying container
    """

    id: str
    position: Tuple[float, float] = (0.0, 0.0)
    speed: float = 270.0  # meters per minute
    is_loaded: bool = False

    def travel_time(self, target: Tuple[float, float]) -> float:
        """Calculate travel time to target."""
        dx = abs(target[0] - self.position[0])
        dy = abs(target[1] - self.position[1])
        distance = dx + dy  # Manhattan distance
        return distance / self.speed


@dataclass
class YardBlock:
    """
    Container yard storage block.

    Attributes
    ----------
    id : str
        Block identifier
    position : Tuple[float, float]
        Block center position
    capacity : int
        Maximum containers
    containers : int
        Current container count
    """

    id: str
    position: Tuple[float, float] = (0.0, 0.0)
    capacity: int = 1000
    containers: int = 0

    @property
    def available_space(self) -> int:
        """Available storage slots."""
        return self.capacity - self.containers


class PortTerminal(Simulation):
    """
    Container port terminal simulation.

    Based on the WSC 2025 simulation challenge for port operations
    optimization with resource allocation decisions.

    Parameters
    ----------
    num_berths : int
        Number of berths
    num_qcs_per_berth : int
        Quay cranes per berth
    num_agvs : int
        Number of AGVs
    num_yard_blocks : int
        Number of yard blocks
    config : Optional[SimulationConfig]
        Simulation configuration
    decision_maker : Optional[Callable]
        Custom decision maker for RL integration

    Examples
    --------
    >>> sim = PortTerminal(num_berths=4, num_agvs=12)
    >>> sim.add_vessel_schedule([
    ...     (0, 100, 80),  # arrives at 0, 100 discharge, 80 load
    ...     (2, 150, 120),
    ... ])
    >>> sim.run(until=24*60)  # 24 hours
    >>> print(sim.report())
    """

    def __init__(
        self,
        num_berths: int = 4,
        num_qcs_per_berth: int = 3,
        num_agvs: int = 12,
        num_yard_blocks: int = 8,
        config: Optional[SimulationConfig] = None,
        decision_maker: Optional[Callable] = None,
    ) -> None:
        """Initialize port terminal simulation."""
        super().__init__(config=config, name="PortTerminal")

        # Configuration
        self.num_berths = num_berths
        self.num_qcs_per_berth = num_qcs_per_berth
        self.num_agvs = num_agvs
        self.num_yard_blocks = num_yard_blocks

        # Resources
        self.berths: Dict[str, Berth] = {}
        self.qcs: Dict[str, QuayCrane] = {}
        self.agv_pool = ResourcePool[AGV](self, name="AGVPool")
        self.yard_blocks: Dict[str, YardBlock] = {}

        self._setup_resources()

        # Queues
        self.vessel_queue: Queue[Vessel] = Queue(self, name="VesselQueue")
        self.container_queue: Queue[Container] = Queue(self, name="ContainerQueue")

        # Statistics
        self.vessels_arrived = Counter(name="vessels_arrived", _sim=self)
        self.vessels_departed = Counter(name="vessels_departed", _sim=self)
        self.containers_handled = Counter(name="containers_handled", _sim=self)

        self.vessel_wait_times = Tally(name="vessel_wait", keep_history=True, _sim=self)
        self.vessel_service_times = Tally(
            name="vessel_service", keep_history=True, _sim=self
        )
        self.berth_utilization = TimeSeries(self, name="berth_util", keep_history=True)

        # Vessels
        self.vessels: List[Vessel] = []
        self.active_vessels: List[Vessel] = []

        # Decision maker
        self.decision_maker = decision_maker or self._default_decision_maker

    def _setup_resources(self) -> None:
        """Create berths, cranes, AGVs, and yard blocks."""
        # Berths and quay cranes
        for i in range(self.num_berths):
            berth_id = f"B{i + 1}"
            self.berths[berth_id] = Berth(id=berth_id, num_qcs=self.num_qcs_per_berth)

            for j in range(self.num_qcs_per_berth):
                qc_id = f"QC{i * self.num_qcs_per_berth + j + 1}"
                self.qcs[qc_id] = QuayCrane(id=qc_id, berth_id=berth_id)

        # AGVs
        for i in range(self.num_agvs):
            agv = AGV(id=f"AGV{i + 1}", position=(0.0, 0.0))
            self.agv_pool.add_resource(agv, id=agv.id)

        # Yard blocks
        for i in range(self.num_yard_blocks):
            block_id = f"YB{i + 1}"
            # Arrange in 2 rows
            row = i // 4
            col = i % 4
            position = (100.0 + col * 50.0, 50.0 + row * 100.0)
            self.yard_blocks[block_id] = YardBlock(
                id=block_id, position=position, capacity=1000
            )

    def add_vessel_schedule(
        self, schedule: List[Tuple[float, int, int]]
    ) -> None:
        """
        Add vessel arrival schedule.

        Parameters
        ----------
        schedule : List[Tuple[float, int, int]]
            List of (arrival_time, discharge_count, load_count)
        """
        for arrival_time, discharge, load in schedule:
            vessel = Vessel(
                arrival_time=arrival_time,
                discharge_count=discharge,
                load_count=load,
            )
            self.vessels.append(vessel)

    def on_init(self) -> None:
        """Schedule vessel arrivals."""
        for vessel in self.vessels:
            self.schedule(
                self._vessel_arrival,
                at=vessel.arrival_time,
                args=(vessel,),
            )

    def _vessel_arrival(self, vessel: Vessel) -> None:
        """Handle vessel arrival."""
        vessel.record_entry(self.now)
        vessel.state = VesselState.WAITING
        self.vessels_arrived.increment()
        self.active_vessels.append(vessel)

        # Queue for berth
        self.vessel_queue.enqueue(vessel)

        # Try to allocate berth
        self._try_allocate_berth()

    def _try_allocate_berth(self) -> None:
        """Try to allocate berth to waiting vessel."""
        if self.vessel_queue.is_empty:
            return

        # Find available berth
        available_berths = [b for b in self.berths.values() if not b.is_occupied]
        if not available_berths:
            return

        # Use decision maker to select berth
        vessel = self.vessel_queue.peek()
        berth = self.decision_maker("select_berth", available_berths, vessel)

        if berth:
            self.vessel_queue.dequeue()
            self._berth_vessel(vessel, berth)

    def _berth_vessel(self, vessel: Vessel, berth: Berth) -> None:
        """Berth a vessel."""
        vessel.state = VesselState.BERTHING
        vessel.berth_id = berth.id
        berth.vessel = vessel

        self.berth_utilization.observe_change(1)

        # Record wait time
        wait_time = self.now - vessel.entry_time
        self.vessel_wait_times.observe(wait_time)

        vessel.record_service_start(self.now)

        # Start discharge operations
        self.schedule(self._start_discharge, delay=5.0, args=(vessel,))

    def _start_discharge(self, vessel: Vessel) -> None:
        """Start discharging containers from vessel."""
        vessel.state = VesselState.DISCHARGING

        # Schedule container discharges
        for i in range(vessel.discharge_count):
            container = Container(is_discharge=True, vessel_id=vessel.id)
            delay = i * 2.0 / self.num_qcs_per_berth  # Parallel QCs
            self.schedule(
                self._discharge_container,
                delay=delay,
                args=(vessel, container),
            )

    def _discharge_container(self, vessel: Vessel, container: Container) -> None:
        """Discharge a single container."""
        if vessel.state == VesselState.DEPARTED:
            return

        # Get AGV
        agv = self.agv_pool.acquire(vessel)
        if agv is None:
            # Retry later
            self.schedule(
                self._discharge_container, delay=1.0, args=(vessel, container)
            )
            return

        # Transport to yard
        yard_block = self._select_yard_block()
        if yard_block:
            travel_time = agv.travel_time(yard_block.position)
            self.schedule(
                self._complete_discharge,
                delay=travel_time,
                args=(vessel, container, agv, yard_block),
            )

    def _complete_discharge(
        self, vessel: Vessel, container: Container, agv: AGV, yard_block: YardBlock
    ) -> None:
        """Complete container discharge."""
        # Store in yard
        yard_block.containers += 1
        container.yard_block = yard_block.id

        # Release AGV
        agv.position = yard_block.position
        self.agv_pool.release(agv)

        vessel.discharged += 1
        self.containers_handled.increment()

        # Check if discharge complete
        if vessel.discharged >= vessel.discharge_count:
            self._start_loading(vessel)

    def _start_loading(self, vessel: Vessel) -> None:
        """Start loading containers onto vessel."""
        vessel.state = VesselState.LOADING

        if vessel.load_count == 0:
            self._vessel_departure(vessel)
            return

        # Schedule container loads
        for i in range(vessel.load_count):
            container = Container(is_discharge=False, vessel_id=vessel.id)
            delay = i * 2.0 / self.num_qcs_per_berth
            self.schedule(
                self._load_container, delay=delay, args=(vessel, container)
            )

    def _load_container(self, vessel: Vessel, container: Container) -> None:
        """Load a single container."""
        if vessel.state == VesselState.DEPARTED:
            return

        # Get AGV
        agv = self.agv_pool.acquire(vessel)
        if agv is None:
            self.schedule(self._load_container, delay=1.0, args=(vessel, container))
            return

        # Get container from yard
        yard_block = self._get_loading_block()
        if yard_block:
            travel_time = agv.travel_time(yard_block.position)
            self.schedule(
                self._complete_loading,
                delay=travel_time * 2,  # Round trip
                args=(vessel, container, agv, yard_block),
            )

    def _complete_loading(
        self, vessel: Vessel, container: Container, agv: AGV, yard_block: YardBlock
    ) -> None:
        """Complete container loading."""
        yard_block.containers = max(0, yard_block.containers - 1)

        # Release AGV
        self.agv_pool.release(agv)

        vessel.loaded += 1
        self.containers_handled.increment()

        # Check if loading complete
        if vessel.is_complete:
            self._vessel_departure(vessel)

    def _vessel_departure(self, vessel: Vessel) -> None:
        """Handle vessel departure."""
        vessel.state = VesselState.DEPARTED
        vessel.record_exit(self.now)

        # Free berth
        berth = self.berths.get(vessel.berth_id or "")
        if berth:
            berth.vessel = None
            self.berth_utilization.observe_change(-1)

        # Record statistics
        self.vessels_departed.increment()
        self.vessel_service_times.observe(vessel.flow_time)

        # Remove from active
        if vessel in self.active_vessels:
            self.active_vessels.remove(vessel)

        # Try next vessel
        self._try_allocate_berth()

    def _select_yard_block(self) -> Optional[YardBlock]:
        """Select yard block for container storage."""
        available = [b for b in self.yard_blocks.values() if b.available_space > 0]
        if not available:
            return None
        return min(available, key=lambda b: b.containers)

    def _get_loading_block(self) -> Optional[YardBlock]:
        """Get yard block with containers for loading."""
        available = [b for b in self.yard_blocks.values() if b.containers > 0]
        if not available:
            return None
        return max(available, key=lambda b: b.containers)

    def _default_decision_maker(
        self, decision_type: str, options: List, context: any
    ) -> any:
        """Default decision maker (FIFO/nearest)."""
        if decision_type == "select_berth" and options:
            return options[0]
        if decision_type == "select_agv" and options:
            return options[0]
        return options[0] if options else None

    def report(self) -> dict:
        """Generate summary report."""
        delayed_count = sum(
            1 for t in self.vessel_wait_times.get_history() if t[1] > 120
        )
        delayed_rate = delayed_count / max(1, self.vessels_departed.value)

        return {
            "simulation_time": self.now,
            "vessels_arrived": self.vessels_arrived.value,
            "vessels_departed": self.vessels_departed.value,
            "containers_handled": self.containers_handled.value,
            "average_wait_time": self.vessel_wait_times.mean,
            "average_service_time": self.vessel_service_times.mean,
            "delayed_vessel_rate": delayed_rate,
            "berth_utilization": self.berth_utilization.average_value / self.num_berths,
            "agv_utilization": self.agv_pool.get_average_utilization(),
        }


def run_port_example() -> None:
    """Run port terminal simulation example."""
    print("=" * 60)
    print("Port Terminal Simulation (WSC 2025 Style)")
    print("=" * 60)

    # Create simulation
    sim = PortTerminal(
        num_berths=4,
        num_qcs_per_berth=3,
        num_agvs=12,
        num_yard_blocks=8,
    )

    # Generate vessel schedule
    import random

    random.seed(42)
    schedule = []
    for i in range(20):
        arrival = i * 180 + random.uniform(-30, 30)  # Every 3 hours +/- 30 min
        discharge = random.randint(100, 300)
        load = random.randint(80, 250)
        schedule.append((arrival, discharge, load))

    sim.add_vessel_schedule(schedule)

    # Run simulation
    sim.run(until=24 * 60 * 7)  # One week

    # Print results
    report = sim.report()

    print(f"\nSimulation Time: {report['simulation_time'] / 60:.1f} hours")
    print(f"\nVessel Statistics:")
    print(f"  Arrived: {report['vessels_arrived']}")
    print(f"  Departed: {report['vessels_departed']}")
    print(f"  Delayed Rate (>2hr wait): {report['delayed_vessel_rate']:.1%}")

    print(f"\nPerformance Metrics:")
    print(f"  Average Wait Time: {report['average_wait_time']:.1f} minutes")
    print(f"  Average Service Time: {report['average_service_time']:.1f} minutes")
    print(f"  Containers Handled: {report['containers_handled']}")

    print(f"\nResource Utilization:")
    print(f"  Berths: {report['berth_utilization']:.1%}")
    print(f"  AGVs: {report['agv_utilization']:.1%}")


if __name__ == "__main__":
    run_port_example()
