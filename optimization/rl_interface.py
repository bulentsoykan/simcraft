"""
Reinforcement learning interface for simulation.

Provides abstractions for integrating simulation models with
RL agents, supporting both Gym-style and custom interfaces.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
)
from enum import Enum, auto
import numpy as np

if TYPE_CHECKING:
    from simcraft.core.simulation import Simulation

# Type aliases
State = Union[np.ndarray, Dict[str, Any]]
Action = Union[int, np.ndarray, Dict[str, Any]]
Reward = float


@dataclass
class Transition:
    """
    A single RL transition.

    Attributes
    ----------
    state : State
        State before action
    action : Action
        Action taken
    reward : Reward
        Reward received
    next_state : State
        State after action
    done : bool
        Whether episode ended
    info : Dict
        Additional information
    """

    state: State
    action: Action
    reward: Reward
    next_state: State
    done: bool = False
    info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionSpace:
    """
    Definition of action space.

    Attributes
    ----------
    type : str
        'discrete', 'continuous', or 'multi_discrete'
    n : Optional[int]
        Number of discrete actions
    shape : Optional[Tuple[int, ...]]
        Shape for continuous actions
    low : Optional[np.ndarray]
        Lower bounds for continuous
    high : Optional[np.ndarray]
        Upper bounds for continuous
    nvec : Optional[List[int]]
        Action counts for multi-discrete
    """

    type: str
    n: Optional[int] = None
    shape: Optional[Tuple[int, ...]] = None
    low: Optional[np.ndarray] = None
    high: Optional[np.ndarray] = None
    nvec: Optional[List[int]] = None

    @classmethod
    def discrete(cls, n: int) -> "ActionSpace":
        """Create discrete action space."""
        return cls(type="discrete", n=n)

    @classmethod
    def continuous(
        cls,
        shape: Tuple[int, ...],
        low: Union[float, np.ndarray] = -1.0,
        high: Union[float, np.ndarray] = 1.0,
    ) -> "ActionSpace":
        """Create continuous action space."""
        if isinstance(low, (int, float)):
            low = np.full(shape, low)
        if isinstance(high, (int, float)):
            high = np.full(shape, high)
        return cls(type="continuous", shape=shape, low=low, high=high)

    @classmethod
    def multi_discrete(cls, nvec: List[int]) -> "ActionSpace":
        """Create multi-discrete action space."""
        return cls(type="multi_discrete", nvec=nvec)


@dataclass
class StateSpace:
    """
    Definition of state space.

    Attributes
    ----------
    shape : Tuple[int, ...]
        State shape
    low : Optional[np.ndarray]
        Lower bounds (for bounded spaces)
    high : Optional[np.ndarray]
        Upper bounds (for bounded spaces)
    dtype : type
        Data type
    """

    shape: Tuple[int, ...]
    low: Optional[np.ndarray] = None
    high: Optional[np.ndarray] = None
    dtype: type = np.float32

    @classmethod
    def box(
        cls,
        shape: Tuple[int, ...],
        low: Union[float, np.ndarray] = -np.inf,
        high: Union[float, np.ndarray] = np.inf,
    ) -> "StateSpace":
        """Create box (continuous) state space."""
        if isinstance(low, (int, float)):
            low = np.full(shape, low)
        if isinstance(high, (int, float)):
            high = np.full(shape, high)
        return cls(shape=shape, low=low, high=high)


class RLInterface(ABC):
    """
    Abstract interface for RL-simulation integration.

    Subclass this to make a simulation model compatible with
    reinforcement learning agents.

    Examples
    --------
    >>> class PortRLInterface(RLInterface):
    ...     def __init__(self, sim):
    ...         self.sim = sim
    ...
    ...     def get_state(self):
    ...         return np.array([
    ...             self.sim.queue_length,
    ...             self.sim.utilization,
    ...         ])
    ...
    ...     def get_action_space(self):
    ...         return ActionSpace.discrete(4)  # 4 berths
    ...
    ...     def apply_action(self, action):
    ...         self.sim.allocate_berth(action)
    ...
    ...     def get_reward(self):
    ...         return -self.sim.waiting_time
    """

    @abstractmethod
    def get_state(self) -> State:
        """
        Get current state observation.

        Returns
        -------
        State
            Current state
        """
        pass

    @abstractmethod
    def get_action_space(self) -> ActionSpace:
        """
        Get action space definition.

        Returns
        -------
        ActionSpace
            Action space
        """
        pass

    @abstractmethod
    def get_state_space(self) -> StateSpace:
        """
        Get state space definition.

        Returns
        -------
        StateSpace
            State space
        """
        pass

    @abstractmethod
    def apply_action(self, action: Action) -> None:
        """
        Apply an action to the simulation.

        Parameters
        ----------
        action : Action
            Action to apply
        """
        pass

    @abstractmethod
    def get_reward(self) -> Reward:
        """
        Get reward for current state/action.

        Returns
        -------
        Reward
            Reward value
        """
        pass

    def is_done(self) -> bool:
        """
        Check if episode is done.

        Returns
        -------
        bool
            True if episode ended
        """
        return False

    def get_info(self) -> Dict[str, Any]:
        """
        Get additional information.

        Returns
        -------
        Dict[str, Any]
            Info dictionary
        """
        return {}

    def reset(self) -> State:
        """
        Reset environment and return initial state.

        Returns
        -------
        State
            Initial state
        """
        return self.get_state()


class RLEnvironment:
    """
    Gym-compatible wrapper for simulation-based RL.

    Wraps an RLInterface to provide a standard RL environment API.

    Parameters
    ----------
    interface : RLInterface
        RL interface implementation
    simulation : Simulation
        Simulation instance
    max_steps : int
        Maximum steps per episode

    Examples
    --------
    >>> env = RLEnvironment(interface, sim, max_steps=1000)
    >>> state = env.reset()
    >>> for _ in range(100):
    ...     action = agent.select_action(state)
    ...     state, reward, done, info = env.step(action)
    ...     if done:
    ...         break
    """

    def __init__(
        self,
        interface: RLInterface,
        simulation: "Simulation",
        max_steps: int = 10000,
    ) -> None:
        """Initialize environment."""
        self._interface = interface
        self._simulation = simulation
        self._max_steps = max_steps
        self._current_step = 0
        self._episode = 0
        self._total_reward = 0.0

        # History for experience replay
        self._history: List[Transition] = []

    @property
    def action_space(self) -> ActionSpace:
        """Get action space."""
        return self._interface.get_action_space()

    @property
    def observation_space(self) -> StateSpace:
        """Get observation (state) space."""
        return self._interface.get_state_space()

    @property
    def current_step(self) -> int:
        """Get current step in episode."""
        return self._current_step

    @property
    def episode(self) -> int:
        """Get current episode number."""
        return self._episode

    def reset(self) -> State:
        """
        Reset environment for new episode.

        Returns
        -------
        State
            Initial state
        """
        self._simulation.reset()
        self._current_step = 0
        self._total_reward = 0.0
        self._episode += 1
        return self._interface.reset()

    def step(self, action: Action) -> Tuple[State, Reward, bool, Dict[str, Any]]:
        """
        Take a step in the environment.

        Parameters
        ----------
        action : Action
            Action to take

        Returns
        -------
        Tuple[State, Reward, bool, Dict]
            (next_state, reward, done, info)
        """
        state = self._interface.get_state()

        # Apply action
        self._interface.apply_action(action)

        # Get results
        next_state = self._interface.get_state()
        reward = self._interface.get_reward()
        done = self._interface.is_done()
        info = self._interface.get_info()

        # Update counters
        self._current_step += 1
        self._total_reward += reward

        # Check max steps
        if self._current_step >= self._max_steps:
            done = True
            info["truncated"] = True

        # Record transition
        transition = Transition(
            state=state,
            action=action,
            reward=reward,
            next_state=next_state,
            done=done,
            info=info,
        )
        self._history.append(transition)

        return next_state, reward, done, info

    def get_history(self) -> List[Transition]:
        """Get transition history."""
        return self._history.copy()

    def clear_history(self) -> None:
        """Clear transition history."""
        self._history.clear()


class DecisionPoint:
    """
    Represents a decision point in the simulation.

    Used for event-driven RL where actions are taken at
    specific simulation events.

    Parameters
    ----------
    name : str
        Decision point name
    state_fn : Callable
        Function returning current state
    action_space : ActionSpace
        Available actions
    apply_fn : Callable
        Function to apply action
    reward_fn : Callable
        Function returning reward
    """

    def __init__(
        self,
        name: str,
        state_fn: Callable[[], State],
        action_space: ActionSpace,
        apply_fn: Callable[[Action], None],
        reward_fn: Callable[[], Reward],
    ) -> None:
        """Initialize decision point."""
        self.name = name
        self._state_fn = state_fn
        self._action_space = action_space
        self._apply_fn = apply_fn
        self._reward_fn = reward_fn

    @property
    def action_space(self) -> ActionSpace:
        """Get action space."""
        return self._action_space

    def get_state(self) -> State:
        """Get current state."""
        return self._state_fn()

    def apply_action(self, action: Action) -> None:
        """Apply action."""
        self._apply_fn(action)

    def get_reward(self) -> Reward:
        """Get reward."""
        return self._reward_fn()


class MultiAgentInterface:
    """
    Interface for multi-agent reinforcement learning.

    Supports multiple agents with potentially different
    action spaces and rewards.

    Parameters
    ----------
    n_agents : int
        Number of agents

    Examples
    --------
    >>> interface = MultiAgentInterface(n_agents=3)
    >>> interface.add_agent("berth_allocator", berth_space, berth_reward)
    >>> interface.add_agent("agv_dispatcher", agv_space, agv_reward)
    """

    def __init__(self, n_agents: int = 1) -> None:
        """Initialize multi-agent interface."""
        self._n_agents = n_agents
        self._agents: Dict[str, DecisionPoint] = {}
        self._shared_state_fn: Optional[Callable[[], State]] = None

    @property
    def n_agents(self) -> int:
        """Get number of agents."""
        return self._n_agents

    @property
    def agent_names(self) -> List[str]:
        """Get agent names."""
        return list(self._agents.keys())

    def add_agent(
        self,
        name: str,
        action_space: ActionSpace,
        reward_fn: Callable[[], Reward],
        state_fn: Optional[Callable[[], State]] = None,
        apply_fn: Optional[Callable[[Action], None]] = None,
    ) -> None:
        """
        Add an agent.

        Parameters
        ----------
        name : str
            Agent name
        action_space : ActionSpace
            Agent's action space
        reward_fn : Callable
            Agent's reward function
        state_fn : Optional[Callable]
            Agent's state function (uses shared if None)
        apply_fn : Optional[Callable]
            Action application function
        """
        self._agents[name] = DecisionPoint(
            name=name,
            state_fn=state_fn or self._shared_state_fn or (lambda: np.array([])),
            action_space=action_space,
            apply_fn=apply_fn or (lambda a: None),
            reward_fn=reward_fn,
        )

    def set_shared_state(self, state_fn: Callable[[], State]) -> None:
        """Set shared state function for all agents."""
        self._shared_state_fn = state_fn

    def get_agent(self, name: str) -> Optional[DecisionPoint]:
        """Get agent by name."""
        return self._agents.get(name)

    def get_states(self) -> Dict[str, State]:
        """Get states for all agents."""
        return {name: agent.get_state() for name, agent in self._agents.items()}

    def apply_actions(self, actions: Dict[str, Action]) -> None:
        """Apply actions for all agents."""
        for name, action in actions.items():
            if name in self._agents:
                self._agents[name].apply_action(action)

    def get_rewards(self) -> Dict[str, Reward]:
        """Get rewards for all agents."""
        return {name: agent.get_reward() for name, agent in self._agents.items()}


class ReplayBuffer:
    """
    Experience replay buffer for RL training.

    Stores transitions and supports random sampling for
    off-policy algorithms.

    Parameters
    ----------
    capacity : int
        Maximum buffer size
    """

    def __init__(self, capacity: int = 10000) -> None:
        """Initialize buffer."""
        self._capacity = capacity
        self._buffer: List[Transition] = []
        self._position = 0

    @property
    def size(self) -> int:
        """Get current buffer size."""
        return len(self._buffer)

    def push(self, transition: Transition) -> None:
        """
        Add transition to buffer.

        Parameters
        ----------
        transition : Transition
            Transition to add
        """
        if len(self._buffer) < self._capacity:
            self._buffer.append(transition)
        else:
            self._buffer[self._position] = transition

        self._position = (self._position + 1) % self._capacity

    def sample(self, batch_size: int) -> List[Transition]:
        """
        Sample random batch of transitions.

        Parameters
        ----------
        batch_size : int
            Number of transitions to sample

        Returns
        -------
        List[Transition]
            Sampled transitions
        """
        import random

        return random.sample(self._buffer, min(batch_size, len(self._buffer)))

    def sample_batch(
        self, batch_size: int
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Sample batch as numpy arrays.

        Parameters
        ----------
        batch_size : int
            Batch size

        Returns
        -------
        Tuple
            (states, actions, rewards, next_states, dones)
        """
        transitions = self.sample(batch_size)

        states = np.array([t.state for t in transitions])
        actions = np.array([t.action for t in transitions])
        rewards = np.array([t.reward for t in transitions])
        next_states = np.array([t.next_state for t in transitions])
        dones = np.array([t.done for t in transitions])

        return states, actions, rewards, next_states, dones

    def clear(self) -> None:
        """Clear buffer."""
        self._buffer.clear()
        self._position = 0
