"""
Order Confirmation Screen

Shows parsed order (items, table) for confirm/edit before creating.
Confirm → POST /api/orders/from-intent. Cancel → back to Chat Order.
"""

import flet as ft
import httpx
from typing import Callable, Optional, List, Dict, Any
from copy import deepcopy
from src.ui.components.ui_helpers import HMSColors, show_error_dialog, show_success_dialog


class OrderConfirmationScreen(ft.Column):
    """Display parsed intent and confirm or edit before placing order."""

    API_BASE = "http://127.0.0.1:8000"

    def __init__(
        self,
        page: ft.Page,
        intent: dict,
        user_id: str = "",
        on_back: Optional[Callable[[], None]] = None,
        on_order_change: Optional[Callable[[str, dict], None]] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._page = page
        self._intent = deepcopy(intent)
        self.user_id = user_id
        self.on_back = on_back or (lambda: None)
        self._on_order_change = on_order_change
        self.expand = True

        self._table_id = intent.get("table_id") or "1"
        self._items: List[Dict[str, Any]] = list(intent.get("items") or [])
        self._item_prices: Dict[str, float] = {}  # item_id -> unit_price (filled on load)

        self._loading = ft.ProgressRing(visible=False, width=32, height=32)
        self._table_dropdown = ft.Dropdown(
            label="Table",
            value=self._table_id,
            width=120,
            options=[ft.dropdown.Option(str(i), str(i)) for i in range(1, 21)]
            + [ft.dropdown.Option("TAKEAWAY", "TAKEAWAY")],
            on_change=self._on_table_change,
        )
        self._items_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
        self._subtotal_text = ft.Text("Subtotal: ₹0.00", size=16)
        self._tax_text = ft.Text("Tax (18%): ₹0.00", size=16)
        self._total_text = ft.Text("Total: ₹0.00", size=22, weight=ft.FontWeight.BOLD, color=HMSColors.SUCCESS)

        self.controls = [
            ft.Row(
                [
                    ft.IconButton(
                        icon=ft.icons.ARROW_BACK,
                        on_click=lambda e: self.on_back(),
                        tooltip="Back",
                    ),
                    ft.Text("Confirm Order", size=20, weight=ft.FontWeight.BOLD),
                ],
                alignment=ft.MainAxisAlignment.START,
            ),
            ft.Divider(),
            ft.Row(
                [ft.Text("Table:", size=16, weight="bold"), self._table_dropdown],
                alignment=ft.MainAxisAlignment.START,
                spacing=12,
            ),
            ft.Text("Items:", size=16, weight="bold"),
            self._items_column,
            ft.Divider(),
            self._subtotal_text,
            self._tax_text,
            self._total_text,
            ft.Divider(),
            ft.Row(
                [
                    ft.ElevatedButton(
                        "Cancel",
                        on_click=lambda e: self.on_back(),
                        bgcolor=HMSColors.NEUTRAL,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                    ),
                    ft.ElevatedButton(
                        "Confirm Order",
                        on_click=self._handle_confirm,
                        bgcolor=HMSColors.SUCCESS,
                        height=48,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                    ),
                ],
                spacing=16,
            ),
            ft.Container(content=self._loading, padding=8),
        ]

        self._build_items_ui()
        self._load_prices_and_update_totals()

    def _on_table_change(self, e):
        self._table_id = self._table_dropdown.value or "1"
        self._intent["table_id"] = self._table_id

    def _build_items_ui(self):
        self._items_column.controls.clear()
        for i, it in enumerate(self._items):
            name = it.get("name", "?")
            qty = it.get("quantity", 1)
            item_id = it.get("item_id", "")
            price = self._item_prices.get(item_id) or 0.0
            line_total = price * qty

            row = ft.Row(
                [
                    ft.Text(f"{name} x{qty}", size=16, expand=True),
                    ft.Text(f"₹{line_total:.2f}", size=16, weight="bold"),
                    ft.IconButton(
                        icon=ft.icons.REMOVE_CIRCLE_OUTLINE,
                        icon_color=HMSColors.ERROR,
                        icon_size=20,
                        on_click=lambda e, idx=i: self._remove_item(idx),
                        tooltip="Remove",
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            self._items_column.controls.append(
                ft.Container(
                    content=row,
                    padding=8,
                    bgcolor="#27272a",
                    border_radius=8,
                )
            )

    def _remove_item(self, index: int):
        if 0 <= index < len(self._items):
            self._items.pop(index)
            self._intent["items"] = self._items
            self._build_items_ui()
            self._update_totals()
            try:
                self._page.update()
            except Exception:
                pass

    def _load_prices_and_update_totals(self):
        """Fetch item prices from API to display totals."""
        try:
            r = httpx.get(f"{self.API_BASE}/api/inventory/items", timeout=5)
            if r.status_code == 200:
                for item in r.json():
                    self._item_prices[item["id"]] = float(item.get("unit_price", 0))
        except Exception:
            pass
        self._build_items_ui()
        self._update_totals()

    def _update_totals(self):
        subtotal = 0.0
        for it in self._items:
            pid = it.get("item_id", "")
            qty = it.get("quantity", 1)
            subtotal += self._item_prices.get(pid, 0) * qty
        tax = subtotal * 0.18
        total = subtotal + tax
        self._subtotal_text.value = f"Subtotal: ₹{subtotal:.2f}"
        self._tax_text.value = f"Tax (18%): ₹{tax:.2f}"
        self._total_text.value = f"Total: ₹{total:.2f}"
        try:
            self._subtotal_text.update()
            self._tax_text.update()
            self._total_text.update()
        except Exception:
            pass

    def _handle_confirm(self, e):
        if not self._items:
            show_error_dialog(self._page, "Error", "Add at least one item.")
            return
        self._intent["table_id"] = self._table_id
        self._intent["items"] = self._items
        self._loading.visible = True
        try:
            self._page.update()
        except Exception:
            pass

        try:
            r = httpx.post(
                f"{self.API_BASE}/api/orders/from-intent",
                json={"intent": self._intent, "user_id": self.user_id},
                timeout=15,
            )
            data = r.json() if r.status_code == 200 else {}
            status = data.get("status", "error")
            message = data.get("message", "Failed to create order")

            if status == "success":
                if callable(self._on_order_change):
                    try:
                        self._on_order_change("order.created", data)
                    except Exception:
                        pass
                show_success_dialog(self._page, "Order Created", message)
                self.on_back()
            else:
                show_error_dialog(self._page, "Order Failed", message)
        except httpx.ConnectError:
            show_error_dialog(self._page, "Error", "Server unavailable.")
        except httpx.TimeoutException:
            show_error_dialog(self._page, "Error", "Request timed out.")
        except Exception as ex:
            show_error_dialog(self._page, "Error", str(ex))
        finally:
            self._loading.visible = False
            try:
                self._page.update()
            except Exception:
                pass
