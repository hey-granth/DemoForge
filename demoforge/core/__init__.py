"""DemoForge core engine — browser automation, interaction planning, and video recording."""

from demoforge.core.browser import BrowserSession
from demoforge.core.discovery import InteractionDiscovery, InteractionElement
from demoforge.core.planner import InteractionPlanner, ActionPlan
from demoforge.core.executor import ExecutionController, ExecutionState, SafetyViolation
from demoforge.core.recorder import VideoProcessor

__all__ = [
    "BrowserSession",
    "InteractionDiscovery",
    "InteractionElement",
    "InteractionPlanner",
    "ActionPlan",
    "ExecutionController",
    "ExecutionState",
    "SafetyViolation",
    "VideoProcessor",
]

