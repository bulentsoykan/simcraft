# ABOUTME: Tests for the visualization recording module.
# ABOUTME: Verifies event capture, callback wrapping, and JSON export.

"""Tests for visualization recording functionality."""

import json
import pytest
from simcraft.core.simulation import Simulation
from simcraft.core.entity import Entity
from simcraft.resources.server import Server
from simcraft.visualization.recorder import VisualizationRecorder
from simcraft.visualization.events import AnimationEvent, EventType


class Customer(Entity):
    """Test entity for visualization tests."""
    pass


class TestAnimationEvent:
    """Tests for AnimationEvent dataclass."""

    def test_event_creation(self):
        """Test creating an animation event."""
        event = AnimationEvent(
            time=1.5,
            event_type=EventType.ENTER_QUEUE,
            entity_id="Customer_1",
            location="Teller.queue",
        )
        assert event.time == 1.5
        assert event.event_type == EventType.ENTER_QUEUE
        assert event.entity_id == "Customer_1"
        assert event.location == "Teller.queue"

    def test_event_to_dict(self):
        """Test converting event to dictionary."""
        event = AnimationEvent(
            time=2.0,
            event_type=EventType.START_SERVICE,
            entity_id="Customer_1",
            location="Teller",
        )
        d = event.to_dict()
        assert d["t"] == 2.0
        assert d["type"] == "start_service"
        assert d["entity"] == "Customer_1"
        assert d["loc"] == "Teller"

    def test_entity_created_event(self):
        """Test entity_created event includes entity_type."""
        event = AnimationEvent(
            time=0.0,
            event_type=EventType.ENTITY_CREATED,
            entity_id="Customer_1",
            entity_type="Customer",
        )
        d = event.to_dict()
        assert d["type"] == "entity_created"
        assert d["entity_type"] == "Customer"


class TestVisualizationRecorder:
    """Tests for VisualizationRecorder class."""

    def test_recorder_creation(self):
        """Test creating a recorder."""
        sim = Simulation()
        recorder = VisualizationRecorder(sim)
        assert recorder is not None
        assert len(recorder.events) == 0
        assert len(recorder.components) == 0

    def test_track_server(self):
        """Test registering a server for tracking."""
        sim = Simulation()
        recorder = VisualizationRecorder(sim)
        server = Server(sim, capacity=1, service_time=5.0, name="Teller")

        recorder.track_server(server)

        assert "Teller" in recorder.components
        assert recorder.components["Teller"]["type"] == "server"
        assert recorder.components["Teller"]["capacity"] == 1

    def test_track_server_with_custom_name(self):
        """Test tracking server with custom name override."""
        sim = Simulation()
        recorder = VisualizationRecorder(sim)
        server = Server(sim, capacity=2, service_time=3.0, name="Original")

        recorder.track_server(server, name="CustomName")

        assert "CustomName" in recorder.components
        assert "Original" not in recorder.components

    def test_captures_arrival_event(self):
        """Test that arrival events are captured."""
        sim = Simulation()
        recorder = VisualizationRecorder(sim)
        server = Server(sim, capacity=1, service_time=5.0, name="Teller")

        recorder.track_server(server)

        customer = Customer()
        server.enqueue(customer)

        # Should have entity_created and either enter_queue or start_service
        assert len(recorder.events) >= 1

        # Check entity_created event exists
        created_events = [e for e in recorder.events if e.event_type == EventType.ENTITY_CREATED]
        assert len(created_events) == 1
        assert created_events[0].entity_id == customer.id
        assert created_events[0].entity_type == "Customer"

    def test_captures_service_start_event(self):
        """Test that service start events are captured."""
        sim = Simulation()
        recorder = VisualizationRecorder(sim)
        server = Server(sim, capacity=1, service_time=5.0, name="Teller")

        recorder.track_server(server)

        customer = Customer()
        server.enqueue(customer)

        # Server has capacity, so should go directly to service
        service_events = [e for e in recorder.events if e.event_type == EventType.START_SERVICE]
        assert len(service_events) == 1
        assert service_events[0].entity_id == customer.id
        assert service_events[0].location == "Teller"

    def test_captures_queue_event_when_busy(self):
        """Test that enter_queue events are captured when server is busy."""
        sim = Simulation()
        recorder = VisualizationRecorder(sim)
        server = Server(sim, capacity=1, service_time=5.0, name="Teller")

        recorder.track_server(server)

        # First customer goes to service
        customer1 = Customer()
        server.enqueue(customer1)

        # Second customer should queue
        customer2 = Customer()
        server.enqueue(customer2)

        queue_events = [e for e in recorder.events if e.event_type == EventType.ENTER_QUEUE]
        assert len(queue_events) == 1
        assert queue_events[0].entity_id == customer2.id
        assert queue_events[0].location == "Teller.queue"

    def test_captures_departure_event(self):
        """Test that departure events are captured."""
        sim = Simulation()
        recorder = VisualizationRecorder(sim)
        server = Server(sim, capacity=1, service_time=5.0, name="Teller")

        recorder.track_server(server)

        customer = Customer()
        server.enqueue(customer)

        # Run simulation to complete service
        sim.run(until=10.0)

        departure_events = [e for e in recorder.events if e.event_type == EventType.DEPART]
        assert len(departure_events) == 1
        assert departure_events[0].entity_id == customer.id
        assert departure_events[0].location == "Teller"
        assert departure_events[0].time == 5.0

    def test_captures_balk_event(self):
        """Test that balk events are captured when queue is full."""
        sim = Simulation()
        recorder = VisualizationRecorder(sim)
        # Server with capacity 1 and queue capacity 1 (only 1 waiting slot)
        server = Server(sim, capacity=1, service_time=5.0, queue_capacity=1, name="Teller")

        recorder.track_server(server)

        # First customer goes to service
        customer1 = Customer()
        server.enqueue(customer1)

        # Second customer goes to queue
        customer2 = Customer()
        server.enqueue(customer2)

        # Third customer should balk (queue full)
        customer3 = Customer()
        server.enqueue(customer3)

        balk_events = [e for e in recorder.events if e.event_type == EventType.BALK]
        assert len(balk_events) == 1
        assert balk_events[0].entity_id == customer3.id
        assert balk_events[0].location == "Teller"

    def test_preserves_existing_callbacks(self):
        """Test that user callbacks are still called after wrapping."""
        sim = Simulation()
        recorder = VisualizationRecorder(sim)
        server = Server(sim, capacity=1, service_time=5.0, name="Teller")

        # Set up user callback before tracking
        arrivals = []
        server.on_arrival(lambda e: arrivals.append(e))

        recorder.track_server(server)

        customer = Customer()
        server.enqueue(customer)

        # User callback should still be called
        assert len(arrivals) == 1
        assert arrivals[0] is customer

    def test_preserves_all_callback_types(self):
        """Test that all user callback types are preserved."""
        sim = Simulation()
        recorder = VisualizationRecorder(sim)
        # Queue capacity 1 so we can test balking
        server = Server(sim, capacity=1, service_time=5.0, queue_capacity=1, name="Teller")

        # Set up all user callbacks
        arrivals = []
        service_starts = []
        departures = []
        balks = []

        server.on_arrival(lambda e: arrivals.append(e))
        server.on_service_start(lambda e: service_starts.append(e))
        server.on_departure(lambda e: departures.append(e))
        server.on_balk(lambda e: balks.append(e))

        recorder.track_server(server)

        # Customer 1: arrives, starts service
        customer1 = Customer()
        server.enqueue(customer1)

        # Customer 2: arrives, goes to queue (capacity 1)
        customer2 = Customer()
        server.enqueue(customer2)

        # Customer 3: arrives, should balk (queue full)
        customer3 = Customer()
        server.enqueue(customer3)

        # Run simulation to let customer1 depart
        sim.run(until=6.0)

        assert len(arrivals) == 3
        assert len(service_starts) >= 1  # At least customer1
        assert len(departures) >= 1  # customer1 departed
        assert len(balks) == 1  # customer3 balked

    def test_event_timing(self):
        """Test that event times are recorded correctly."""
        sim = Simulation()
        recorder = VisualizationRecorder(sim)
        server = Server(sim, capacity=1, service_time=5.0, name="Teller")

        recorder.track_server(server)

        # Enqueue at t=0
        customer1 = Customer()
        server.enqueue(customer1)

        # Schedule another arrival at t=2
        def arrive_later():
            customer2 = Customer()
            server.enqueue(customer2)

        sim.schedule(arrive_later, delay=2.0)
        sim.run(until=3.0)

        # Check times
        created_events = [e for e in recorder.events if e.event_type == EventType.ENTITY_CREATED]
        assert created_events[0].time == 0.0
        assert created_events[1].time == 2.0


class TestVisualizationExport:
    """Tests for JSON export functionality."""

    def test_to_dict(self):
        """Test exporting recorder state to dictionary."""
        sim = Simulation(name="TestSimulation")
        recorder = VisualizationRecorder(sim)
        server = Server(sim, capacity=1, service_time=5.0, name="Teller")

        recorder.track_server(server)

        customer = Customer()
        server.enqueue(customer)
        sim.run(until=10.0)

        data = recorder.to_dict()

        assert "version" in data
        assert "simulation" in data
        assert "components" in data
        assert "events" in data

        assert data["simulation"]["name"] == "TestSimulation"
        assert "Teller" in data["components"]
        assert len(data["events"]) > 0

    def test_to_json(self):
        """Test exporting recorder state to JSON string."""
        sim = Simulation()
        recorder = VisualizationRecorder(sim)
        server = Server(sim, capacity=1, service_time=5.0, name="Teller")

        recorder.track_server(server)

        customer = Customer()
        server.enqueue(customer)
        sim.run(until=10.0)

        json_str = recorder.to_json()

        # Should be valid JSON
        data = json.loads(json_str)
        assert "events" in data
        assert len(data["events"]) > 0

    def test_save(self, tmp_path):
        """Test saving recorder state to file."""
        sim = Simulation()
        recorder = VisualizationRecorder(sim)
        server = Server(sim, capacity=1, service_time=5.0, name="Teller")

        recorder.track_server(server)

        customer = Customer()
        server.enqueue(customer)
        sim.run(until=10.0)

        # Save to temp file
        output_path = tmp_path / "animation.json"
        recorder.save(str(output_path))

        # Verify file contents
        assert output_path.exists()
        with open(output_path) as f:
            data = json.load(f)

        assert "events" in data
        assert len(data["events"]) > 0

    def test_event_order_in_export(self):
        """Test that events are exported in chronological order."""
        sim = Simulation()
        recorder = VisualizationRecorder(sim)
        server = Server(sim, capacity=1, service_time=5.0, name="Teller")

        recorder.track_server(server)

        # Create arrivals at different times
        customer1 = Customer()
        server.enqueue(customer1)

        sim.schedule(lambda: server.enqueue(Customer()), delay=1.0)
        sim.schedule(lambda: server.enqueue(Customer()), delay=2.0)

        sim.run(until=20.0)

        data = recorder.to_dict()
        events = data["events"]

        # Verify chronological order
        times = [e["t"] for e in events]
        assert times == sorted(times)


class TestIntegrationMM1Queue:
    """Integration tests using MM1Queue-like simulation."""

    def test_mm1_queue_recording(self):
        """Test recording a simple MM1 queue simulation."""
        sim = Simulation(name="MM1Queue")
        recorder = VisualizationRecorder(sim)

        server = Server(
            sim,
            capacity=1,
            service_time=lambda: sim.rng.exponential(1.0),
            name="Server"
        )
        recorder.track_server(server)

        # Generate arrivals
        arrivals = 0

        def customer_arrival():
            nonlocal arrivals
            if arrivals < 10:
                customer = Customer()
                server.enqueue(customer)
                arrivals += 1
                sim.schedule(customer_arrival, delay=sim.rng.exponential(1.2))

        sim.schedule(customer_arrival, delay=0)
        sim.run(until=50.0)

        # Should have recorded events for all customers
        data = recorder.to_dict()

        # Check we have the expected event types
        event_types = set(e["type"] for e in data["events"])
        assert "entity_created" in event_types
        assert "start_service" in event_types
        assert "depart" in event_types

        # Verify simulation metadata
        assert data["simulation"]["name"] == "MM1Queue"
        assert data["simulation"]["duration"] > 0  # Simulation ran for some time

    def test_multiple_servers(self):
        """Test recording with multiple servers."""
        sim = Simulation()
        recorder = VisualizationRecorder(sim)

        server1 = Server(sim, capacity=1, service_time=5.0, name="Server1")
        server2 = Server(sim, capacity=1, service_time=3.0, name="Server2")

        recorder.track_server(server1)
        recorder.track_server(server2)

        # Send customers to both servers
        server1.enqueue(Customer())
        server2.enqueue(Customer())

        sim.run(until=10.0)

        data = recorder.to_dict()

        # Should have both servers in components
        assert "Server1" in data["components"]
        assert "Server2" in data["components"]

        # Should have events for both
        locations = set(e.get("loc") for e in data["events"] if "loc" in e)
        assert "Server1" in locations
        assert "Server2" in locations
