"""
Receipt Screen

Display and print finalized order receipt.
"""

import flet as ft
from datetime import datetime
from src.ui.components.ui_helpers import (
    HMSButton, HMSColors, show_error_dialog, show_success_dialog, create_header
)


class ReceiptScreen(ft.Column):
    """Receipt display and printing screen."""

    def __init__(self, page: ft.Page, order_data: dict, on_continue):
        self.page = page
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
            padding=20,
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
        """Print receipt."""
        # TODO: Integrate with actual printer
        show_success_dialog(
            self.page,
            "Print Sent",
            "Receipt sent to printer (Phase 1 stub)"
        )

    def _handle_email(self, e):
        """Email receipt."""
        # TODO: Implement email
        show_error_dialog(
            self.page,
            "Coming Soon",
            "Email receipt feature coming in Phase 2"
        )


# TODO: Implement actual printing
# TODO: Implement email sending
# TODO: Add digital signature option
