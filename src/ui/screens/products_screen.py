"""
Menu Management Screen (Products/Inventory)

Add, edit, delete menu items. Dark theme, touch-friendly.
"""

import flet as ft
import httpx
from src.ui.components.ui_helpers import (
    HMSButton, HMSColors, HMSInput, show_error_dialog, show_success_dialog, build_header,
    section_header, status_tag, stock_bar, tag_chip, activity_item,
    RefreshButton,
)

MENU_BG = HMSColors.BG
MENU_EMERALD = HMSColors.ACCENT


class ProductsScreen(ft.Column):
    """Menu management screen: add, edit, delete items (exposed as Menu in nav)."""

    def __init__(self, page: ft.Page, user_info: dict, on_back):
        self._page = page
        self.user_info = user_info
        self.on_back = on_back
        self.api_base = "http://127.0.0.1:8000"
        self.items = []

        self.ledger_entries = []

        self.items_list = ft.Column(spacing=8, expand=True, scroll=ft.ScrollMode.AUTO)
        self.alerts_list = ft.Column(spacing=8)
        self.ledger_list = ft.Column(spacing=6)
        self.snapshot_container = ft.Container(
            padding=ft.padding.symmetric(horizontal=4, vertical=2),
            content=ft.Text("Loading...", size=11, color="#4B5675"),
        )

        add_product_button = HMSButton("Add New Item", self._handle_add_product, height=48, color=MENU_EMERALD, width=150)
        stock_in_button = HMSButton("Record Stock-In", self._handle_stock_in, color=HMSColors.BLUE, width=150, height=48)

        self.category_filter = ft.Dropdown(
            label="Category",
            width=200,
            value=None,
            on_change=self._handle_category_filter,
            options=[],
            bgcolor=HMSColors.SURFACE2,
            border_color=HMSColors.BORDER,
            color=HMSColors.TEXT_PRIMARY,
        )

        self.loading = ft.ProgressRing(visible=False, color=HMSColors.ACCENT)
        self.refresh_button = RefreshButton(on_refresh=self._refresh_with_filter, page=self._page, tooltip="Refresh inventory")

        sidebar = ft.Container(
            width=280,
            bgcolor=HMSColors.SURFACE,
            border=ft.border.only(right=ft.BorderSide(1, HMSColors.BORDER)),
            padding=16,
            content=ft.Column(
                [
                    section_header("Alerts"),
                    self.alerts_list,
                    ft.Divider(color=HMSColors.BORDER),
                    section_header("Categories"),
                    self.category_filter,
                    ft.Divider(color=HMSColors.BORDER),
                    section_header("Snapshot"),
                    self.snapshot_container,
                ],
                spacing=10,
                expand=True,
            ),
        )

        main_area = ft.Container(
            expand=True,
            padding=16,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("Inventory / Stock", size=20, weight=ft.FontWeight.W_700, color=HMSColors.TEXT_PRIMARY, font_family="Syne"),
                            ft.Container(expand=True),
                            self.refresh_button,
                            add_product_button,
                            stock_in_button,
                            HMSButton("Back to POS", lambda e: on_back(), width=130, height=48),
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Divider(color=HMSColors.BORDER),
                    section_header("All Items"),
                    ft.Container(content=self.items_list, expand=True),
                    ft.Divider(color=HMSColors.BORDER),
                    section_header("Stock Ledger History"),
                    ft.Container(content=self.ledger_list, height=200),
                    ft.Row([self.loading], alignment=ft.MainAxisAlignment.CENTER),
                ],
                spacing=10,
                expand=True,
            ),
        )

        super().__init__(
            controls=[
                build_header("Inventory", user_info),
                ft.Row([sidebar, main_area], spacing=0, expand=True),
            ],
            expand=True,
            spacing=0,
        )

        self._load_items()

    def _refresh_with_filter(self):
        """Refresh items while preserving the current category filter."""
        self._load_items(category=self.category_filter.value)

    def _handle_category_filter(self, e):
        """Filter items by category."""
        selected = self.category_filter.value or ""
        self._load_items(category=selected)

    def _rebuild_category_dropdown(self):
        categories = sorted(
            set(
                item.get("category", "").strip()
                for item in self.items
                if item.get("category", "").strip()
            )
        )

        new_options = [ft.dropdown.Option(key="", text="All Categories")]
        for cat in categories:
            new_options.append(ft.dropdown.Option(key=cat, text=cat))

        self.category_filter.options = new_options

        valid_keys = [""] + categories
        if self.category_filter.value not in valid_keys:
            self.category_filter.value = ""

        try:
            self.category_filter.update()
        except Exception:
            pass

    def _load_items(self, category: str = ""):
        """Load products from API with optional category filter."""
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.api_base}/api/inventory/items")
                if response.status_code == 200:
                    all_items = response.json()
                    self.items = all_items
                    self._rebuild_category_dropdown()
                    self._load_ledger(client)
                    if category:
                        display_items = [
                            item for item in all_items
                            if item.get("category", "") == category
                        ]
                    else:
                        display_items = all_items
                    self._display_items(display_items)
        except Exception as e:
            pass

    def _load_ledger(self, client: httpx.Client):
        try:
            res = client.get(f"{self.api_base}/api/audit/log", params={"limit": 25, "offset": 0})
            if res.status_code == 200:
                entries = res.json()
                self.ledger_entries = [e for e in entries if str(e.get("event_type", "")).startswith("inventory.")]
            else:
                self.ledger_entries = []
        except Exception:
            self.ledger_entries = []

    def _build_snapshot(self) -> ft.Control:
        items = self.items

        total = len(items)
        in_stock = sum(1 for i in items if i.get("stock_on_hand", 0) > i.get("reorder_level", 0))
        low_stock = sum(1 for i in items if 0 < i.get("stock_on_hand", 0) <= i.get("reorder_level", 0))
        out_stock = sum(1 for i in items if i.get("stock_on_hand", 0) <= 0)

        def snap_row(label, value, color):
            return ft.Row(
                [
                    ft.Text(label, size=12, color="#8B96B0", expand=True),
                    ft.Text(str(value), size=12, weight=ft.FontWeight.W_700, color=color, font_family="DM Mono"),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )

        return ft.Column(
            [
                ft.Text("SNAPSHOT", size=10, weight=ft.FontWeight.W_600, color="#4B5675", letter_spacing=1.2),
                snap_row("Total Items", total, "#F0F4FF"),
                snap_row("Low Stock", low_stock, "#EAB308"),
                snap_row("Out of Stock", out_stock, "#EF4444"),
                snap_row("In Stock", in_stock, "#22C55E"),
            ],
            spacing=4,
            tight=True,
        )

    def _display_items(self, items=None):
        """Display items in list."""
        if items is None:
            items = self.items
        self.items_list.controls.clear()
        self.alerts_list.controls.clear()
        self.ledger_list.controls.clear()

        for item in items:
            stock = int(item.get("stock_on_hand", 0))
            reorder = int(item.get("reorder_level", 10))

            # Stock indicator
            if stock <= 0:
                stock_color = HMSColors.ERROR
                stock_badge = "OUT"
            elif stock < reorder:
                stock_color = HMSColors.WARNING
                stock_badge = "LOW"
            else:
                stock_color = HMSColors.SUCCESS
                stock_badge = "IN STOCK"

            item_id = item.get("id", "")
            row = ft.Container(
                content=ft.Row(
                    [
                        ft.Text(str(item["name"]), size=14, weight=ft.FontWeight.W_600, color=HMSColors.TEXT_PRIMARY, width=200),
                        tag_chip(str(item["category"]).title(), HMSColors.SURFACE2, HMSColors.TEXT_SECONDARY),
                        ft.Text(f"Rs.{float(item['unit_price']):.2f}", size=13, color=HMSColors.ACCENT2, width=90, font_family="DM Mono"),
                        stock_bar(stock, max(reorder * 3, stock, 1), stock_color),
                        ft.Text(str(reorder), size=12, color=HMSColors.TEXT_SECONDARY, width=60),
                        status_tag(stock_badge, stock_color),
                        ft.IconButton(
                            icon=ft.icons.EDIT,
                            icon_color=HMSColors.ACCENT,
                            icon_size=20,
                            tooltip="Edit product",
                            on_click=lambda e, iid=item_id: self._handle_edit_product(iid),
                        ),
                        ft.IconButton(
                            icon=ft.icons.ARCHIVE,
                            icon_color=HMSColors.RED,
                            icon_size=20,
                            tooltip="Archive product",
                            on_click=lambda e, iid=item_id: self._handle_archive_product(iid),
                        ),
                    ],
                    spacing=12,
                    wrap=True,
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=12,
                bgcolor=HMSColors.SURFACE,
                border_radius=8,
                border=ft.border.all(1, HMSColors.BORDER),
            )
            self.items_list.controls.append(row)

            if stock_badge in ("LOW", "OUT"):
                self.alerts_list.controls.append(
                    ft.Container(
                        bgcolor=HMSColors.RED_DIM if stock_badge == "OUT" else HMSColors.YELLOW_DIM,
                        border=ft.border.all(1, HMSColors.RED + "66" if stock_badge == "OUT" else HMSColors.YELLOW + "66"),
                        border_radius=8,
                        padding=10,
                        content=ft.Column(
                            [
                                ft.Text(item["name"], size=12, weight=ft.FontWeight.W_600, color=HMSColors.TEXT_PRIMARY),
                                ft.Text(f"{stock} / {reorder} units", size=11, color=HMSColors.TEXT_SECONDARY),
                            ],
                            spacing=2,
                            tight=True,
                        ),
                    )
                )

        self.snapshot_container.content = self._build_snapshot()
        try:
            self.snapshot_container.update()
        except Exception:
            pass

        if not self.alerts_list.controls:
            self.alerts_list.controls.append(ft.Text("No critical alerts", color=HMSColors.TEXT_SECONDARY, size=12))

        if not self.ledger_entries:
            self.ledger_list.controls.append(ft.Text("No recent ledger activity", color=HMSColors.TEXT_SECONDARY, size=12))
        else:
            for entry in self.ledger_entries[:20]:
                et = str(entry.get("event_type", "inventory.event"))
                color = HMSColors.YELLOW
                if "add" in et or "purchase" in et:
                    color = HMSColors.GREEN
                if "deduct" in et or "wastage" in et:
                    color = HMSColors.RED
                ts = str(entry.get("created_at", ""))[:19].replace("T", " ")
                self.ledger_list.controls.append(
                    activity_item(et, str(entry.get("description", "Stock activity")), ts, color)
                )

        for ctl in [self.items_list, self.alerts_list, self.ledger_list]:
            try:
                if ctl.page:
                    ctl.update()
            except Exception:
                pass

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
