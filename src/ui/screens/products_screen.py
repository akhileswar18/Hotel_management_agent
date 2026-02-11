"""
Products/Inventory Screen

Manage products: view, add new, update prices, record stock.
"""

import flet as ft
import httpx
import asyncio
from src.ui.components.ui_helpers import (
    HMSButton, HMSColors, HMSInput, show_error_dialog, show_success_dialog, create_header
)


class ProductsScreen(ft.Column):
    """Product management screen."""

    def __init__(self, page: ft.Page, user_info: dict, on_back):
        self.page = page
        self.user_info = user_info
        self.on_back = on_back
        self.api_base = "http://127.0.0.1:8000"
        self.items = []

        header = create_header(page, "Inventory Management", user_info.get("username"))

        # Items list
        self.items_list = ft.ListView(
            spacing=10,
            expand=True,
        )

        # Add product button
        add_product_button = HMSButton(
            "Add New Product",
            self._handle_add_product,
            color=HMSColors.SUCCESS,
        )

        # Stock-in button
        stock_in_button = HMSButton(
            "Record Stock-In",
            self._handle_stock_in,
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
                        ft.Text("Products", size=20, weight="bold"),
                        ft.Container(expand=True),
                        add_product_button,
                        stock_in_button,
                        back_button,
                    ],
                    spacing=10,
                ),
                ft.Divider(),
                self.items_list,
                ft.Row([self.loading], alignment=ft.MainAxisAlignment.CENTER),
            ],
            spacing=10,
            padding=20,
            expand=True,
        )

        # Load items
        asyncio.run(self._load_items())

    async def _load_items(self):
        """Load products from API."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base}/api/inventory/items",
                    timeout=5.0,
                )
                if response.status_code == 200:
                    self.items = response.json()
                    self._display_items()
        except Exception as e:
            show_error_dialog(self.page, "Error", f"Failed to load items: {str(e)}")

    def _display_items(self):
        """Display items in list."""
        self.items_list.controls.clear()

        for item in self.items:
            stock = item.get("stock_on_hand", 0)
            reorder = item.get("reorder_level", 10)

            # Stock indicator
            if stock <= 0:
                stock_color = HMSColors.ERROR
                stock_badge = "❌ Out"
            elif stock < reorder:
                stock_color = HMSColors.WARNING
                stock_badge = f"⚠️  Low ({stock})"
            else:
                stock_color = HMSColors.SUCCESS
                stock_badge = f"✓ {stock}"

            item_card = ft.Container(
                content=ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(item["name"], size=16, weight="bold"),
                                ft.Text(f"Category: {item['category']}", size=12, color=HMSColors.TEXT_SECONDARY),
                                ft.Text(f"Price: ₹{item['unit_price']:.2f}", size=14),
                            ],
                            spacing=4,
                            expand=True,
                        ),
                        ft.Column(
                            [
                                ft.Text(stock_badge, size=14, weight="bold", color=stock_color),
                                ft.Text(f"Reorder: {reorder}", size=12),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=20,
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                padding=15,
                bgcolor=HMSColors.BG_SECONDARY,
                border_radius=8,
                border=ft.border.all(1, HMSColors.TEXT_SECONDARY if stock > 0 else HMSColors.ERROR),
            )
            self.items_list.controls.append(item_card)

        self.items_list.update()

    def _handle_add_product(self, e):
        """Add new product dialog."""
        # TODO: Implement add product dialog
        show_error_dialog(self.page, "Coming Soon", "Add product feature coming soon")

    def _handle_stock_in(self, e):
        """Record stock-in dialog."""
        # TODO: Implement stock-in dialog
        show_error_dialog(self.page, "Coming Soon", "Stock-in feature coming soon")


# TODO: Implement product CRUD
# TODO: Implement stock-in workflow
# TODO: Add barcode scanning (Phase 2+)
