"""
Billing / Invoice Screen

Cashier workspace with payment method cards, receipt preview, and recent invoices.
"""

from datetime import datetime
from typing import Optional

import flet as ft
import httpx

from src.ui.components.ui_helpers import (
    HMSButton,
    HMSColors,
    build_header,
    section_header,
    status_tag,
    show_error_dialog,
    show_success_dialog,
)


class ReceiptScreen(ft.Column):
    """Billing screen with optional compatibility mode for direct receipt view."""

    def __init__(
        self,
        page: ft.Page,
        order_data: Optional[dict] = None,
        on_continue=None,
        user_info: Optional[dict] = None,
        on_back=None,
        register_order_listener=None,
        unregister_order_listener=None,
    ):
        self._page = page
        self.user_info = user_info or {}
        self.on_continue = on_continue
        self.on_back = on_back
        self._register_order_listener = register_order_listener
        self._unregister_order_listener = unregister_order_listener
        self._order_listener_id = f"billing:{id(self)}"
        self.api_base = "http://127.0.0.1:8000"

        self.payment_method = "CASH"
        self.draft_orders = []
        self.selected_table = None
        self.selected_order = order_data or {}
        self.recent_orders = []
        self.table_chips = ft.Row(
            wrap=True,
            spacing=8,
            run_spacing=8,
        )
        self.bill_summary = ft.Container(
            visible=False,
            padding=14,
            border_radius=10,
            bgcolor=HMSColors.SURFACE2,
            border=ft.border.all(1, HMSColors.BORDER),
            content=ft.Column(spacing=6),
        )

        self.amount_received = ft.TextField(
            label="Amount Received",
            width=280,
            height=48,
            value=f"{float(self.selected_order.get('total_amount', 0.0)):.2f}" if self.selected_order else "",
            keyboard_type=ft.KeyboardType.NUMBER,
            bgcolor=HMSColors.SURFACE2,
            border_color=HMSColors.BORDER,
            color=HMSColors.TEXT_PRIMARY,
            on_change=self._recompute_change,
        )
        self.change_text = ft.Text("Change: Rs.0.00", size=14, color=HMSColors.GREEN, font_family="DM Mono")

        self.preview_area = ft.Column(spacing=6)
        self.recent_list = ft.Column(
            spacing=4,
            scroll=ft.ScrollMode.AUTO,
        )

        self.cash_btn = self._payment_chip("CASH", "💵")
        self.card_btn = self._payment_chip("CARD", "💳")
        self.voucher_btn = self._payment_chip("VOUCHER", "🎟")
        self.confirm_btn = ft.ElevatedButton(
            "Confirm Payment",
            bgcolor=HMSColors.GREEN,
            color="#FFFFFF",
            height=48,
            width=300,
            on_click=None,
        )

        super().__init__(
            [
                build_header("Billing", self.user_info),
                ft.Container(
                    expand=True,
                    padding=16,
                    content=ft.Row(
                        [
                            ft.Container(
                                expand=2,
                                content=ft.Column(
                                    [
                                        self._surface_card(
                                            ft.Column(
                                                [
                                                    ft.Text(
                                                        "SELECT ORDER",
                                                        size=10,
                                                        weight=ft.FontWeight.W_700,
                                                        color=HMSColors.TEXT_MUTED,
                                                    ),
                                                    ft.Container(
                                                        padding=ft.padding.symmetric(vertical=4),
                                                        content=self.table_chips,
                                                    ),
                                                    self.bill_summary,
                                                    ft.Divider(height=1, color=HMSColors.BORDER),
                                                    section_header("Select Payment Method"),
                                                    ft.Row([self.cash_btn, self.card_btn, self.voucher_btn], spacing=10),
                                                    self.amount_received,
                                                    self.change_text,
                                                    self.confirm_btn,
                                                ],
                                                spacing=10,
                                                tight=True,
                                            )
                                        ),
                                        self._surface_card(
                                            ft.Column(
                                                [
                                                    section_header(
                                                        "Recent Invoices",
                                                        HMSButton("Refresh", self._load_recent, width=120, height=48, color=HMSColors.BLUE),
                                                    ),
                                                    ft.Container(
                                                        content=self.recent_list,
                                                        height=520,
                                                    ),
                                                ],
                                                spacing=8,
                                            )
                                        ),
                                    ],
                                    spacing=12,
                                ),
                            ),
                            ft.Container(
                                expand=2,
                                content=self._surface_card(
                                    ft.Column(
                                        [
                                            section_header("Receipt Preview"),
                                            self.preview_area,
                                            ft.Row(
                                                [
                                                    HMSButton("Print Receipt", self._handle_print, width=170, height=48, color=HMSColors.ACCENT),
                                                    HMSButton("Email", self._handle_email, width=120, height=48, color=HMSColors.BLUE),
                                                    HMSButton(
                                                        "New Order",
                                                        lambda e: self._handle_back(),
                                                        width=140,
                                                        height=48,
                                                        color=HMSColors.GREEN,
                                                    ),
                                                ],
                                                spacing=10,
                                                wrap=True,
                                            ),
                                        ],
                                        spacing=10,
                                    ),
                                    padding=16,
                                ),
                            ),
                        ],
                        spacing=14,
                        expand=True,
                    ),
                ),
            ],
            spacing=0,
            expand=True,
        )

        self._sync_payment_chips()
        self._load_recent()
        self._render_preview()
        self._recompute_change(None)
        self._load_draft_orders()
        if self.selected_order:
            initial_table = str(self.selected_order.get("table_id") or "").strip() or None
            self.selected_table = initial_table
            if initial_table:
                self._populate_bill_summary(self.selected_order)
                self._set_confirm_enabled(True)
                self._rebuild_table_chips()
        if callable(self._register_order_listener):
            self._register_order_listener(self._order_listener_id, self.notify_external_update)

    def _surface_card(self, content: ft.Control, padding: int = 14) -> ft.Container:
        return ft.Container(
            bgcolor=HMSColors.SURFACE,
            border=ft.border.all(1, HMSColors.BORDER),
            border_radius=12,
            padding=padding,
            content=content,
        )

    def _payment_chip(self, method: str, icon: str) -> ft.Container:
        return ft.Container(
            width=120,
            height=56,
            border_radius=10,
            border=ft.border.all(2, HMSColors.BORDER),
            bgcolor=HMSColors.SURFACE2,
            on_click=lambda e, m=method: self._set_payment(m),
            content=ft.Row(
                [ft.Text(icon, size=18), ft.Text(method.title(), size=12, color=HMSColors.TEXT_PRIMARY)],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
            ),
            data=method,
        )

    def _set_payment(self, method: str):
        self.payment_method = method
        self._sync_payment_chips()

    def _sync_payment_chips(self):
        for chip in [self.cash_btn, self.card_btn, self.voucher_btn]:
            active = chip.data == self.payment_method
            chip.border = ft.border.all(2, HMSColors.ACCENT if active else HMSColors.BORDER)
            chip.bgcolor = HMSColors.ACCENT + "20" if active else HMSColors.SURFACE2
            if chip.page:
                chip.update()

    def _set_confirm_enabled(self, enabled: bool):
        self.confirm_btn.on_click = self._handle_confirm_payment if enabled else None
        self.confirm_btn.bgcolor = HMSColors.GREEN if enabled else HMSColors.SURFACE3
        self.confirm_btn.color = "#FFFFFF" if enabled else HMSColors.TEXT_SECONDARY
        try:
            self.confirm_btn.update()
        except Exception:
            pass

    def _load_draft_orders(self):
        """Fetch all draft orders from API to populate table chips."""
        try:
            resp = httpx.get(
                f"{self.api_base}/api/sales/orders",
                params={"status": "draft"},
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    self.draft_orders = data
                elif isinstance(data, dict):
                    self.draft_orders = data.get("orders", [])
        except Exception:
            self.draft_orders = []
        try:
            self._rebuild_table_chips()
        except Exception:
            pass

    def _rebuild_table_chips(self):
        """Build table selector chips from draft orders."""
        self.table_chips.controls.clear()

        occupied = {}
        for order in self.draft_orders:
            table_id = str(order.get("table_id") or "").strip()
            if table_id and table_id not in occupied:
                occupied[table_id] = order

        for table_num in range(1, 11):
            tid = str(table_num)
            has_order = tid in occupied
            is_selected = self.selected_table == tid
            chip = ft.Container(
                width=56,
                height=44,
                border_radius=8,
                bgcolor=(
                    HMSColors.ACCENT + "30" if is_selected else
                    "#22C55E20" if has_order else
                    HMSColors.SURFACE3
                ),
                border=ft.border.all(
                    2 if is_selected else 1,
                    HMSColors.ACCENT if is_selected else
                    "#22C55E" if has_order else
                    HMSColors.BORDER
                ),
                alignment=ft.alignment.center,
                on_click=lambda e, table_id=tid, order=occupied.get(tid): self._select_table(table_id, order),
                content=ft.Column(
                    [
                        ft.Text(
                            f"T{table_num}",
                            size=13,
                            weight=ft.FontWeight.W_700,
                            color=(
                                HMSColors.ACCENT if is_selected else
                                "#22C55E" if has_order else
                                HMSColors.TEXT_SECONDARY
                            ),
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Container(
                            width=6,
                            height=6,
                            border_radius=3,
                            bgcolor=(
                                HMSColors.ACCENT if is_selected else
                                "#22C55E" if has_order else
                                "transparent"
                            ),
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=2,
                    tight=True,
                ),
            )
            self.table_chips.controls.append(chip)

        is_takeaway = self.selected_table == "TAKEAWAY"
        self.table_chips.controls.append(
            ft.Container(
                width=100,
                height=44,
                border_radius=8,
                bgcolor=HMSColors.ACCENT + "30" if is_takeaway else HMSColors.SURFACE3,
                border=ft.border.all(
                    2 if is_takeaway else 1,
                    HMSColors.ACCENT if is_takeaway else HMSColors.BORDER
                ),
                alignment=ft.alignment.center,
                on_click=lambda e: self._select_table("TAKEAWAY", None),
                content=ft.Text(
                    "🛍 Takeaway",
                    size=12,
                    weight=ft.FontWeight.W_600,
                    color=HMSColors.ACCENT if is_takeaway else HMSColors.TEXT_SECONDARY,
                ),
            )
        )
        self.table_chips.controls.append(
            ft.Container(
                width=44,
                height=44,
                border_radius=8,
                bgcolor=HMSColors.SURFACE3,
                border=ft.border.all(1, HMSColors.BORDER),
                alignment=ft.alignment.center,
                on_click=lambda e: self._load_draft_orders(),
                content=ft.Icon(ft.icons.REFRESH, size=18, color=HMSColors.TEXT_SECONDARY),
            )
        )
        try:
            self.table_chips.update()
        except Exception:
            pass

    def _select_table(self, table_id: str, order: Optional[dict]):
        """Handle table chip click and load pending bill details."""
        self.selected_table = table_id
        self.selected_order = order or {}
        self._rebuild_table_chips()

        if order:
            self._populate_bill_summary(order)
            total = float(order.get("total_amount", 0.0))
            self.amount_received.value = f"{total:.2f}"
            try:
                self.amount_received.update()
            except Exception:
                pass
            self._recompute_change(None)
            self._set_confirm_enabled(True)
        else:
            self._clear_bill_summary()
            self.amount_received.value = ""
            try:
                self.amount_received.update()
            except Exception:
                pass
            self._recompute_change(None)
            self._set_confirm_enabled(table_id == "TAKEAWAY")

    def _populate_bill_summary(self, order: dict):
        """Fill bill summary panel with order line items and totals."""
        column = self.bill_summary.content
        column.controls.clear()

        table_id = order.get("table_id", "—")
        order_id = str(order.get("id", ""))[:8]
        items = order.get("line_items") or order.get("items") or []
        subtotal = float(order.get("subtotal", 0.0))
        discount = float(order.get("discount_amount", 0.0))
        tax = float(order.get("tax_amount", 0.0))
        total = float(order.get("total_amount", 0.0))

        def money(value: float) -> str:
            return f"₹{value:,.2f}"

        column.controls.append(
            ft.Row(
                [
                    ft.Text(f"Table {table_id}", size=13, weight=ft.FontWeight.W_700, color=HMSColors.TEXT_PRIMARY),
                    ft.Text(
                        f"#{order_id}",
                        size=11,
                        color=HMSColors.TEXT_MUTED,
                        font_family="DM Mono",
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )
        )
        column.controls.append(ft.Divider(height=1, color=HMSColors.BORDER))

        for line_item in items:
            name = line_item.get("item_name") or line_item.get("name", "Item")
            qty = line_item.get("quantity", 1)
            line_total = float(line_item.get("total_amount", 0.0))
            column.controls.append(
                ft.Row(
                    [
                        ft.Text(
                            f"{name} ×{qty}",
                            size=12,
                            color=HMSColors.TEXT_SECONDARY,
                            expand=True,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Text(
                            money(line_total),
                            size=12,
                            color=HMSColors.TEXT_PRIMARY,
                            font_family="DM Mono",
                        ),
                    ]
                )
            )

        column.controls.append(ft.Divider(height=1, color=HMSColors.BORDER))

        def total_row(label: str, value: float, color: Optional[str] = None, bold: bool = False) -> ft.Row:
            return ft.Row(
                [
                    ft.Text(label, size=12, color=color or HMSColors.TEXT_SECONDARY),
                    ft.Text(
                        money(value),
                        size=12,
                        color=color or HMSColors.TEXT_PRIMARY,
                        weight=ft.FontWeight.W_700 if bold else ft.FontWeight.W_400,
                        font_family="DM Mono",
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )

        column.controls.append(total_row("Subtotal", subtotal))
        if discount > 0:
            column.controls.append(total_row("Discount", -discount, HMSColors.GREEN))
        column.controls.append(total_row("Tax (18%)", tax))
        column.controls.append(ft.Container(height=4, content=ft.Divider(height=1, color=HMSColors.BORDER)))
        column.controls.append(
            ft.Row(
                [
                    ft.Text("TOTAL", size=14, weight=ft.FontWeight.W_800, color=HMSColors.TEXT_PRIMARY),
                    ft.Text(
                        money(total),
                        size=16,
                        weight=ft.FontWeight.W_800,
                        color=HMSColors.GREEN,
                        font_family="DM Mono",
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )
        )
        self.bill_summary.visible = True
        try:
            self.bill_summary.update()
        except Exception:
            pass

    def _clear_bill_summary(self):
        column = self.bill_summary.content
        column.controls.clear()
        column.controls.append(
            ft.Text(
                "Takeaway — enter amount manually",
                size=12,
                color=HMSColors.TEXT_MUTED,
                italic=True,
            )
        )
        self.bill_summary.visible = True
        try:
            self.bill_summary.update()
        except Exception:
            pass

    def _show_snack(self, message: str, color: str):
        self._page.snack_bar = ft.SnackBar(
            content=ft.Text(message, color="#FFFFFF"),
            bgcolor=color,
            duration=2000,
        )
        self._page.snack_bar.open = True
        self._page.update()

    def _load_recent(self, e=None):
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{self.api_base}/api/sales/orders", params={"status": "finalized"})
                if resp.status_code == 200:
                    self.recent_orders = resp.json()[:20]
        except Exception:
            self.recent_orders = []
        self._render_recent()

    def notify_external_update(self, event: Optional[dict] = None):
        """Refresh billing data in response to successful order-change events."""
        event_type = str((event or {}).get("event_type") or "order.updated")
        self._load_draft_orders()
        if event_type in {"order.finalized", "order.voided"}:
            self._load_recent()
        try:
            self._render_preview()
        except Exception:
            pass
        try:
            self._page.update()
        except Exception:
            pass

    def on_show(self):
        self._load_draft_orders()
        self._load_recent()
        try:
            self._page.update()
        except Exception:
            pass

    def _render_recent(self):
        self.recent_list.controls.clear()
        if not self.recent_orders:
            self.recent_list.controls.append(ft.Text("No recent invoices", color=HMSColors.TEXT_SECONDARY))
        for order in self.recent_orders:
            status = str(order.get("status", "draft")).upper()
            tag_color = HMSColors.GREEN if status == "FINALIZED" else HMSColors.RED
            self.recent_list.controls.append(
                ft.Container(
                    padding=10,
                    border_radius=8,
                    bgcolor=HMSColors.SURFACE2,
                    border=ft.border.all(1, HMSColors.BORDER),
                    content=ft.Row(
                        [
                            ft.Text(str(order.get("receipt_number") or "-"), width=120, color=HMSColors.TEXT_PRIMARY, font_family="DM Mono"),
                            ft.Text(str(order.get("table_id") or "-"), width=52, color=HMSColors.TEXT_SECONDARY),
                            ft.Text(str(len(order.get("line_items", []))), width=40, color=HMSColors.TEXT_SECONDARY),
                            ft.Text(f"Rs.{float(order.get('total_amount', 0.0)):.2f}", width=100, color=HMSColors.ACCENT2, font_family="DM Mono"),
                            status_tag(status, tag_color),
                            ft.IconButton(
                                icon=ft.icons.PRINT,
                                tooltip="Reprint",
                                on_click=lambda e, o=order: self._select_invoice(o),
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )
        if self.recent_list.page:
            self.recent_list.update()

    def _select_invoice(self, order: dict):
        self.selected_order = order
        self.selected_table = str(order.get("table_id") or "").strip() or None
        self.amount_received.value = f"{float(order.get('total_amount', 0.0)):.2f}"
        self.amount_received.update()
        self._set_confirm_enabled(False)
        self._clear_bill_summary()
        self._rebuild_table_chips()
        self._render_preview()
        self._recompute_change(None)

    def _render_preview(self):
        order = self.selected_order or {}
        self.preview_area.controls.clear()
        if not order:
            self.preview_area.controls.append(ft.Text("Select an invoice to preview", color=HMSColors.TEXT_SECONDARY))
        else:
            self.preview_area.controls.extend(
                [
                    ft.Container(
                        border_radius=10,
                        padding=12,
                        gradient=ft.LinearGradient(colors=[HMSColors.ACCENT, HMSColors.ACCENT2]),
                        content=ft.Row(
                            [
                                ft.Text("HOTEL MANAGEMENT", color=HMSColors.TEXT_LIGHT, weight=ft.FontWeight.W_800, font_family="Syne"),
                                ft.Container(expand=True),
                                ft.Text(str(order.get("receipt_number") or "-"), color=HMSColors.TEXT_LIGHT, font_family="DM Mono"),
                            ]
                        ),
                    ),
                    ft.Row(
                        [
                            ft.Text(f"Table: {order.get('table_id', '-')}", color=HMSColors.TEXT_SECONDARY),
                            ft.Container(expand=True),
                            ft.Text(datetime.now().strftime("%Y-%m-%d %H:%M"), color=HMSColors.TEXT_SECONDARY, font_family="DM Mono"),
                        ]
                    ),
                    ft.Divider(color=HMSColors.BORDER),
                ]
            )
            for li in order.get("line_items", []):
                self.preview_area.controls.append(
                    ft.Row(
                        [
                            ft.Text(li.get("item_name", "Item"), expand=True, color=HMSColors.TEXT_PRIMARY),
                            ft.Text(f"x{li.get('quantity', 1)}", width=36, color=HMSColors.TEXT_SECONDARY, font_family="DM Mono"),
                            ft.Text(f"Rs.{float(li.get('total_amount', 0.0)):.2f}", width=90, text_align=ft.TextAlign.RIGHT, color=HMSColors.TEXT_PRIMARY, font_family="DM Mono"),
                        ]
                    )
                )
            self.preview_area.controls.extend(
                [
                    ft.Divider(color=HMSColors.BORDER),
                    self._totals_row("Subtotal", float(order.get("subtotal", 0.0))),
                    self._totals_row("Discount", float(order.get("discount_amount", 0.0))),
                    self._totals_row("GST", float(order.get("tax_amount", 0.0))),
                    self._totals_row("Total", float(order.get("total_amount", 0.0)), highlight=True),
                ]
            )
        if self.preview_area.page:
            self.preview_area.update()

    def _totals_row(self, label: str, amount: float, highlight: bool = False) -> ft.Row:
        return ft.Row(
            [
                ft.Text(label, color=HMSColors.TEXT_SECONDARY if not highlight else HMSColors.TEXT_PRIMARY),
                ft.Container(expand=True),
                ft.Text(
                    f"Rs.{amount:.2f}",
                    color=HMSColors.ACCENT2 if highlight else HMSColors.TEXT_PRIMARY,
                    weight=ft.FontWeight.W_700 if highlight else ft.FontWeight.W_500,
                    font_family="DM Mono",
                ),
            ]
        )

    def _recompute_change(self, e):
        total = float((self.selected_order or {}).get("total_amount", 0.0))
        try:
            received = float(self.amount_received.value or 0.0)
        except Exception:
            received = 0.0
        change = max(received - total, 0.0)
        self.change_text.value = f"Change: Rs.{change:.2f}"
        if self.change_text.page:
            self.change_text.update()

    def _handle_confirm_payment(self, e):
        order_id = self.selected_order.get("id")
        if not order_id and self.selected_table != "TAKEAWAY":
            self._show_snack("Please select a table with a pending order", "#EF4444")
            return

        if self.selected_table == "TAKEAWAY" and not order_id:
            self._show_snack("Takeaway payment recorded", HMSColors.GREEN)
            self._load_draft_orders()
            return

        try:
            amount_tendered = float(self.amount_received.value or 0)
        except Exception:
            self._show_snack("Enter a valid amount received", "#EF4444")
            return

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    f"{self.api_base}/api/sales/orders/{order_id}/finalize",
                    json={
                        "payment_method": self.payment_method,
                        "amount_tendered": amount_tendered,
                        "finalized_by": self.user_info.get("id") or self.user_info.get("user_id", ""),
                    },
                )
            if resp.status_code == 200:
                finalized = resp.json()
                self.selected_order = finalized
                self._render_preview()
                self._load_recent()
                self._load_draft_orders()
                self.bill_summary.visible = False
                self.bill_summary.update()
                self.selected_table = None
                self._rebuild_table_chips()
                self._set_confirm_enabled(False)
                self._show_snack("Payment recorded", HMSColors.GREEN)
            else:
                self._show_snack(f"Payment failed: {resp.text[:60]}", "#EF4444")
        except Exception as ex:
            self._show_snack(f"Error: {str(ex)[:60]}", "#EF4444")

    def _confirm_payment(self, e):
        self._handle_confirm_payment(e)

    def _handle_print(self, e):
        if not self.selected_order:
            show_error_dialog(self._page, "No Invoice", "Select an invoice to print.")
            return
        try:
            from src.infrastructure.printer import ESCPOSPrinter

            printer = ESCPOSPrinter()
            filepath = printer.print_receipt(self.selected_order)
            show_success_dialog(self._page, "Receipt Printed", f"Saved to: {filepath}")
        except Exception as err:
            show_error_dialog(self._page, "Print Error", str(err))

    def _handle_email(self, e):
        if not self.selected_order:
            show_error_dialog(self._page, "No Invoice", "Select an invoice to email.")
            return
        show_success_dialog(self._page, "Email", "Email flow is available from the legacy receipt action.")

    def _handle_back(self):
        if callable(self.on_back):
            self.on_back()
        elif callable(self.on_continue):
            self.on_continue()

    def cleanup(self):
        if callable(self._unregister_order_listener):
            self._unregister_order_listener(self._order_listener_id)
