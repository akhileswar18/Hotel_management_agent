"""
Reports Screen

Rebuilt reporting dashboard with resilient dark layouts and empty-state rendering.
"""

import csv
from datetime import date, timedelta
from typing import Dict, List

import flet as ft
import httpx

from src.ui.components.ui_helpers import (
    HMSColors,
    RefreshButton,
    build_header,
    show_error_dialog,
    show_success_dialog,
)


class ReportsScreen(ft.Column):
    """Reports and analytics dashboard."""

    BG = "#0E1117"
    SURFACE = "#161B27"
    SURFACE2 = "#1E2535"
    SURFACE3 = "#252D40"
    BORDER = "#2A3349"
    ACCENT = "#FF6B35"
    ACCENT2 = "#FFB347"
    GREEN = "#22C55E"
    RED = "#EF4444"
    YELLOW = "#EAB308"
    BLUE = "#3B82F6"
    TEXT_PRI = "#F0F4FF"
    TEXT_SEC = "#8B96B0"
    TEXT_MUT = "#4B5675"

    def __init__(self, page: ft.Page, user_info: dict, on_back):
        self._page = page
        self.user_info = user_info
        self.on_back = on_back
        self.api_base = "http://127.0.0.1:8000"
        self._selected_date = date.today()

        self._sales_data: Dict = {}
        self._inventory_data: Dict = {}
        self._yesterday_sales_data: Dict = {}

        self.date_display = ft.Text("", size=14, color=self.TEXT_SEC)
        self.refresh_button = RefreshButton(
            on_refresh=self._refresh_reports,
            page=self._page,
            tooltip="Refresh reports",
        )
        self.toolbar = self._build_toolbar()
        self.content_area = ft.Column([], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)

        super().__init__(
            controls=[
                build_header("Reports", user_info),
                self.toolbar,
                ft.Container(
                    expand=True,
                    bgcolor=self.BG,
                    padding=ft.padding.all(20),
                    content=self.content_area,
                ),
            ],
            spacing=0,
            expand=True,
        )

        self._load_reports()

    def _nav_btn(self, label: str, handler, primary: bool = False) -> ft.ElevatedButton:
        return ft.ElevatedButton(
            label,
            on_click=handler,
            height=36,
            style=ft.ButtonStyle(
                bgcolor=self.ACCENT if primary else self.SURFACE2,
                color="#FFFFFF" if primary else self.TEXT_SEC,
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.padding.symmetric(horizontal=16),
            ),
        )

    def _toolbar_btn(self, label: str, handler, color: str) -> ft.ElevatedButton:
        return ft.ElevatedButton(
            label,
            on_click=handler,
            height=36,
            style=ft.ButtonStyle(
                bgcolor=color,
                color="#0A0A0A",
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.padding.symmetric(horizontal=16),
            ),
        )

    def _build_toolbar(self) -> ft.Container:
        return ft.Container(
            bgcolor=self.SURFACE,
            border=ft.border.only(bottom=ft.BorderSide(1, self.BORDER)),
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            content=ft.Row(
                [
                    self._nav_btn("Prev", self._handle_prev_day),
                    self._nav_btn("Today", self._handle_today, primary=True),
                    self._nav_btn("Next", self._handle_next_day),
                    ft.Container(width=16),
                    self.date_display,
                    ft.Container(expand=True),
                    self._toolbar_btn("Export Sales CSV", self._handle_export_sales, self.GREEN),
                    self._toolbar_btn("Export Inventory CSV", self._handle_export_inventory, self.GREEN),
                    self.refresh_button,
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _refresh_reports(self, *_args):
        self._load_reports()

    def _safe_update(self, control: ft.Control):
        try:
            if control.page:
                control.update()
        except Exception:
            pass

    def _daily_sales_total(self, sales: Dict) -> float:
        return float(sales.get("total_revenue", sales.get("total_sales", 0.0)) or 0.0)

    def _transactions_count(self, sales: Dict) -> int:
        return int(sales.get("transaction_count", sales.get("transactions_count", sales.get("orders_count", 0))) or 0)

    def _avg_order_value(self, sales: Dict) -> float:
        return float(sales.get("average_order_value", sales.get("avg_order_value", 0.0)) or 0.0)

    def _payment_breakdown(self, sales: Dict) -> Dict[str, float]:
        payment_breakdown = sales.get("payment_breakdown")
        if isinstance(payment_breakdown, dict):
            return {
                "CASH": float(payment_breakdown.get("CASH", payment_breakdown.get("cash", 0.0)) or 0.0),
                "CARD": float(payment_breakdown.get("CARD", payment_breakdown.get("card", 0.0)) or 0.0),
                "VOUCHER": float(payment_breakdown.get("VOUCHER", payment_breakdown.get("voucher", 0.0)) or 0.0),
            }

        payment_methods = sales.get("payment_methods", {}) or {}
        return {
            "CASH": float((payment_methods.get("CASH") or {}).get("total", 0.0) or 0.0),
            "CARD": float((payment_methods.get("CARD") or {}).get("total", 0.0) or 0.0),
            "VOUCHER": float((payment_methods.get("VOUCHER") or {}).get("total", 0.0) or 0.0),
        }

    def _top_items(self, sales: Dict) -> List[Dict]:
        top_items = sales.get("top_items", []) or []
        normalized: List[Dict] = []
        for item in top_items:
            normalized.append(
                {
                    "name": item.get("name", item.get("item_name", "")),
                    "qty_sold": int(item.get("qty_sold", item.get("quantity_sold", 0)) or 0),
                }
            )
        return normalized

    def _inventory_counts(self) -> Dict[str, int]:
        inv = self._inventory_data or {}
        inventory_rows = inv.get("inventory", []) or []
        total = int(inv.get("total_items", len(inventory_rows)) or 0)
        low_stock = int(inv.get("low_stock_count", 0) or 0)
        out_of_stock = int(inv.get("out_of_stock_count", 0) or 0)

        if not out_of_stock and inventory_rows:
            out_of_stock = sum(1 for item in inventory_rows if int(item.get("stock_on_hand", 0) or 0) <= 0)

        in_stock = int(inv.get("in_stock_count", 0) or 0)
        if not in_stock and inventory_rows:
            in_stock = sum(1 for item in inventory_rows if int(item.get("stock_on_hand", 0) or 0) > 0)
        if not in_stock and total:
            in_stock = max(total - out_of_stock, 0)

        return {
            "in_stock": in_stock,
            "low_stock": low_stock,
            "out_stock": out_of_stock,
            "total": total,
        }

    def _revenue_change_pct(self) -> float:
        today_total = self._daily_sales_total(self._sales_data)
        yesterday_total = self._daily_sales_total(self._yesterday_sales_data)
        if yesterday_total <= 0:
            return 0.0
        return ((today_total - yesterday_total) / yesterday_total) * 100.0

    def _hourly_breakdown(self) -> List[Dict]:
        sales = self._sales_data or {}
        hourly = sales.get("hourly_breakdown")
        if isinstance(hourly, list) and hourly:
            return hourly

        today_series = sales.get("hourly_sales", {}) or {}
        yesterday_series = (self._yesterday_sales_data or {}).get("hourly_sales", {}) or {}
        labels = ["8A", "9A", "10A", "11A", "12P", "1P", "2P", "3P", "4P"]
        hour_map = {
            "8A": "08",
            "9A": "09",
            "10A": "10",
            "11A": "11",
            "12P": "12",
            "1P": "13",
            "2P": "14",
            "3P": "15",
            "4P": "16",
        }
        rows = []
        for label in labels:
            key = hour_map[label]
            rows.append(
                {
                    "hour": label,
                    "revenue": float(today_series.get(key, 0.0) or 0.0),
                    "prev_revenue": float(yesterday_series.get(key, 0.0) or 0.0),
                }
            )
        return rows

    def _card_shell(self, content: ft.Control, expand: bool = False, width: int | None = None) -> ft.Container:
        return ft.Container(
            expand=expand,
            width=width,
            bgcolor=self.SURFACE,
            border=ft.border.all(1, self.BORDER),
            border_radius=12,
            padding=20,
            content=content,
        )

    def _stat_card(self, icon: str, value: str, label: str, sublabel: str, color: str) -> ft.Container:
        sublabel_color = self.TEXT_MUT
        if sublabel.startswith("↑") or sublabel.startswith("✓"):
            sublabel_color = self.GREEN
        elif sublabel.startswith("↓") or sublabel.startswith("⚠"):
            sublabel_color = self.RED if sublabel.startswith("↓") else self.YELLOW

        return ft.Container(
            expand=True,
            bgcolor=self.SURFACE,
            border=ft.border.all(1, self.BORDER),
            border_radius=12,
            padding=20,
            content=ft.Stack(
                [
                    ft.Container(height=2, bgcolor=color, left=0, right=0, top=0),
                    ft.Container(
                        margin=ft.margin.only(top=10),
                        content=ft.Column(
                            [
                                ft.Container(
                                    width=40,
                                    height=40,
                                    border_radius=10,
                                    bgcolor=color + "20",
                                    alignment=ft.alignment.center,
                                    content=ft.Text(icon, size=20, text_align=ft.TextAlign.CENTER),
                                ),
                                ft.Text(value, size=26, weight=ft.FontWeight.W_800, color=color, font_family="Syne"),
                                ft.Text(label, size=12, color=self.TEXT_SEC),
                                ft.Text(sublabel, size=11, color=sublabel_color),
                            ],
                            spacing=6,
                            tight=True,
                        ),
                    ),
                ]
            ),
        )

    def _build_bar_chart(self) -> ft.Container:
        hours = self._hourly_breakdown() or [
            {"hour": h, "revenue": 0, "prev_revenue": 0}
            for h in ["8A", "9A", "10A", "11A", "12P", "1P", "2P", "3P", "4P"]
        ]
        max_val = max([max(float(h.get("revenue", 0)), float(h.get("prev_revenue", 0))) for h in hours] + [1.0])
        bar_height = 120
        bars = []
        for hour in hours:
            today_h = max(int(bar_height * float(hour.get("revenue", 0)) / max_val), 3)
            prev_h = max(int(bar_height * float(hour.get("prev_revenue", 0)) / max_val), 3)
            bars.append(
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Container(
                                    width=16,
                                    height=today_h,
                                    bgcolor=self.ACCENT,
                                    border_radius=ft.border_radius.only(top_left=3, top_right=3),
                                ),
                                ft.Container(
                                    width=16,
                                    height=prev_h,
                                    bgcolor=self.SURFACE3,
                                    border_radius=ft.border_radius.only(top_left=3, top_right=3),
                                ),
                            ],
                            spacing=2,
                            vertical_alignment=ft.CrossAxisAlignment.END,
                        ),
                        ft.Text(str(hour.get("hour", "")), size=9, color=self.TEXT_MUT, text_align=ft.TextAlign.CENTER),
                    ],
                    spacing=4,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.END,
                )
            )

        return ft.Container(
            height=bar_height + 24,
            bgcolor=self.SURFACE2,
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            content=ft.Row(
                bars,
                alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                vertical_alignment=ft.CrossAxisAlignment.END,
                expand=True,
            ),
        )

    def _chart_card(self) -> ft.Container:
        return self._card_shell(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("📊 Hourly Revenue Today", size=14, weight=ft.FontWeight.W_700, color=self.TEXT_PRI),
                            ft.Container(expand=True),
                            ft.Row(
                                [
                                    ft.Container(width=10, height=10, border_radius=2, bgcolor=self.ACCENT),
                                    ft.Text("Today", size=11, color=self.TEXT_SEC),
                                    ft.Container(width=10, height=10, border_radius=2, bgcolor=self.SURFACE3),
                                    ft.Text("Yesterday", size=11, color=self.TEXT_SEC),
                                ],
                                spacing=6,
                            ),
                        ]
                    ),
                    self._build_bar_chart(),
                ],
                spacing=12,
            ),
            expand=True,
        )

    def _build_payment_rows(self) -> ft.Column:
        payment = self._payment_breakdown(self._sales_data)
        total = sum(payment.values()) or 1.0

        def pay_row(label: str, amount: float, color: str) -> ft.Column:
            pct = int(amount / total * 100)
            return ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(label, size=13, color=self.TEXT_SEC, expand=True),
                            ft.Text(f"₹{amount:,.0f} ({pct}%)", size=13, color=self.TEXT_PRI, font_family="DM Mono"),
                        ]
                    ),
                    ft.Stack(
                        [
                            ft.Container(height=6, bgcolor=self.SURFACE3, border_radius=3, width=300),
                            ft.Container(height=6, border_radius=3, bgcolor=color, width=300 * pct / 100),
                        ]
                    ),
                ],
                spacing=6,
            )

        return ft.Column(
            [
                pay_row("Cash", payment.get("CASH", 0.0), self.GREEN),
                ft.Container(height=8),
                pay_row("Card", payment.get("CARD", 0.0), self.BLUE),
                ft.Container(height=8),
                pay_row("Voucher", payment.get("VOUCHER", 0.0), self.ACCENT),
            ],
            spacing=0,
        )

    def _payment_card(self) -> ft.Container:
        return self._card_shell(
            ft.Column(
                [
                    ft.Text("💳 Payment Split", size=14, weight=ft.FontWeight.W_700, color=self.TEXT_PRI),
                    ft.Container(height=12),
                    self._build_payment_rows(),
                ],
                spacing=0,
            ),
            width=380,
        )

    def _build_top_items_rows(self) -> List[ft.Control]:
        items = self._top_items(self._sales_data)[:5]
        max_qty = max([i.get("qty_sold", 1) for i in items] + [1])
        rows: List[ft.Control] = []
        for idx, item in enumerate(items):
            qty = int(item.get("qty_sold", 0))
            fill = int(200 * (qty / max_qty))
            rows.append(
                ft.Container(
                    border=ft.border.only(bottom=ft.BorderSide(1, self.BORDER + "60")),
                    padding=ft.padding.symmetric(vertical=10),
                    content=ft.Row(
                        [
                            ft.Text(str(idx + 1), size=18, weight=ft.FontWeight.W_800, color=self.TEXT_MUT, width=28),
                            ft.Text(str(item.get("name", "")), size=13, color=self.TEXT_PRI, expand=True),
                            ft.Stack(
                                [
                                    ft.Container(height=6, width=200, bgcolor=self.SURFACE3, border_radius=3),
                                    ft.Container(height=6, width=fill, bgcolor=self.ACCENT, border_radius=3),
                                ]
                            ),
                            ft.Text(
                                f"{qty}\nsold",
                                size=11,
                                color=self.TEXT_SEC,
                                font_family="DM Mono",
                                text_align=ft.TextAlign.RIGHT,
                                width=40,
                            ),
                        ],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )
        if not rows:
            rows = [ft.Text("No sales data for this date", size=13, color=self.TEXT_MUT)]
        return rows

    def _top_items_card(self) -> ft.Container:
        return self._card_shell(
            ft.Column(
                [
                    ft.Text("🏆 Top 5 Selling Items", size=14, weight=ft.FontWeight.W_700, color=self.TEXT_PRI),
                    ft.Container(height=12),
                    *self._build_top_items_rows(),
                ],
                spacing=0,
            ),
            expand=True,
        )

    def _build_inv_grid(self) -> ft.Column:
        counts = self._inventory_counts()

        def inv_cell(number: int, label: str, color: str) -> ft.Container:
            return ft.Container(
                expand=True,
                border=ft.border.all(1, color + "30"),
                border_radius=8,
                padding=16,
                bgcolor=color + "10",
                content=ft.Column(
                    [
                        ft.Text(str(number), size=28, weight=ft.FontWeight.W_800, color=color, font_family="Syne"),
                        ft.Text(label, size=11, color=self.TEXT_SEC),
                    ],
                    spacing=4,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )

        return ft.Column(
            [
                ft.Row(
                    [
                        inv_cell(counts["in_stock"], "In Stock", self.GREEN),
                        ft.Container(width=8),
                        inv_cell(counts["low_stock"], "Low Stock", self.YELLOW),
                    ]
                ),
                ft.Container(height=8),
                ft.Row(
                    [
                        inv_cell(counts["out_stock"], "Out of Stock", self.RED),
                        ft.Container(width=8),
                        inv_cell(counts["total"], "Total Items", self.BLUE),
                    ]
                ),
            ],
            spacing=0,
        )

    def _inventory_card(self) -> ft.Container:
        return self._card_shell(
            ft.Column(
                [
                    ft.Text("📦 Inventory Snapshot", size=14, weight=ft.FontWeight.W_700, color=self.TEXT_PRI),
                    ft.Container(height=12),
                    self._build_inv_grid(),
                    ft.Container(height=12),
                    ft.ElevatedButton(
                        "📦 View Full Inventory",
                        on_click=lambda e: self.on_back(),
                        style=ft.ButtonStyle(
                            bgcolor=self.SURFACE2,
                            color=self.TEXT_SEC,
                            shape=ft.RoundedRectangleBorder(radius=8),
                            side=ft.BorderSide(1, self.BORDER),
                        ),
                        expand=True,
                        height=40,
                    ),
                ],
                spacing=0,
            ),
            width=400,
        )

    def _render_reports(self):
        sales = self._sales_data or {}
        inv_counts = self._inventory_counts()
        total_revenue = self._daily_sales_total(sales)
        transaction_count = self._transactions_count(sales)
        avg_order_value = self._avg_order_value(sales)
        low_count = inv_counts["low_stock"]

        self.stats_row = ft.Row(
            [
                self._stat_card(
                    "💰",
                    f"₹{total_revenue:,.0f}",
                    "Total Revenue",
                    f"↑ {self._revenue_change_pct():.0f}% vs yesterday" if total_revenue > 0 else "No sales yet",
                    self.GREEN,
                ),
                self._stat_card(
                    "🧾",
                    str(transaction_count),
                    "Transactions",
                    f"Avg order ₹{avg_order_value:,.0f}",
                    self.ACCENT,
                ),
                self._stat_card(
                    "📈",
                    f"₹{avg_order_value:,.0f}",
                    "Avg Order Value",
                    "— Peak: 1-2 PM" if avg_order_value > 0 else "—",
                    self.YELLOW,
                ),
                self._stat_card(
                    "📦",
                    str(inv_counts["total"]),
                    "Items in Stock",
                    f"⚠ {low_count} need restocking" if low_count > 0 else "✓ All stocked",
                    self.BLUE,
                ),
            ],
            spacing=16,
            expand=False,
        )

        charts_row = ft.Row(
            [
                self._chart_card(),
                self._payment_card(),
            ],
            spacing=16,
            expand=False,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        bottom_row = ft.Row(
            [
                self._top_items_card(),
                self._inventory_card(),
            ],
            spacing=16,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        self.content_area.controls = [
            self.stats_row,
            charts_row,
            bottom_row,
        ]
        self._safe_update(self.content_area)

    def _load_reports(self):
        today = self._selected_date.isoformat()
        yesterday = (self._selected_date - timedelta(days=1)).isoformat()
        self.date_display.value = self._selected_date.strftime("%A, %d %b %Y")
        try:
            with httpx.Client(timeout=5.0) as client:
                sales_resp = client.get(f"{self.api_base}/api/reports/daily-sales", params={"date": today})
                inv_resp = client.get(f"{self.api_base}/api/reports/inventory-snapshot")
                y_sales_resp = client.get(f"{self.api_base}/api/reports/daily-sales", params={"date": yesterday})
                self._sales_data = sales_resp.json() if sales_resp.status_code == 200 else {}
                self._inventory_data = inv_resp.json() if inv_resp.status_code == 200 else {}
                self._yesterday_sales_data = y_sales_resp.json() if y_sales_resp.status_code == 200 else {}
        except Exception:
            self._sales_data = {}
            self._inventory_data = {}
            self._yesterday_sales_data = {}
        finally:
            self._render_reports()
            try:
                self._page.update()
            except Exception:
                pass

    def _handle_prev_day(self, e):
        self._selected_date -= timedelta(days=1)
        self._load_reports()

    def _handle_next_day(self, e):
        self._selected_date += timedelta(days=1)
        self._load_reports()

    def _handle_today(self, e):
        self._selected_date = date.today()
        self._load_reports()

    def _handle_export_sales(self, e):
        try:
            filename = f"sales_report_{self._selected_date.isoformat()}.csv"
            rows: List[dict] = self._sales_data.get("transactions", []) or []
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["order_id", "receipt_number", "table_id", "total_amount", "payment_method", "finalized_at"],
                )
                writer.writeheader()
                for r in rows:
                    writer.writerow(
                        {
                            "order_id": r.get("order_id", ""),
                            "receipt_number": r.get("receipt_number", ""),
                            "table_id": r.get("table_id", ""),
                            "total_amount": r.get("total_amount", ""),
                            "payment_method": r.get("payment_method", ""),
                            "finalized_at": r.get("finalized_at", ""),
                        }
                    )
            show_success_dialog(self._page, "CSV Exported", f"Sales report saved to {filename}")
        except Exception as err:
            show_error_dialog(self._page, "Export Error", str(err))

    def _handle_export_inventory(self, e):
        try:
            filename = f"inventory_snapshot_{self._selected_date.isoformat()}.csv"
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["total_items", "in_stock_count", "low_stock_count", "out_of_stock_count"],
                )
                writer.writeheader()
                counts = self._inventory_counts()
                writer.writerow(
                    {
                        "total_items": counts["total"],
                        "in_stock_count": counts["in_stock"],
                        "low_stock_count": counts["low_stock"],
                        "out_of_stock_count": counts["out_stock"],
                    }
                )
            show_success_dialog(self._page, "CSV Exported", f"Inventory snapshot saved to {filename}")
        except Exception as err:
            show_error_dialog(self._page, "Export Error", str(err))
