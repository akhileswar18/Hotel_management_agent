"""
Products/Inventory Screen

Manage products: view, add new, update prices, record stock.
"""

import flet as ft
import httpx
from src.ui.components.ui_helpers import (
    HMSButton, HMSColors, HMSInput, show_error_dialog, show_success_dialog, create_header,
    RefreshButton,
)


class ProductsScreen(ft.Column):
    """Product management screen."""

    def __init__(self, page: ft.Page, user_info: dict, on_back):
        self._page = page
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

        # Category filter
        self.category_filter = ft.Dropdown(
            label="Filter by Category",
            options=[
                ft.dropdown.Option("", "All Categories"),
                ft.dropdown.Option("food", "Food"),
                ft.dropdown.Option("beverage", "Beverage"),
                ft.dropdown.Option("dessert", "Dessert"),
                ft.dropdown.Option("other", "Other"),
            ],
            value="",
            width=200,
            on_change=self._handle_category_filter,
        )

        back_button = HMSButton(
            "Back to POS",
            lambda e: on_back(),
        )

        self.loading = ft.ProgressRing(visible=False)

        # Refresh button — reloads items while preserving category filter
        self.refresh_button = RefreshButton(
            on_refresh=self._refresh_with_filter,
            page=self._page,
            tooltip="Refresh products",
        )

        super().__init__(
            [
                ft.Row(
                    [
                        ft.Text("Products", size=20, weight="bold"),
                        ft.Container(expand=True),
                        self.category_filter,
                        self.refresh_button,
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
            expand=True,
        )

        # Load items
        self._load_items()

    def _refresh_with_filter(self):
        """Refresh items while preserving the current category filter."""
        self._load_items(category=self.category_filter.value)

    def _handle_category_filter(self, e):
        """Filter items by category."""
        category = self.category_filter.value
        self._load_items(category=category)

    def _load_items(self, category: str = ""):
        """Load products from API with optional category filter."""
        try:
            params = {}
            if category:
                params["category"] = category
            with httpx.Client(timeout=5.0) as client:
                response = client.get(
                    f"{self.api_base}/api/inventory/items",
                    params=params,
                )
                if response.status_code == 200:
                    self.items = response.json()
                    self._display_items()
        except Exception as e:
            pass

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

            item_id = item.get("id", "")
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
                        ft.IconButton(
                            icon=ft.Icons.EDIT,
                            icon_color=HMSColors.PRIMARY,
                            icon_size=20,
                            tooltip="Edit product",
                            on_click=lambda e, iid=item_id: self._handle_edit_product(iid),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.ARCHIVE,
                            icon_color=HMSColors.ERROR,
                            icon_size=20,
                            tooltip="Archive product",
                            on_click=lambda e, iid=item_id: self._handle_archive_product(iid),
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
        """Add new product dialog with form fields."""
        name_field = ft.TextField(label="Product Name", hint_text="e.g. Masala Dosa", width=300)
        category_field = ft.Dropdown(
            label="Category",
            options=[
                ft.dropdown.Option("food", "Food"),
                ft.dropdown.Option("beverage", "Beverage"),
                ft.dropdown.Option("dessert", "Dessert"),
                ft.dropdown.Option("other", "Other"),
            ],
            value="food",
            width=300,
        )
        price_field = ft.TextField(
            label="Unit Price (₹)", hint_text="e.g. 120.00",
            keyboard_type=ft.KeyboardType.NUMBER, width=300,
        )
        reorder_field = ft.TextField(
            label="Reorder Level", hint_text="e.g. 10",
            keyboard_type=ft.KeyboardType.NUMBER, width=300, value="10",
        )
        initial_stock_field = ft.TextField(
            label="Initial Stock Qty", hint_text="e.g. 50",
            keyboard_type=ft.KeyboardType.NUMBER, width=300, value="0",
        )

        error_text = ft.Text("", color=HMSColors.ERROR, size=12, visible=False)

        def confirm_add(ev):
            name = name_field.value.strip()
            price_str = price_field.value.strip()
            if not name or not price_str:
                error_text.value = "Name and price are required"
                error_text.visible = True
                self._page.update()
                return
            try:
                price = float(price_str)
                reorder = int(reorder_field.value.strip() or "10")
                initial_stock = int(initial_stock_field.value.strip() or "0")
            except ValueError:
                error_text.value = "Enter valid numbers"
                error_text.visible = True
                self._page.update()
                return

            dlg.open = False
            self._page.update()

            try:
                with httpx.Client(timeout=5.0) as client:
                    # Create item
                    resp = client.post(
                        f"{self.api_base}/api/inventory/items",
                        json={
                            "name": name,
                            "category": category_field.value,
                            "unit_price": price,
                            "reorder_level": reorder,
                            "user_id": self.user_info.get("user_id"),
                        },
                    )
                    if resp.status_code == 200:
                        new_item = resp.json()
                        # Optionally record initial stock
                        if initial_stock > 0:
                            client.post(
                                f"{self.api_base}/api/inventory/stock-in",
                                json={
                                    "item_id": new_item["id"],
                                    "quantity": initial_stock,
                                    "reference": "initial_stock",
                                    "user_id": self.user_info.get("user_id"),
                                },
                            )
                        show_success_dialog(self.page, "Product Created",
                            f"{name} added successfully" + (f" with {initial_stock} units" if initial_stock > 0 else ""))
                        self._load_items()
                    else:
                        detail = resp.json().get("detail", "Failed to create product")
                        show_error_dialog(self.page, "Error", detail)
            except Exception as err:
                show_error_dialog(self.page, "Error", str(err))

        dlg = ft.AlertDialog(
            title=ft.Text("Add New Product"),
            content=ft.Column([
                name_field,
                category_field,
                price_field,
                reorder_field,
                initial_stock_field,
                error_text,
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("Cancel", on_click=lambda ev: _close(dlg)),
                ft.ElevatedButton("Create Product", on_click=confirm_add,
                    bgcolor=HMSColors.SUCCESS, color=HMSColors.TEXT_LIGHT),
            ],
        )

        def _close(d):
            d.open = False
            self._page.update()

        self._page.dialog = dlg
        dlg.open = True
        self._page.update()

    def _handle_edit_product(self, item_id: str):
        """Open Edit Product dialog to update price and reorder level."""
        # Find current item data
        current = next((i for i in self.items if i["id"] == item_id), None)
        if not current:
            show_error_dialog(self.page, "Error", "Product not found")
            return

        price_field = ft.TextField(
            label="Unit Price (₹)",
            hint_text="Leave blank to keep current",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=300,
            value=str(current["unit_price"]),
        )
        reorder_field = ft.TextField(
            label="Reorder Level",
            hint_text="Leave blank to keep current",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=300,
            value=str(current.get("reorder_level", 10)),
        )

        error_text = ft.Text("", color=HMSColors.ERROR, size=12, visible=False)

        def confirm_edit(ev):
            price_str = price_field.value.strip()
            reorder_str = reorder_field.value.strip()

            payload = {"user_id": self.user_info.get("user_id")}
            if price_str:
                try:
                    payload["unit_price"] = float(price_str)
                except ValueError:
                    error_text.value = "Enter a valid price"
                    error_text.visible = True
                    self._page.update()
                    return
            if reorder_str:
                try:
                    payload["reorder_level"] = int(reorder_str)
                except ValueError:
                    error_text.value = "Enter a valid reorder level"
                    error_text.visible = True
                    self._page.update()
                    return

            dlg.open = False
            self._page.update()

            try:
                with httpx.Client(timeout=5.0) as client:
                    resp = client.patch(
                        f"{self.api_base}/api/inventory/items/{item_id}",
                        json=payload,
                    )
                    if resp.status_code == 200:
                        show_success_dialog(self.page, "Product Updated",
                            f"{current['name']} updated successfully")
                        self._load_items()
                    else:
                        detail = resp.json().get("detail", "Failed to update product")
                        show_error_dialog(self.page, "Error", detail)
            except Exception as err:
                show_error_dialog(self.page, "Error", str(err))

        dlg = ft.AlertDialog(
            title=ft.Text(f"Edit: {current['name']}"),
            content=ft.Column([
                ft.Text(f"Current Price: ₹{current['unit_price']:.2f}", size=13, color=HMSColors.TEXT_SECONDARY),
                price_field,
                ft.Text(f"Current Reorder Level: {current.get('reorder_level', 10)}", size=13, color=HMSColors.TEXT_SECONDARY),
                reorder_field,
                error_text,
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("Cancel", on_click=lambda ev: _close(dlg)),
                ft.ElevatedButton("Save Changes", on_click=confirm_edit,
                    bgcolor=HMSColors.PRIMARY, color=HMSColors.TEXT_LIGHT),
            ],
        )

        def _close(d):
            d.open = False
            self._page.update()

        self._page.dialog = dlg
        dlg.open = True
        self._page.update()

    def _handle_archive_product(self, item_id: str):
        """Archive (soft delete) a product."""
        current = next((i for i in self.items if i["id"] == item_id), None)
        if not current:
            return

        def confirm_archive(e):
            dlg.open = False
            self._page.update()
            try:
                with httpx.Client(timeout=5.0) as client:
                    resp = client.patch(
                        f"{self.api_base}/api/inventory/items/{item_id}/archive",
                        json={"user_id": self.user_info.get("user_id")},
                    )
                    if resp.status_code == 200:
                        show_success_dialog(self.page, "Archived", f"{current['name']} has been archived")
                        self._load_items(category=self.category_filter.value if hasattr(self, 'category_filter') else "")
                    else:
                        detail = resp.json().get("detail", "Failed to archive")
                        show_error_dialog(self.page, "Error", detail)
            except Exception as err:
                show_error_dialog(self.page, "Error", str(err))

        dlg = ft.AlertDialog(
            title=ft.Text(f"Archive {current['name']}?"),
            content=ft.Text("This will hide the product from the menu. It can be restored later.", size=14),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: _close(dlg)),
                ft.ElevatedButton("Archive", on_click=confirm_archive,
                    bgcolor=HMSColors.ERROR, color=HMSColors.TEXT_LIGHT),
            ],
        )

        def _close(d):
            d.open = False
            self._page.update()

        self._page.dialog = dlg
        dlg.open = True
        self._page.update()

    def _handle_stock_in(self, e):
        """Record stock-in dialog with item picker."""
        if not self.items:
            show_error_dialog(self.page, "Error", "No products available. Add a product first.")
            return

        item_dropdown = ft.Dropdown(
            label="Select Product",
            options=[ft.dropdown.Option(item["id"], item["name"]) for item in self.items],
            value=self.items[0]["id"] if self.items else None,
            width=300,
        )

        qty_field = ft.TextField(
            label="Quantity to Add",
            hint_text="e.g. 25",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=300,
        )

        error_text = ft.Text("", color=HMSColors.ERROR, size=12, visible=False)

        def confirm_stock_in(ev):
            qty_str = qty_field.value.strip()
            if not item_dropdown.value or not qty_str:
                error_text.value = "Select a product and enter quantity"
                error_text.visible = True
                self._page.update()
                return
            try:
                qty = int(qty_str)
                if qty <= 0:
                    raise ValueError
            except ValueError:
                error_text.value = "Enter a positive whole number"
                error_text.visible = True
                self._page.update()
                return

            dlg.open = False
            self._page.update()

            try:
                with httpx.Client(timeout=5.0) as client:
                    resp = client.post(
                        f"{self.api_base}/api/inventory/stock-in",
                        json={
                            "item_id": item_dropdown.value,
                            "quantity": qty,
                            "reference": "manual_stock_in",
                            "user_id": self.user_info.get("user_id"),
                        },
                    )
                    if resp.status_code == 200:
                        item_name = next((i["name"] for i in self.items if i["id"] == item_dropdown.value), "Item")
                        show_success_dialog(self.page, "Stock Updated",
                            f"Added {qty} units of {item_name}")
                        self._load_items()
                    else:
                        detail = resp.json().get("detail", "Failed to record stock-in")
                        show_error_dialog(self.page, "Error", detail)
            except Exception as err:
                show_error_dialog(self.page, "Error", str(err))

        dlg = ft.AlertDialog(
            title=ft.Text("Record Stock-In"),
            content=ft.Column([
                item_dropdown,
                qty_field,
                error_text,
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("Cancel", on_click=lambda ev: _close(dlg)),
                ft.ElevatedButton("Record Stock", on_click=confirm_stock_in,
                    bgcolor=HMSColors.PRIMARY, color=HMSColors.TEXT_LIGHT),
            ],
        )

        def _close(d):
            d.open = False
            self._page.update()

        self._page.dialog = dlg
        dlg.open = True
        self._page.update()
