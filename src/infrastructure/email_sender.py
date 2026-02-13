"""
Email Service for Receipt Delivery

Sends HTML-formatted receipts via SMTP.
Configurable via environment variables.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional


class EmailConfig:
    """Email configuration from environment."""

    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_name = os.getenv("EMAIL_FROM_NAME", "HMS Receipts")
        self.from_email = os.getenv("EMAIL_FROM", self.smtp_user)

    @property
    def is_configured(self) -> bool:
        return bool(self.smtp_user and self.smtp_password)


class ReceiptEmailSender:
    """Send receipt emails via SMTP."""

    def __init__(self):
        self.config = EmailConfig()

    def send_receipt(self, to_email: str, order_data: dict) -> bool:
        """
        Send receipt email.

        Returns True on success, raises on failure.
        """
        if not self.config.is_configured:
            raise ValueError(
                "Email not configured. Set SMTP_USER and SMTP_PASSWORD environment variables."
            )

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Receipt #{order_data.get('receipt_number', 'N/A')} - HMS"
        msg["From"] = f"{self.config.from_name} <{self.config.from_email}>"
        msg["To"] = to_email

        # Plain text version
        text_body = self._format_text(order_data)
        msg.attach(MIMEText(text_body, "plain"))

        # HTML version
        html_body = self._format_html(order_data)
        msg.attach(MIMEText(html_body, "html"))

        try:
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.smtp_user, self.config.smtp_password)
                server.send_message(msg)
            return True
        except smtplib.SMTPAuthenticationError:
            raise ValueError("SMTP authentication failed. Check credentials.")
        except Exception as e:
            raise ValueError(f"Failed to send email: {e}")

    def _format_text(self, order: dict) -> str:
        """Format receipt as plain text for email."""
        lines = [
            "HOTEL MANAGEMENT SYSTEM - RECEIPT",
            "=" * 40,
            f"Receipt #: {order.get('receipt_number', 'N/A')}",
            f"Table: {order.get('table_id', 'N/A')}",
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "Items:",
            "-" * 40,
        ]
        for item in order.get("line_items", []):
            name = item.get("item_name", "?")
            qty = item.get("quantity", 1)
            total = item.get("total_amount", 0)
            lines.append(f"  {name} x{qty} = Rs.{total:.2f}")
        lines.extend([
            "-" * 40,
            f"Subtotal:  Rs.{order.get('subtotal', 0):.2f}",
            f"Discount: -Rs.{order.get('discount_amount', 0):.2f}",
            f"Tax (18%):  Rs.{order.get('tax_amount', 0):.2f}",
            f"TOTAL:      Rs.{order.get('total_amount', 0):.2f}",
            "",
            "Thank you for dining with us!",
        ])
        return "\n".join(lines)

    def _format_html(self, order: dict) -> str:
        """Format receipt as HTML for email."""
        items_html = ""
        for item in order.get("line_items", []):
            name = item.get("item_name", "?")
            qty = item.get("quantity", 1)
            total = item.get("total_amount", 0)
            items_html += f"<tr><td>{name}</td><td align='center'>{qty}</td><td align='right'>Rs.{total:.2f}</td></tr>"

        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 400px; margin: 0 auto;">
            <div style="background: #1565C0; color: white; padding: 20px; text-align: center;">
                <h2 style="margin: 0;">Hotel Management System</h2>
                <p style="margin: 5px 0;">Receipt #{order.get('receipt_number', 'N/A')}</p>
            </div>
            <div style="padding: 20px;">
                <p><strong>Table:</strong> {order.get('table_id', 'N/A')}</p>
                <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                <table width="100%" style="border-collapse: collapse;">
                    <tr style="border-bottom: 2px solid #333;">
                        <th align="left">Item</th>
                        <th align="center">Qty</th>
                        <th align="right">Total</th>
                    </tr>
                    {items_html}
                </table>
                <hr>
                <table width="100%">
                    <tr><td>Subtotal:</td><td align="right">Rs.{order.get('subtotal', 0):.2f}</td></tr>
                    <tr><td>Discount:</td><td align="right">-Rs.{order.get('discount_amount', 0):.2f}</td></tr>
                    <tr><td>Tax (18%):</td><td align="right">Rs.{order.get('tax_amount', 0):.2f}</td></tr>
                    <tr style="font-size: 1.2em; font-weight: bold;">
                        <td>TOTAL:</td><td align="right">Rs.{order.get('total_amount', 0):.2f}</td></tr>
                </table>
            </div>
            <div style="background: #f5f5f5; padding: 15px; text-align: center; font-size: 0.9em;">
                Thank you for dining with us!
            </div>
        </body>
        </html>
        """
