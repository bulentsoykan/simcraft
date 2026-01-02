# Installation

## Requirements

- Python 3.8 or higher
- sortedcontainers >= 2.4.0
- numpy >= 1.20.0

## Install from PyPI

The simplest way to install SimCraft is from PyPI:

```bash
pip install simcraft
```

## Optional Dependencies

SimCraft provides optional dependency groups for additional functionality:

### Visualization

For plotting and data analysis capabilities:

```bash
pip install simcraft[visualization]
```

This includes:
- matplotlib >= 3.5.0
- pandas >= 1.4.0

### Reinforcement Learning

For RL integration with PyTorch:

```bash
pip install simcraft[rl]
```

This includes:
- torch >= 2.0.0

### All Dependencies

To install all optional dependencies:

```bash
pip install simcraft[all]
```

### Development

For development and testing:

```bash
pip install simcraft[dev]
```

This includes:
- pytest >= 7.0.0
- pytest-cov >= 4.0.0
- black >= 23.0.0
- mypy >= 1.0.0

## Install from Source

To install the latest development version:

```bash
git clone https://github.com/bulentsoykan/simcraft.git
cd simcraft
pip install -e .
```

For development with all dependencies:

```bash
pip install -e ".[dev,all]"
```

## Verify Installation

Verify that SimCraft is installed correctly:

```python
import simcraft
print(simcraft.__version__)
```

Run a simple test:

```python
class TestSimulation(simcraft.Simulation):
    def on_init(self):
        self.schedule(lambda: print(f"Time: {self.now}"), delay=1.0)

sim = TestSimulation()
sim.run(until=1.0)
# Output: Time: 1.0
```
