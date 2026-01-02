# Examples

Complete simulation examples demonstrating SimCraft capabilities.

## Available Examples

```{toctree}
:maxdepth: 2

mm1_queue
manufacturing
port_terminal
```

## Example Overview

| Example | Complexity | Concepts Demonstrated |
|---------|------------|----------------------|
| [M/M/1 Queue](mm1_queue) | Beginner | Basic events, server, statistics, theoretical validation |
| [Manufacturing](manufacturing) | Intermediate | Multi-step routing, constraints, batch processing |
| [Port Terminal](port_terminal) | Advanced | Multiple resources, decision points, RL integration |

## Running Examples

All examples can be run from the examples module:

```python
from simcraft.examples import mm1_queue, manufacturing, port_terminal

# Run M/M/1 queue
mm1_queue.run_mm1_example()

# Run manufacturing simulation
manufacturing.run_manufacturing_example()

# Run port terminal simulation
port_terminal.run_port_example()
```

Or run directly from the command line:

```bash
python -m simcraft.examples.mm1_queue
python -m simcraft.examples.manufacturing
python -m simcraft.examples.port_terminal
```

## Learning Path

1. **Start with M/M/1 Queue**: Learn the basics of event scheduling, servers, and statistics collection. Validate against theoretical results.

2. **Progress to Manufacturing**: Understand multi-step processes, quality constraints, and batch processing.

3. **Master Port Terminal**: See how to build complex simulations with multiple resource types and RL integration points.
