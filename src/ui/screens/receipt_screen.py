"""
Receipt Screen

Display and print finalized order receipt.
"""

import flet as ft
from datetime import datetime
from src.ui.components.ui_helpers import (
    HMSButton, HMSColors, show_error_dialog, show_success_dialog, show_success_toast, create_header
)


class ReceiptScreen(ft.Column):
    """Receipt display and printing screen."""

    def __init__(self, page: ft.Page, order_data: dict, on_continue):
        self._page = page
        self.order_data = order_data
        self.on_continue = on_continue

        # Receipt display (monospace, fixed width)
        receipt_text = self._format_receipt(order_data)

        receipt_display = ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        receipt_text,
                        font_family="Courier New",
                        size=12,
                        selectable=True,
                    ),
                ],
                spacing=0,
            ),
            padding=20,
            bgcolor=HMSColors.BG_SECONDARY,
            border_radius=8,
            expand=True,
        )

        # Digital Receipt link (copyable URL)
        receipt_number = order_data.get("receipt_number", "")
        receipt_url = f"http://127.0.0.1:8000/api/receipts/{receipt_number}" if receipt_number else ""

        def _copy_url(e):
            if receipt_url and hasattr(self._page, "set_clipboard"):
                self._page.set_clipboard(receipt_url)
                show_success_toast(self._page, "Link copied to clipboard")

        digital_receipt_section = ft.Container(
            content=ft.Column([
                ft.Text("Digital Receipt", size=14, weight="bold", color=HMSColors.TEXT_SECONDARY),
                ft.Row([
                    ft.Text(receipt_url or "N/A", size=12, selectable=True, expand=True, no_wrap=False),
                    ft.IconButton(
                        icon=ft.Icons.COPY,
                        tooltip="Copy link",
                        on_click=_copy_url,
                        data=receipt_url,
                    ) if receipt_url else ft.Container(),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], tight=True, spacing=4),
            padding=ft.padding.symmetric(vertical=8),
        )

        # Action buttons
        print_button = HMSButton(
            "🖨️  Print Receipt",
            self._handle_print,
            color=HMSColors.PRIMARY,
        )

        email_button = HMSButton(
            "📧 Email Receipt",
            self._handle_email,
        )

        new_order_button = HMSButton(
            "✓ New Order",
            lambda e: on_continue(),
            color=HMSColors.SUCCESS,
            width=200,
        )

        super().__init__(
            [
                ft.Text("Receipt", size=20, weight="bold"),
                ft.Divider(),
                receipt_display,
                ft.Divider(),
                digital_receipt_section,
                ft.Divider(),
                ft.Row(
                    [
                        print_button,
                        email_button,
                        ft.Container(expand=True),
                        new_order_button,
                    ],
                    spacing=10,
                ),
            ],
            spacing=10,
            expand=True,
        )

    @staticmethod
    def _format_receipt(order: dict) -> str:
        """Format order as receipt text."""
        lines = [
            "╔════════════════════════════════════════╗",
            "║   HOTEL MANAGEMENT SYSTEM - RECEIPT    ║",
            "╚════════════════════════════════════════╝",
            "",
            f"Receipt #: {order.get('receipt_number', 'N/A')}",
            f"Table: {order.get('table_id', 'N/A')}",
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "────────────────────────────────────────",
            "ITEMS",
            "────────────────────────────────────────",
        ]

        # Add line items
        for item in order.get("line_items", []):
            qty = item.get("quantity", 1)
            name = item.get("item_name", "Unknown")
            total = item.get("total_amount", 0.0)
            lines.append(f"{name:30} {qty:2} x ₹{total/qty:8.2f}")
            lines.append(f"  Subtotal: ₹{total:23.2f}")

        lines.extend([
            "────────────────────────────────────────",
            f"Subtotal:             ₹{order.get('subtotal', 0.0):8.2f}",
            f"Discount:            -₹{order.get('discount_amount', 0.0):8.2f}",
            f"Tax (18%):            ₹{order.get('tax_amount', 0.0):8.2f}",
            "────────────────────────────────────────",
            f"TOTAL:               ₹{order.get('total_amount', 0.0):8.2f}",
            "════════════════════════════════════════",
            "",
            "Thank you for your patronage!",
            "Please visit again soon.",
            "",
            "Questions? Contact support@hms.local",
        ])

        return "\n".join(lines)

    def _handle_print(self, e):
        """Print receipt to thermal printer or file."""
        try:
            from src.infrastructure.printer import ESCPOSPrinter
            printer = ESCPOSPrinter()
            filepath = printer.print_receipt(self.order_data)
            show_success_dialog(
                self._page,
                "Receipt Printed",
                f"Receipt saved to: {filepath}"
            )
        except Exception as err:
            show_error_dialog(self._page, "Print Error", str(err))

    def _handle_email(self, e):
        """Email receipt to customer."""
        email_field = ft.TextField(
            label="Customer Email",
            width=300,
            keyboard_type=ft.KeyboardType.EMAIL,
            autofocus=True,
        )

        def _close(ev=None):
            dlg.open = False
            self._page.update()

        def _send(ev):
            email = email_field.value.strip()
            if not email or "@" not in email:
                show_error_dialog(self._page, "Invalid Email", "Please enter a valid email address.")
                return
            _close()
            try:
                from src.infrastructure.email_sender import ReceiptEmailSender
                sender = ReceiptEmailSender()
                sender.send_receipt(email, self.order_data)
                show_success_dialog(self._page, "Email Sent", f"Receipt emailed to {email}")
            except Exception as err:
                show_error_dialog(self._page, "Email Error", str(err))

        dlg = ft.AlertDialog(
            title=ft.Text("Email Receipt"),
            content=ft.Column([
                ft.Text("Enter the customer's email address:"),
                email_field,
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("Cancel", on_click=lambda ev: _close()),
                ft.ElevatedButton("Send", on_click=_send,
                    bgcolor=HMSColors.PRIMARY, color=HMSColors.TEXT_LIGHT),
            ],
        )
        self._page.dialog = dlg
        dlg.open = True
        self._page.update()
