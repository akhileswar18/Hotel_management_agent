"""
Reports Screen

Daily sales summary, inventory snapshot, date filtering, and CSV export.
"""

import csv
import io
import flet as ft
import httpx
from datetime import datetime, date, timedelta
from src.ui.components.ui_helpers import (
    HMSButton, HMSColors, show_error_dialog, show_success_dialog, create_header,
    RefreshButton,
)


class ReportsScreen(ft.Column):
    """Reports and analytics screen."""

    def __init__(self, page: ft.Page, user_info: dict, on_back):
        self._page = page
        self.user_info = user_info
        self.on_back = on_back
        self.api_base = "http://127.0.0.1:8000"
        self._sales_data = {}
        self._inventory_data = {}
        self._selected_date = date.today()

        header = create_header(page, "Reports & Analytics", user_info.get("username"))

        # Date filter row
        self.date_display = ft.Text(
            self._selected_date.strftime("%A, %B %d, %Y"),
            size=16, weight="bold",
        )

        prev_day_btn = ft.IconButton(
            icon=ft.icons.CHEVRON_LEFT,
            tooltip="Previous day",
            on_click=self._handle_prev_day,
        )
        next_day_btn = ft.IconButton(
            icon=ft.icons.CHEVRON_RIGHT,
            tooltip="Next day",
            on_click=self._handle_next_day,
        )
        today_btn = HMSButton(
            "Today",
            self._handle_today,
            width=80,
            color=HMSColors.PRIMARY,
        )
        self.date_input = ft.TextField(
            label="Date (YYYY-MM-DD)",
            hint_text="e.g. 2026-02-11",
            width=180,
            height=48,
            text_size=14,
            value=self._selected_date.isoformat(),
            on_submit=self._handle_date_input,
        )
        go_btn = HMSButton(
            "Go",
            self._handle_date_input,
            width=60,
            color=HMSColors.PRIMARY,
        )

        date_row = ft.Row(
            [
                prev_day_btn,
                self.date_display,
                next_day_btn,
                ft.Container(width=20),
                today_btn,
                ft.Container(width=20),
                self.date_input,
                go_btn,
            ],
            spacing=5,
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # Sales summary section
        self.sales_summary = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Daily Sales Summary", size=18, weight="bold"),
                        ft.Text("Loading...", size=14, color=HMSColors.TEXT_SECONDARY),
                    ],
                    spacing=10,
                ),
                padding=20,
            ),
            margin=10,
        )

        # Inventory snapshot section
        self.inventory_summary = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Inventory Status", size=18, weight="bold"),
                        ft.Text("Loading...", size=14, color=HMSColors.TEXT_SECONDARY),
                    ],
                    spacing=10,
                ),
                padding=20,
            ),
            margin=10,
        )

        # Transaction search section
        self.txn_method_filter = ft.Dropdown(
            label="Payment Method",
            options=[
                ft.dropdown.Option("", "All Methods"),
                ft.dropdown.Option("CASH", "Cash"),
                ft.dropdown.Option("CARD", "Card"),
                ft.dropdown.Option("VOUCHER", "Voucher"),
            ],
            value="",
            width=160,
        )

        self.txn_start_date = ft.TextField(
            label="Start Date",
            hint_text="YYYY-MM-DD",
            width=150,
            height=48,
            text_size=14,
        )

        self.txn_end_date = ft.TextField(
            label="End Date",
            hint_text="YYYY-MM-DD",
            width=150,
            height=48,
            text_size=14,
        )

        txn_search_btn = HMSButton(
            "Search Transactions",
            self._handle_txn_search,
            color=HMSColors.PRIMARY,
        )

        self.txn_results_list = ft.ListView(spacing=5, height=250)
        self.txn_count_text = ft.Text("", size=13, color=HMSColors.TEXT_SECONDARY)

        self.transaction_section = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Transaction Search", size=18, weight="bold"),
                        ft.Row([
                            self.txn_start_date,
                            self.txn_end_date,
                            self.txn_method_filter,
                            txn_search_btn,
                        ], spacing=10, wrap=True),
                        self.txn_count_text,
                        self.txn_results_list,
                    ],
                    spacing=10,
                ),
                padding=20,
            ),
            margin=10,
        )

        # Standardized Refresh button (replaces ad-hoc HMSButton)
        self.refresh_button = RefreshButton(
            on_refresh=self._load_reports,
            page=self._page,
            tooltip="Refresh reports",
        )

        export_sales_button = HMSButton(
            "Export Sales CSV",
            self._handle_export_sales,
            color=HMSColors.SUCCESS,
        )

        export_inv_button = HMSButton(
            "Export Inventory CSV",
            self._handle_export_inventory,
            color=HMSColors.SUCCESS,
        )

        back_button = HMSButton(
            "Back to POS",
            lambda e: on_back(),
        )

        self.loading = ft.ProgressRing(visible=False)

        super().__init__(
            [
                ft.Row(
                    [
                        ft.Text("Reports", size=20, weight="bold"),
                        ft.Container(expand=True),
                        self.refresh_button,
                        export_sales_button,
                        export_inv_button,
                        back_button,
                    ],
                    spacing=10,
                ),
                ft.Divider(),
                date_row,
                ft.Divider(),
                self.sales_summary,
                self.inventory_summary,
                self.transaction_section,
                ft.Row([self.loading], alignment=ft.MainAxisAlignment.CENTER),
            ],
            spacing=10,
            expand=True,
        )

        # Load reports
        self._load_reports()

    def _set_date(self, new_date: date):
        """Update selected date and refresh."""
        self._selected_date = new_date
        self.date_display.value = new_date.strftime("%A, %B %d, %Y")
        self.date_input.value = new_date.isoformat()
        self._load_reports()
        try:
            self._page.update()
        except Exception:
            pass

    def _handle_prev_day(self, e):
        self._set_date(self._selected_date - timedelta(days=1))

    def _handle_next_day(self, e):
        self._set_date(self._selected_date + timedelta(days=1))

    def _handle_today(self, e):
        self._set_date(date.today())

    def _handle_date_input(self, e):
        val = self.date_input.value.strip()
        try:
            parsed = date.fromisoformat(val)
            self._set_date(parsed)
        except ValueError:
            show_error_dialog(self.page, "Invalid Date", "Enter date as YYYY-MM-DD")

    def _load_reports(self):
        """Load reports from API for selected date."""
        try:
            with httpx.Client(timeout=5.0) as client:
                sales_response = client.get(
                    f"{self.api_base}/api/reports/daily-sales",
                    params={"report_date": self._selected_date.isoformat()},
                )
                inventory_response = client.get(
                    f"{self.api_base}/api/reports/inventory-snapshot",
                )

                if sales_response.status_code == 200:
                    self._sales_data = sales_response.json()
                    self._display_sales_summary(self._sales_data)

                if inventory_response.status_code == 200:
                    self._inventory_data = inventory_response.json()
                    self._display_inventory_summary(self._inventory_data)

        except Exception:
            pass  # API may not be running yet

    def _display_sales_summary(self, data: dict):
        """Display sales summary by rebuilding the card content."""
        revenue = data.get("total_revenue", 0.0)
        tx_count = data.get("transaction_count", 0)
        avg_order = data.get("average_order_value", revenue / tx_count if tx_count > 0 else 0.0)

        # Payment breakdown — API returns "payment_methods": {method: {count, total}}
        payment_methods = data.get("payment_methods", {})
        breakdown_chips = []
        for method, info in payment_methods.items():
            total = info.get("total", 0.0) if isinstance(info, dict) else info
            count = info.get("count", 0) if isinstance(info, dict) else 0
            breakdown_chips.append(
                ft.Chip(
                    label=ft.Text(f"{method}: ₹{total:.2f} ({count})"),
                    bgcolor=HMSColors.BG_SECONDARY,
                )
            )

        # Top sellers — API returns "quantity_sold" not "quantity"
        top_items = data.get("top_items", [])
        top_items_widgets = []
        for idx, item in enumerate(top_items[:5], 1):
            qty = item.get("quantity_sold", item.get("quantity", 0))
            rev = item.get("revenue", 0.0)
            top_items_widgets.append(
                ft.Text(f"  {idx}. {item.get('name', 'Unknown')} — {qty} sold (₹{rev:,.2f})", size=13)
            )

        report_date_str = data.get("date", self._selected_date.isoformat())

        self.sales_summary.content = ft.Container(
            content=ft.Column(
                [
                    ft.Row([
                        ft.Text("Daily Sales Summary", size=18, weight="bold"),
                        ft.Container(expand=True),
                        ft.Text(report_date_str, size=12, color=HMSColors.TEXT_SECONDARY),
                    ]),
                    ft.Row([
                        ft.Column([
                            ft.Text("Total Revenue", size=12, color=HMSColors.TEXT_SECONDARY),
                            ft.Text(f"₹{revenue:,.2f}", size=24, weight="bold", color=HMSColors.SUCCESS),
                        ]),
                        ft.Column([
                            ft.Text("Transactions", size=12, color=HMSColors.TEXT_SECONDARY),
                            ft.Text(str(tx_count), size=24, weight="bold"),
                        ]),
                        ft.Column([
                            ft.Text("Average Order", size=12, color=HMSColors.TEXT_SECONDARY),
                            ft.Text(f"₹{avg_order:,.2f}", size=24, weight="bold"),
                        ]),
                    ], spacing=40),
                    ft.Divider(),
                    ft.Text("Payment Breakdown", size=14, weight="bold"),
                    ft.Row(breakdown_chips, spacing=10, wrap=True) if breakdown_chips else ft.Text("No payments yet", size=12, color=HMSColors.TEXT_SECONDARY),
                    ft.Divider(),
                    ft.Text("Top Selling Items", size=14, weight="bold"),
                    *(top_items_widgets if top_items_widgets else [ft.Text("No sales data yet", size=12, color=HMSColors.TEXT_SECONDARY)]),
                ],
                spacing=10,
            ),
            padding=20,
        )
        try:
            self.sales_summary.update()
        except Exception:
            pass

    def _display_inventory_summary(self, data: dict):
        """Display inventory summary by rebuilding the card content."""
        items_list = data.get("inventory", data.get("items", []))
        total_items = data.get("total_items", len(items_list))
        low_stock_items = data.get("low_stock_items", [i for i in items_list if i.get("is_low_stock", False)])

        low_stock_widgets = []
        for item in low_stock_items:
            stock = item.get("stock_on_hand", 0)
            low_stock_widgets.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.WARNING_AMBER_ROUNDED, color=HMSColors.WARNING, size=18),
                        ft.Text(item.get("name", "Unknown"), size=13, weight="bold"),
                        ft.Container(expand=True),
                        ft.Text(f"Stock: {stock}", size=13, color=HMSColors.ERROR if stock <= 0 else HMSColors.WARNING),
                        ft.Text(f"Reorder: {item.get('reorder_level', 0)}", size=12, color=HMSColors.TEXT_SECONDARY),
                    ]),
                    padding=ft.padding.symmetric(vertical=4),
                )
            )

        if not low_stock_widgets:
            low_stock_widgets = [ft.Text("All items well stocked", size=13, color=HMSColors.SUCCESS)]

        self.inventory_summary.content = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Inventory Status", size=18, weight="bold"),
                    ft.Row([
                        ft.Column([
                            ft.Text("Total Items", size=12, color=HMSColors.TEXT_SECONDARY),
                            ft.Text(str(total_items), size=24, weight="bold"),
                        ]),
                        ft.Column([
                            ft.Text("Low Stock Items", size=12, color=HMSColors.WARNING),
                            ft.Text(str(len(low_stock_items)), size=24, weight="bold", color=HMSColors.WARNING),
                        ]),
                    ], spacing=40),
                    ft.Divider(),
                    ft.Text("Low Stock Alerts", size=14, weight="bold"),
                    *low_stock_widgets,
                ],
                spacing=10,
            ),
            padding=20,
        )
        try:
            self.inventory_summary.update()
        except Exception:
            pass

    def _handle_txn_search(self, e):
        """Search transactions with filters."""
        try:
            params = {}
            if self.txn_start_date.value.strip():
                params["start_date"] = self.txn_start_date.value.strip()
            if self.txn_end_date.value.strip():
                params["end_date"] = self.txn_end_date.value.strip()
            if self.txn_method_filter.value:
                params["payment_method"] = self.txn_method_filter.value

            with httpx.Client(timeout=5.0) as client:
                response = client.get(
                    f"{self.api_base}/api/reports/transactions",
                    params=params,
                )
                if response.status_code == 200:
                    results = response.json()
                    self._display_transactions(results)
        except Exception as err:
            show_error_dialog(self.page, "Search Error", str(err))

    def _display_transactions(self, transactions: list):
        """Display transaction search results."""
        self.txn_results_list.controls.clear()
        self.txn_count_text.value = f"{len(transactions)} transaction(s) found"

        if not transactions:
            self.txn_results_list.controls.append(
                ft.Text("No transactions found", size=13, color=HMSColors.TEXT_SECONDARY)
            )
        else:
            for txn in transactions:
                self.txn_results_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text(f"#{txn.get('receipt_number', '—')}", size=13, weight="bold"),
                            ft.Text(f"Table {txn.get('table_id', '—')}", size=13),
                            ft.Text(txn.get("payment_method", "—"), size=12, color=HMSColors.TEXT_SECONDARY),
                            ft.Container(expand=True),
                            ft.Text(f"₹{txn.get('total', 0):.2f}", size=13, weight="bold"),
                        ]),
                        padding=ft.padding.symmetric(vertical=4, horizontal=8),
                        bgcolor=HMSColors.BG_SECONDARY,
                        border_radius=4,
                    )
                )

        try:
            self.txn_results_list.update()
            self.txn_count_text.update()
        except Exception:
            pass

    def _handle_export_sales(self, e):
        """Export daily sales summary to CSV file."""
        if not self._sales_data:
            show_error_dialog(self.page, "No Data", "Load reports first before exporting.")
            return

        try:
            output = io.StringIO()
            writer = csv.writer(output)

            # Header
            writer.writerow(["Daily Sales Report", self._sales_data.get("date", "")])
            writer.writerow([])
            writer.writerow(["Metric", "Value"])
            writer.writerow(["Total Revenue", f"₹{self._sales_data.get('total_revenue', 0):.2f}"])
            writer.writerow(["Transaction Count", self._sales_data.get("transaction_count", 0)])
            writer.writerow(["Average Order Value", f"₹{self._sales_data.get('average_order_value', 0):.2f}"])
            writer.writerow([])

            # Payment methods
            writer.writerow(["Payment Method", "Count", "Total"])
            for method, info in self._sales_data.get("payment_methods", {}).items():
                total = info.get("total", 0) if isinstance(info, dict) else info
                count = info.get("count", 0) if isinstance(info, dict) else 0
                writer.writerow([method, count, f"₹{total:.2f}"])
            writer.writerow([])

            # Top items
            writer.writerow(["Top Item", "Quantity Sold", "Revenue"])
            for item in self._sales_data.get("top_items", []):
                writer.writerow([
                    item.get("name", "Unknown"),
                    item.get("quantity_sold", 0),
                    f"₹{item.get('revenue', 0):.2f}",
                ])

            csv_content = output.getvalue()
            filename = f"sales_report_{self._selected_date.isoformat()}.csv"

            # Save to current directory
            with open(filename, "w", newline="", encoding="utf-8") as f:
                f.write(csv_content)

            show_success_dialog(self.page, "CSV Exported", f"Sales report saved to {filename}")
        except Exception as err:
            show_error_dialog(self.page, "Export Error", str(err))

    def _handle_export_inventory(self, e):
        """Export inventory snapshot to CSV file."""
        if not self._inventory_data:
            show_error_dialog(self.page, "No Data", "Load reports first before exporting.")
            return

        try:
            output = io.StringIO()
            writer = csv.writer(output)

            writer.writerow(["Inventory Snapshot", datetime.now().strftime("%Y-%m-%d %H:%M")])
            writer.writerow([])
            writer.writerow(["Item Name", "Category", "Unit Price", "Stock On Hand", "Reorder Level", "Low Stock?"])

            for item in self._inventory_data.get("inventory", []):
                writer.writerow([
                    item.get("name", ""),
                    item.get("category", ""),
                    f"₹{item.get('unit_price', 0):.2f}",
                    item.get("stock_on_hand", 0),
                    item.get("reorder_level", 0),
                    "YES" if item.get("is_low_stock", False) else "No",
                ])

            csv_content = output.getvalue()
            filename = f"inventory_snapshot_{date.today().isoformat()}.csv"

            with open(filename, "w", newline="", encoding="utf-8") as f:
                f.write(csv_content)

            show_success_dialog(self.page, "CSV Exported", f"Inventory snapshot saved to {filename}")
        except Exception as err:
            show_error_dialog(self.page, "Export Error", str(err))
