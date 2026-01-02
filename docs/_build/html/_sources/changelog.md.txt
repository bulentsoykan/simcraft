# Changelog

All notable changes to SimCraft will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-12-28

### Added

- **Core Simulation Engine**
  - `Simulation` class with event scheduling and hierarchical composition
  - `SimulationConfig` for execution parameters
  - Multiple execution modes: `run(until=...)`, `run(for_duration=...)`, `step()`
  - Warmup period support with automatic statistics reset

- **Entity Framework**
  - `Entity` base class with state tracking
  - `TimedEntity` with automatic timing (entry, service start, exit)
  - `EntityFactory` for entity creation
  - `EntityPool` for object recycling and performance optimization

- **Event Management**
  - `Event` with priority support
  - `ConditionalEvent` for conditional execution
  - `EventList` with O(log n) operations
  - Event tagging and bulk cancellation

- **Resource Management**
  - `Server` for multi-server processing stations
  - `Queue` with FIFO ordering and statistics
  - `PriorityQueue` with heap-based implementation
  - `Resource` with acquire/release semantics
  - `PreemptiveResource` for preemption support
  - `ResourcePool` for distinguishable resources
  - Rich callback system (on_arrival, on_service_start, on_departure)

- **Statistics Collection**
  - `Counter` with rate calculation
  - `WindowedCounter` with sliding window statistics
  - `Tally` using Welford's algorithm for online computation
  - `TimeSeries` for time-weighted statistics
  - `Monitor` for unified data collection
  - `SimulationRecorder` for execution history

- **Activity Framework**
  - `Activity` for time-based operations with capacity
  - `ParallelActivity` for batch processing
  - `State` and `Transition` for state machines
  - `StateMachine` for complex entity lifecycles

- **Random Number Generation**
  - `RandomGenerator` with 20+ distributions
  - `RandomStream` with checkpointing
  - `StreamManager` for independent streams
  - `CommonRandomNumbers` for variance reduction

- **Optimization Integration**
  - `OptimizationInterface` for simulation-optimization
  - `SimulationExperiment` for parameter evaluation
  - `RLInterface` for reinforcement learning
  - `RLEnvironment` for Gym compatibility
  - `ReplayBuffer` for experience replay
  - Multi-agent RL support

- **Utilities**
  - `ConfigLoader` for YAML/JSON configuration
  - `SimulationLogger` for structured logging
  - Visualization helpers for matplotlib

- **Example Models**
  - M/M/1 queue with theoretical validation
  - Manufacturing simulation (WSC 2023 style)
  - Port terminal simulation (WSC 2025 style)

### Documentation

- Complete API documentation with docstrings
- Quick start guide
- Tutorial examples
- ReadTheDocs integration
