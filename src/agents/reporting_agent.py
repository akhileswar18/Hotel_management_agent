"""
ReportingAgent — Handles report.daily_sales, report.inventory, report.transactions, report.export_csv.

Delegates to ReportingService for read-only report generation.
"""

import csv
import io
from datetime import date
from typing import Optional, Any, Dict
from src.agents.base import BaseAgent
from src.events.event import Event
from src.application import ReportingService


class ReportingAgent(BaseAgent):
    """Reporting agent delegating to ReportingService."""

    name = "ReportingAgent"
    subscribes_to = [
        "report.daily_sales",
        "report.inventory",
        "report.transactions",
        "report.export_csv",
    ]
    publishes = ["report.generated", "report.exported", "report.error"]
    writes_to_db = False
    uses_llm = False

    def __init__(self):
        self.reporting_service = ReportingService()

    def handle(self, event: Event) -> Optional[Event]:
        """Route report events to handlers."""
        handlers = {
            "report.daily_sales": self._handle_daily_sales,
            "report.inventory": self._handle_inventory,
            "report.transactions": self._handle_transactions,
            "report.export_csv": self._handle_export_csv,
        }
        handler = handlers.get(event.type)
        if handler:
            try:
                return handler(event)
            except Exception as e:
                return Event.create(
                    type="report.error",
                    source=self.name,
                    correlation_id=event.correlation_id,
                    payload={
                        "error_code": type(e).__name__,
                        "message": str(e),
                    },
                    user_id=event.user_id,
                )
        return None

    def _handle_daily_sales(self, event: Event) -> Event:
        """Call ReportingService.daily_sales_summary(date) and return report.generated."""
        payload = event.payload or {}
        report_date = payload.get("date")
        if isinstance(report_date, str):
            report_date = date.fromisoformat(report_date) if report_date else None
        elif report_date is not None and not isinstance(report_date, date):
            report_date = None
        data = self.reporting_service.daily_sales_summary(report_date)
        return Event.create(
            type="report.generated",
            source=self.name,
            correlation_id=event.correlation_id,
            payload={"report_type": "daily_sales", "data": data},
            user_id=event.user_id,
        )

    def _handle_inventory(self, event: Event) -> Event:
        """Call ReportingService.inventory_snapshot() and return report.generated."""
        data = self.reporting_service.inventory_snapshot()
        return Event.create(
            type="report.generated",
            source=self.name,
            correlation_id=event.correlation_id,
            payload={"report_type": "inventory", "data": data},
            user_id=event.user_id,
        )

    def _handle_transactions(self, event: Event) -> Event:
        """Call ReportingService.search_transactions() and return report.generated."""
        payload = event.payload or {}
        data = self.reporting_service.search_transactions(
            start_date=payload.get("start_date"),
            end_date=payload.get("end_date"),
            payment_method=payload.get("payment_method"),
        )
        return Event.create(
            type="report.generated",
            source=self.name,
            correlation_id=event.correlation_id,
            payload={"report_type": "transactions", "data": data},
            user_id=event.user_id,
        )

    def _handle_export_csv(self, event: Event) -> Event:
        """Generate CSV export and return report.exported."""
        payload = event.payload or {}
        report_type = payload.get("report_type", "transactions")
        if report_type == "daily_sales":
            report_date = payload.get("date")
            if isinstance(report_date, str) and report_date:
                report_date = date.fromisoformat(report_date)
            else:
                report_date = None
            data = self.reporting_service.daily_sales_summary(report_date)
            csv_content = self._daily_sales_to_csv(data)
        elif report_type == "inventory":
            data = self.reporting_service.inventory_snapshot()
            csv_content = self._inventory_to_csv(data)
        else:
            data = self.reporting_service.search_transactions(
                start_date=payload.get("start_date"),
                end_date=payload.get("end_date"),
                payment_method=payload.get("payment_method"),
            )
            csv_content = self._transactions_to_csv(data)

        return Event.create(
            type="report.exported",
            source=self.name,
            correlation_id=event.correlation_id,
            payload={
                "report_type": report_type,
                "csv_content": csv_content,
            },
            user_id=event.user_id,
        )

    @staticmethod
    def _daily_sales_to_csv(data: Dict[str, Any]) -> str:
        """Convert daily sales summary to CSV string."""
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["date", "total_revenue", "transaction_count", "average_order_value"])
        w.writerow([
            data.get("date", ""),
            data.get("total_revenue", 0),
            data.get("transaction_count", 0),
            data.get("average_order_value", 0),
        ])
        return out.getvalue()

    @staticmethod
    def _inventory_to_csv(data: Dict[str, Any]) -> str:
        """Convert inventory snapshot to CSV string."""
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["id", "name", "category", "unit_price", "stock_on_hand", "reorder_level", "is_low_stock"])
        for item in data.get("inventory", []):
            w.writerow([
                item.get("id"),
                item.get("name"),
                item.get("category"),
                item.get("unit_price"),
                item.get("stock_on_hand"),
                item.get("reorder_level"),
                item.get("is_low_stock", False),
            ])
        return out.getvalue()

    @staticmethod
    def _transactions_to_csv(data: list) -> str:
        """Convert transactions list to CSV string."""
        if not data:
            return "receipt_number,table_id,total,payment_method,paid,finalized_at\n"
        out = io.StringIO()
        w = csv.DictWriter(out, fieldnames=data[0].keys())
        w.writeheader()
        w.writerows(data)
        return out.getvalue()
