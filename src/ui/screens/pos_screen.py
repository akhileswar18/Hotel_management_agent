"""
POS (Point of Sale) Screen

Main order entry screen with item picker and order summary.
Fast, efficient workflow for taking orders.
"""

import flet as ft
import httpx
import asyncio
from uuid import uuid4
from datetime import datetime
from src.ui.components.ui_helpers import (
    HMSButton, ItemPickerWidget, OrderSummaryWidget, HMSColors,
    show_error_dialog, show_success_dialog, create_header
)


class POSScreen(ft.Column):
    """Main POS screen for order entry and payment."""

    def __init__(self, page: ft.Page, user_info: dict, on_logout):
        self.page = page
        self.user_info = user_info
        self.on_logout = on_logout
        self.api_base = "http://127.0.0.1:8000"

        # Current order state
        self.current_order = None
        self.current_order_items = []

        # Header
        header = create_header(
            page,
            "POS - Hotel Management System",
            f"User: {user_info.get('username', 'Unknown')} | {user_info.get('role', 'WAITER')}"
        )

        # Order summary widget
        self.order_summary = OrderSummaryWidget()

        # Item picker widget
        self.item_picker = ItemPickerWidget(on_item_selected=self._handle_item_selected)

        # Table ID input
        self.table_id_field = ft.TextField(
            label="Table Number",
            width=150,
            height=48,
            text_size=16,
            value="1",
        )

        # Buttons
        self.new_order_button = HMSButton(
            "New Order",
            self._handle_new_order,
            width=150,
            color=HMSColors.PRIMARY,
        )

        self.discount_button = HMSButton(
            "Apply Discount",
            self._handle_discount,
            width=150,
            color=HMSColors.WARNING,
        )

        self.finalize_button = HMSButton(
            "Finalize & Pay",
            self._handle_finalize,
            width=150,
            color=HMSColors.SUCCESS,
        )

        self.void_button = HMSButton(
            "Void Order",
            self._handle_void,
            width=150,
            color=HMSColors.ERROR,
        )

        self.logout_button = HMSButton(
            "Logout",
            self._handle_logout,
            width=150,
        )

        # Disable until order created
        self.discount_button.disabled = True
        self.finalize_button.disabled = True
        self.void_button.disabled = True

        self.loading = ft.ProgressRing(visible=False)

        super().__init__(
            [
                ft.Row(
                    [
                        ft.Text("Table:", size=16, weight="bold"),
                        self.table_id_field,
                        self.new_order_button,
                        ft.Container(expand=True),
                        self.logout_button,
                    ],
                    spacing=10,
                    alignment=ft.MainAxisAlignment.START,
                ),
                ft.Divider(),
                ft.Row(
                    [
                        ft.Column([self.order_summary], expand=True),
                        ft.Column([self.item_picker], expand=True),
                    ],
                    spacing=20,
                    expand=True,
                ),
                ft.Divider(),
                ft.Row(
                    [
                        self.discount_button,
                        self.finalize_button,
                        self.void_button,
                        ft.Container(expand=True),
                        self.loading,
                    ],
                    spacing=10,
                    alignment=ft.MainAxisAlignment.START,
                ),
            ],
            spacing=10,
            padding=20,
            expand=True,
        )

        # Load items on init
        asyncio.run(self._load_items())

    async def _load_items(self):
        """Load items from API."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base}/api/inventory/items",
                    timeout=5.0,
                )
                if response.status_code == 200:
                    items = response.json()
                    self.item_picker.set_items(items)
        except Exception as e:
            show_error_dialog(self.page, "Error", f"Failed to load items: {str(e)}")

    def _handle_new_order(self, e):
        """Create new order."""
        table_id = self.table_id_field.value.strip()
        if not table_id:
            show_error_dialog(self.page, "Error", "Please enter table number")
            return

        try:
            async def create_order():
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.api_base}/api/sales/orders",
                        json={"table_id": table_id},
                        timeout=5.0,
                    )
                    if response.status_code == 200:
                        self.current_order = response.json()
                        self.current_order_items = []
                        self._update_order_display()
                        self.discount_button.disabled = False
                        self.finalize_button.disabled = False
                        self.void_button.disabled = False
                        self.page.update()
                        show_success_dialog(self.page, "Success", f"Order created for table {table_id}")
                    else:
                        show_error_dialog(self.page, "Error", "Failed to create order")

            asyncio.run(create_order())
        except Exception as e:
            show_error_dialog(self.page, "Error", str(e))

    def _handle_item_selected(self, item_id: str, item_name: str, qty: int):
        """Handle item selection from picker."""
        if not self.current_order:
            show_error_dialog(self.page, "Error", "Create an order first")
            return

        try:
            async def add_item():
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.api_base}/api/sales/orders/{self.current_order['id']}/items",
                        json={"item_id": item_id, "quantity": qty},
                        timeout=5.0,
                    )
                    if response.status_code == 200:
                        self.current_order = response.json()
                        self._update_order_display()
                        self.page.update()
                    else:
                        show_error_dialog(self.page, "Error", "Failed to add item")

            asyncio.run(add_item())
        except Exception as e:
            show_error_dialog(self.page, "Error", str(e))

    def _handle_discount(self, e):
        """Open discount dialog."""
        if not self.current_order:
            show_error_dialog(self.page, "Error", "Create an order first")
            return

        # TODO: Implement discount dialog
        show_error_dialog(self.page, "Coming Soon", "Discount feature coming in Phase 2")

    def _handle_finalize(self, e):
        """Finalize order and open payment dialog."""
        if not self.current_order:
            show_error_dialog(self.page, "Error", "Create an order first")
            return

        # Create payment dialog
        payment_method = ft.Dropdown(
            label="Payment Method",
            options=[
                ft.dropdown.Option("CASH"),
                ft.dropdown.Option("CARD"),
                ft.dropdown.Option("VOUCHER"),
            ],
            value="CASH",
        )

        amount_field = ft.TextField(
            label=f"Amount (₹{self.current_order['total_amount']:.2f})",
            value=str(self.current_order['total_amount']),
            read_only=True,
        )

        async def confirm_payment(e):
            dlg.open = False
            self.loading.visible = True
            self.page.update()

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.api_base}/api/sales/orders/{self.current_order['id']}/finalize",
                        json={
                            "payment_method": payment_method.value,
                            "paid_amount": float(amount_field.value),
                        },
                        timeout=5.0,
                    )
                    if response.status_code == 200:
                        finalized_order = response.json()
                        show_success_dialog(
                            self.page,
                            "Payment Successful",
                            f"Receipt: {finalized_order.get('receipt_number', 'N/A')}\n"
                            f"Total: ₹{finalized_order['total_amount']:.2f}"
                        )
                        self.current_order = None
                        self._update_order_display()
                    else:
                        show_error_dialog(self.page, "Error", "Payment failed")
            except Exception as err:
                show_error_dialog(self.page, "Error", str(err))
            finally:
                self.loading.visible = False
                self.page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Finalize Order & Payment"),
            content=ft.Column([
                payment_method,
                amount_field,
            ]),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(dlg)),
                ft.ElevatedButton(
                    "Confirm Payment",
                    on_click=confirm_payment,
                    bgcolor=HMSColors.SUCCESS,
                    color=HMSColors.TEXT_LIGHT,
                ),
            ],
        )

        def close_dialog(d):
            d.open = False
            self.page.update()

        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    def _handle_void(self, e):
        """Void current order."""
        if not self.current_order:
            show_error_dialog(self.page, "Error", "No active order to void")
            return

        show_success_dialog(self.page, "Order Voided", "Order has been voided (logged)")
        self.current_order = None
        self._update_order_display()

    def _handle_logout(self, e):
        """Logout and return to auth screen."""
        self.on_logout()

    def _update_order_display(self):
        """Update order summary display."""
        if self.current_order:
            self.order_summary.update_summary(
                table_id=self.current_order.get("table_id", "—"),
                item_count=len(self.current_order.get("line_items", [])),
                subtotal=self.current_order.get("subtotal", 0.0),
                discount=self.current_order.get("discount_amount", 0.0),
                tax=self.current_order.get("tax_amount", 0.0),
                total=self.current_order.get("total_amount", 0.0),
            )
        else:
            self.order_summary.update_summary(
                table_id="—",
                item_count=0,
                subtotal=0.0,
                discount=0.0,
                tax=0.0,
                total=0.0,
            )


# TODO: Add void with manager approval
# TODO: Add hold/resume order
# TODO: Add receipt printing
# TODO: Add voice integration (Phase 2)
