"""
Configuration loading utilities.

Supports YAML and JSON configuration files for simulation parameters.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar
from dataclasses import dataclass, field, fields, is_dataclass

T = TypeVar("T")


class ConfigLoader:
    """
    Load configuration from various file formats.

    Examples
    --------
    >>> config = ConfigLoader.load("config.yaml")
    >>> print(config["simulation"]["duration"])
    """

    @staticmethod
    def load(filepath: str) -> Dict[str, Any]:
        """
        Load configuration from file.

        Supports .yaml, .yml, and .json files.

        Parameters
        ----------
        filepath : str
            Path to configuration file

        Returns
        -------
        Dict[str, Any]
            Configuration dictionary
        """
        path = Path(filepath)

        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {filepath}")

        suffix = path.suffix.lower()

        if suffix in (".yaml", ".yml"):
            return ConfigLoader._load_yaml(path)
        elif suffix == ".json":
            return ConfigLoader._load_json(path)
        else:
            raise ValueError(f"Unsupported config format: {suffix}")

    @staticmethod
    def _load_yaml(path: Path) -> Dict[str, Any]:
        """Load YAML file."""
        try:
            import yaml
        except ImportError:
            raise ImportError("PyYAML is required for YAML config files")

        with open(path, "r") as f:
            return yaml.safe_load(f)

    @staticmethod
    def _load_json(path: Path) -> Dict[str, Any]:
        """Load JSON file."""
        with open(path, "r") as f:
            return json.load(f)

    @staticmethod
    def save(config: Dict[str, Any], filepath: str) -> None:
        """
        Save configuration to file.

        Parameters
        ----------
        config : Dict[str, Any]
            Configuration dictionary
        filepath : str
            Output path
        """
        path = Path(filepath)
        suffix = path.suffix.lower()

        if suffix in (".yaml", ".yml"):
            try:
                import yaml
            except ImportError:
                raise ImportError("PyYAML is required for YAML config files")

            with open(path, "w") as f:
                yaml.dump(config, f, default_flow_style=False)

        elif suffix == ".json":
            with open(path, "w") as f:
                json.dump(config, f, indent=2)
        else:
            raise ValueError(f"Unsupported config format: {suffix}")


@dataclass
class YAMLConfig:
    """
    Base class for typed configuration.

    Subclass this to create strongly-typed configuration classes.

    Examples
    --------
    >>> @dataclass
    ... class SimConfig(YAMLConfig):
    ...     duration: float = 100.0
    ...     warmup: float = 10.0
    ...     seed: int = 42
    ...
    >>> config = SimConfig.from_file("config.yaml")
    >>> print(config.duration)
    """

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """
        Create instance from dictionary.

        Parameters
        ----------
        data : Dict[str, Any]
            Configuration data

        Returns
        -------
        T
            Configuration instance
        """
        if not is_dataclass(cls):
            raise TypeError(f"{cls.__name__} must be a dataclass")

        # Filter to only known fields
        known_fields = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data.items() if k in known_fields}

        return cls(**filtered_data)

    @classmethod
    def from_file(cls: Type[T], filepath: str) -> T:
        """
        Create instance from file.

        Parameters
        ----------
        filepath : str
            Configuration file path

        Returns
        -------
        T
            Configuration instance
        """
        data = ConfigLoader.load(filepath)
        return cls.from_dict(data)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.

        Returns
        -------
        Dict[str, Any]
            Configuration dictionary
        """
        if not is_dataclass(self):
            raise TypeError("Must be a dataclass")

        result = {}
        for f in fields(self):
            value = getattr(self, f.name)
            if is_dataclass(value):
                result[f.name] = value.to_dict()
            else:
                result[f.name] = value
        return result

    def save(self, filepath: str) -> None:
        """
        Save to file.

        Parameters
        ----------
        filepath : str
            Output path
        """
        ConfigLoader.save(self.to_dict(), filepath)


@dataclass
class SimulationConfig(YAMLConfig):
    """
    Standard simulation configuration.

    Attributes
    ----------
    name : str
        Simulation name
    duration : float
        Total simulation time
    warmup : float
        Warmup period
    seed : int
        Random seed
    replications : int
        Number of replications
    time_unit : str
        Time unit (hours, minutes, etc.)
    """

    name: str = "Simulation"
    duration: float = 100.0
    warmup: float = 0.0
    seed: Optional[int] = None
    replications: int = 1
    time_unit: str = "hours"
    log_level: str = "WARNING"
    collect_trace: bool = False
