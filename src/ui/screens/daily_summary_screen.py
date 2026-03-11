"""
Daily Summary Screen

End-of-day close register view. Shows daily sales summary and "Close Day" button.
"""

import flet as ft
import httpx
from datetime import date
from src.ui.components.ui_helpers import HMSColors, show_error_dialog, show_success_dialog, RefreshButton


class DailySummaryScreen(ft.Column):
    """Daily summary and Close Day action."""

    API_BASE = "http://127.0.0.1:8000"

    def __init__(self, page: ft.Page, user_info: dict, on_back, **kwargs):
        super().__init__(**kwargs)
        self._page = page
        self.user_info = user_info
        self.on_back = on_back
        self.expand = True
        self._summary = {}
        self._loading = ft.ProgressRing(visible=False, width=32, height=32)

        self._date_text = ft.Text("", size=18, weight="bold")
        self._revenue_text = ft.Text("Total Revenue: ₹0.00", size=20, weight="bold", color=HMSColors.SUCCESS)
        self._txn_text = ft.Text("Transactions: 0", size=16)
        self._avg_text = ft.Text("Average Order: ₹0.00", size=16)
        self._payment_list = ft.Column(spacing=4)
        self._top_items_list = ft.Column(spacing=4)
        self._close_day_btn = ft.ElevatedButton(
            "Close Day",
            on_click=self._handle_close_day,
            bgcolor=HMSColors.WARNING,
            height=48,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        )

        self.controls = [
            ft.Row(
                [
                    ft.Text("Daily Summary", size=20, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    RefreshButton(on_refresh=self._load_summary, page=self._page, tooltip="Refresh"),
                    ft.IconButton(icon=ft.icons.ARROW_BACK, on_click=lambda e: on_back(), tooltip="Back"),
                ],
                alignment=ft.MainAxisAlignment.START,
            ),
            ft.Divider(),
            self._date_text,
            self._revenue_text,
            self._txn_text,
            self._avg_text,
            ft.Divider(),
            ft.Text("By payment method:", size=14, weight="bold"),
            ft.Container(content=self._payment_list, padding=ft.padding.only(left=16)),
            ft.Divider(),
            ft.Text("Top items:", size=14, weight="bold"),
            ft.Container(content=self._top_items_list, padding=ft.padding.only(left=16)),
            ft.Divider(),
            self._close_day_btn,
            ft.Container(content=self._loading, padding=8),
        ]

        self._load_summary()

    def _load_summary(self):
        try:
            r = httpx.get(f"{self.API_BASE}/api/reports/daily-sales", timeout=10)
            if r.status_code == 200:
                self._summary = r.json()
                self._render()
            else:
                self._revenue_text.value = "Failed to load summary"
        except Exception:
            self._revenue_text.value = "Could not load summary"
        try:
            self._page.update()
        except Exception:
            pass

    def _render(self):
        s = self._summary
        self._date_text.value = s.get("date", date.today().isoformat())
        rev = s.get("total_revenue", 0) or 0
        self._revenue_text.value = f"Total Revenue: ₹{rev:.2f}"
        self._txn_text.value = f"Transactions: {s.get('transaction_count', 0)}"
        avg = s.get("average_order_value", 0) or 0
        self._avg_text.value = f"Average Order: ₹{avg:.2f}"

        self._payment_list.controls.clear()
        for method, data in (s.get("payment_methods") or {}).items():
            self._payment_list.controls.append(
                ft.Text(f"  {method}: {data.get('count', 0)} — ₹{data.get('total', 0):.2f}", size=13)
            )
        if not self._payment_list.controls:
            self._payment_list.controls.append(ft.Text("  No payments today", size=13, color=HMSColors.TEXT_SECONDARY))

        self._top_items_list.controls.clear()
        for item in s.get("top_items") or []:
            self._top_items_list.controls.append(
                ft.Text(f"  {item.get('name', '?')}: {item.get('quantity_sold', 0)} — ₹{item.get('revenue', 0):.2f}", size=13)
            )
        if not self._top_items_list.controls:
            self._top_items_list.controls.append(ft.Text("  No items sold", size=13, color=HMSColors.TEXT_SECONDARY))

    def _handle_close_day(self, e):
        self._loading.visible = True
        self._close_day_btn.disabled = True
        try:
            self._page.update()
        except Exception:
            pass
        try:
            r = httpx.post(f"{self.API_BASE}/api/reports/close-day", timeout=10)
            if r.status_code == 200:
                data = r.json()
                show_success_dialog(self._page, "Day Closed", "Daily summary saved. Register closed.")
            else:
                show_error_dialog(self._page, "Error", "Failed to close day.")
        except httpx.ConnectError:
            show_error_dialog(self._page, "Error", "Server unavailable.")
        except Exception as ex:
            show_error_dialog(self._page, "Error", str(ex))
        finally:
            self._loading.visible = False
            self._close_day_btn.disabled = False
            try:
                self._page.update()
            except Exception:
                pass
