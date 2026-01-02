"""
State machine framework for entity lifecycle management.

Provides a flexible state machine implementation for modeling
complex entity behaviors and workflows.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
)
from enum import Enum, auto

if TYPE_CHECKING:
    from simcraft.core.simulation import Simulation

T = TypeVar("T")


@dataclass
class State:
    """
    A state in a state machine.

    Attributes
    ----------
    name : str
        State identifier
    on_enter : Optional[Callable]
        Called when entering the state
    on_exit : Optional[Callable]
        Called when exiting the state
    on_stay : Optional[Callable]
        Called while staying in the state
    is_initial : bool
        Whether this is an initial state
    is_final : bool
        Whether this is a final state
    metadata : Dict
        Additional state metadata
    """

    name: str
    on_enter: Optional[Callable[[Any], None]] = None
    on_exit: Optional[Callable[[Any], None]] = None
    on_stay: Optional[Callable[[Any], None]] = None
    is_initial: bool = False
    is_final: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, State):
            return self.name == other.name
        if isinstance(other, str):
            return self.name == other
        return False

    def __str__(self) -> str:
        return self.name


@dataclass
class Transition:
    """
    A transition between states.

    Attributes
    ----------
    source : str
        Source state name
    target : str
        Target state name
    trigger : str
        Event that triggers the transition
    guard : Optional[Callable]
        Condition that must be true for transition
    action : Optional[Callable]
        Action to perform during transition
    priority : int
        Priority when multiple transitions match (higher = first)
    """

    source: str
    target: str
    trigger: str = ""
    guard: Optional[Callable[[Any], bool]] = None
    action: Optional[Callable[[Any], None]] = None
    priority: int = 0

    def can_fire(self, context: Any) -> bool:
        """Check if transition can fire."""
        if self.guard is None:
            return True
        return self.guard(context)

    def fire(self, context: Any) -> None:
        """Execute transition action."""
        if self.action is not None:
            self.action(context)


class StateMachine(Generic[T]):
    """
    Flexible state machine for entity lifecycle management.

    Supports hierarchical states, guards, actions, and timed transitions.

    Parameters
    ----------
    sim : Simulation
        Parent simulation
    name : str
        State machine name

    Examples
    --------
    >>> sm = StateMachine(sim, name="OrderProcess")
    >>>
    >>> # Define states
    >>> sm.add_state("created", is_initial=True)
    >>> sm.add_state("processing")
    >>> sm.add_state("shipped")
    >>> sm.add_state("delivered", is_final=True)
    >>>
    >>> # Define transitions
    >>> sm.add_transition("created", "processing", trigger="start")
    >>> sm.add_transition("processing", "shipped",
    ...                   trigger="complete",
    ...                   guard=lambda ctx: ctx.payment_verified)
    >>> sm.add_transition("shipped", "delivered", trigger="arrive")
    >>>
    >>> # Create instance and process
    >>> order = Order(id=1)
    >>> instance = sm.create_instance(order)
    >>> instance.trigger("start")  # -> processing
    >>> instance.trigger("complete")  # -> shipped (if payment verified)
    """

    def __init__(
        self,
        sim: "Simulation",
        name: str = "",
    ) -> None:
        """Initialize state machine."""
        self._sim = sim
        self._name = name or f"StateMachine_{id(self)}"

        self._states: Dict[str, State] = {}
        self._transitions: Dict[str, List[Transition]] = {}
        self._initial_state: Optional[str] = None

        # Global callbacks
        self._on_state_enter: Optional[Callable[[str, T], None]] = None
        self._on_state_exit: Optional[Callable[[str, T], None]] = None
        self._on_transition: Optional[Callable[[str, str, T], None]] = None

    @property
    def name(self) -> str:
        """Get state machine name."""
        return self._name

    @property
    def states(self) -> List[str]:
        """Get list of state names."""
        return list(self._states.keys())

    @property
    def initial_state(self) -> Optional[str]:
        """Get initial state name."""
        return self._initial_state

    def add_state(
        self,
        name: str,
        on_enter: Optional[Callable[[T], None]] = None,
        on_exit: Optional[Callable[[T], None]] = None,
        is_initial: bool = False,
        is_final: bool = False,
        **metadata: Any,
    ) -> State:
        """
        Add a state to the machine.

        Parameters
        ----------
        name : str
            State identifier
        on_enter : Optional[Callable]
            Called when entering state
        on_exit : Optional[Callable]
            Called when exiting state
        is_initial : bool
            Whether this is the initial state
        is_final : bool
            Whether this is a final state
        **metadata
            Additional state metadata

        Returns
        -------
        State
            The created state
        """
        state = State(
            name=name,
            on_enter=on_enter,
            on_exit=on_exit,
            is_initial=is_initial,
            is_final=is_final,
            metadata=metadata,
        )

        self._states[name] = state
        self._transitions[name] = []

        if is_initial:
            self._initial_state = name

        return state

    def add_transition(
        self,
        source: str,
        target: str,
        trigger: str = "",
        guard: Optional[Callable[[T], bool]] = None,
        action: Optional[Callable[[T], None]] = None,
        priority: int = 0,
    ) -> Transition:
        """
        Add a transition between states.

        Parameters
        ----------
        source : str
            Source state name
        target : str
            Target state name
        trigger : str
            Event trigger name (empty for automatic)
        guard : Optional[Callable]
            Condition for transition
        action : Optional[Callable]
            Action to perform during transition
        priority : int
            Priority (higher = checked first)

        Returns
        -------
        Transition
            The created transition
        """
        if source not in self._states:
            raise ValueError(f"Unknown source state: {source}")
        if target not in self._states:
            raise ValueError(f"Unknown target state: {target}")

        transition = Transition(
            source=source,
            target=target,
            trigger=trigger,
            guard=guard,
            action=action,
            priority=priority,
        )

        # Insert by priority (descending)
        transitions = self._transitions[source]
        insert_idx = 0
        for i, t in enumerate(transitions):
            if transition.priority > t.priority:
                insert_idx = i
                break
            insert_idx = i + 1
        transitions.insert(insert_idx, transition)

        return transition

    def add_timed_transition(
        self,
        source: str,
        target: str,
        duration: Union[float, Callable[[T], float]],
        action: Optional[Callable[[T], None]] = None,
    ) -> Transition:
        """
        Add a timed transition that fires after a duration.

        Parameters
        ----------
        source : str
            Source state name
        target : str
            Target state name
        duration : Union[float, Callable]
            Time to wait or function returning time
        action : Optional[Callable]
            Action to perform

        Returns
        -------
        Transition
            The created transition
        """
        # Store duration info in transition for later scheduling
        transition = self.add_transition(
            source=source,
            target=target,
            trigger=f"_timeout_{source}_{target}",
            action=action,
        )

        # Store duration for instance scheduling
        if not hasattr(self, "_timed_transitions"):
            self._timed_transitions = {}
        self._timed_transitions[transition.trigger] = duration

        return transition

    def get_state(self, name: str) -> Optional[State]:
        """
        Get a state by name.

        Parameters
        ----------
        name : str
            State name

        Returns
        -------
        Optional[State]
            The state or None
        """
        return self._states.get(name)

    def get_transitions_from(self, state: str) -> List[Transition]:
        """
        Get all transitions from a state.

        Parameters
        ----------
        state : str
            Source state name

        Returns
        -------
        List[Transition]
            Transitions from the state
        """
        return self._transitions.get(state, [])

    def create_instance(self, context: T) -> "StateMachineInstance[T]":
        """
        Create a new state machine instance.

        Parameters
        ----------
        context : T
            Context object (entity) for this instance

        Returns
        -------
        StateMachineInstance
            New instance in initial state
        """
        return StateMachineInstance(self, context)

    def on_state_enter(self, callback: Callable[[str, T], None]) -> None:
        """Set global callback for state entry."""
        self._on_state_enter = callback

    def on_state_exit(self, callback: Callable[[str, T], None]) -> None:
        """Set global callback for state exit."""
        self._on_state_exit = callback

    def on_transition(self, callback: Callable[[str, str, T], None]) -> None:
        """Set global callback for transitions."""
        self._on_transition = callback

    def __repr__(self) -> str:
        """Return detailed representation."""
        return (
            f"StateMachine(name={self._name!r}, "
            f"states={len(self._states)}, "
            f"initial={self._initial_state})"
        )


class StateMachineInstance(Generic[T]):
    """
    Instance of a state machine for a specific entity.

    Parameters
    ----------
    machine : StateMachine
        Parent state machine definition
    context : T
        Context object (entity)
    """

    def __init__(
        self,
        machine: StateMachine[T],
        context: T,
    ) -> None:
        """Initialize instance."""
        self._machine = machine
        self._context = context
        self._current_state: Optional[str] = None
        self._history: List[Tuple[float, str, str]] = []
        self._pending_timeouts: Dict[str, Any] = {}

        # Enter initial state
        if machine.initial_state:
            self._enter_state(machine.initial_state)

    @property
    def current_state(self) -> Optional[str]:
        """Get current state name."""
        return self._current_state

    @property
    def context(self) -> T:
        """Get context object."""
        return self._context

    @property
    def history(self) -> List[Tuple[float, str, str]]:
        """Get transition history (time, from_state, to_state)."""
        return self._history.copy()

    @property
    def is_in_final_state(self) -> bool:
        """Check if in a final state."""
        if self._current_state is None:
            return False
        state = self._machine.get_state(self._current_state)
        return state is not None and state.is_final

    def trigger(self, event: str) -> bool:
        """
        Trigger an event to potentially cause a transition.

        Parameters
        ----------
        event : str
            Event name

        Returns
        -------
        bool
            True if a transition occurred
        """
        if self._current_state is None:
            return False

        transitions = self._machine.get_transitions_from(self._current_state)

        for transition in transitions:
            if transition.trigger == event and transition.can_fire(self._context):
                self._execute_transition(transition)
                return True

        return False

    def can_trigger(self, event: str) -> bool:
        """
        Check if an event can cause a transition.

        Parameters
        ----------
        event : str
            Event name

        Returns
        -------
        bool
            True if a transition would occur
        """
        if self._current_state is None:
            return False

        transitions = self._machine.get_transitions_from(self._current_state)

        for transition in transitions:
            if transition.trigger == event and transition.can_fire(self._context):
                return True

        return False

    def force_state(self, state: str) -> None:
        """
        Force transition to a state (bypassing guards).

        Parameters
        ----------
        state : str
            Target state name
        """
        if state not in self._machine._states:
            raise ValueError(f"Unknown state: {state}")

        self._exit_current_state()
        self._enter_state(state)

    def _execute_transition(self, transition: Transition) -> None:
        """Execute a transition."""
        from_state = self._current_state
        to_state = transition.target

        # Exit current state
        self._exit_current_state()

        # Execute transition action
        transition.fire(self._context)

        # Global transition callback
        if self._machine._on_transition:
            self._machine._on_transition(from_state, to_state, self._context)

        # Record history
        self._history.append((self._machine._sim.now, from_state, to_state))

        # Enter new state
        self._enter_state(to_state)

    def _enter_state(self, state_name: str) -> None:
        """Enter a state."""
        self._current_state = state_name
        state = self._machine.get_state(state_name)

        if state:
            # State entry callback
            if state.on_enter:
                state.on_enter(self._context)

            # Global entry callback
            if self._machine._on_state_enter:
                self._machine._on_state_enter(state_name, self._context)

            # Schedule timed transitions
            self._schedule_timed_transitions(state_name)

    def _exit_current_state(self) -> None:
        """Exit current state."""
        if self._current_state is None:
            return

        state = self._machine.get_state(self._current_state)

        # Cancel pending timeouts
        for event in list(self._pending_timeouts.keys()):
            scheduled_event = self._pending_timeouts.pop(event)
            if scheduled_event:
                scheduled_event.cancel()

        if state:
            # State exit callback
            if state.on_exit:
                state.on_exit(self._context)

            # Global exit callback
            if self._machine._on_state_exit:
                self._machine._on_state_exit(self._current_state, self._context)

    def _schedule_timed_transitions(self, state_name: str) -> None:
        """Schedule any timed transitions from the state."""
        if not hasattr(self._machine, "_timed_transitions"):
            return

        transitions = self._machine.get_transitions_from(state_name)

        for transition in transitions:
            if transition.trigger in self._machine._timed_transitions:
                duration = self._machine._timed_transitions[transition.trigger]

                if callable(duration):
                    duration = duration(self._context)

                event = self._machine._sim.schedule(
                    self.trigger,
                    delay=duration,
                    args=(transition.trigger,),
                )

                self._pending_timeouts[transition.trigger] = event

    def __repr__(self) -> str:
        """Return detailed representation."""
        return (
            f"StateMachineInstance("
            f"machine={self._machine.name!r}, "
            f"state={self._current_state}, "
            f"context={self._context})"
        )


# Common state machine patterns


def create_simple_workflow(
    sim: "Simulation",
    states: List[str],
    name: str = "Workflow",
) -> StateMachine:
    """
    Create a simple linear workflow state machine.

    Parameters
    ----------
    sim : Simulation
        Parent simulation
    states : List[str]
        State names in order
    name : str
        Machine name

    Returns
    -------
    StateMachine
        Configured state machine

    Examples
    --------
    >>> sm = create_simple_workflow(sim, ["start", "step1", "step2", "end"])
    """
    sm: StateMachine = StateMachine(sim, name)

    for i, state in enumerate(states):
        sm.add_state(
            state, is_initial=(i == 0), is_final=(i == len(states) - 1)
        )

    for i in range(len(states) - 1):
        sm.add_transition(states[i], states[i + 1], trigger="next")

    return sm


def create_processing_workflow(
    sim: "Simulation",
    processing_time: Union[float, Callable[..., float]],
    name: str = "ProcessingWorkflow",
) -> StateMachine:
    """
    Create a workflow with timed processing state.

    Parameters
    ----------
    sim : Simulation
        Parent simulation
    processing_time : Union[float, Callable]
        Processing duration
    name : str
        Machine name

    Returns
    -------
    StateMachine
        Configured state machine
    """
    sm: StateMachine = StateMachine(sim, name)

    sm.add_state("waiting", is_initial=True)
    sm.add_state("processing")
    sm.add_state("completed", is_final=True)

    sm.add_transition("waiting", "processing", trigger="start")
    sm.add_timed_transition("processing", "completed", duration=processing_time)

    return sm
