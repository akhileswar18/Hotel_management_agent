"""
Order History Screen

View past orders with search by status and date.
"""

import flet as ft
import httpx
from datetime import date
from src.ui.components.ui_helpers import (
    HMSButton, HMSColors, show_error_dialog, show_success_dialog, create_header
)


class OrderHistoryScreen(ft.Column):
    """Order history screen with search and filters."""

    def __init__(self, page: ft.Page, user_info: dict, on_back):
        self.page = page
        self.user_info = user_info
        self.on_back = on_back
        self.api_base = "http://127.0.0.1:8000"

        # Filters
        self.status_filter = ft.Dropdown(
            label="Status",
            options=[
                ft.dropdown.Option("", "All"),
                ft.dropdown.Option("draft", "Draft"),
                ft.dropdown.Option("held", "Held"),
                ft.dropdown.Option("finalized", "Finalized"),
                ft.dropdown.Option("voided", "Voided"),
            ],
            value="",
            width=160,
            on_change=self._handle_filter_change,
        )

        self.date_filter = ft.TextField(
            label="Date (YYYY-MM-DD)",
            hint_text="e.g. 2026-02-11",
            width=180,
            height=48,
            text_size=14,
            value="",
        )

        search_btn = HMSButton(
            "Search",
            self._handle_search,
            width=100,
            color=HMSColors.PRIMARY,
        )

        today_btn = HMSButton(
            "Today",
            self._handle_today,
            width=80,
            color=HMSColors.PRIMARY,
        )

        all_btn = HMSButton(
            "Show All",
            self._handle_show_all,
            width=100,
        )

        back_button = HMSButton(
            "Back to POS",
            lambda e: on_back(),
        )

        # Orders list
        self.orders_list = ft.ListView(
            spacing=8,
            expand=True,
        )

        self.order_count_text = ft.Text("0 orders found", size=13, color=HMSColors.TEXT_SECONDARY)

        super().__init__(
            [
                ft.Row(
                    [
                        ft.Text("Order History", size=20, weight="bold"),
                        ft.Container(expand=True),
                        back_button,
                    ],
                    spacing=10,
                ),
                ft.Divider(),
                ft.Row(
                    [
                        self.status_filter,
                        self.date_filter,
                        search_btn,
                        today_btn,
                        all_btn,
                        ft.Container(expand=True),
                        self.order_count_text,
                    ],
                    spacing=10,
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Divider(),
                self.orders_list,
            ],
            spacing=10,
            expand=True,
        )

        # Load recent orders
        self._load_orders()

    def _handle_filter_change(self, e):
        self._load_orders()

    def _handle_search(self, e):
        self._load_orders()

    def _handle_today(self, e):
        self.date_filter.value = date.today().isoformat()
        self._load_orders()
        try:
            self.page.update()
        except Exception:
            pass

    def _handle_show_all(self, e):
        self.status_filter.value = ""
        self.date_filter.value = ""
        self._load_orders()
        try:
            self.page.update()
        except Exception:
            pass

    def _load_orders(self):
        """Load orders from API with filters."""
        try:
            params = {}
            if self.status_filter.value:
                params["status"] = self.status_filter.value
            if self.date_filter.value.strip():
                params["date"] = self.date_filter.value.strip()

            with httpx.Client(timeout=5.0) as client:
                response = client.get(
                    f"{self.api_base}/api/sales/orders",
                    params=params,
                )
                if response.status_code == 200:
                    orders = response.json()
                    self._display_orders(orders)
        except Exception:
            pass

    def _display_orders(self, orders: list):
        """Display orders in the list."""
        self.orders_list.controls.clear()
        self.order_count_text.value = f"{len(orders)} order(s) found"

        if not orders:
            self.orders_list.controls.append(
                ft.Container(
                    content=ft.Text("No orders found", size=14, color=HMSColors.TEXT_SECONDARY),
                    padding=20,
                    alignment=ft.alignment.center,
                )
            )
        else:
            for order in orders:
                status = order.get("status", "unknown")
                # Color coding by status
                if status == "finalized":
                    status_color = HMSColors.SUCCESS
                    status_icon = ft.icons.CHECK_CIRCLE
                elif status == "voided":
                    status_color = HMSColors.ERROR
                    status_icon = ft.icons.CANCEL
                elif status == "held":
                    status_color = HMSColors.WARNING
                    status_icon = ft.icons.PAUSE_CIRCLE
                else:
                    status_color = HMSColors.PRIMARY
                    status_icon = ft.icons.EDIT

                line_items = order.get("line_items", [])
                items_str = ", ".join(
                    f"{li.get('item_name', '?')} x{li.get('quantity', 1)}"
                    for li in line_items[:3]
                )
                if len(line_items) > 3:
                    items_str += f" +{len(line_items) - 3} more"
                if not items_str:
                    items_str = "No items"

                finalized_at = order.get("finalized_at", "")
                receipt = order.get("receipt_number", "")

                card = ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(status_icon, color=status_color, size=24),
                            ft.Column(
                                [
                                    ft.Row([
                                        ft.Text(f"Table {order.get('table_id', '—')}", size=15, weight="bold"),
                                        ft.Container(
                                            content=ft.Text(status.upper(), size=11, color=HMSColors.TEXT_LIGHT, weight="bold"),
                                            bgcolor=status_color,
                                            border_radius=4,
                                            padding=ft.padding.symmetric(horizontal=8, vertical=2),
                                        ),
                                        ft.Text(f"#{receipt}" if receipt else "", size=12, color=HMSColors.TEXT_SECONDARY),
                                    ], spacing=8),
                                    ft.Text(items_str, size=12, color=HMSColors.TEXT_SECONDARY),
                                ],
                                spacing=4,
                                expand=True,
                            ),
                            ft.Column(
                                [
                                    ft.Text(f"₹{order.get('total_amount', 0):.2f}", size=16, weight="bold"),
                                    ft.Text(f"{len(line_items)} items", size=12, color=HMSColors.TEXT_SECONDARY),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.END,
                            ),
                        ],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=12,
                    bgcolor=HMSColors.BG_SECONDARY,
                    border_radius=8,
                    border=ft.border.all(1, status_color),
                )
                self.orders_list.controls.append(card)

        try:
            self.orders_list.update()
            self.order_count_text.update()
        except Exception:
            pass
