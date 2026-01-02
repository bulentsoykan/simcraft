"""
Base optimization interface for simulation.

Provides abstractions for connecting simulation models to
optimization algorithms and sensitivity analysis.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)
from enum import Enum, auto
import json
import math

if TYPE_CHECKING:
    from simcraft.core.simulation import Simulation


class ObjectiveType(Enum):
    """Types of optimization objectives."""

    MINIMIZE = auto()
    MAXIMIZE = auto()


@dataclass
class Parameter:
    """
    A simulation parameter for optimization.

    Attributes
    ----------
    name : str
        Parameter name
    lower_bound : float
        Minimum value
    upper_bound : float
        Maximum value
    initial_value : float
        Starting value
    is_integer : bool
        Whether parameter must be integer
    description : str
        Parameter description
    """

    name: str
    lower_bound: float
    upper_bound: float
    initial_value: Optional[float] = None
    is_integer: bool = False
    description: str = ""

    def __post_init__(self) -> None:
        """Validate parameter."""
        if self.lower_bound > self.upper_bound:
            raise ValueError(
                f"Lower bound {self.lower_bound} > upper bound {self.upper_bound}"
            )
        if self.initial_value is None:
            self.initial_value = (self.lower_bound + self.upper_bound) / 2

    def validate(self, value: float) -> float:
        """
        Validate and clip value to bounds.

        Parameters
        ----------
        value : float
            Value to validate

        Returns
        -------
        float
            Validated value
        """
        value = max(self.lower_bound, min(self.upper_bound, value))
        if self.is_integer:
            value = round(value)
        return value


@dataclass
class SimulationObjective:
    """
    An objective function for optimization.

    Attributes
    ----------
    name : str
        Objective name
    direction : ObjectiveType
        Minimize or maximize
    weight : float
        Weight for multi-objective (default 1.0)
    target : Optional[float]
        Target value for satisfaction-based objectives
    """

    name: str
    direction: ObjectiveType = ObjectiveType.MINIMIZE
    weight: float = 1.0
    target: Optional[float] = None

    @property
    def is_minimization(self) -> bool:
        """Check if this is a minimization objective."""
        return self.direction == ObjectiveType.MINIMIZE

    def normalize(self, value: float, worst: float, best: float) -> float:
        """
        Normalize objective value to [0, 1].

        Parameters
        ----------
        value : float
            Raw objective value
        worst : float
            Worst observed value
        best : float
            Best observed value

        Returns
        -------
        float
            Normalized value (0 = worst, 1 = best)
        """
        if worst == best:
            return 0.5

        normalized = (value - worst) / (best - worst)

        if self.is_minimization:
            normalized = 1.0 - normalized

        return max(0.0, min(1.0, normalized))


@dataclass
class EvaluationResult:
    """
    Result of a simulation evaluation.

    Attributes
    ----------
    parameters : Dict[str, float]
        Parameter values used
    objectives : Dict[str, float]
        Objective values obtained
    constraints : Dict[str, bool]
        Constraint satisfaction
    simulation_time : float
        Final simulation time
    replications : int
        Number of replications
    metadata : Dict[str, Any]
        Additional evaluation data
    """

    parameters: Dict[str, float]
    objectives: Dict[str, float]
    constraints: Dict[str, bool] = field(default_factory=dict)
    simulation_time: float = 0.0
    replications: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_feasible(self) -> bool:
        """Check if all constraints are satisfied."""
        return all(self.constraints.values()) if self.constraints else True

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "parameters": self.parameters,
            "objectives": self.objectives,
            "constraints": self.constraints,
            "simulation_time": self.simulation_time,
            "replications": self.replications,
            "is_feasible": self.is_feasible,
            "metadata": self.metadata,
        }


class OptimizationInterface(ABC):
    """
    Abstract interface for simulation-optimization integration.

    Subclass this to create an optimizable simulation model.

    Examples
    --------
    >>> class MyOptModel(OptimizationInterface):
    ...     def get_parameters(self):
    ...         return [Parameter("capacity", 1, 10, is_integer=True)]
    ...
    ...     def get_objectives(self):
    ...         return [SimulationObjective("cost", ObjectiveType.MINIMIZE)]
    ...
    ...     def evaluate(self, params):
    ...         sim = MySimulation(capacity=params["capacity"])
    ...         sim.run(until=100)
    ...         return {"cost": sim.total_cost}
    """

    @abstractmethod
    def get_parameters(self) -> List[Parameter]:
        """
        Get list of optimization parameters.

        Returns
        -------
        List[Parameter]
            Optimization parameters
        """
        pass

    @abstractmethod
    def get_objectives(self) -> List[SimulationObjective]:
        """
        Get list of optimization objectives.

        Returns
        -------
        List[SimulationObjective]
            Optimization objectives
        """
        pass

    @abstractmethod
    def evaluate(
        self,
        parameters: Dict[str, float],
        replications: int = 1,
    ) -> Dict[str, float]:
        """
        Evaluate objective(s) for given parameters.

        Parameters
        ----------
        parameters : Dict[str, float]
            Parameter values
        replications : int
            Number of replications

        Returns
        -------
        Dict[str, float]
            Objective values
        """
        pass

    def get_constraints(self) -> List[Callable[[Dict[str, float]], bool]]:
        """
        Get constraint functions.

        Returns
        -------
        List[Callable]
            Constraint functions returning True if satisfied
        """
        return []

    def evaluate_full(
        self,
        parameters: Dict[str, float],
        replications: int = 1,
    ) -> EvaluationResult:
        """
        Full evaluation with constraints.

        Parameters
        ----------
        parameters : Dict[str, float]
            Parameter values
        replications : int
            Number of replications

        Returns
        -------
        EvaluationResult
            Complete evaluation result
        """
        objectives = self.evaluate(parameters, replications)

        # Check constraints
        constraints = {}
        for i, constraint in enumerate(self.get_constraints()):
            constraints[f"constraint_{i}"] = constraint(parameters)

        return EvaluationResult(
            parameters=parameters,
            objectives=objectives,
            constraints=constraints,
            replications=replications,
        )

    def get_parameter_bounds(self) -> Tuple[List[float], List[float]]:
        """
        Get parameter bounds as lists.

        Returns
        -------
        Tuple[List[float], List[float]]
            (lower_bounds, upper_bounds)
        """
        params = self.get_parameters()
        lower = [p.lower_bound for p in params]
        upper = [p.upper_bound for p in params]
        return lower, upper

    def get_initial_point(self) -> Dict[str, float]:
        """
        Get initial parameter values.

        Returns
        -------
        Dict[str, float]
            Initial parameter values
        """
        return {p.name: p.initial_value for p in self.get_parameters()}


class SimulationExperiment:
    """
    Manages simulation experiments for optimization.

    Handles parameter sampling, replication, and result collection.

    Parameters
    ----------
    interface : OptimizationInterface
        Optimization interface
    """

    def __init__(self, interface: OptimizationInterface) -> None:
        """Initialize experiment."""
        self._interface = interface
        self._results: List[EvaluationResult] = []
        self._best_result: Optional[EvaluationResult] = None

    @property
    def results(self) -> List[EvaluationResult]:
        """Get all evaluation results."""
        return self._results.copy()

    @property
    def best_result(self) -> Optional[EvaluationResult]:
        """Get best result found."""
        return self._best_result

    def run_evaluation(
        self,
        parameters: Dict[str, float],
        replications: int = 1,
    ) -> EvaluationResult:
        """
        Run a single evaluation.

        Parameters
        ----------
        parameters : Dict[str, float]
            Parameter values
        replications : int
            Number of replications

        Returns
        -------
        EvaluationResult
            Evaluation result
        """
        result = self._interface.evaluate_full(parameters, replications)
        self._results.append(result)
        self._update_best(result)
        return result

    def run_grid_search(
        self,
        levels: Dict[str, List[float]],
        replications: int = 1,
    ) -> List[EvaluationResult]:
        """
        Run full factorial grid search.

        Parameters
        ----------
        levels : Dict[str, List[float]]
            Parameter levels to test
        replications : int
            Replications per point

        Returns
        -------
        List[EvaluationResult]
            All results
        """
        import itertools

        params = list(levels.keys())
        values = list(levels.values())

        results = []
        for combo in itertools.product(*values):
            param_dict = dict(zip(params, combo))
            result = self.run_evaluation(param_dict, replications)
            results.append(result)

        return results

    def run_random_search(
        self,
        n_evaluations: int,
        replications: int = 1,
        seed: Optional[int] = None,
    ) -> List[EvaluationResult]:
        """
        Run random search.

        Parameters
        ----------
        n_evaluations : int
            Number of evaluations
        replications : int
            Replications per point
        seed : Optional[int]
            Random seed

        Returns
        -------
        List[EvaluationResult]
            All results
        """
        from simcraft.random.distributions import RandomGenerator

        rng = RandomGenerator(seed=seed)
        params = self._interface.get_parameters()

        results = []
        for _ in range(n_evaluations):
            param_dict = {}
            for p in params:
                if p.is_integer:
                    param_dict[p.name] = rng.randint(
                        int(p.lower_bound), int(p.upper_bound)
                    )
                else:
                    param_dict[p.name] = rng.uniform(p.lower_bound, p.upper_bound)

            result = self.run_evaluation(param_dict, replications)
            results.append(result)

        return results

    def _update_best(self, result: EvaluationResult) -> None:
        """Update best result if applicable."""
        if not result.is_feasible:
            return

        if self._best_result is None:
            self._best_result = result
            return

        # Simple comparison using first objective
        objectives = self._interface.get_objectives()
        if not objectives:
            return

        obj = objectives[0]
        current = result.objectives.get(obj.name, float("inf"))
        best = self._best_result.objectives.get(obj.name, float("inf"))

        if obj.is_minimization:
            if current < best:
                self._best_result = result
        else:
            if current > best:
                self._best_result = result

    def export_results(self, filename: str) -> None:
        """
        Export results to JSON file.

        Parameters
        ----------
        filename : str
            Output filename
        """
        data = {
            "parameters": [
                {
                    "name": p.name,
                    "lower_bound": p.lower_bound,
                    "upper_bound": p.upper_bound,
                    "is_integer": p.is_integer,
                }
                for p in self._interface.get_parameters()
            ],
            "objectives": [
                {
                    "name": o.name,
                    "direction": o.direction.name,
                    "weight": o.weight,
                }
                for o in self._interface.get_objectives()
            ],
            "results": [r.to_dict() for r in self._results],
            "best_result": self._best_result.to_dict() if self._best_result else None,
        }

        with open(filename, "w") as f:
            json.dump(data, f, indent=2)

    def clear(self) -> None:
        """Clear all results."""
        self._results.clear()
        self._best_result = None
