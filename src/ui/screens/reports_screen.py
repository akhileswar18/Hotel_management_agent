"""
Reports Screen

Visual analytics with primitive bar/progress charts (no new dependencies).
"""

import csv
from datetime import date, timedelta
from typing import Dict, List

import flet as ft
import httpx

from src.ui.components.ui_helpers import (
    HMSButton,
    HMSColors,
    build_header,
    stat_card,
    section_header,
    show_error_dialog,
    show_success_dialog,
)


class ReportsScreen(ft.Column):
    """Reports and analytics dashboard."""

    def __init__(self, page: ft.Page, user_info: dict, on_back):
        self._page = page
        self.user_info = user_info
        self.on_back = on_back
        self.api_base = "http://127.0.0.1:8000"
        self._selected_date = date.today()

        self._sales_data: Dict = {}
        self._inventory_data: Dict = {}
        self._yesterday_sales_data: Dict = {}

        self.date_text = ft.Text("", size=14, color=HMSColors.TEXT_SECONDARY)
        self.stats_row = ft.Row(spacing=12, wrap=True)
        self.hourly_chart = ft.Row(height=150, spacing=8, alignment=ft.MainAxisAlignment.END)
        self.payment_rows = ft.Column(spacing=10)
        self.top_items_rows = ft.Column(spacing=8)
        self.inventory_snapshot_grid = ft.Row(spacing=8, wrap=True)

        super().__init__(
            [
                build_header("Reports", user_info),
                ft.Container(
                    expand=True,
                    padding=16,
                    content=ft.Column(
                        [
                            self._build_top_controls(),
                            self.stats_row,
                            ft.Row(
                                [
                                    self._surface_card(
                                        ft.Column([section_header("Hourly Revenue (Today vs Yesterday)"), self.hourly_chart], spacing=8),
                                        expand=1,
                                    ),
                                    self._surface_card(
                                        ft.Column([section_header("Payment Breakdown"), self.payment_rows], spacing=8),
                                        expand=1,
                                    ),
                                ],
                                spacing=12,
                                expand=True,
                            ),
                            ft.Row(
                                [
                                    self._surface_card(
                                        ft.Column([section_header("Top 5 Items"), self.top_items_rows], spacing=8),
                                        expand=1,
                                    ),
                                    self._surface_card(
                                        ft.Column([section_header("Inventory Snapshot"), self.inventory_snapshot_grid], spacing=8),
                                        expand=1,
                                    ),
                                ],
                                spacing=12,
                                expand=True,
                            ),
                        ],
                        spacing=12,
                        expand=True,
                    ),
                ),
            ],
            spacing=0,
            expand=True,
        )

        self._load_reports()
        self._render()

    def _surface_card(self, content: ft.Control, expand: int = 0) -> ft.Container:
        return ft.Container(
            expand=expand,
            bgcolor=HMSColors.SURFACE,
            border=ft.border.all(1, HMSColors.BORDER),
            border_radius=12,
            padding=14,
            content=content,
        )

    def _build_top_controls(self) -> ft.Row:
        return ft.Row(
            [
                HMSButton("Prev", self._handle_prev_day, width=90, height=48, color=HMSColors.SURFACE2),
                HMSButton("Today", self._handle_today, width=100, height=48, color=HMSColors.BLUE),
                HMSButton("Next", self._handle_next_day, width=90, height=48, color=HMSColors.SURFACE2),
                self.date_text,
                ft.Container(expand=True),
                HMSButton("Export Sales CSV", self._handle_export_sales, width=170, height=48, color=HMSColors.GREEN),
                HMSButton("Export Inventory CSV", self._handle_export_inventory, width=190, height=48, color=HMSColors.GREEN),
                HMSButton("Back", lambda e: self.on_back(), width=100, height=48),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _load_reports(self):
        today = self._selected_date.isoformat()
        yesterday = (self._selected_date - timedelta(days=1)).isoformat()
        self.date_text.value = self._selected_date.strftime("%A, %d %b %Y")
        try:
            with httpx.Client(timeout=5.0) as client:
                sales_resp = client.get(f"{self.api_base}/api/reports/daily-sales", params={"date": today})
                inv_resp = client.get(f"{self.api_base}/api/reports/inventory-snapshot")
                y_sales_resp = client.get(f"{self.api_base}/api/reports/daily-sales", params={"date": yesterday})
                self._sales_data = sales_resp.json() if sales_resp.status_code == 200 else {}
                self._inventory_data = inv_resp.json() if inv_resp.status_code == 200 else {}
                self._yesterday_sales_data = y_sales_resp.json() if y_sales_resp.status_code == 200 else {}
        except Exception as ex:
            show_error_dialog(self._page, "Report Error", str(ex))
            self._sales_data = {}
            self._inventory_data = {}
            self._yesterday_sales_data = {}

    def _render(self):
        total_sales = float(self._sales_data.get("total_sales", 0.0))
        tx_count = int(self._sales_data.get("transactions_count", 0))
        avg_order = float(self._sales_data.get("avg_order_value", 0.0))
        pay = self._sales_data.get("payment_breakdown", {}) or {}
        low_stock_count = int(self._inventory_data.get("low_stock_count", 0))

        self.stats_row.controls = [
            ft.Container(expand=1, content=stat_card("Rs", f"Rs.{total_sales:.2f}", "Revenue", HMSColors.GREEN)),
            ft.Container(expand=1, content=stat_card("🧾", str(tx_count), "Transactions", HMSColors.ACCENT)),
            ft.Container(expand=1, content=stat_card("AVG", f"Rs.{avg_order:.2f}", "Avg Order", HMSColors.BLUE)),
            ft.Container(expand=1, content=stat_card("⚠", str(low_stock_count), "Low Stock", HMSColors.YELLOW)),
        ]

        self._render_hourly_chart()
        self._render_payment_breakdown(pay)
        self._render_top_items()
        self._render_inventory_snapshot()

        for ctl in [self.date_text, self.stats_row, self.hourly_chart, self.payment_rows, self.top_items_rows, self.inventory_snapshot_grid]:
            if ctl.page:
                ctl.update()

    def _render_hourly_chart(self):
        hours = [f"{h:02d}" for h in range(8, 21)]
        today_series = self._sales_data.get("hourly_sales", {}) or {}
        y_series = self._yesterday_sales_data.get("hourly_sales", {}) or {}
        vals = [float(today_series.get(h, 0.0)) for h in hours] + [float(y_series.get(h, 0.0)) for h in hours]
        max_val = max(vals) if vals else 1.0
        max_val = max(max_val, 1.0)

        self.hourly_chart.controls.clear()
        for h in hours:
            t_val = float(today_series.get(h, 0.0))
            y_val = float(y_series.get(h, 0.0))
            t_height = max(4, int((t_val / max_val) * 100))
            y_height = max(4, int((y_val / max_val) * 100))
            self.hourly_chart.controls.append(
                ft.Column(
                    [
                        ft.Container(width=12, height=t_height, bgcolor=HMSColors.ACCENT, border_radius=4),
                        ft.Container(width=12, height=y_height, bgcolor=HMSColors.SURFACE3, border_radius=4),
                        ft.Text(h, size=9, color=HMSColors.TEXT_MUTED),
                    ],
                    spacing=2,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.END,
                )
            )

    def _render_payment_breakdown(self, pay: dict):
        self.payment_rows.controls.clear()
        total = max(float(pay.get("cash", 0.0)) + float(pay.get("card", 0.0)) + float(pay.get("voucher", 0.0)), 1.0)
        rows = [
            ("Cash", float(pay.get("cash", 0.0)), HMSColors.GREEN),
            ("Card", float(pay.get("card", 0.0)), HMSColors.BLUE),
            ("Voucher", float(pay.get("voucher", 0.0)), HMSColors.ACCENT),
        ]
        for label, value, color in rows:
            pct = (value / total) * 100.0
            self.payment_rows.controls.append(
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(label, size=12, color=HMSColors.TEXT_SECONDARY),
                                ft.Container(expand=True),
                                ft.Text(f"Rs.{value:.2f}", size=12, color=HMSColors.TEXT_PRIMARY, font_family="DM Mono"),
                                ft.Text(f"{pct:.0f}%", size=12, color=HMSColors.TEXT_SECONDARY, font_family="DM Mono"),
                            ]
                        ),
                        ft.Stack(
                            [
                                ft.Container(width=260, height=4, bgcolor=HMSColors.SURFACE3, border_radius=4),
                                ft.Container(width=max(4, int(260 * pct / 100.0)), height=4, bgcolor=color, border_radius=4),
                            ],
                            width=260,
                            height=4,
                        ),
                    ],
                    spacing=4,
                    tight=True,
                )
            )

    def _render_top_items(self):
        self.top_items_rows.controls.clear()
        top = self._sales_data.get("top_items", []) or []
        if not top:
            self.top_items_rows.controls.append(ft.Text("No top-item data", color=HMSColors.TEXT_SECONDARY))
            return
        max_qty = max(int(item.get("qty_sold", 0)) for item in top) if top else 1
        max_qty = max(max_qty, 1)
        for idx, item in enumerate(top[:5], start=1):
            qty = int(item.get("qty_sold", 0))
            w = max(4, int((qty / max_qty) * 110))
            self.top_items_rows.controls.append(
                ft.Row(
                    [
                        ft.Text(str(idx), width=24, size=18, color=HMSColors.TEXT_MUTED, font_family="Syne"),
                        ft.Text(str(item.get("item_name", "Item")), expand=True, color=HMSColors.TEXT_PRIMARY),
                        ft.Stack(
                            [
                                ft.Container(width=110, height=6, bgcolor=HMSColors.SURFACE3, border_radius=4),
                                ft.Container(width=w, height=6, bgcolor=HMSColors.ACCENT, border_radius=4),
                            ],
                            width=110,
                            height=6,
                        ),
                        ft.Text(str(qty), width=40, text_align=ft.TextAlign.RIGHT, color=HMSColors.TEXT_SECONDARY, font_family="DM Mono"),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )

    def _render_inventory_snapshot(self):
        self.inventory_snapshot_grid.controls.clear()
        tiles = [
            ("In Stock", int(self._inventory_data.get("in_stock_count", 0)), HMSColors.GREEN),
            ("Low Stock", int(self._inventory_data.get("low_stock_count", 0)), HMSColors.YELLOW),
            ("Out of Stock", int(self._inventory_data.get("out_of_stock_count", 0)), HMSColors.RED),
            ("Total", int(self._inventory_data.get("total_items", 0)), HMSColors.BLUE),
        ]
        for label, value, color in tiles:
            self.inventory_snapshot_grid.controls.append(
                ft.Container(
                    width=130,
                    height=90,
                    bgcolor=HMSColors.SURFACE2,
                    border=ft.border.all(1, HMSColors.BORDER),
                    border_radius=10,
                    padding=10,
                    content=ft.Column(
                        [
                            ft.Text(str(value), size=26, color=color, weight=ft.FontWeight.W_800, font_family="Syne"),
                            ft.Text(label, size=12, color=HMSColors.TEXT_SECONDARY),
                        ],
                        spacing=4,
                        tight=True,
                    ),
                )
            )

    def _handle_prev_day(self, e):
        self._selected_date -= timedelta(days=1)
        self._load_reports()
        self._render()

    def _handle_next_day(self, e):
        self._selected_date += timedelta(days=1)
        self._load_reports()
        self._render()

    def _handle_today(self, e):
        self._selected_date = date.today()
        self._load_reports()
        self._render()

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
                writer.writerow(
                    {
                        "total_items": self._inventory_data.get("total_items", 0),
                        "in_stock_count": self._inventory_data.get("in_stock_count", 0),
                        "low_stock_count": self._inventory_data.get("low_stock_count", 0),
                        "out_of_stock_count": self._inventory_data.get("out_of_stock_count", 0),
                    }
                )
            show_success_dialog(self._page, "CSV Exported", f"Inventory snapshot saved to {filename}")
        except Exception as err:
            show_error_dialog(self._page, "Export Error", str(err))

