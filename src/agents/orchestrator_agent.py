"""
OrchestratorAgent — Handles multi-step workflow events.

Decomposes high-level intents (e.g. create_order, stock_in) into ordered
sub-events and executes them sequentially. Rolls back (e.g. void order)
on step failure. Rule-based; does not write to DB or use LLM.
"""

from typing import Optional, List, Dict, Any
from src.agents.base import BaseAgent
from src.events.event import Event


class OrchestratorAgent(BaseAgent):
    """Rule-based workflow orchestrator; delegates to other agents."""

    name = "OrchestratorAgent"
    subscribes_to = ["workflow.multi_step"]
    publishes = ["workflow.completed", "workflow.failed", "workflow.step_completed"]
    writes_to_db = False
    uses_llm = False

    def __init__(self, event_bus=None):
        self.event_bus = event_bus

    def handle(self, event: Event) -> Optional[Event]:
        """Handle multi-step workflow events."""
        intent = event.payload.get("intent", {})
        steps = self._decompose_intent(intent)
        return self._execute_steps(steps, event)

    def _decompose_intent(self, intent: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse a high-level intent into ordered event sequence."""
        action = intent.get("action", "")
        steps = []

        if action == "create_order":
            steps.append({
                "type": "order.create",
                "payload": {
                    "table_id": intent.get("table_id", "1"),
                    "user_id": intent.get("user_id", ""),
                },
            })
            for item in intent.get("items", []):
                steps.append({
                    "type": "order.add_item",
                    "payload": {
                        "item_id": item["item_id"],
                        "quantity": item.get("quantity", 1),
                    },
                })
            if intent.get("payment_method"):
                steps.append({
                    "type": "order.finalize",
                    "payload": {
                        "payment_method": intent["payment_method"],
                        "amount_tendered": intent.get("amount", 0),
                    },
                })
        elif action == "stock_in":
            steps.append({"type": "inventory.stock_in", "payload": intent})
        elif action == "report":
            steps.append({"type": "report.daily_sales", "payload": intent})
        # ... other patterns

        return steps

    def _execute_steps(
        self, steps: List[Dict[str, Any]], original_event: Event
    ) -> Event:
        """Execute steps sequentially, rolling back on failure."""
        if not self.event_bus:
            return Event.create(
                type="workflow.failed",
                payload={"error": "No event bus"},
                source=self.name,
                correlation_id=original_event.correlation_id,
            )

        results = []
        order_id = None
        for i, step in enumerate(steps):
            payload = dict(step["payload"])
            if order_id and "order_id" not in payload:
                payload["order_id"] = order_id

            sub_event = Event.create(
                type=step["type"],
                source=self.name,
                payload=payload,
                user_id=original_event.user_id,
                correlation_id=original_event.correlation_id,
            )
            result = self.event_bus.publish_sync(sub_event)

            if not result.success or (
                result.event and result.event.type.endswith(".error")
            ):
                # Rollback: void the order if one was created
                if order_id:
                    void_event = Event.create(
                        type="order.void",
                        source=self.name,
                        payload={
                            "order_id": order_id,
                            "reason": "Workflow step failed",
                        },
                        user_id=original_event.user_id,
                        correlation_id=original_event.correlation_id,
                    )
                    self.event_bus.publish_sync(void_event)
                return Event.create(
                    type="workflow.failed",
                    source=self.name,
                    correlation_id=original_event.correlation_id,
                    payload={
                        "step": i,
                        "error": result.error or "Step failed",
                    },
                )

            # Extract order_id from first step if it was order.create
            if result.event and step["type"] == "order.create":
                order_id = result.event.payload.get("order_id")

            results.append({"step": i, "type": step["type"], "status": "ok"})

        return Event.create(
            type="workflow.completed",
            source=self.name,
            correlation_id=original_event.correlation_id,
            payload={
                "steps_completed": len(results),
                "order_id": order_id or "",
                "results": results,
            },
        )
