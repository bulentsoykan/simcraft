"""
Tests for resource management components.
"""

import pytest
from simcraft.core.simulation import Simulation
from simcraft.core.entity import Entity
from simcraft.resources.queue import Queue, PriorityQueue
from simcraft.resources.server import Server
from simcraft.resources.resource import Resource, PreemptiveResource
from simcraft.resources.pool import ResourcePool


class TestQueue:
    """Tests for Queue class."""

    def test_queue_creation(self):
        """Test queue creation."""
        sim = Simulation()
        queue = Queue(sim, capacity=10, name="TestQueue")
        assert len(queue) == 0
        assert queue.is_empty
        assert not queue.is_full

    def test_enqueue_dequeue(self):
        """Test basic enqueue/dequeue."""
        sim = Simulation()
        queue = Queue(sim)
        entity = Entity()

        queue.enqueue(entity)
        assert len(queue) == 1

        result = queue.dequeue()
        assert result is entity
        assert len(queue) == 0

    def test_fifo_order(self):
        """Test FIFO ordering."""
        sim = Simulation()
        queue = Queue(sim)

        e1 = Entity(id="first")
        e2 = Entity(id="second")
        e3 = Entity(id="third")

        queue.enqueue(e1)
        queue.enqueue(e2)
        queue.enqueue(e3)

        assert queue.dequeue() is e1
        assert queue.dequeue() is e2
        assert queue.dequeue() is e3

    def test_capacity_limit(self):
        """Test queue capacity limit."""
        sim = Simulation()
        queue = Queue(sim, capacity=2)

        assert queue.enqueue(Entity()) is True
        assert queue.enqueue(Entity()) is True
        assert queue.enqueue(Entity()) is False  # Full
        assert queue.is_full

    def test_statistics(self):
        """Test queue statistics."""
        sim = Simulation()
        queue = Queue(sim)

        e1 = Entity()
        queue.enqueue(e1)
        sim._clock.advance(5.0)  # Wait 5 time units
        queue.dequeue()

        assert queue.stats.entries == 1
        assert queue.stats.exits == 1


class TestPriorityQueue:
    """Tests for PriorityQueue class."""

    def test_priority_ordering(self):
        """Test priority ordering."""
        sim = Simulation()

        class PriorityEntity(Entity):
            def __init__(self, priority: int):
                super().__init__()
                self.priority = priority

        queue = PriorityQueue(sim, priority_fn=lambda e: e.priority)

        e1 = PriorityEntity(priority=5)
        e2 = PriorityEntity(priority=1)  # Highest priority (lowest number)
        e3 = PriorityEntity(priority=3)

        queue.enqueue(e1)
        queue.enqueue(e2)
        queue.enqueue(e3)

        assert queue.dequeue().priority == 1
        assert queue.dequeue().priority == 3
        assert queue.dequeue().priority == 5


class TestServer:
    """Tests for Server class."""

    def test_server_creation(self):
        """Test server creation."""
        sim = Simulation()
        server = Server(sim, capacity=2, service_time=5.0)
        assert server.capacity == 2
        assert server.is_idle

    def test_single_server(self):
        """Test single server processing."""
        sim = Simulation()
        departures = []

        server = Server(sim, capacity=1, service_time=5.0)
        server.on_departure(lambda e: departures.append(e))

        entity = Entity()
        server.enqueue(entity)

        sim.run(until=10.0)
        assert len(departures) == 1
        assert departures[0] is entity

    def test_parallel_servers(self):
        """Test parallel server capacity."""
        sim = Simulation()
        departures = []

        server = Server(sim, capacity=2, service_time=5.0)
        server.on_departure(lambda e: departures.append(sim.now))

        server.enqueue(Entity())
        server.enqueue(Entity())

        sim.run(until=10.0)

        # Both should complete at t=5 (parallel processing)
        assert len(departures) == 2
        assert all(t == 5.0 for t in departures)

    def test_queueing(self):
        """Test server queueing when busy."""
        sim = Simulation()
        server = Server(sim, capacity=1, service_time=5.0)

        e1 = Entity(id="first")
        e2 = Entity(id="second")

        server.enqueue(e1)
        server.enqueue(e2)

        assert server.queue_length == 1
        assert server.in_service_count == 1

    def test_random_service_time(self):
        """Test random service time function."""
        sim = Simulation(config={"seed": 42})

        def random_service():
            return sim.rng.exponential(5.0)

        server = Server(sim, capacity=1, service_time=random_service)
        server.enqueue(Entity())

        sim.run(until=100.0)
        # Service should complete within reasonable time


class TestResource:
    """Tests for Resource class."""

    def test_acquire_release(self):
        """Test basic acquire/release."""
        sim = Simulation()
        resource = Resource(sim, capacity=1)

        entity = Entity()
        assert resource.acquire(entity) is True
        assert resource.available == 0

        assert resource.release(entity) is True
        assert resource.available == 1

    def test_multiple_units(self):
        """Test multi-unit resource."""
        sim = Simulation()
        resource = Resource(sim, capacity=3)

        e1 = Entity()
        e2 = Entity()

        resource.acquire(e1, quantity=2)
        assert resource.available == 1

        resource.acquire(e2, quantity=1)
        assert resource.available == 0

    def test_waiting_queue(self):
        """Test waiting for resource."""
        sim = Simulation()
        resource = Resource(sim, capacity=1)

        e1 = Entity()
        e2 = Entity()
        acquired = []

        resource.acquire(e1)
        resource.request(e2, callback=lambda r, e: acquired.append(e))

        assert len(acquired) == 0  # Waiting

        resource.release(e1)
        assert len(acquired) == 1  # Now acquired


class TestResourcePool:
    """Tests for ResourcePool class."""

    def test_pool_creation(self):
        """Test pool creation."""
        sim = Simulation()
        pool = ResourcePool(sim, name="TestPool")

        pool.add_resource("Resource1", id="R1")
        pool.add_resource("Resource2", id="R2")

        assert pool.size == 2
        assert pool.available_count == 2

    def test_pool_acquire_release(self):
        """Test pool acquire/release."""
        sim = Simulation()
        pool = ResourcePool(sim)

        class Machine:
            def __init__(self, id):
                self.id = id

        pool.add_resource(Machine("M1"), id="M1")
        pool.add_resource(Machine("M2"), id="M2")

        entity = Entity()
        machine = pool.acquire(entity)

        assert machine is not None
        assert pool.available_count == 1

        pool.release(machine)
        assert pool.available_count == 2

    def test_pool_custom_selection(self):
        """Test custom resource selection."""
        sim = Simulation()
        pool = ResourcePool(sim)

        class LocatedResource:
            def __init__(self, x):
                self.x = x

        pool.add_resource(LocatedResource(10), id="R1")
        pool.add_resource(LocatedResource(5), id="R2")
        pool.add_resource(LocatedResource(15), id="R3")

        # Select nearest to x=0
        def nearest(resources):
            return min(resources, key=lambda r: abs(r.x))

        entity = Entity()
        resource = pool.acquire(entity, selector=nearest)

        assert resource.x == 5
