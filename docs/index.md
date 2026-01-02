```{image} _static/simcraft_logo.png
:alt: SimCraft
:width: 400px
:align: center
```

# SimCraft Documentation

**SimCraft** is a discrete event simulation (DES) framework for Python, designed for academic research, industrial applications, and integration with optimization algorithms including reinforcement learning.

[![PyPI](https://img.shields.io/pypi/v/simcraft.svg)](https://pypi.org/project/simcraft/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Key Features

- **Event-Driven Architecture**: O(log n) event scheduling with priority support
- **Hierarchical Composition**: Build complex models from reusable components
- **Rich Resource Management**: Servers, queues, resources, and resource pools
- **Comprehensive Statistics**: Counters, tallies, time-series, and monitors
- **20+ Random Distributions**: Reproducible random number generation
- **Optimization Integration**: Native support for simulation-optimization and RL
- **Full Type Hints**: Complete type annotations for IDE support

## Quick Example

```python
import simcraft

class HelloWorld(simcraft.Simulation):
    def on_init(self):
        self.schedule(self.say_hello, delay=1.0)

    def say_hello(self):
        print(f"Hello at time {self.now}!")
        self.schedule(self.say_hello, delay=1.0)

sim = HelloWorld()
sim.run(until=5.0)
```

## Getting Started

```{toctree}
:maxdepth: 2
:caption: Getting Started

installation
quickstart
```

## Tutorials

```{toctree}
:maxdepth: 2
:caption: Tutorials

tutorials/index
```

## Examples

```{toctree}
:maxdepth: 2
:caption: Examples

examples/index
```

## API Reference

```{toctree}
:maxdepth: 2
:caption: API Reference

api/index
```

## Project Information

```{toctree}
:maxdepth: 1
:caption: Project Info

changelog
```

## Indices and Tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
