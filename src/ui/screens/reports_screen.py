"""
Reports Screen

Daily sales summary, inventory snapshot, and transaction search.
"""

import flet as ft
import httpx
from datetime import datetime
from src.ui.components.ui_helpers import (
    HMSButton, HMSColors, show_error_dialog, show_success_dialog, create_header
)


class ReportsScreen(ft.Column):
    """Reports and analytics screen."""

    def __init__(self, page: ft.Page, user_info: dict, on_back):
        self.page = page
        self.user_info = user_info
        self.on_back = on_back
        self.api_base = "http://127.0.0.1:8000"

        header = create_header(page, "Reports & Analytics", user_info.get("username"))

        # Sales summary section
        self.sales_summary = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Daily Sales Summary", size=18, weight="bold"),
                        ft.Row([
                            ft.Column([
                                ft.Text("Total Revenue", size=12, color=HMSColors.TEXT_SECONDARY),
                                ft.Text("₹0.00", size=24, weight="bold", key="revenue"),
                            ]),
                            ft.Column([
                                ft.Text("Transactions", size=12, color=HMSColors.TEXT_SECONDARY),
                                ft.Text("0", size=24, weight="bold", key="transactions"),
                            ]),
                            ft.Column([
                                ft.Text("Average Order", size=12, color=HMSColors.TEXT_SECONDARY),
                                ft.Text("₹0.00", size=24, weight="bold", key="avg_order"),
                            ]),
                        ]),
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
                        ft.Row([
                            ft.Column([
                                ft.Text("Total Items", size=12, color=HMSColors.TEXT_SECONDARY),
                                ft.Text("0", size=24, weight="bold", key="total_items"),
                            ]),
                            ft.Column([
                                ft.Text("Low Stock Items", size=12, color=HMSColors.WARNING),
                                ft.Text("0", size=24, weight="bold", color=HMSColors.WARNING, key="low_stock"),
                            ]),
                        ]),
                        ft.Divider(),
                        ft.Text("Low Stock Alerts", size=14, weight="bold"),
                        ft.ListView(key="low_stock_list", spacing=5, height=150),
                    ],
                    spacing=10,
                ),
                padding=20,
            ),
            margin=10,
        )

        # Buttons
        refresh_button = HMSButton(
            "Refresh Reports",
            self._handle_refresh,
            color=HMSColors.PRIMARY,
        )

        export_button = HMSButton(
            "Export to CSV",
            self._handle_export,
            color=HMSColors.PRIMARY,
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
                        refresh_button,
                        export_button,
                        back_button,
                    ],
                    spacing=10,
                ),
                ft.Divider(),
                self.sales_summary,
                self.inventory_summary,
                ft.Row([self.loading], alignment=ft.MainAxisAlignment.CENTER),
            ],
            spacing=10,
            expand=True,
        )

        # Load reports
        self._load_reports()

    def _load_reports(self):
        """Load reports from API."""
        try:
            with httpx.Client(timeout=5.0) as client:
                # Load daily sales
                sales_response = client.get(
                    f"{self.api_base}/api/reports/daily-sales",
                )
                # Load inventory
                inventory_response = client.get(
                    f"{self.api_base}/api/reports/inventory-snapshot",
                )

                if sales_response.status_code == 200:
                    sales_data = sales_response.json()
                    self._display_sales_summary(sales_data)

                if inventory_response.status_code == 200:
                    inventory_data = inventory_response.json()
                    self._display_inventory_summary(inventory_data)

        except Exception as e:
            pass  # API may not be running yet

    def _display_sales_summary(self, data: dict):
        """Display sales summary."""
        # TODO: Update card with actual data
        pass

    def _display_inventory_summary(self, data: dict):
        """Display inventory summary."""
        # TODO: Update card with actual data
        pass

    def _handle_refresh(self, e):
        """Refresh reports."""
        self._load_reports()

    def _handle_export(self, e):
        """Export reports to CSV."""
        # TODO: Implement CSV export
        show_error_dialog(self.page, "Coming Soon", "CSV export coming in Phase 2")


# TODO: Implement full reporting
# TODO: Add date range filters
# TODO: Add CSV/PDF export
# TODO: Add payment method breakdown
