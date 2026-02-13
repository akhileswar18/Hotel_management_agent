"""
InsightAgent — LLM advisory, read-only, async.

Subscribes to: insight.suggest_upsell, insight.analyze_trends, insight.natural_query.
Publishes: insight.suggestion, insight.analysis, insight.query_result, insight.error, insight.unavailable.
READ-ONLY: Never writes to DB. Degradable: system works 100% without LLM.
"""

from uuid import UUID
from typing import Optional, Any, Dict
from src.agents.base import BaseAgent
from src.agents.llm_client import LLMClient
from src.events.event import Event
from src.application import ReportingService, SalesService


class InsightAgent(BaseAgent):
    """LLM-powered advisory agent; read-only and degradable."""

    name = "InsightAgent"
    subscribes_to = [
        "insight.suggest_upsell",
        "insight.analyze_trends",
        "insight.natural_query",
    ]
    publishes = [
        "insight.suggestion",
        "insight.analysis",
        "insight.query_result",
        "insight.error",
        "insight.unavailable",
    ]
    writes_to_db = False
    uses_llm = True
    degradable = True

    def __init__(self):
        self.llm = LLMClient()
        self.reporting = ReportingService()
        self.sales_service = SalesService()

    def handle(self, event: Event) -> Optional[Event]:
        handlers = {
            "insight.suggest_upsell": self._suggest_upsell,
            "insight.analyze_trends": self._analyze_trends,
            "insight.natural_query": self._handle_query,
        }
        handler = handlers.get(event.type)
        if handler:
            try:
                return handler(event)
            except Exception as e:
                return Event.create(
                    type="insight.error",
                    source=self.name,
                    correlation_id=event.correlation_id,
                    payload={"message": str(e), "event_type": event.type},
                    user_id=event.user_id,
                )
        return None

    def _suggest_upsell(self, event: Event) -> Event:
        order_id = event.payload.get("order_id")
        if not order_id:
            return Event.create(
                type="insight.error",
                source=self.name,
                correlation_id=event.correlation_id,
                payload={"message": "order_id required"},
                user_id=event.user_id,
            )
        try:
            order = self.sales_service.get_order(UUID(order_id))
        except (ValueError, TypeError):
            order = None
        if not order:
            return Event.create(
                type="insight.error",
                source=self.name,
                correlation_id=event.correlation_id,
                payload={"message": "Order not found", "order_id": order_id},
                user_id=event.user_id,
            )
        order_items = [
            {"name": li.item_name, "quantity": li.quantity}
            for li in order.line_items
        ]
        summary = self.reporting.daily_sales_summary(None)
        top_items = summary.get("top_items", [])
        inv = self.reporting.inventory_snapshot()
        catalog = [{"name": i["name"], "category": i.get("category", "")} for i in inv.get("inventory", [])[:30]]
        popular = [t.get("name", "") for t in top_items] if top_items else [c["name"] for c in catalog[:10]]
        prompt = (
            f"Given order items: {order_items}. "
            f"Suggest 1-3 complementary upsell items from this list (or similar): {popular}. "
            f"Available catalog (sample): {catalog[:15]}. "
            "Respond with a JSON array of strings, e.g. [\"Item A\", \"Item B\"]."
        )
        result = self.llm.query(prompt, system_prompt="You are a restaurant upsell advisor. Reply only with a JSON array of item names.")
        if result is None:
            return Event.create(
                type="insight.unavailable",
                source=self.name,
                correlation_id=event.correlation_id,
                payload={"order_id": order_id, "message": "LLM unavailable or timed out"},
                user_id=event.user_id,
            )
        suggestions = self._parse_json_array(result)
        return Event.create(
            type="insight.suggestion",
            source=self.name,
            correlation_id=event.correlation_id,
            payload={"suggestions": suggestions, "order_id": order_id, "raw": result},
            user_id=event.user_id,
        )

    def _analyze_trends(self, event: Event) -> Event:
        from datetime import date
        payload = event.payload or {}
        report_date = payload.get("date")
        if isinstance(report_date, str) and report_date:
            try:
                report_date = date.fromisoformat(report_date)
            except ValueError:
                report_date = None
        summary = self.reporting.daily_sales_summary(report_date)
        prompt = (
            f"Based on this daily sales summary, give 2-3 short bullet insights (trends, recommendations): {summary}. "
            "Keep each bullet to one line."
        )
        result = self.llm.query(prompt, system_prompt="You are a restaurant analytics advisor.")
        if result is None:
            return Event.create(
                type="insight.unavailable",
                source=self.name,
                correlation_id=event.correlation_id,
                payload={"message": "LLM unavailable or timed out"},
                user_id=event.user_id,
            )
        return Event.create(
            type="insight.analysis",
            source=self.name,
            correlation_id=event.correlation_id,
            payload={"analysis": result, "summary": summary},
            user_id=event.user_id,
        )

    def _handle_query(self, event: Event) -> Event:
        question = (event.payload or {}).get("question", "").strip()
        if not question:
            return Event.create(
                type="insight.error",
                source=self.name,
                correlation_id=event.correlation_id,
                payload={"message": "question required"},
                user_id=event.user_id,
            )
        summary = self.reporting.daily_sales_summary(None)
        transactions = self.reporting.search_transactions()
        inventory = self.reporting.inventory_snapshot()
        context = {
            "daily_sales": summary,
            "recent_transactions_count": len(transactions),
            "sample_transactions": transactions[:5],
            "inventory_summary": {
                "total_items": inventory.get("total_items", 0),
                "low_stock_count": inventory.get("low_stock_count", 0),
            },
        }
        prompt = (
            f"Question: {question}\n\n"
            f"Context (restaurant data): {context}\n\n"
            "Answer briefly based only on the context. If the context does not contain enough information, say so."
        )
        result = self.llm.query(prompt, system_prompt="You are a restaurant data assistant. Answer concisely.")
        if result is None:
            return Event.create(
                type="insight.unavailable",
                source=self.name,
                correlation_id=event.correlation_id,
                payload={"message": "LLM unavailable or timed out"},
                user_id=event.user_id,
            )
        return Event.create(
            type="insight.query_result",
            source=self.name,
            correlation_id=event.correlation_id,
            payload={"answer": result, "question": question},
            user_id=event.user_id,
        )

    @staticmethod
    def _parse_json_array(text: str) -> list:
        """Try to extract a JSON array from LLM response."""
        import json
        text = (text or "").strip()
        start_idx = text.find("[")
        if start_idx < 0:
            return []
        end_idx = text.rfind("]")
        if end_idx < start_idx:
            return []
        try:
            parsed = json.loads(text[start_idx : end_idx + 1])
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except (json.JSONDecodeError, TypeError):
            pass
        return []
