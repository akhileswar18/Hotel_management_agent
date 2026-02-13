"""
ESC/POS Thermal Printer Integration

Formats and sends receipts to ESC/POS compatible thermal printers.
Falls back to file output when no printer is connected.
"""

import os
from datetime import datetime
from typing import Optional


class ESCPOSPrinter:
    """ESC/POS thermal printer driver."""

    # ESC/POS command constants
    ESC = b'\x1b'
    GS = b'\x1d'
    INIT = b'\x1b\x40'          # Initialize printer
    CUT = b'\x1d\x56\x00'      # Full cut
    BOLD_ON = b'\x1b\x45\x01'
    BOLD_OFF = b'\x1b\x45\x00'
    CENTER = b'\x1b\x61\x01'
    LEFT = b'\x1b\x61\x00'
    DOUBLE_HEIGHT = b'\x1b\x21\x10'
    NORMAL_SIZE = b'\x1b\x21\x00'
    FEED_LINES = b'\x1b\x64\x03'  # Feed 3 lines

    def __init__(self, printer_path: Optional[str] = None):
        """
        Initialize printer.

        Args:
            printer_path: OS path to printer device (e.g., 'COM3' on Windows, '/dev/usb/lp0' on Linux).
                         If None, falls back to file output.
        """
        self.printer_path = printer_path or os.getenv("PRINTER_PATH")
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "receipts")
        os.makedirs(self.output_dir, exist_ok=True)

    def print_receipt(self, order_data: dict) -> str:
        """
        Print a receipt for the given order.

        Returns:
            Path to saved receipt file (always saved as backup).
        """
        text_receipt = self._format_text_receipt(order_data)

        # Save to file always (backup)
        receipt_num = order_data.get("receipt_number", "unknown")
        filename = f"receipt_{receipt_num}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text_receipt)

        # Try sending to physical printer
        if self.printer_path:
            try:
                esc_data = self._format_escpos(order_data)
                with open(self.printer_path, "wb") as printer:
                    printer.write(esc_data)
            except Exception as e:
                print(f"[WARN] Printer error: {e}. Receipt saved to {filepath}")

        return filepath

    def _format_text_receipt(self, order: dict) -> str:
        """Format receipt as plain text."""
        w = 40  # receipt width in chars
        lines = []
        lines.append("=" * w)
        lines.append("HOTEL MANAGEMENT SYSTEM".center(w))
        lines.append("RECEIPT".center(w))
        lines.append("=" * w)
        lines.append("")
        lines.append(f"Receipt #: {order.get('receipt_number', 'N/A')}")
        lines.append(f"Table:     {order.get('table_id', 'N/A')}")
        lines.append(f"Date:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append("-" * w)
        lines.append(f"{'Item':<22} {'Qty':>3} {'Price':>6} {'Total':>7}")
        lines.append("-" * w)

        for item in order.get("line_items", []):
            name = item.get("item_name", "?")[:22]
            qty = item.get("quantity", 1)
            total = item.get("total_amount", 0.0)
            unit = total / qty if qty else 0
            lines.append(f"{name:<22} {qty:>3} {unit:>6.0f} {total:>7.2f}")

        lines.append("-" * w)
        lines.append(f"{'Subtotal:':<30} {order.get('subtotal', 0.0):>9.2f}")
        lines.append(f"{'Discount:':<30} -{order.get('discount_amount', 0.0):>8.2f}")
        lines.append(f"{'Tax (18% GST):':<30} {order.get('tax_amount', 0.0):>9.2f}")
        lines.append("=" * w)
        lines.append(f"{'TOTAL:':<30} {order.get('total_amount', 0.0):>9.2f}")
        lines.append("=" * w)
        lines.append("")
        lines.append("Thank you for dining with us!".center(w))
        lines.append("Please visit again.".center(w))
        lines.append("")
        return "\n".join(lines)

    def _format_escpos(self, order: dict) -> bytes:
        """Format receipt as ESC/POS binary commands."""
        data = bytearray()
        data.extend(self.INIT)

        # Header
        data.extend(self.CENTER)
        data.extend(self.BOLD_ON)
        data.extend(self.DOUBLE_HEIGHT)
        data.extend(b"HOTEL MANAGEMENT SYSTEM\n")
        data.extend(self.NORMAL_SIZE)
        data.extend(b"RECEIPT\n")
        data.extend(self.BOLD_OFF)
        data.extend(self.LEFT)

        # Receipt details
        data.extend(f"\nReceipt #: {order.get('receipt_number', 'N/A')}\n".encode())
        data.extend(f"Table:     {order.get('table_id', 'N/A')}\n".encode())
        data.extend(f"Date:      {datetime.now().strftime('%Y-%m-%d %H:%M')}\n".encode())
        data.extend(b"\n" + b"-" * 32 + b"\n")

        # Items
        for item in order.get("line_items", []):
            name = item.get("item_name", "?")[:20]
            qty = item.get("quantity", 1)
            total = item.get("total_amount", 0.0)
            data.extend(f"{name:<20} x{qty:>2} {total:>7.2f}\n".encode())

        data.extend(b"-" * 32 + b"\n")

        # Totals
        data.extend(self.BOLD_ON)
        data.extend(f"TOTAL: Rs.{order.get('total_amount', 0.0):.2f}\n".encode())
        data.extend(self.BOLD_OFF)

        # Footer
        data.extend(b"\n")
        data.extend(self.CENTER)
        data.extend(b"Thank you!\n")
        data.extend(self.FEED_LINES)
        data.extend(self.CUT)

        return bytes(data)
