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
  - name: University of Central Florida, Orlando, FL, USA
    index: 1
date: 1 January 2026
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

The framework has been designed for academic research and industrial applications, including use cases inspired by Winter Simulation Conference challenges in semiconductor manufacturing and container port operations.

# Software Design

SimCraft's architecture reflects three deliberate trade-offs. First, we chose an event-driven, object-oriented paradigm over the process-based generator approach used by SimPy and Salabim. While generators provide elegant syntax for sequential processes, they complicate programmatic control—pausing mid-process, extracting state, or resetting simulations requires workarounds that conflict with optimization loop requirements. Event-driven design makes simulation state explicitly accessible, which is essential for RL algorithms that must observe, act, and reset repeatedly.

Second, we implemented hierarchical composition through parent-child relationships with automatic clock sharing. Child simulations inherit their parent's clock and event queue, enabling modular model construction where components (e.g., a Workstation) can be developed independently and composed into larger systems (e.g., a Factory). This pattern does not exist in current Python DES frameworks.

Third, we integrated RL interfaces at the framework level rather than as an external adapter. State spaces, action spaces, and reward signals are first-class concepts, reducing the implementation overhead that researchers typically face when connecting simulations to learning algorithms.

**Build vs. Contribute Justification**: These architectural choices are incompatible with SimPy's generator-centric design and would require fundamental restructuring rather than incremental contribution. SimCraft addresses a different design point in the DES solution space—one optimized for optimization algorithm integration rather than process modeling convenience.

# Key Features

SimCraft provides a layered architecture with four main components:

**Core Engine**: The simulation engine uses sorted containers for O(log n) event scheduling with priority support. Simulations support multiple execution modes (run until time, for duration, or by event count), warmup periods for steady-state analysis, and hierarchical nesting for modular model construction.

**Resource Management**: The framework includes rich resource primitives: `Server` for multi-server queueing stations, `Queue` for FIFO and priority-based waiting, `Resource` for acquire/release semantics with preemption support, and `ResourcePool` for distinguishable resources with custom selection policies.

**Statistics Collection**: Four collector types cover common analysis needs: `Counter` for event counting with rate calculation, `Tally` for observation-based statistics using Welford's algorithm, `TimeSeries` for time-weighted metrics, and `Monitor` for unified data collection with JSON and DataFrame export.

**Optimization Interface**: The `RLInterface` abstract class defines the contract for RL-compatible simulations, while `RLEnvironment` provides a Gym-compatible wrapper. Additional classes support state/action space definitions, experience replay buffers, and multi-agent scenarios.

# Example Applications

The package includes three documented example models demonstrating progressive complexity:

- **M/M/1 Queue**: A classic single-server queueing model with validation against theoretical steady-state values.
- **Manufacturing Simulation**: A semiconductor fabrication model with multi-step routing and quality time constraints, inspired by WSC 2023 benchmarks.
- **Port Terminal**: A container terminal with multiple resource types (berths, cranes, vehicles) and decision points suitable for RL-based optimization.

# Research Impact Statement

SimCraft addresses a documented gap in Python's simulation ecosystem: the lack of DES frameworks designed for optimization and reinforcement learning integration. While simulation-optimization is well-established in operations research, researchers currently face significant implementation overhead connecting Python simulations to modern RL libraries.

**Credible Near-Term Significance**: The framework provides novel capability through its native Gym-compatible RL interface, eliminating the adapter code typically required to use DES environments with libraries like Stable-Baselines3. Benchmark validation against M/M/1 theoretical values confirms correctness of the core engine. The included manufacturing and port terminal examples demonstrate applicability to established research domains, including WSC simulation challenges.

**Community Readiness**: SimCraft is available on PyPI (`pip install simcraft`), licensed under MIT, and includes comprehensive documentation on ReadTheDocs. The test suite covers core functionality with pytest. The GitHub repository accepts contributions and issue reports.

**Early Adoption Signals**: Following public announcement, the framework has received inquiries from industry practitioners exploring integration with digital twin platforms, suggesting relevance to both academic and industrial applications. The hierarchical composition pattern has generated discussion among simulation practitioners regarding its applicability to complex system modeling.

# AI Usage Disclosure

Generative AI tools were not used in the creation of SimCraft's core software implementation. 

# Acknowledgements

SimCraft builds upon concepts from O2DES.NET, SimPy, and Salabim. The framework design was informed by challenges from the need for better integration between simulation and machine learning research.

# References
