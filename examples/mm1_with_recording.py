# ABOUTME: Example demonstrating visualization recording for an M/M/1 queue.
# ABOUTME: Generates animation.json for playback in the Three.js viewer.

"""
M/M/1 Queue with Visualization Recording.

This example demonstrates how to use the VisualizationRecorder to capture
simulation events for animated playback.

Usage:
    python examples/mm1_with_recording.py

This will generate an 'animation.json' file that can be loaded into the
Three.js visualization viewer.
"""

from simcraft import Simulation, Server, VisualizationRecorder
from simcraft.core.entity import Entity


class Customer(Entity):
    """A customer in the queueing system."""
    pass


def main():
    """Run M/M/1 queue simulation with recording."""
    # Create simulation
    sim = Simulation(name="MM1Queue")

    # Create server with exponential service time
    server = Server(
        sim,
        capacity=1,
        service_time=lambda: sim.rng.exponential(1.0),
        name="Teller",
    )

    # Create visualization recorder and track the server
    recorder = VisualizationRecorder(sim)
    recorder.track_server(server)

    # Generate arrivals using Poisson process (exponential interarrival times)
    arrival_rate = 0.8  # customers per time unit

    def generate_arrival():
        customer = Customer()
        server.enqueue(customer)
        # Schedule next arrival
        sim.schedule(generate_arrival, delay=sim.rng.exponential(1.0 / arrival_rate))

    # Schedule first arrival
    sim.schedule(generate_arrival, delay=0)

    # Run simulation
    sim.run(until=50.0)

    # Export animation data
    output_path = "animation.json"
    recorder.save(output_path)

    # Print summary
    print(f"Simulation completed at t={sim.now:.2f}")
    print(f"Server arrivals: {server.stats.arrivals}")
    print(f"Server departures: {server.stats.departures}")
    print(f"Server utilization: {server.stats.utilization:.2%}")
    print(f"\nRecorded {len(recorder.events)} events")
    print(f"Animation data saved to: {output_path}")

    # Show a preview of the JSON
    print("\nJSON Preview:")
    data = recorder.to_dict()
    print(f"  Version: {data['version']}")
    print(f"  Simulation: {data['simulation']['name']}")
    print(f"  Components: {list(data['components'].keys())}")
    print(f"  Event types: {set(e['type'] for e in data['events'])}")


if __name__ == "__main__":
    main()
