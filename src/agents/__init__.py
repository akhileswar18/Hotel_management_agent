"""
Agents Package — Agent registry and factory.

All agents register with the AgentRegistry, which the EventBus uses
to dispatch events to the correct handlers.
"""

from src.agents.base import BaseAgent
from src.agents.registry import AgentRegistry

__all__ = ["BaseAgent", "AgentRegistry"]
