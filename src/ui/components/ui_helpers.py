"""
Reusable UI Components and Helpers

Touch-friendly buttons, widgets, and utility functions.
"""

import time
import threading
from datetime import datetime
import flet as ft
import httpx
from typing import Callable, Optional


class HMSColors:
    """HMS design tokens aligned with the dark redesign prototype."""

    BG = "#0E1117"
    SURFACE = "#161B27"
    SURFACE2 = "#1E2535"
    SURFACE3 = "#252D40"
    BORDER = "#2A3349"

    ACCENT = "#FF6B35"
    ACCENT2 = "#FFB347"

    GREEN = "#22C55E"
    GREEN_DIM = "#16A34A20"
    RED = "#EF4444"
    RED_DIM = "#DC262620"
    YELLOW = "#EAB308"
    YELLOW_DIM = "#CA8A0420"
    BLUE = "#3B82F6"
    BLUE_DIM = "#2563EB20"

    TEXT_PRIMARY = "#F0F4FF"
    TEXT_SECONDARY = "#8B96B0"
    TEXT_MUTED = "#4B5675"
    TEXT_LIGHT = "#FFFFFF"

    # Backward compatibility aliases used throughout existing screens.
    BG_PRIMARY = BG
    BG_SECONDARY = SURFACE
    PRIMARY = ACCENT
    SUCCESS = GREEN
    WARNING = YELLOW
    ERROR = RED
    NEUTRAL = TEXT_MUTED
    EMERALD = GREEN
    BG_DARK = BG
    BG_CARD_DARK = SURFACE
    BORDER_DARK = BORDER
    TEXT_ON_DARK = TEXT_PRIMARY


class HMSButton(ft.ElevatedButton):
    """
    Large, touch-friendly button (min 48dp height; default 56).

    Styled for HMS with high contrast and accessibility.
    """

    def __init__(
        self,
        text: str,
        on_click: Callable,
        width: int = 300,
        height: int = 56,  # min 48 for touch
        color: str = HMSColors.PRIMARY,
        text_size: int = 18,
        **kwargs
    ):
        super().__init__(
            text,
            on_click=on_click,
            width=width,
            height=height,
            bgcolor=color,
            color=HMSColors.TEXT_LIGHT,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            **kwargs
        )


class HMSInput(ft.TextField):
    """
    Large, touch-friendly text input field.

    Minimum 48px height, large font for accessibility.
    """

    def __init__(
        self,
        label: str,
        width: int = 400,
        height: int = 56,
        text_size: int = 20,
        input_filter: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            label=label,
            width=width,
            height=height,
            text_size=text_size,
            label_style=ft.TextStyle(size=16),
            input_filter=ft.InputFilter(
                regex_string=input_filter
            ) if input_filter else None,
            border_color=HMSColors.PRIMARY,
            border_width=2,
            **kwargs
        )


class NumericKeypad(ft.Column):
    """
    Touch-friendly numeric keypad for PIN entry.

    0-9 buttons, Clear, and Backspace.
    """

    def __init__(self, on_key_press: Callable[[str], None]):
        self.on_key_press = on_key_press

        super().__init__(
            controls=[
                # Row 1: 1-3
                ft.Row(
                    [
                        self._make_button("1"),
                        self._make_button("2"),
                        self._make_button("3"),
                    ],
                    spacing=10,
                ),
                # Row 2: 4-6
                ft.Row(
                    [
                        self._make_button("4"),
                        self._make_button("5"),
                        self._make_button("6"),
                    ],
                    spacing=10,
                ),
                # Row 3: 7-9
                ft.Row(
                    [
                        self._make_button("7"),
                        self._make_button("8"),
                        self._make_button("9"),
                    ],
                    spacing=10,
                ),
                # Row 4: 0, Clear, Backspace
                ft.Row(
                    [
                        self._make_button("0", width=100),
                        self._make_button("CLR", width=95, color=HMSColors.WARNING),
                        self._make_button("⌫", width=95, color=HMSColors.ERROR),
                    ],
                    spacing=10,
                ),
            ],
            spacing=10,
        )

    def _make_button(
        self,
        text: str,
        width: int = 100,
        color: str = HMSColors.PRIMARY
    ) -> ft.ElevatedButton:
        """Create numeric keypad button."""
        def handle_click(e):
            self.on_key_press(text)

        return ft.ElevatedButton(
            text,
            on_click=handle_click,
            width=width,
            height=56,
            bgcolor=color,
            color=HMSColors.TEXT_LIGHT,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
        )


class OrderSummaryWidget(ft.Card):
    """
    Order summary display (always visible).

    Shows: table, line items with remove buttons, subtotal, tax, discount, total.
    """

    def __init__(self):
        self.table_id_text = ft.Text("Table: —", size=16, weight="bold")
        self.item_count_text = ft.Text("Items: 0", size=16)
        self.line_items_list = ft.ListView(spacing=2, height=200)
        self.subtotal_text = ft.Text("Subtotal: ₹0.00", size=16)
        self.discount_text = ft.Text("Discount: ₹0.00", size=16, color=HMSColors.WARNING)
        self.tax_text = ft.Text("Tax (18%): ₹0.00", size=16)
        self.total_text = ft.Text(
            "Total: ₹0.00",
            size=28,
            weight="bold",
            color=HMSColors.SUCCESS,
        )

        super().__init__(
            content=ft.Container(
                content=ft.Column(
                    [
                        self.table_id_text,
                        self.item_count_text,
                        ft.Divider(),
                        ft.Text("Order Items:", size=13, weight="bold", color=HMSColors.TEXT_SECONDARY),
                        self.line_items_list,
                        ft.Divider(),
                        self.subtotal_text,
                        self.discount_text,
                        self.tax_text,
                        ft.Divider(),
                        self.total_text,
                    ],
                    spacing=8,
                ),
                padding=20,
                bgcolor=HMSColors.BG_SECONDARY,
            ),
            margin=10,
        )
        self._summary_values = {
            "table_id": "—",
            "item_count": 0,
            "subtotal": 0.0,
            "discount": 0.0,
            "tax": 0.0,
            "total": 0.0,
        }

    def update_summary(
        self,
        table_id: str,
        item_count: int,
        subtotal: float,
        discount: float,
        tax: float,
        total: float,
        line_item_widgets: list = None,
    ):
        """Update summary with order data and optional line item widgets with remove buttons."""
        self.table_id_text.value = f"Table: {table_id}"
        self.item_count_text.value = f"Items: {item_count}"
        self.subtotal_text.value = f"Subtotal: ₹{subtotal:.2f}"
        self.discount_text.value = f"Discount: ₹{discount:.2f}"
        self.tax_text.value = f"Tax (18%): ₹{tax:.2f}"
        self.total_text.value = f"Total: ₹{total:.2f}"
        self._summary_values.update(
            {
                "table_id": table_id,
                "item_count": item_count,
                "subtotal": subtotal,
                "discount": discount,
                "tax": tax,
                "total": total,
            }
        )

        # Update line items list
        self.line_items_list.controls.clear()
        if line_item_widgets:
            for w in line_item_widgets:
                self.line_items_list.controls.append(w)
        elif item_count == 0:
            self.line_items_list.controls.append(
                ft.Text("No items yet", size=12, color=HMSColors.TEXT_SECONDARY)
            )

        self.update()

    @property
    def total_value(self) -> float:
        """Return the most recent total amount."""
        return self._summary_values["total"]


class ItemPickerWidget(ft.Column):
    """
    Product/item picker with search and selection.

    Shows items, stock status, price, and quantity selector.
    """

    def __init__(self, on_item_selected: Callable[[str, str, int], None]):
        self.on_item_selected = on_item_selected
        self.items = []

        self.search_field = ft.TextField(
            label="Search items...",
            width=300,
            height=48,
            text_size=16,
            on_change=self._filter_items,
        )

        self.qty_field = ft.TextField(
            label="Qty",
            width=100,
            height=48,
            text_align=ft.TextAlign.CENTER,
            keyboard_type=ft.KeyboardType.NUMBER,
            value="1",
        )

        self.item_list = ft.ListView(
            spacing=10,
            expand=True,
        )

        super().__init__(
            [
                ft.Text("Select Item", size=20, weight="bold"),
                self.search_field,
                ft.Text("Quantity", size=14),
                self.qty_field,
                ft.Divider(),
                ft.Text("Available Items", size=14, weight="bold"),
                self.item_list,
            ],
            spacing=10,
            expand=True,
        )

    def set_items(self, items: list):
        """Set available items."""
        self.items = items
        self._filter_items(None)

    def _filter_items(self, e):
        """Filter items by search."""
        search_text = self.search_field.value.lower()
        self.item_list.controls.clear()

        for item in self.items:
            if search_text in item["name"].lower():
                item_row = self._make_item_row(item)
                self.item_list.controls.append(item_row)

        self.item_list.update()

    def _make_item_row(self, item: dict) -> ft.Container:
        """Create item row with stock indicator."""
        stock = item.get("stock_on_hand", 0)
        reorder_level = item.get("reorder_level", 10)

        # Stock indicator color
        if stock <= 0:
            stock_color = HMSColors.ERROR
            stock_text = "Out of Stock"
        elif stock < reorder_level:
            stock_color = HMSColors.WARNING
            stock_text = f"Low ({stock})"
        else:
            stock_color = HMSColors.SUCCESS
            stock_text = f"In Stock ({stock})"

        def add_item_click(e):
            try:
                qty = int(self.qty_field.value)
                if qty > 0:
                    self.on_item_selected(item["id"], item["name"], qty)
                    self.qty_field.value = "1"
                    self.qty_field.update()
            except ValueError:
                pass

        return ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(item["name"], size=16, weight="bold"),
                            ft.Text(f"₹{item['unit_price']:.2f}", size=14),
                            ft.Text(stock_text, size=12, color=stock_color, weight="bold"),
                        ],
                        spacing=4,
                        expand=True,
                    ),
                    ft.ElevatedButton(
                        "Add",
                        on_click=add_item_click,
                        width=80,
                        height=48,
                        bgcolor=HMSColors.SUCCESS,
                        color=HMSColors.TEXT_LIGHT,
                    ),
                ],
                spacing=10,
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=10,
            bgcolor=HMSColors.BG_SECONDARY,
            border_radius=8,
        )


def build_header(screen_title: str, current_user: Optional[dict]) -> ft.Container:
    """Build the shared HMS dark header used across operational screens."""
    user = current_user or {}
    username = str(user.get("username", "User"))
    role = str(user.get("role", "STAFF")).upper()
    initial = (username[:1] or "U").upper()

    clock_text = ft.Text(
        datetime.now().strftime("%H:%M"),
        size=12,
        color=HMSColors.TEXT_SECONDARY,
        font_family="DM Mono",
    )

    def _tick():
        clock_text.value = datetime.now().strftime("%H:%M")
        try:
            if clock_text.page:
                clock_text.update()
        except Exception:
            pass
        timer = threading.Timer(60.0, _tick)
        timer.daemon = True
        timer.start()

    timer = threading.Timer(60.0, _tick)
    timer.daemon = True
    timer.start()

    return ft.Container(
        height=60,
        bgcolor=HMSColors.SURFACE,
        border=ft.border.only(bottom=ft.BorderSide(1, HMSColors.BORDER)),
        padding=ft.padding.symmetric(horizontal=16),
        content=ft.Row(
            [
                ft.Text("HMS", size=20, weight=ft.FontWeight.W_800, color=HMSColors.ACCENT, font_family="Syne"),
                ft.Text("· Hotel Management", size=12, color=HMSColors.TEXT_SECONDARY),
                ft.Container(width=1, height=20, bgcolor=HMSColors.BORDER),
                ft.Text(screen_title, size=15, weight=ft.FontWeight.W_600, color=HMSColors.TEXT_PRIMARY, font_family="Syne"),
                ft.Container(expand=True),
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    bgcolor=HMSColors.GREEN_DIM,
                    border=ft.border.all(1, HMSColors.GREEN + "60"),
                    border_radius=8,
                    content=ft.Row(
                        [
                            ft.Container(width=8, height=8, bgcolor=HMSColors.GREEN, border_radius=6),
                            ft.Text("OFFLINE READY", size=11, color=HMSColors.GREEN, font_family="DM Mono"),
                        ],
                        spacing=6,
                        tight=True,
                    ),
                ),
                clock_text,
                ft.Container(
                    bgcolor=HMSColors.SURFACE2,
                    border_radius=40,
                    border=ft.border.all(1, HMSColors.BORDER),
                    padding=ft.padding.symmetric(horizontal=8, vertical=6),
                    content=ft.Row(
                        [
                            ft.Container(
                                width=26,
                                height=26,
                                border_radius=20,
                                gradient=ft.LinearGradient(colors=[HMSColors.ACCENT, HMSColors.ACCENT2]),
                                alignment=ft.alignment.center,
                                content=ft.Text(initial, size=12, color=HMSColors.TEXT_LIGHT, weight=ft.FontWeight.W_700),
                            ),
                            ft.Text(username, size=12, color=HMSColors.TEXT_PRIMARY),
                            status_tag(role, HMSColors.ACCENT),
                        ],
                        spacing=8,
                        tight=True,
                    ),
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        ),
    )


def stat_card(icon: str, value: str, label: str, color: str) -> ft.Container:
    """Build a dark stat card with top accent strip and icon highlight."""
    return ft.Container(
        bgcolor=HMSColors.SURFACE,
        border=ft.border.all(1, HMSColors.BORDER),
        border_radius=12,
        padding=20,
        content=ft.Column(
            [
                ft.Container(height=2, bgcolor=color, border_radius=2),
                ft.Row(
                    [
                        ft.Container(
                            width=40,
                            height=40,
                            border_radius=10,
                            bgcolor=color + "20",
                            alignment=ft.alignment.center,
                            content=ft.Text(icon, size=16, color=color),
                        ),
                        ft.Container(expand=True),
                    ]
                ),
                ft.Text(str(value), size=28, weight=ft.FontWeight.W_800, color=HMSColors.TEXT_PRIMARY, font_family="Syne"),
                ft.Text(label, size=12, color=HMSColors.TEXT_SECONDARY),
            ],
            spacing=8,
            tight=True,
        ),
    )


def status_tag(text: str, color: str) -> ft.Container:
    """Build a compact status pill used across screens."""
    return ft.Container(
        bgcolor=color + "20",
        border=ft.border.all(1, color + "40"),
        border_radius=6,
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
        content=ft.Text(text.upper(), size=11, color=color, weight=ft.FontWeight.W_600, font_family="DM Mono"),
    )


def stock_bar(current: int, max_stock: int, color: Optional[str] = None) -> ft.Column:
    """Render a stock progress bar with threshold-based coloring."""
    safe_max = max(max_stock, 1)
    ratio = max(0.0, min(float(current) / float(safe_max), 1.0))

    if color is None:
        if ratio > 0.5:
            fill = HMSColors.GREEN
        elif ratio >= 0.2:
            fill = HMSColors.YELLOW
        else:
            fill = HMSColors.RED
    else:
        fill = color

    bar_width = 120
    return ft.Column(
        [
            ft.Row(
                [
                    ft.Text(str(current), size=11, color=HMSColors.TEXT_PRIMARY),
                    ft.Container(expand=True),
                    ft.Text(f"/ {safe_max}", size=11, color=HMSColors.TEXT_SECONDARY),
                ],
                spacing=2,
            ),
            ft.Stack(
                [
                    ft.Container(width=bar_width, height=4, bgcolor=HMSColors.SURFACE3, border_radius=4),
                    ft.Container(width=max(2, int(bar_width * ratio)), height=4, bgcolor=fill, border_radius=4),
                ],
                width=bar_width,
                height=4,
            ),
        ],
        spacing=4,
        tight=True,
    )


def tag_chip(text: str, bg: str, fg: str = HMSColors.TEXT_LIGHT) -> ft.Container:
    """Build a compact rounded chip for tags, filters, and role pills."""
    return ft.Container(
        bgcolor=bg,
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=14, vertical=6),
        content=ft.Text(text, size=12, weight=ft.FontWeight.W_600, color=fg),
    )


def activity_item(event_type: str, description: str, ts: str, color: str) -> ft.Container:
    """Build one activity row used by dashboard and AI event feed panels."""
    return ft.Container(
        padding=ft.padding.symmetric(vertical=8, horizontal=2),
        border=ft.border.only(bottom=ft.BorderSide(1, HMSColors.BORDER + "66")),
        content=ft.Row(
            [
                ft.Container(width=8, height=8, bgcolor=color, border_radius=6),
                ft.Column(
                    [
                        ft.Text(description, size=12, color=HMSColors.TEXT_PRIMARY, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(event_type, size=10, color=HMSColors.TEXT_MUTED),
                    ],
                    spacing=2,
                    expand=True,
                    tight=True,
                ),
                ft.Text(ts, size=11, color=HMSColors.TEXT_SECONDARY, font_family="DM Mono"),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
    )


def section_header(title: str, action: Optional[ft.Control] = None) -> ft.Row:
    """Build a section heading row with optional action control."""
    controls = [
        ft.Text(title.upper(), size=11, weight=ft.FontWeight.W_700, color=HMSColors.TEXT_MUTED),
        ft.Container(expand=True),
    ]
    if action is not None:
        controls.append(action)
    return ft.Row(controls, vertical_alignment=ft.CrossAxisAlignment.CENTER)


def create_header(
    page: ft.Page,
    title: str,
    user_info: str = "",
) -> ft.AppBar:
    """Legacy AppBar helper kept for compatibility with older screens."""
    return ft.AppBar(
        title=ft.Text(title, size=18, weight="bold", color=HMSColors.TEXT_PRIMARY),
        center_title=False,
        bgcolor=HMSColors.SURFACE,
        color=HMSColors.TEXT_LIGHT,
        actions=[
            ft.Text(user_info, color=HMSColors.TEXT_SECONDARY, size=13),
        ] if user_info else [],
    )


def show_error_dialog(page: ft.Page, title: str, message: str):
    """Show error dialog to user."""
    dlg = ft.AlertDialog(
        title=ft.Text(title, color=HMSColors.ERROR),
        content=ft.Text(message),
        actions=[
            ft.TextButton("OK", on_click=lambda e: close_dialog(dlg, page)),
        ],
    )
    page.dialog = dlg
    dlg.open = True
    page.update()


def show_success_dialog(page: ft.Page, title: str, message: str):
    """Show success dialog to user."""
    dlg = ft.AlertDialog(
        title=ft.Text(title, color=HMSColors.SUCCESS),
        content=ft.Text(message),
        actions=[
            ft.TextButton("OK", on_click=lambda e: close_dialog(dlg, page)),
        ],
    )
    page.dialog = dlg
    dlg.open = True
    page.update()


def close_dialog(dlg: ft.AlertDialog, page: ft.Page):
    """Close dialog."""
    dlg.open = False
    page.update()


def show_toast(page: ft.Page, message: str, bgcolor: str = HMSColors.PRIMARY, duration: int = 3000):
    """Show a non-blocking toast/snackbar notification."""
    page.snack_bar = ft.SnackBar(
        content=ft.Text(message, color=HMSColors.TEXT_LIGHT, size=14),
        bgcolor=bgcolor,
        duration=duration,
        action="OK",
    )
    page.snack_bar.open = True
    page.update()


def show_success_toast(page: ft.Page, message: str):
    """Show success toast (green, non-blocking)."""
    show_toast(page, message, bgcolor=HMSColors.SUCCESS)


def show_error_toast(page: ft.Page, message: str):
    """Show error toast (red, non-blocking)."""
    show_toast(page, message, bgcolor=HMSColors.ERROR, duration=5000)


def show_warning_toast(page: ft.Page, message: str):
    """Show warning toast (orange, non-blocking)."""
    show_toast(page, message, bgcolor=HMSColors.WARNING, duration=4000)


class RefreshButton(ft.Container):
    """
    Reusable Refresh button with debounce, loading spinner, and toast feedback.

    Usage:
        refresh_btn = RefreshButton(on_refresh=self._load_items, page=self._page)
        # Add refresh_btn to any ft.Row or layout

    Behavior:
        1. User taps → debounce check (2s cooldown)
        2. If allowed → show spinner, disable button
        3. Call on_refresh()
        4. On success → restore icon, show "Data refreshed" toast
        5. On error → restore icon, show error toast, retain existing data
        6. Re-enable button
    """

    DEBOUNCE_SECONDS = 2.0

    def __init__(
        self,
        on_refresh: Callable,
        page: ft.Page,
        tooltip: str = "Refresh data",
    ):
        self._on_refresh = on_refresh
        self._ref_page = page
        self._is_refreshing = False
        self._last_refresh_time: float = 0.0

        # Icon button (visible when idle)
        self._icon_button = ft.IconButton(
            icon=ft.icons.REFRESH,
            icon_color=HMSColors.PRIMARY,
            icon_size=24,
            tooltip=tooltip,
            on_click=self._handle_tap,
        )

        # Spinner (visible when refreshing)
        self._spinner = ft.ProgressRing(
            width=24,
            height=24,
            stroke_width=3,
            color=HMSColors.PRIMARY,
            visible=False,
        )

        super().__init__(
            content=ft.Stack(
                controls=[self._icon_button, self._spinner],
                width=40,
                height=40,
            ),
            width=40,
            height=40,
            alignment=ft.alignment.center,
        )

    def _handle_tap(self, e):
        """Handle tap with debounce and loading state."""
        now = time.time()

        # Debounce: ignore taps within DEBOUNCE_SECONDS of last refresh
        if now - self._last_refresh_time < self.DEBOUNCE_SECONDS:
            return

        # Prevent concurrent refreshes
        if self._is_refreshing:
            return

        self._is_refreshing = True
        self._last_refresh_time = now

        # Show spinner, hide icon
        self._icon_button.visible = False
        self._spinner.visible = True
        try:
            self._ref_page.update()
        except Exception:
            pass

        try:
            self._on_refresh()
            show_success_toast(self._ref_page, "Data refreshed")
        except httpx.ConnectError:
            show_error_toast(self._ref_page, "Could not refresh \u2014 server unavailable")
        except httpx.TimeoutException:
            show_error_toast(self._ref_page, "Refresh timed out \u2014 try again")
        except Exception as err:
            show_error_toast(self._ref_page, f"Refresh failed: {err}")
        finally:
            # Restore icon, hide spinner
            self._icon_button.visible = True
            self._spinner.visible = False
            self._is_refreshing = False
            try:
                self._ref_page.update()
            except Exception:
                pass
