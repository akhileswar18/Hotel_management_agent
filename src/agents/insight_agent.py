"""
InsightAgent — LLM advisory, read-only, async.

Subscribes to: insight.suggest_upsell, insight.analyze_trends, insight.natural_query.
Publishes: insight.suggestion, insight.analysis, insight.query_result, insight.error, insight.unavailable.
READ-ONLY: Never writes to DB. Degradable: system works 100% without LLM.

When LLM is unavailable, provides rule-based data summaries instead.
"""

import logging
from uuid import UUID
from typing import Optional, Any, Dict
from src.agents.base import BaseAgent
from src.agents.llm_client import LLMClient
from src.events.event import Event
from src.application import ReportingService, SalesService

logger = logging.getLogger("hms.insight")


class InsightAgent(BaseAgent):
    """LLM-powered advisory agent; read-only and degradable.

    Falls back to rule-based data summaries when LLM is unavailable.
    """

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
        logger.info(f"InsightAgent initialized with LLM: {self.llm.provider}/{self.llm.model} (available={self.llm.is_available})")

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
        if result is not None:
            suggestions = self._parse_json_array(result)
        else:
            # Rule-based fallback: suggest popular items not in the order
            order_item_names = {i["name"].lower() for i in order_items}
            suggestions = [
                p for p in popular
                if p.lower() not in order_item_names
            ][:3]
            logger.info(f"LLM unavailable, rule-based upsell suggestions: {suggestions}")
        return Event.create(
            type="insight.suggestion",
            source=self.name,
            correlation_id=event.correlation_id,
            payload={"suggestions": suggestions, "order_id": order_id, "source": "llm" if result else "rules"},
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
        if result is not None:
            analysis = result
            source = "llm"
        else:
            # Rule-based fallback: summarize the data directly
            total = summary.get("total_revenue", summary.get("total_sales", 0))
            count = summary.get("total_orders", summary.get("order_count", 0))
            top = summary.get("top_items", [])
            lines = [f"Daily summary: {count} orders, Rs.{total:.2f} total revenue."]
            if top:
                lines.append(f"Top sellers: {', '.join(t.get('name', '?') for t in top[:3])}")
            if count > 0:
                avg = total / count
                lines.append(f"Average order value: Rs.{avg:.2f}")
            analysis = "\n".join(lines)
            source = "rules"
            logger.info("LLM unavailable, providing rule-based trend analysis")
        return Event.create(
            type="insight.analysis",
            source=self.name,
            correlation_id=event.correlation_id,
            payload={"analysis": analysis, "summary": summary, "source": source},
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

        # Gather real data context
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

        # Try LLM first
        prompt = (
            f"Question: {question}\n\n"
            f"Context (restaurant data): {context}\n\n"
            "Answer briefly based only on the context. If the context does not contain enough information, say so."
        )
        result = self.llm.query(prompt, system_prompt="You are a restaurant data assistant. Answer concisely.")
        if result is not None:
            return Event.create(
                type="insight.query_result",
                source=self.name,
                correlation_id=event.correlation_id,
                payload={"answer": result, "question": question, "source": "llm"},
                user_id=event.user_id,
            )

        # Fallback: rule-based data summary
        logger.info(f"LLM unavailable, providing rule-based answer for: {question[:60]}")
        answer = self._rule_based_answer(question, summary, inventory, transactions)
        return Event.create(
            type="insight.query_result",
            source=self.name,
            correlation_id=event.correlation_id,
            payload={"answer": answer, "question": question, "source": "rules"},
            user_id=event.user_id,
        )

    def _rule_based_answer(self, question: str, summary: dict, inventory: dict, transactions: list) -> str:
        """Provide a useful answer from data without LLM."""
        q = question.lower()

        # Sales-related questions
        if any(kw in q for kw in ["sales", "revenue", "total", "today", "how much"]):
            total = summary.get("total_revenue", summary.get("total_sales", 0))
            count = summary.get("total_orders", summary.get("order_count", 0))
            top = summary.get("top_items", [])
            answer = f"Today's sales: Rs.{total:.2f} from {count} orders."
            if top:
                top_str = ", ".join(
                    f"{t.get('name', '?')} ({t.get('quantity', '?')} sold)"
                    for t in top[:5]
                )
                answer += f"\nTop items: {top_str}"
            return answer

        # Inventory-related questions
        if any(kw in q for kw in ["inventory", "stock", "items", "low stock", "out of stock"]):
            total_items = inventory.get("total_items", 0)
            low_stock = inventory.get("low_stock_count", 0)
            answer = f"Inventory: {total_items} items tracked. {low_stock} items below reorder level."
            inv_list = inventory.get("inventory", [])
            if inv_list:
                low = [i for i in inv_list if i.get("quantity", 0) <= i.get("reorder_level", 10)]
                if low:
                    low_str = ", ".join(f"{i['name']} ({i.get('quantity', 0)} left)" for i in low[:5])
                    answer += f"\nLow stock items: {low_str}"
            return answer

        # Order-related questions
        if any(kw in q for kw in ["order", "recent", "last"]):
            count = len(transactions)
            answer = f"There are {count} recent transactions."
            if transactions:
                last = transactions[0]
                answer += f"\nMost recent: #{last.get('receipt_number', '?')}, Rs.{last.get('total', 0):.2f}"
            return answer

        # Generic fallback
        total = summary.get("total_revenue", summary.get("total_sales", 0))
        count = summary.get("total_orders", summary.get("order_count", 0))
        total_items = inventory.get("total_items", 0)
        return (
            f"Quick summary: {count} orders today (Rs.{total:.2f} revenue), "
            f"{total_items} items in inventory. "
            f"Ask about 'sales', 'inventory', or 'orders' for more details."
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
