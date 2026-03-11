"""
Kitchen Screen

Displays active orders for the kitchen with quick refresh and POS push updates.
"""

from datetime import datetime
from typing import Dict, Optional

import flet as ft
import httpx

from src.ui.components.ui_helpers import (
    HMSColors,
    RefreshButton,
    show_error_dialog,
)


class KitchenScreen(ft.Column):
    """Kitchen dashboard showing active (draft/held) orders."""

    ACTIVE_STATUSES = {"draft", "held"}

    def __init__(self, page: ft.Page, user_info: Optional[dict], api_base: str = "http://127.0.0.1:8000"):
        self._page = page
        self.user_info = user_info or {}
        self.api_base = api_base
        self._orders: Dict[str, dict] = {}

        self.status_filter = ft.Dropdown(
            label="Status",
            width=160,
            value="draft",
            options=[
                ft.dropdown.Option("draft", "Draft"),
                ft.dropdown.Option("held", "Held"),
                ft.dropdown.Option("all", "Draft + Held"),
            ],
            on_change=self._handle_filter_change,
        )
        self.last_sync_text = ft.Text("Last sync: --", size=12, color=HMSColors.TEXT_SECONDARY)
        self.order_list = ft.ListView(spacing=10, expand=True)
        refresh_button = RefreshButton(on_refresh=lambda e: self.refresh_orders(), page=self._page, tooltip="Refresh orders")

        super().__init__(
            [
                ft.Row(
                    [
                        ft.Text("Kitchen Queue", size=22, weight="bold"),
                        ft.Container(expand=True),
                        self.status_filter,
                        refresh_button,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                self.last_sync_text,
                ft.Divider(),
                self.order_list,
            ],
            spacing=10,
            expand=True,
        )

        # Data refresh is triggered by caller after the main layout is mounted.

    def _handle_filter_change(self, e):
        self.refresh_orders()

    def refresh_orders(self):
        """Fetch orders from API according to the current filter."""
        params = {}
        selected = self.status_filter.value
        if selected and selected != "all":
            params["status"] = selected
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.api_base}/api/sales/orders", params=params or None)
                if response.status_code == 200:
                    data = response.json()
                    self._orders = {
                        order["id"]: order
                        for order in data
                        if (order.get("status") or "").lower() in self.ACTIVE_STATUSES
                    }
                    self.last_sync_text.value = f"Last sync: {datetime.utcnow().strftime('%H:%M:%S')} UTC"
                    self._render_orders()
                else:
                    detail = response.json().get("detail", "Failed to load orders")
                    if self._is_attached():
                        show_error_dialog(self._page, "Kitchen", detail)
        except Exception as err:
            if self._is_attached():
                show_error_dialog(self._page, "Kitchen", str(err))

    def ingest_order(self, order_payload: dict):
        """Receive order updates from POS workflow."""
        if not order_payload or "id" not in order_payload:
            return
        status = (order_payload.get("status") or "").lower()
        if status in self.ACTIVE_STATUSES:
            self._orders[order_payload["id"]] = order_payload
        else:
            self._orders.pop(order_payload["id"], None)
        self._render_orders()

    def _status_matches(self, status: Optional[str]) -> bool:
        status = (status or "").lower()
        if status not in self.ACTIVE_STATUSES:
            return False
        if self.status_filter.value == "all":
            return True
        if self.status_filter.value:
            return status == self.status_filter.value
        return True

    def _render_orders(self):
        """Render current kitchen queue."""
        self.order_list.controls.clear()
        if not self._orders:
            self.order_list.controls.append(
                ft.Container(
                    content=ft.Text(
                        "No active orders. Take an order on POS to populate the kitchen queue.",
                        size=14,
                        color=HMSColors.TEXT_SECONDARY,
                    ),
                    padding=20,
                )
            )
            self._safe_refresh()
            return

        for order in sorted(self._orders.values(), key=lambda o: o.get("updated_at") or o.get("created_at") or ""):
            self.order_list.controls.append(self._build_order_card(order))
        self._safe_refresh()

    def _is_attached(self) -> bool:
        """Return True only when this screen has been attached to the page tree."""
        return getattr(self.order_list, "page", None) is not None

    def _safe_refresh(self):
        """Refresh controls only when mounted; no-op while screen is detached."""
        if self._is_attached():
            self.update()

    def _build_order_card(self, order: dict) -> ft.Container:
        """Create UI card for a single order."""
        status = (order.get("status") or "").upper()
        status_color = HMSColors.WARNING if status == "HELD" else HMSColors.PRIMARY
        line_items = order.get("line_items", [])
        item_labels = [
            f"{li.get('item_name', '?')} x{li.get('quantity', 1)}"
            for li in line_items
        ] or ["(No items yet)"]

        items_column = ft.Column(
            [ft.Text(text, size=13) for text in item_labels],
            spacing=2,
        )

        header = ft.Row(
            [
                ft.Text(f"Table {order.get('table_id', '?')}", size=18, weight="bold"),
                ft.Container(
                    content=ft.Text(status, size=12, color=HMSColors.TEXT_LIGHT),
                    bgcolor=status_color,
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=6,
                ),
                ft.Container(expand=True),
                ft.Text(f"Items: {len(line_items)}", size=12, color=HMSColors.TEXT_SECONDARY),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        footer = ft.Row(
            [
                ft.Text(f"Subtotal: ₹{order.get('subtotal', 0.0):.2f}", size=12, color=HMSColors.TEXT_SECONDARY),
                ft.Text(f"Total: ₹{order.get('total_amount', 0.0):.2f}", size=14, weight="bold"),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        return ft.Container(
            bgcolor=HMSColors.BG_SECONDARY,
            border_radius=12,
            padding=15,
            content=ft.Column(
                [
                    header,
                    ft.Divider(),
                    items_column,
                    ft.Divider(),
                    footer,
                ],
                spacing=6,
            ),
        )
