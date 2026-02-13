"""
AgentRegistry — Maps event types to agent handlers.
"""

from typing import Dict, List, Optional
from src.agents.base import BaseAgent


class AgentRegistry:
    """Registry that maps event types to agent handlers."""

    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        """Register an agent. Its subscriptions are automatically resolved during dispatch."""
        self._agents[agent.name] = agent

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get agent by name."""
        return self._agents.get(name)

    def get_subscribers(self, event_type: str) -> List[BaseAgent]:
        """Get all agents that subscribe to the given event type."""
        return [
            agent for agent in self._agents.values()
            if agent.can_handle(event_type)
        ]

    def list_agents(self) -> List[BaseAgent]:
        """List all registered agents."""
        return list(self._agents.values())

    @property
    def agent_count(self) -> int:
        return len(self._agents)
