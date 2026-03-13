# ABOUTME: Visualization module for recording and exporting simulation events.
# ABOUTME: Provides VisualizationRecorder for animation playback support.

"""Visualization recording and export functionality."""

from simcraft.visualization.events import AnimationEvent, EventType
from simcraft.visualization.recorder import VisualizationRecorder

__all__ = [
    "AnimationEvent",
    "EventType",
    "VisualizationRecorder",
]
