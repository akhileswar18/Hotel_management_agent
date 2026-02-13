"""
BaseAgent — Abstract base class for all HMS agents.

Every agent must:
- Declare which events it subscribes to
- Declare which events it may publish
- Implement handle() to process events
- Declare whether it writes to DB and/or uses LLM
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from src.events.event import Event


class BaseAgent(ABC):
    """Abstract base class for HMS agents."""

    name: str = "BaseAgent"
    subscribes_to: List[str] = []
    publishes: List[str] = []
    writes_to_db: bool = False
    uses_llm: bool = False
    degradable: bool = False  # If True, system works without this agent

    @abstractmethod
    def handle(self, event: Event) -> Optional[Event]:
        """
        Process an event. Return a response Event or None.
        
        Args:
            event: The event to handle
            
        Returns:
            Response event (for request-reply) or None (for fire-and-forget)
        """
        pass

    def can_handle(self, event_type: str) -> bool:
        """Check if this agent handles the given event type."""
        for sub in self.subscribes_to:
            if sub == "*":
                return True
            if sub == event_type:
                return True
            if sub.endswith(".*"):
                prefix = sub[:-2]
                if event_type.startswith(prefix + "."):
                    return True
        return False

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name} subs={self.subscribes_to}>"
