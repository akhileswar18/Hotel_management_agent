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
    ):
        self._page = page
        self.user_info = user_info or {}
        self.on_continue = on_continue
        self.on_back = on_back
        self.api_base = "http://127.0.0.1:8000"

        self.payment_method = "CASH"
        self.selected_order = order_data or {}
        self.recent_orders = []

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
        self.recent_list = ft.Column(spacing=4)

        self.cash_btn = self._payment_chip("CASH", "💵")
        self.card_btn = self._payment_chip("CARD", "💳")
        self.voucher_btn = self._payment_chip("VOUCHER", "🎟")

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
                                                    section_header("Select Payment Method"),
                                                    ft.Row([self.cash_btn, self.card_btn, self.voucher_btn], spacing=10),
                                                    self.amount_received,
                                                    self.change_text,
                                                    HMSButton(
                                                        "Confirm Payment",
                                                        self._confirm_payment,
                                                        width=300,
                                                        height=52,
                                                        color=HMSColors.GREEN,
                                                    ),
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
                                                    self.recent_list,
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

    def _load_recent(self, e=None):
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{self.api_base}/api/sales/orders", params={"status": "finalized"})
                if resp.status_code == 200:
                    self.recent_orders = resp.json()[:20]
        except Exception:
            self.recent_orders = []
        self._render_recent()

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
        self.amount_received.value = f"{float(order.get('total_amount', 0.0)):.2f}"
        self.amount_received.update()
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

    def _confirm_payment(self, e):
        if not self.selected_order:
            show_error_dialog(self._page, "No Invoice", "Select an invoice/order first.")
            return
        show_success_dialog(
            self._page,
            "Payment Confirmed",
            f"Payment method: {self.payment_method}\nAmount recorded for receipt {self.selected_order.get('receipt_number', '-')}.",
        )

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
