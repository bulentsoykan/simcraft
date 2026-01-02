---
title: 'SimCraft: A Discrete Event Simulation Framework for Python with Native Optimization and Reinforcement Learning Integration'
tags:
  - Python
  - discrete event simulation
  - reinforcement learning
  - optimization
  - simulation modeling
authors:
  - name: Bulent Soykan
    orcid: 0000-0002-7958-2650
    affiliation: 1
affiliations:
  - name: Independent Researcher
    index: 1
date: 1 January 2025
bibliography: paper.bib
---

# Summary

SimCraft is a discrete event simulation (DES) framework for Python designed to bridge the gap between traditional simulation modeling and modern optimization techniques, including reinforcement learning (RL). The framework provides a clean, object-oriented API for building hierarchical simulation models with comprehensive statistics collection, resource management, and native integration with optimization algorithms.

Unlike process-based simulation frameworks that rely on Python generators, SimCraft uses an event-driven architecture with O(log n) scheduling complexity, making it particularly suitable for integration with external optimization loops where simulations must be controlled programmatically. The framework includes built-in support for Gym-compatible RL environments, enabling researchers to apply deep reinforcement learning algorithms directly to simulation-based decision problems.

# Statement of Need

Discrete event simulation is a fundamental tool in operations research, manufacturing, logistics, and service systems analysis. While established Python frameworks like SimPy [@simpy] and Salabim [@salabim] provide robust simulation capabilities, they were not designed with optimization algorithm integration as a primary concern. Researchers working on simulation-optimization problems, particularly those involving reinforcement learning, often face significant implementation overhead when connecting simulation environments to learning algorithms.

SimCraft addresses this need by providing:

1. **Native RL Integration**: A built-in `RLInterface` that exposes simulations as Gym-compatible environments [@brockman2016openai], enabling direct use with popular RL libraries like Stable-Baselines3 [@stable-baselines3].

2. **Hierarchical Composition**: Support for building complex models from modular, reusable components with shared clocks and coordinated event handling, following patterns established in frameworks like O2DES.NET [@li2019o2des].

3. **Comprehensive Statistics**: Built-in collectors including tallies with Welford's online algorithm for numerical stability, time-weighted statistics for utilization metrics, and monitors for unified data export.

4. **Full Type Annotations**: Complete type hints throughout the codebase, improving developer experience and enabling static analysis tools.

The framework has been designed for academic research and industrial applications, including use cases inspired by Winter Simulation Conference challenges in semiconductor manufacturing [@wsc2023] and container port operations [@wsc2025].

# Key Features

SimCraft provides a layered architecture with four main components:

**Core Engine**: The simulation engine uses sorted containers for O(log n) event scheduling with priority support. Simulations support multiple execution modes (run until time, for duration, or by event count), warmup periods for steady-state analysis, and hierarchical nesting for modular model construction.

**Resource Management**: The framework includes rich resource primitives: `Server` for multi-server queueing stations, `Queue` for FIFO and priority-based waiting, `Resource` for acquire/release semantics with preemption support, and `ResourcePool` for distinguishable resources with custom selection policies.

**Statistics Collection**: Four collector types cover common analysis needs: `Counter` for event counting with rate calculation, `Tally` for observation-based statistics using Welford's algorithm, `TimeSeries` for time-weighted metrics equivalent to O2DES's HourCounter pattern, and `Monitor` for unified data collection with JSON and DataFrame export.

**Optimization Interface**: The `RLInterface` abstract class defines the contract for RL-compatible simulations, while `RLEnvironment` provides a Gym-compatible wrapper. Additional classes support state/action space definitions, experience replay buffers, and multi-agent scenarios.

# Example Applications

The package includes three documented example models demonstrating progressive complexity:

- **M/M/1 Queue**: A classic single-server queueing model with validation against theoretical steady-state values.
- **Manufacturing Simulation**: A semiconductor fabrication model with multi-step routing and quality time constraints, inspired by WSC 2023 benchmarks.
- **Port Terminal**: A container terminal with multiple resource types (berths, cranes, vehicles) and decision points suitable for RL-based optimization.

# Acknowledgements

SimCraft builds upon concepts from O2DES.NET, SimPy, and Salabim. The framework design was informed by challenges from the Winter Simulation Conference and the need for better integration between simulation and machine learning research.

# References
