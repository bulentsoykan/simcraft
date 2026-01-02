"""
Activity and state machine framework.

This module provides components for modeling activities (time-based
operations) and state machines for complex entity lifecycle management.
"""

from simcraft.activities.activity import Activity, ActivityState
from simcraft.activities.state_machine import StateMachine, State, Transition

__all__ = ["Activity", "ActivityState", "StateMachine", "State", "Transition"]
