"""
POS (Point of Sale) Screen

Main order entry screen with item picker and order summary.
Dark theme, emerald accents, touch-friendly (min 48dp).
"""

import flet as ft
import httpx
from uuid import uuid4
from datetime import datetime
from typing import Callable, Optional
from src.ui.image_assets import get_menu_image_base64
from src.ui.components.ui_helpers import (
    HMSButton,
    OrderSummaryWidget,
    HMSColors,
    build_header,
    tag_chip,
    status_tag,
    section_header,
    show_error_dialog,
    show_success_dialog,
    show_success_toast,
    RefreshButton,
)

# POS color palette — default to light surfaces for readability
POS_EMERALD = "#10b981"
POS_BG = HMSColors.BG_PRIMARY
POS_CARD_BG = HMSColors.BG_SECONDARY


class POSScreen(ft.Column):
    """Main POS screen for order entry and payment."""

    def __init__(
        self,
        page: ft.Page,
        user_info: dict,
        on_logout,
        on_kitchen_update: Optional[Callable[[dict], None]] = None,
    ):
        self._page = page
        self.user_info = user_info
        self.on_logout = on_logout
        self.api_base = "http://127.0.0.1:8000"
        self._on_kitchen_update = on_kitchen_update

        # Current order state
        self.current_order = None
        self.current_order_items = []

        # Data for menu card grid
        self.all_items = []
        self.active_category = "All"
        self.category_tabs = ft.Row(spacing=8, scroll=ft.ScrollMode.ALWAYS)
        self.menu_grid = ft.GridView(
            runs_count=3,
            max_extent=300,
            child_aspect_ratio=1.4,
            spacing=12,
            run_spacing=12,
            expand=True,
        )
        self.search_field = ft.TextField(
            hint_text="Search menu items...",
            width=260,
            height=48,
            bgcolor=HMSColors.SURFACE2,
            border_color=HMSColors.BORDER,
            color=HMSColors.TEXT_PRIMARY,
            on_change=lambda e: self._render_menu_grid(),
        )

        # Order summary widget (right panel)
        self.order_summary = OrderSummaryWidget()

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
            "New Order (F2)",
            self._handle_new_order,
            width=150,
            height=48,
            color=POS_EMERALD,
        )

        self.discount_button = HMSButton(
            "Discount",
            self._handle_discount,
            width=145,
            height=48,
            color=HMSColors.WARNING,
        )

        self.finalize_button = HMSButton(
            "Finalize & Pay (F5)",
            self._handle_finalize,
            width=300,
            height=52,
            color=POS_EMERALD,
        )

        self.void_button = HMSButton(
            "Void Order",
            self._handle_void,
            width=145,
            height=48,
            color=HMSColors.ERROR,
        )

        self.hold_button = HMSButton(
            "Hold (F8)",
            self._handle_hold,
            width=145,
            height=48,
            color=HMSColors.WARNING,
        )

        self.resume_button = HMSButton(
            "Resume (F9)",
            self._handle_resume_held,
            width=145,
            height=48,
            color=HMSColors.BLUE,
        )

        self.logout_button = HMSButton(
            "Logout",
            self._handle_logout,
            width=110,
            height=48,
        )

        self.voice_button = ft.IconButton(
            icon=ft.icons.MIC,
            tooltip="Voice order",
            on_click=self._handle_voice_click,
            icon_color=HMSColors.BLUE,
        )

        # Disable until order created
        self.discount_button.disabled = True
        self.finalize_button.disabled = True
        self.void_button.disabled = True
        self.hold_button.disabled = True

        # Role-based visibility (spec): discount for manager/cashier/admin;
        # void only for manager/admin.
        user_role = user_info.get("role", "WAITER").upper()
        self.discount_button.visible = user_role in ["MANAGER", "CASHIER", "ADMIN"]
        self.void_button.visible = user_role in ["MANAGER", "ADMIN"]

        self.loading = ft.ProgressRing(visible=False)

        # Refresh button — reloads item grid without losing draft order
        self.refresh_button = RefreshButton(
            on_refresh=self._load_items,
            page=self._page,
            tooltip="Refresh menu items",
        )

        left_panel = ft.Container(
            expand=3,
            bgcolor=HMSColors.SURFACE,
            border=ft.border.all(1, HMSColors.BORDER),
            border_radius=12,
            padding=12,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("Table", size=13, color=HMSColors.TEXT_SECONDARY),
                            self.table_id_field,
                            self.new_order_button,
                            ft.Container(expand=True),
                            self.search_field,
                            self.refresh_button,
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    section_header("Categories"),
                    self.category_tabs,
                    ft.Divider(color=HMSColors.BORDER),
                    self.menu_grid,
                ],
                spacing=10,
                expand=True,
            ),
        )

        right_panel = ft.Container(
            width=390,
            bgcolor=HMSColors.SURFACE,
            border=ft.border.all(1, HMSColors.BORDER),
            border_radius=12,
            padding=12,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("Current Order", size=15, weight=ft.FontWeight.W_700, color=HMSColors.TEXT_PRIMARY, font_family="Syne"),
                            ft.Container(expand=True),
                            self.logout_button,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    self.order_summary,
                    ft.Row([self.discount_button, self.hold_button], spacing=10),
                    ft.Row([self.resume_button, self.void_button], spacing=10),
                    self.finalize_button,
                    ft.Row(
                        [
                            self.voice_button,
                            ft.Container(expand=True),
                            self.loading,
                        ]
                    ),
                ],
                spacing=10,
                expand=True,
            ),
        )

        _content = ft.Column(
            [
                ft.Row(
                    [
                        left_panel,
                        right_panel,
                    ],
                    spacing=12,
                    expand=True,
                ),
            ],
            spacing=0,
            expand=True,
        )
        super().__init__(
            controls=[
                build_header("POS / Order Entry", user_info),
                ft.Container(
                    content=_content,
                    bgcolor=POS_BG,
                    padding=16,
                    expand=True,
                ),
            ],
            expand=True,
            spacing=0,
        )

        # Load items on init
        self._load_items()

        # Register keyboard shortcuts
        self._page.on_keyboard_event = self._handle_keyboard

    def _handle_keyboard(self, e: ft.KeyboardEvent):
        """Handle keyboard shortcuts.

        F2 = New Order
        F5 = Finalize & Pay
        F8 = Hold Order
        F9 = Resume Held
        Escape = Void Order (if visible)
        """
        key = e.key

        if key == "F2":
            self._handle_new_order(None)
        elif key == "F5" and not self.finalize_button.disabled:
            self._handle_finalize(None)
        elif key == "F8" and not self.hold_button.disabled:
            self._handle_hold(None)
        elif key == "F9":
            self._handle_resume_held(None)
        elif key == "Escape" and self.void_button.visible and not self.void_button.disabled:
            self._handle_void(None)

    def _load_items(self):
        """Load items from API."""
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(
                    f"{self.api_base}/api/inventory/items",
                )
                if response.status_code == 200:
                    self.all_items = response.json()
                    self._render_category_tabs()
                    self._render_menu_grid()
        except Exception as e:
            pass  # API may not be running yet; items will load when navigated to

    def _render_category_tabs(self):
        categories = sorted({str(it.get("category", "Other")) for it in self.all_items if it.get("category")})
        labels = ["All"] + [c.title() for c in categories]
        self.category_tabs.controls.clear()
        for label in labels:
            active = label == self.active_category
            self.category_tabs.controls.append(
                ft.Container(
                    content=tag_chip(
                        label,
                        HMSColors.ACCENT if active else HMSColors.SURFACE2,
                        HMSColors.TEXT_LIGHT if active else HMSColors.TEXT_SECONDARY,
                    ),
                    on_click=lambda e, cat=label: self._set_category(cat),
                )
            )
        if self.category_tabs.page:
            self.category_tabs.update()

    def _set_category(self, category: str):
        self.active_category = category
        self._render_category_tabs()
        self._render_menu_grid()

    def _render_menu_grid(self):
        search = (self.search_field.value or "").strip().lower()
        active = self.active_category.lower()
        self.menu_grid.controls.clear()
        for item in self.all_items:
            category = str(item.get("category", "")).lower()
            name = str(item.get("name", ""))
            if active != "all" and category != active:
                continue
            if search and search not in name.lower():
                continue
            self.menu_grid.controls.append(self._build_menu_card(item))
        if not self.menu_grid.controls:
            self.menu_grid.controls.append(ft.Text("No menu items found", color=HMSColors.TEXT_SECONDARY))
        if self.menu_grid.page:
            self.menu_grid.update()

    def _build_menu_card(self, item: dict) -> ft.Control:
        stock = int(item.get("stock_on_hand", 0))
        reorder = int(item.get("reorder_level", 0))
        is_out = stock <= 0
        if is_out:
            stock_text = "✕ Out of Stock"
            stock_color = "#EF4444"
        elif stock <= reorder:
            stock_text = f"⚠ Low ({stock})"
            stock_color = "#EAB308"
        else:
            stock_text = f"✓ In Stock ({stock})"
            stock_color = "#22C55E"

        image_data = get_menu_image_base64(str(item.get("name", "")))

        def _add(_):
            if int(item.get("stock_on_hand", 0)) > 0:
                self._handle_add_item(str(item.get("id")), str(item.get("name")), 1)

        return ft.Container(
            height=130,
            border=ft.border.all(1, "#2A334960" if not is_out else "#EF444440"),
            border_radius=10,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            opacity=0.45 if is_out else 1.0,
            on_click=None if is_out else _add,
            content=ft.Stack(
                [
                    (
                        ft.Image(
                            src_base64=image_data,
                            fit=ft.ImageFit.COVER,
                            width=float("inf"),
                            height=130,
                        )
                        if image_data
                        else ft.Container(
                            bgcolor=HMSColors.SURFACE2,
                            width=float("inf"),
                            height=130,
                            content=ft.Text(
                                "🍽",
                                size=32,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            alignment=ft.alignment.center,
                        )
                    ),
                    ft.Container(
                        width=float("inf"),
                        height=130,
                        gradient=ft.LinearGradient(
                            begin=ft.alignment.top_center,
                            end=ft.alignment.bottom_center,
                            colors=["#00000000", "#BB000000"],
                        ),
                    ),
                    ft.Container(
                        padding=ft.padding.all(10),
                        width=float("inf"),
                        height=130,
                        content=ft.Column(
                            [
                                ft.Text(
                                    str(item.get("name", "Item")),
                                    size=13,
                                    weight=ft.FontWeight.W_700,
                                    color="#FFFFFF",
                                    max_lines=2,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                ft.Text(
                                    str(item.get("category", "")).title(),
                                    size=10,
                                    color="#AAFFFFFF",
                                ),
                                ft.Container(expand=True),
                                ft.Row(
                                    [
                                        ft.Text(
                                            f"₹{float(item.get('unit_price', 0.0)):.0f}",
                                            size=15,
                                            weight=ft.FontWeight.W_800,
                                            color=HMSColors.ACCENT2,
                                            font_family="DM Mono",
                                        ),
                                        ft.Text(
                                            stock_text,
                                            size=10,
                                            color=stock_color,
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    vertical_alignment=ft.CrossAxisAlignment.END,
                                ),
                            ],
                            spacing=2,
                            tight=True,
                        ),
                    ),
                ]
            ),
        )

    def _emit_kitchen_update(self, payload: Optional[dict] = None):
        """Forward latest order data to kitchen screen, if callback provided."""
        if not self._on_kitchen_update:
            return
        order_payload = payload or self.current_order
        if not order_payload:
            return
        try:
            self._on_kitchen_update(order_payload)
        except Exception:
            pass

    def _handle_new_order(self, e):
        """Create new order."""
        table_id = self.table_id_field.value.strip()
        if not table_id:
            show_error_dialog(self.page, "Error", "Please enter table number")
            return

        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.post(
                    f"{self.api_base}/api/sales/orders",
                    json={"table_id": table_id, "user_id": self.user_info.get("user_id")},
                )
                if response.status_code == 200:
                    self.current_order = response.json()
                    self.current_order_items = []
                    self._update_order_display()
                    self._emit_kitchen_update()
                    self.discount_button.disabled = False
                    self.finalize_button.disabled = False
                    self.void_button.disabled = False
                    self.hold_button.disabled = False
                    self._page.update()
                    show_success_dialog(self.page, "Success", f"Order created for table {table_id}")
                else:
                    show_error_dialog(self.page, "Error", "Failed to create order")
        except Exception as ex:
            show_error_dialog(self.page, "Error", str(ex))

    def _handle_item_selected(self, item_id: str, item_name: str, qty: int):
        """Handle item selection from picker."""
        if not self.current_order:
            show_error_dialog(self.page, "Error", "Create an order first")
            return

        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.post(
                    f"{self.api_base}/api/sales/orders/{self.current_order['id']}/items",
                    json={"item_id": item_id, "quantity": qty, "user_id": self.user_info.get("user_id")},
                )
                if response.status_code == 200:
                    self.current_order = response.json()
                    self._update_order_display()
                    self._emit_kitchen_update()
                    self._page.update()
                else:
                    show_error_dialog(self.page, "Error", "Failed to add item")
        except Exception as ex:
            show_error_dialog(self.page, "Error", str(ex))

    def _handle_add_item(self, item_id: str, item_name: str, qty: int):
        """Compatibility alias preserving the legacy add-item handler name."""
        self._handle_item_selected(item_id, item_name, qty)

    def _handle_discount(self, e):
        """Open discount dialog and apply via API."""
        if not self.current_order:
            show_error_dialog(self.page, "Error", "Create an order first")
            return

        if self.current_order.get("subtotal", 0) == 0:
            show_error_dialog(self.page, "Error", "Add items before applying discount")
            return

        discount_type = ft.Dropdown(
            label="Discount Type",
            options=[
                ft.dropdown.Option("percentage", "Percentage (%)"),
                ft.dropdown.Option("absolute", "Absolute (₹)"),
            ],
            value="percentage",
            width=250,
        )

        discount_value = ft.TextField(
            label="Discount Value",
            hint_text="e.g. 10 for 10%",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=250,
            value="",
        )

        def confirm_discount(e):
            val = discount_value.value.strip()
            if not val:
                return
            try:
                amount = float(val)
            except ValueError:
                show_error_dialog(self.page, "Error", "Enter a valid number")
                return

            dlg.open = False
            self._page.update()

            try:
                with httpx.Client(timeout=5.0) as client:
                    response = client.patch(
                        f"{self.api_base}/api/sales/orders/{self.current_order['id']}/discount",
                        json={
                            "discount_type": discount_type.value,
                            "amount": amount,
                            "user_id": self.user_info.get("user_id"),
                        },
                    )
                    if response.status_code == 200:
                        self.current_order = response.json()
                        self._update_order_display()
                        self._emit_kitchen_update()
                        self._page.update()
                        show_success_dialog(self.page, "Discount Applied",
                            f"Discount of {amount}{'%' if discount_type.value == 'percentage' else ' ₹'} applied")
                    else:
                        detail = response.json().get("detail", "Failed to apply discount")
                        show_error_dialog(self.page, "Error", detail)
            except Exception as err:
                show_error_dialog(self.page, "Error", str(err))

        dlg = ft.AlertDialog(
            title=ft.Text("Apply Discount"),
            content=ft.Column([
                discount_type,
                discount_value,
                ft.Text(f"Subtotal: ₹{self.current_order.get('subtotal', 0):.2f}", size=14),
                ft.Text("Max percentage: 50%", size=12, color=HMSColors.TEXT_SECONDARY),
            ], tight=True, spacing=12),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: _close(dlg)),
                ft.ElevatedButton("Apply", on_click=confirm_discount,
                    bgcolor=HMSColors.WARNING, color=HMSColors.TEXT_LIGHT),
            ],
        )

        def _close(d):
            d.open = False
            self._page.update()

        self._page.dialog = dlg
        dlg.open = True
        self._page.update()

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

        current_total = self.order_summary.total_value or self.current_order.get("total_amount", 0.0)
        amount_field = ft.TextField(
            label="Amount Tendered (₹)",
            value=f"{current_total:.2f}",
            keyboard_type=ft.KeyboardType.NUMBER,
            hint_text=f"Due: ₹{current_total:.2f}",
        )

        def confirm_payment(e):
            nonlocal dlg
            dlg.open = False
            self.loading.visible = True
            self._page.update()

            try:
                try:
                    paid_amount = float(amount_field.value or current_total)
                except ValueError:
                    show_error_dialog(self.page, "Error", "Enter a valid amount")
                    return

                with httpx.Client(timeout=5.0) as client:
                    response = client.post(
                        f"{self.api_base}/api/sales/orders/{self.current_order['id']}/finalize",
                        json={
                            "payment_method": payment_method.value,
                            "paid_amount": paid_amount,
                            "user_id": self.user_info.get("user_id"),
                        },
                    )
                    if response.status_code == 200:
                        data = response.json()
                        self._emit_kitchen_update(data)
                        self.current_order = None
                        self._update_order_display()
                        # Show receipt dialog with print option
                        from src.infrastructure.printer import ESCPOSPrinter

                        def _print_and_continue(ev):
                            receipt_dlg.open = False
                            self._page.update()
                            try:
                                printer = ESCPOSPrinter()
                                filepath = printer.print_receipt(data)
                                show_success_toast(self._page, f"Receipt saved: {filepath}")
                            except Exception as err:
                                show_error_dialog(self._page, "Print Error", str(err))

                        def _skip_print(ev):
                            receipt_dlg.open = False
                            self._page.update()

                        receipt_dlg = ft.AlertDialog(
                            title=ft.Text("Order Finalized!", color=HMSColors.SUCCESS),
                            content=ft.Text(f"Total: Rs.{data.get('total_amount', 0):.2f}\nReceipt #{data.get('receipt_number', '')}"),
                            actions=[
                                ft.ElevatedButton("Print Receipt", on_click=_print_and_continue,
                                    bgcolor=HMSColors.PRIMARY, color=HMSColors.TEXT_LIGHT),
                                ft.TextButton("Skip", on_click=_skip_print),
                            ],
                        )
                        self._page.dialog = receipt_dlg
                        receipt_dlg.open = True
                        self._page.update()
                    else:
                        show_error_dialog(self.page, "Error", "Payment failed")
            except Exception as err:
                show_error_dialog(self.page, "Error", str(err))
            finally:
                self.loading.visible = False
                self._page.update()

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
            self._page.update()

        self._page.dialog = dlg
        dlg.open = True
        self._page.update()

    def _handle_void(self, e):
        """Void current order via API with confirmation."""
        if not self.current_order:
            show_error_dialog(self.page, "Error", "No active order to void")
            return

        reason_field = ft.TextField(
            label="Reason for voiding",
            hint_text="e.g. Customer changed mind",
            multiline=True,
            min_lines=2,
            max_lines=4,
            width=350,
        )

        def confirm_void(e):
            reason = reason_field.value.strip() or "No reason provided"
            dlg.open = False
            self._page.update()

            try:
                with httpx.Client(timeout=5.0) as client:
                    response = client.post(
                        f"{self.api_base}/api/sales/orders/{self.current_order['id']}/void",
                        json={
                            "reason": reason,
                            "user_id": self.user_info.get("user_id"),
                        },
                    )
                    if response.status_code == 200:
                        voided_payload = response.json()
                        self._emit_kitchen_update(voided_payload)
                        show_success_dialog(self.page, "Order Voided",
                            f"Order has been voided.\nReason: {reason}")
                        self.current_order = None
                        self.discount_button.disabled = True
                        self.finalize_button.disabled = True
                        self.void_button.disabled = True
                        self._update_order_display()
                        self._page.update()
                    else:
                        detail = response.json().get("detail", "Failed to void order")
                        show_error_dialog(self.page, "Error", detail)
            except Exception as err:
                show_error_dialog(self.page, "Error", str(err))

        dlg = ft.AlertDialog(
            title=ft.Text("Void Order"),
            content=ft.Column([
                ft.Text(
                    "Are you sure you want to void this order? This action is logged and cannot be undone.",
                    size=14,
                    color=HMSColors.ERROR,
                ),
                reason_field,
            ], tight=True, spacing=12),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: _close(dlg)),
                ft.ElevatedButton("Void Order", on_click=confirm_void,
                    bgcolor=HMSColors.ERROR, color=HMSColors.TEXT_LIGHT),
            ],
        )

        def _close(d):
            d.open = False
            self._page.update()

        self._page.dialog = dlg
        dlg.open = True
        self._page.update()

    def _handle_hold(self, e):
        """Put current order on hold."""
        if not self.current_order:
            return
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.post(
                    f"{self.api_base}/api/sales/orders/{self.current_order['id']}/hold",
                    json={"user_id": self.user_info.get("user_id")},
                )
                if response.status_code == 200:
                    held_payload = response.json()
                    self._emit_kitchen_update(held_payload)
                    show_success_dialog(self.page, "Order Held", "Order has been put on hold.")
                    self.current_order = None
                    self.discount_button.disabled = True
                    self.finalize_button.disabled = True
                    self.void_button.disabled = True
                    self.hold_button.disabled = True
                    self._update_order_display()
                    self._page.update()
                else:
                    detail = response.json().get("detail", "Failed to hold order")
                    show_error_dialog(self.page, "Error", detail)
        except Exception as ex:
            show_error_dialog(self.page, "Error", str(ex))

    def _handle_resume_held(self, e):
        """Show a dialog to pick a held order and resume it."""
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(
                    f"{self.api_base}/api/sales/orders",
                    params={"status": "held"},
                )
                if response.status_code == 200:
                    held_orders = response.json()
                    if not held_orders:
                        show_error_dialog(self.page, "No Held Orders", "There are no orders on hold.")
                        return
                    self._show_resume_dialog(held_orders)
        except Exception as ex:
            show_error_dialog(self.page, "Error", str(ex))

    def _handle_resume(self, e):
        """Compatibility alias preserving the legacy resume handler name."""
        self._handle_resume_held(e)

    def _show_resume_dialog(self, held_orders: list):
        """Show dialog listing held orders to resume."""
        order_options = []
        for o in held_orders:
            items_count = len(o.get("line_items", []))
            label = f"Table {o.get('table_id', '?')} — {items_count} items — ₹{o.get('total_amount', 0):.2f}"
            order_options.append(ft.dropdown.Option(o["id"], label))

        order_dropdown = ft.Dropdown(
            label="Select order to resume",
            options=order_options,
            value=held_orders[0]["id"] if held_orders else None,
            width=400,
        )

        def confirm_resume(ev):
            dlg.open = False
            self._page.update()
            if not order_dropdown.value:
                return
            try:
                with httpx.Client(timeout=5.0) as client:
                    response = client.post(
                        f"{self.api_base}/api/sales/orders/{order_dropdown.value}/resume",
                        json={"user_id": self.user_info.get("user_id")},
                    )
                    if response.status_code == 200:
                        self.current_order = response.json()
                        self._update_order_display()
                        self._emit_kitchen_update()
                        self.discount_button.disabled = False
                        self.finalize_button.disabled = False
                        self.void_button.disabled = False
                        self.hold_button.disabled = False
                        self._page.update()
                        show_success_dialog(self.page, "Order Resumed",
                            f"Order for table {self.current_order.get('table_id', '?')} resumed.")
                    else:
                        detail = response.json().get("detail", "Failed to resume order")
                        show_error_dialog(self.page, "Error", detail)
            except Exception as err:
                show_error_dialog(self.page, "Error", str(err))

        dlg = ft.AlertDialog(
            title=ft.Text("Resume Held Order"),
            content=ft.Column([order_dropdown], tight=True),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: _close(dlg)),
                ft.ElevatedButton("Resume", on_click=confirm_resume,
                    bgcolor=HMSColors.PRIMARY, color=HMSColors.TEXT_LIGHT),
            ],
        )

        def _close(d):
            d.open = False
            self._page.update()

        self._page.dialog = dlg
        dlg.open = True
        self._page.update()

    def _handle_edit_qty(self, line_item_id: str, current_qty: int):
        """Open dialog to edit a line item's quantity."""
        qty_field = ft.TextField(
            label="New Quantity",
            value=str(current_qty),
            keyboard_type=ft.KeyboardType.NUMBER,
            width=150,
        )

        def confirm_edit(ev):
            dlg.open = False
            self._page.update()
            try:
                new_qty = int(qty_field.value.strip())
                if new_qty <= 0:
                    show_error_dialog(self.page, "Error", "Quantity must be positive")
                    return
            except ValueError:
                show_error_dialog(self.page, "Error", "Enter a valid number")
                return

            try:
                with httpx.Client(timeout=5.0) as client:
                    response = client.patch(
                        f"{self.api_base}/api/sales/orders/{self.current_order['id']}/items/{line_item_id}",
                        json={"quantity": new_qty, "user_id": self.user_info.get("user_id")},
                    )
                    if response.status_code == 200:
                        self.current_order = response.json()
                        self._update_order_display()
                        self._emit_kitchen_update()
                        self._page.update()
                    else:
                        detail = response.json().get("detail", "Failed to update quantity")
                        show_error_dialog(self.page, "Error", detail)
            except Exception as err:
                show_error_dialog(self.page, "Error", str(err))

        dlg = ft.AlertDialog(
            title=ft.Text("Edit Quantity"),
            content=ft.Column([qty_field], tight=True),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: _close(dlg)),
                ft.ElevatedButton("Update", on_click=confirm_edit,
                    bgcolor=HMSColors.PRIMARY, color=HMSColors.TEXT_LIGHT),
            ],
        )

        def _close(d):
            d.open = False
            self._page.update()

        self._page.dialog = dlg
        dlg.open = True
        self._page.update()

    def _handle_voice_click(self, e):
        """Open quick command dialog for text-based ordering with follow-up support."""
        # Track pending intent for multi-turn follow-ups
        self._pos_pending_intent = None

        command_field = ft.TextField(
            label="Quick Command",
            hint_text="e.g. '2 biryani and 1 coke for table 3'",
            width=400,
            autofocus=True,
            on_submit=lambda ev: _execute_command(ev),
        )

        self._voice_status = ft.Text("", size=12, color=HMSColors.TEXT_SECONDARY)
        self._voice_result = ft.Column([], spacing=4)

        def _close(d):
            d.open = False
            self._pos_pending_intent = None
            self._page.update()

        def _execute_command(ev):
            text = command_field.value.strip()
            if not text:
                return

            # Allow cancel
            if text.lower() in ("cancel", "nevermind", "stop", "reset"):
                self._pos_pending_intent = None
                self._voice_status.value = "Cancelled. Type a new command."
                self._voice_status.color = HMSColors.TEXT_SECONDARY
                command_field.value = ""
                command_field.hint_text = "e.g. '2 biryani and 1 coke for table 3'"
                try:
                    self._page.update()
                except Exception:
                    pass
                return

            self._voice_status.value = "Processing..."
            self._voice_status.color = HMSColors.PRIMARY
            try:
                self._page.update()
            except Exception:
                pass

            try:
                payload = {"text": text, "user_id": self.user_info.get("user_id", "")}
                if self._pos_pending_intent:
                    payload["pending_intent"] = self._pos_pending_intent

                with httpx.Client(timeout=15.0) as client:
                    response = client.post(
                        f"{self.api_base}/api/voice/text-command",
                        json=payload,
                    )
                    if response.status_code == 200:
                        data = response.json()
                        intent = data.get("intent", {})
                        status = data.get("status", "")
                        message = data.get("message", "")

                        if status == "followup":
                            # Store pending intent and show the follow-up question
                            self._pos_pending_intent = intent
                            action_label = intent.get("action", "").replace("_", " ").title()
                            self._voice_status.value = f"[{action_label}] {message}"
                            self._voice_status.color = HMSColors.PRIMARY
                            self._voice_result.controls = [
                                ft.Text("Answer above, or type 'cancel' to abort.", size=11, color=HMSColors.TEXT_SECONDARY),
                            ]
                            command_field.hint_text = "Answer the question..."

                        elif status == "success":
                            self._pos_pending_intent = None
                            self._voice_status.value = message
                            self._voice_status.color = HMSColors.SUCCESS
                            command_field.hint_text = "e.g. '2 biryani and 1 coke for table 3'"

                            # If order was created, update the POS display
                            result = data.get("result", {})
                            order_id = result.get("order_id", "")
                            if order_id:
                                try:
                                    order_resp = client.get(f"{self.api_base}/api/sales/orders/{order_id}")
                                    if order_resp.status_code == 200:
                                        self.current_order = order_resp.json()
                                        self._update_order_display()
                                        self.discount_button.disabled = False
                                        self.finalize_button.disabled = False
                                        self.void_button.disabled = False
                                        self.hold_button.disabled = False
                                except Exception:
                                    pass

                            self._voice_result.controls = [
                                ft.Text(message, size=13, color=HMSColors.SUCCESS),
                            ]

                        elif status == "error":
                            self._pos_pending_intent = None
                            self._voice_status.value = message or "Command failed"
                            self._voice_status.color = HMSColors.ERROR
                            command_field.hint_text = "e.g. '2 biryani and 1 coke for table 3'"

                        else:
                            # info or unknown
                            self._pos_pending_intent = None
                            self._voice_status.value = message
                            self._voice_status.color = HMSColors.PRIMARY
                            command_field.hint_text = "e.g. '2 biryani and 1 coke for table 3'"
                    else:
                        detail = response.json().get("detail", "Command failed")
                        self._voice_status.value = f"Error: {detail}"
                        self._voice_status.color = HMSColors.ERROR
            except Exception as err:
                self._voice_status.value = f"Connection error: {str(err)[:50]}"
                self._voice_status.color = HMSColors.ERROR

            command_field.value = ""
            try:
                self._page.update()
            except Exception:
                pass

        cmd_dlg = ft.AlertDialog(
            title=ft.Text("Quick Command"),
            content=ft.Column([
                ft.Text("Type a command (orders, inventory, payments, etc.):", size=13, color=HMSColors.TEXT_SECONDARY),
                command_field,
                ft.Divider(),
                self._voice_status,
                self._voice_result,
                ft.Divider(),
                ft.Text("Examples:", size=12, weight="bold"),
                ft.Text("• '2 biryani and 1 lassi for table 5'", size=11, color=HMSColors.TEXT_SECONDARY),
                ft.Text("• '3 coke for table 2, pay cash'", size=11, color=HMSColors.TEXT_SECONDARY),
            ], tight=True, spacing=8, width=420),
            actions=[
                ft.TextButton("Close", on_click=lambda ev: _close(cmd_dlg)),
                ft.ElevatedButton("Execute", on_click=_execute_command,
                    bgcolor=HMSColors.PRIMARY, color=HMSColors.TEXT_LIGHT),
            ],
        )

        self._page.dialog = cmd_dlg
        cmd_dlg.open = True
        self._page.update()

    def _handle_logout(self, e):
        """Logout and return to auth screen."""
        self.on_logout()

    def _handle_remove_item(self, line_item_id: str):
        """Remove a line item from the current order."""
        if not self.current_order:
            return

        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.request(
                    "DELETE",
                    f"{self.api_base}/api/sales/orders/{self.current_order['id']}/items/{line_item_id}",
                    json={"user_id": self.user_info.get("user_id")},
                )
                if response.status_code == 200:
                    self.current_order = response.json()
                    self._update_order_display()
                    self._emit_kitchen_update()
                    self._page.update()
                else:
                    detail = response.json().get("detail", "Failed to remove item")
                    show_error_dialog(self.page, "Error", detail)
        except Exception as ex:
            show_error_dialog(self.page, "Error", str(ex))

    def _update_order_display(self):
        """Update order summary display with line items and remove buttons."""
        if self.current_order:
            line_items = self.current_order.get("line_items", [])
            # Build line item widgets with remove buttons
            item_widgets = []
            for li in line_items:
                li_id = li.get("id", "")
                li_qty = li.get("quantity", 1)
                item_widgets.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Text(
                                    f"{li.get('item_name', '?')} x{li_qty}",
                                    size=13, expand=True,
                                ),
                                ft.Text(
                                    f"₹{li.get('total_amount', 0):.2f}",
                                    size=13, weight="bold",
                                ),
                                ft.IconButton(
                                    icon=ft.icons.EDIT,
                                    icon_color=HMSColors.PRIMARY,
                                    icon_size=18,
                                    tooltip="Edit quantity",
                                    on_click=lambda e, lid=li_id, q=li_qty: self._handle_edit_qty(lid, q),
                                ),
                                ft.IconButton(
                                    icon=ft.icons.DELETE_OUTLINE,
                                    icon_color=HMSColors.ERROR,
                                    icon_size=18,
                                    tooltip="Remove item",
                                    on_click=lambda e, lid=li_id: self._handle_remove_item(lid),
                                ),
                            ],
                            spacing=4,
                        ),
                        padding=ft.padding.symmetric(vertical=2),
                    )
                )
            self.order_summary.update_summary(
                table_id=self.current_order.get("table_id", "—"),
                item_count=len(line_items),
                subtotal=self.current_order.get("subtotal", 0.0),
                discount=self.current_order.get("discount_amount", 0.0),
                tax=self.current_order.get("tax_amount", 0.0),
                total=self.current_order.get("total_amount", 0.0),
                line_item_widgets=item_widgets,
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


# TODO: Add voice/STT integration (future)
