"""
Tests for core simulation components.
"""

import pytest
from simcraft.core.simulation import Simulation, SimulationConfig
from simcraft.core.event import Event, EventList
from simcraft.core.entity import Entity, TimedEntity, EntityState
from simcraft.core.clock import Clock, TimeUnit


class TestClock:
    """Tests for Clock class."""

    def test_initial_state(self):
        """Test clock initializes correctly."""
        clock = Clock()
        assert clock.now == 0.0
        assert clock.time_unit == TimeUnit.HOURS
        assert clock.is_warmed_up is True

    def test_advance(self):
        """Test clock advancement."""
        clock = Clock()
        clock.advance(5.0)
        assert clock.now == 5.0
        clock.advance(3.0)
        assert clock.now == 8.0

    def test_advance_to(self):
        """Test advancing to specific time."""
        clock = Clock()
        clock.advance_to(10.0)
        assert clock.now == 10.0

    def test_advance_to_past_raises(self):
        """Test that advancing to past raises error."""
        clock = Clock()
        clock.advance_to(5.0)
        with pytest.raises(ValueError):
            clock.advance_to(3.0)

    def test_warmup(self):
        """Test warmup period tracking."""
        clock = Clock()
        clock.set_warmup(10.0)
        assert clock.is_warmed_up is False
        clock.advance_to(5.0)
        assert clock.is_warmed_up is False
        clock.advance_to(15.0)
        assert clock.is_warmed_up is True

    def test_time_conversion(self):
        """Test time unit conversion."""
        clock = Clock(time_unit=TimeUnit.HOURS)
        clock.advance_to(2.0)
        assert clock.now_in(TimeUnit.MINUTES) == pytest.approx(120.0)
        assert clock.now_in(TimeUnit.SECONDS) == pytest.approx(7200.0)


class TestEvent:
    """Tests for Event class."""

    def test_event_creation(self):
        """Test event creation."""

        def action():
            pass

        event = Event(scheduled_time=5.0, action=action, index=1)
        assert event.scheduled_time == 5.0
        assert event.cancelled is False

    def test_event_ordering(self):
        """Test event ordering by time."""
        e1 = Event(scheduled_time=5.0, action=lambda: None, index=1)
        e2 = Event(scheduled_time=3.0, action=lambda: None, index=2)
        e3 = Event(scheduled_time=5.0, action=lambda: None, index=3)

        assert e2 < e1
        assert e1 < e3  # Same time, lower index first
        assert e2 < e3

    def test_event_priority(self):
        """Test priority-based ordering."""
        e1 = Event(scheduled_time=5.0, action=lambda: None, index=1, priority=0)
        e2 = Event(scheduled_time=5.0, action=lambda: None, index=2, priority=10)

        assert e2 < e1  # Higher priority first

    def test_event_invoke(self):
        """Test event invocation."""
        result = []

        def action(x):
            result.append(x)

        event = Event(scheduled_time=1.0, action=action, args=(42,), index=1)
        event.invoke()

        assert result == [42]

    def test_cancelled_event(self):
        """Test cancelled event doesn't invoke."""
        result = []

        def action():
            result.append(1)

        event = Event(scheduled_time=1.0, action=action, index=1)
        event.cancel()
        event.invoke()

        assert result == []


class TestEventList:
    """Tests for EventList class."""

    def test_add_and_pop(self):
        """Test adding and popping events."""
        events = EventList()
        e1 = Event(scheduled_time=5.0, action=lambda: None, index=1)
        e2 = Event(scheduled_time=3.0, action=lambda: None, index=2)

        events.add(e1)
        events.add(e2)

        assert len(events) == 2
        next_event = events.pop_next()
        assert next_event.scheduled_time == 3.0

    def test_peek(self):
        """Test peeking at next event."""
        events = EventList()
        e1 = Event(scheduled_time=5.0, action=lambda: None, index=1)
        events.add(e1)

        peeked = events.peek_next()
        assert peeked.scheduled_time == 5.0
        assert len(events) == 1  # Still there


class TestEntity:
    """Tests for Entity class."""

    def test_entity_creation(self):
        """Test entity creation."""
        entity = Entity()
        assert entity.state == EntityState.CREATED
        assert entity.index > 0

    def test_entity_unique_ids(self):
        """Test entities have unique indices."""
        e1 = Entity()
        e2 = Entity()
        assert e1.index != e2.index

    def test_entity_state_transitions(self):
        """Test entity state transitions."""
        entity = Entity()
        assert entity.state == EntityState.CREATED

        entity.activate()
        assert entity.state == EntityState.ACTIVE
        assert entity.is_active

        entity.wait()
        assert entity.state == EntityState.WAITING
        assert entity.is_waiting

        entity.complete()
        assert entity.state == EntityState.COMPLETED
        assert entity.is_completed

    def test_entity_attributes(self):
        """Test custom attributes."""
        entity = Entity()
        entity.set_attribute("priority", 5)
        entity.set_attribute("name", "test")

        assert entity.get_attribute("priority") == 5
        assert entity.get_attribute("name") == "test"
        assert entity.get_attribute("missing", "default") == "default"


class TestTimedEntity:
    """Tests for TimedEntity class."""

    def test_timed_entity_tracking(self):
        """Test time tracking."""
        entity = TimedEntity()
        entity.record_entry(0.0)
        entity.record_service_start(5.0)
        entity.record_service_end(10.0)
        entity.record_exit(12.0)

        assert entity.waiting_time == 5.0
        assert entity.service_time == 5.0
        assert entity.flow_time == 12.0


class TestSimulation:
    """Tests for Simulation class."""

    def test_simulation_creation(self):
        """Test simulation creation."""
        sim = Simulation()
        assert sim.now == 0.0
        assert sim.events_pending == 0

    def test_schedule_event(self):
        """Test event scheduling."""
        sim = Simulation()
        result = []

        def action():
            result.append(sim.now)

        sim.schedule(action, delay=5.0)
        assert sim.events_pending == 1

        sim.run(until=10.0)
        assert result == [5.0]

    def test_schedule_at_time(self):
        """Test scheduling at specific time."""
        sim = Simulation()
        result = []

        sim.schedule(lambda: result.append(sim.now), at=7.0)
        sim.run(until=10.0)

        assert result == [7.0]

    def test_run_until(self):
        """Test running until specific time."""
        sim = Simulation()
        sim.run(until=100.0)
        assert sim.now == 100.0

    def test_run_for_duration(self):
        """Test running for duration."""
        sim = Simulation()
        sim.schedule(lambda: None, delay=0)  # Need at least one event
        sim.run(for_duration=50.0)
        assert sim.now == 50.0

    def test_run_events_limit(self):
        """Test running limited events."""
        sim = Simulation()
        count = [0]

        def event():
            count[0] += 1
            sim.schedule(event, delay=1.0)

        sim.schedule(event, delay=0)
        sim.run(events=10)

        assert count[0] == 10

    def test_hierarchical_simulation(self):
        """Test parent-child simulation."""

        class Child(Simulation):
            pass

        parent = Simulation(name="Parent")
        child = Child(parent=parent, name="Child")

        assert child.parent == parent
        assert child.root == parent
        assert child.clock is parent.clock

    def test_event_cancellation(self):
        """Test event cancellation."""
        sim = Simulation()
        result = []

        event = sim.schedule(lambda: result.append(1), delay=5.0)
        sim.cancel_event(event)

        sim.run(until=10.0)
        assert result == []

    def test_random_generator(self):
        """Test RNG access."""
        sim = Simulation(config=SimulationConfig(seed=42))
        value1 = sim.rng.uniform()
        sim.reset()
        value2 = sim.rng.uniform()

        # After reset with same seed, should get same values
        assert value1 == value2

    def test_on_init_hook(self):
        """Test on_init callback."""
        result = []

        class MySimulation(Simulation):
            def on_init(self):
                result.append("init")
                self.schedule(lambda: result.append("event"), delay=1.0)

        sim = MySimulation()
        sim.run(until=5.0)

        assert "init" in result
        assert "event" in result


class TestSimulationIntegration:
    """Integration tests for simulation."""

    def test_mm1_like_model(self):
        """Test M/M/1-like simulation."""
        sim = Simulation(config=SimulationConfig(seed=42))
        arrivals = []
        departures = []

        def arrive():
            arrivals.append(sim.now)
            # Service time
            service = sim.rng.exponential(1.0)
            sim.schedule(depart, delay=service)
            # Next arrival
            interarrival = sim.rng.exponential(2.0)
            sim.schedule(arrive, delay=interarrival)

        def depart():
            departures.append(sim.now)

        sim.schedule(arrive, delay=0)
        sim.run(until=100.0)

        assert len(arrivals) > 0
        assert len(departures) > 0
        assert len(departures) <= len(arrivals)

    def test_step_execution(self):
        """Test step-by-step execution."""
        sim = Simulation()
        result = []

        sim.schedule(lambda: result.append(1), delay=1.0)
        sim.schedule(lambda: result.append(2), delay=2.0)
        sim.schedule(lambda: result.append(3), delay=3.0)

        sim.step()
        assert result == [1]

        sim.step()
        assert result == [1, 2]

        sim.step()
        assert result == [1, 2, 3]

        # No more events
        has_more = sim.step()
        assert has_more is False
