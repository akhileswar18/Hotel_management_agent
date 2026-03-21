"""
Main Flet Application

Dark app shell with custom sidebar and dashboard-first routing.
"""

import os as _os

import flet as ft
import httpx

from src.ui.i18n import set_language
from src.ui.components.ui_helpers import HMSColors
from src.ui.screens.auth_screen import AuthScreen
from src.ui.screens.dashboard_screen import DashboardScreen
from src.ui.screens.pos_screen import POSScreen
from src.ui.screens.products_screen import ProductsScreen
from src.ui.screens.receipt_screen import ReceiptScreen
from src.ui.screens.reports_screen import ReportsScreen
from src.ui.screens.order_history_screen import OrderHistoryScreen
from src.ui.screens.chat_screen import ChatScreen


class HMSApp:
    """Main HMS application shell and routing."""

    def __init__(self, page: ft.Page):
        self.page = page
        set_language("en")
        self.page.title = "Hotel Management System"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = HMSColors.BG
        self.page.padding = 0
        self.page.spacing = 0
        self.page.scroll = None

        self.current_user = None
        self.screens = {}
        self.current_route = "login"
        self.nav_items = {}
        self.has_low_stock = False
        self.low_stock_badge = ft.Container(
            width=8,
            height=8,
            border_radius=8,
            bgcolor=HMSColors.RED,
            visible=False,
        )

        self._show_login_screen()

    def _show_login_screen(self):
        auth_screen = AuthScreen(self.page, on_login_success=self._handle_login_success)
        self.page.controls = [auth_screen]
        self.page.update()
        self.current_route = "login"

    def _handle_login_success(self, user_data: dict):
        self.current_user = user_data
        self._init_main_shell()
        self._show_route("dashboard")

    def _init_main_shell(self):
        self.screens = {
            "dashboard": DashboardScreen(self.page, self.current_user, on_nav=self._show_route),
            "pos": POSScreen(self.page, self.current_user, on_logout=self._handle_logout),
            "inventory": ProductsScreen(self.page, self.current_user, on_back=lambda: self._show_route("pos")),
            "billing": ReceiptScreen(self.page, user_info=self.current_user, on_back=lambda: self._show_route("pos")),
            "reports": ReportsScreen(self.page, self.current_user, on_back=lambda: self._show_route("pos")),
            "kitchen": OrderHistoryScreen(self.page, self.current_user, on_back=lambda: self._show_route("dashboard")),
            "agent": ChatScreen(
                self.page,
                user_role=str(self.current_user.get("role", "WAITER")),
                user_id=str(self.current_user.get("user_id", "")),
            ),
        }
        self.screens["ai"] = self.screens["agent"]
        self.screens["invoice"] = self.screens["billing"]

        self.content_area = ft.Container(expand=True, content=self.screens["dashboard"])

        nav_column = ft.Column(
            controls=[],
            spacing=0,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.nav_column = nav_column
        self._build_sidebar_items()

        self.sidebar = ft.Container(
            width=90,
            bgcolor="#161B27",
            border=ft.border.only(right=ft.BorderSide(1, "#2A3349")),
            padding=ft.padding.symmetric(vertical=12),
            content=nav_column,
        )

        shell = ft.Row(
            [
                self.sidebar,
                self.content_area,
            ],
            spacing=0,
            expand=True,
        )
        self.page.controls = [shell]
        self._refresh_low_stock_badge()
        self.page.update()

    def _build_sidebar_items(self):
        items = [
            self._make_nav_item(self._resolve_nav_icon("DASHBOARD_OUTLINED"), "Dash", "dashboard"),
            self._make_nav_item(self._resolve_nav_icon("POINT_OF_SALE"), "POS", "pos"),
            self._make_nav_item(self._resolve_nav_icon("INVENTORY_2_OUTLINED"), "Inv", "inventory", dot=self.has_low_stock),
            self._make_nav_item(self._resolve_nav_icon("RECEIPT_LONG_OUTLINED"), "Bill", "invoice"),
            self._make_nav_item(self._resolve_nav_icon("BAR_CHART_OUTLINED"), "Rpt", "reports"),
            ft.Container(expand=True),
            ft.Container(
                width=36,
                height=1,
                bgcolor="#2A3349",
                margin=ft.margin.symmetric(vertical=4),
            ),
            self._make_nav_item(self._resolve_nav_icon("RESTAURANT_MENU"), "KDS", "kitchen"),
            self._make_nav_item(self._resolve_nav_icon("PSYCHOLOGY_OUTLINED"), "AI", "agent", special=True),
            self._make_nav_item(self._resolve_nav_icon("LOGOUT"), "Out", "logout"),
        ]

        self.nav_column.controls.clear()
        self.nav_items.clear()
        self.nav_column.controls.extend(items)

    def _resolve_nav_icon(self, icon_name: str):
        icon_set = getattr(ft, "Icons", None)
        if icon_set is not None and hasattr(icon_set, icon_name):
            return getattr(icon_set, icon_name)
        lower_icon_set = getattr(ft, "icons", None)
        if lower_icon_set is not None and hasattr(lower_icon_set, icon_name):
            return getattr(lower_icon_set, icon_name)
        if icon_set is not None and hasattr(icon_set, "CIRCLE_OUTLINED"):
            return getattr(icon_set, "CIRCLE_OUTLINED")
        return getattr(ft.icons, "CIRCLE_OUTLINED")

    def _navigate(self, screen_key: str):
        if screen_key == "logout":
            self._handle_logout()
            return
        if screen_key == "agent":
            self._show_chat_screen()
            return
        self._show_route(screen_key)

    def _make_nav_item(self, icon_name, label: str, screen_key: str, dot: bool = False, special: bool = False) -> ft.Control:
        active_screen = "invoice" if self.current_route == "billing" else self.current_route
        is_active = screen_key == active_screen

        if is_active:
            icon_color = "#FF6B35"
            bg_color = "#FF6B3520"
            border_col = "#FF6B3540"
        elif special:
            icon_color = "#FF6B35"
            bg_color = "#FF6B3508"
            border_col = "#FF6B3530"
        else:
            icon_color = "#4B5675"
            bg_color = "transparent"
            border_col = "transparent"

        icon_widget = ft.Icon(
            name=icon_name,
            size=40,
            color=icon_color,
        )

        label_widget = ft.Text(
            label,
            size=9,
            weight=ft.FontWeight.W_600,
            color=icon_color,
            text_align=ft.TextAlign.CENTER,
        )

        inner_column = ft.Column(
            controls=[icon_widget, label_widget],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4,
            tight=True,
        )
        inner_container = ft.Container(
            width=56,
            height=72,
            border_radius=10,
            bgcolor=bg_color,
            border=ft.border.all(1, border_col),
            alignment=ft.alignment.center,
            content=inner_column,
        )
        if special:
            inner_container.gradient = ft.LinearGradient(
                colors=["#FF6B3510", "#FF6B3504"],
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
            )

        inner = inner_container
        if dot:
            inner = ft.Stack(
                [
                    inner_container,
                    ft.Container(
                        width=8,
                        height=8,
                        border_radius=4,
                        bgcolor="#EF4444",
                        border=ft.border.all(2, "#161B27"),
                        right=4,
                        top=4,
                    ),
                ],
                width=56,
                height=72,
            )

        def _on_hover(e: ft.HoverEvent):
            if is_active:
                return
            hovering = str(getattr(e, "data", "")).lower() == "true"
            inner_container.bgcolor = "#1E2535" if hovering else bg_color
            inner_container.border = ft.border.all(1, "#2A3349" if hovering else border_col)
            try:
                self.page.update()
            except Exception:
                pass

        nav_item_container = ft.Container(
            content=inner,
            padding=ft.padding.symmetric(vertical=4),
            on_click=lambda e, s=screen_key: self._navigate(s),
            on_hover=_on_hover,
        )

        item = nav_item_container
        if is_active:
            item = ft.Stack(
                [
                    nav_item_container,
                    ft.Container(
                        width=2,
                        height=72,
                        bgcolor="#FF6B35",
                        left=0,
                        top=4,
                    ),
                ],
                width=56,
                height=80,
            )

        self.nav_items[screen_key] = item
        return item

    def _refresh_low_stock_badge(self):
        prev_has_low_stock = self.has_low_stock
        count = 0
        try:
            with httpx.Client(timeout=4.0) as client:
                resp = client.get("http://127.0.0.1:8000/api/inventory/items")
                if resp.status_code == 200:
                    rows = resp.json()
                    count = len([r for r in rows if int(r.get("stock_on_hand", 0)) < int(r.get("reorder_level", 0))])
        except Exception:
            count = 0
        self.has_low_stock = count > 0
        self.low_stock_badge.visible = self.has_low_stock
        if hasattr(self, "nav_column") and self.has_low_stock != prev_has_low_stock:
            self._build_sidebar_items()

    def _show_route(self, route: str):
        if route == "ai":
            route = "agent"
        if route == "invoice":
            route = "billing"
        if route not in self.screens:
            return
        previous_route = self.current_route
        if previous_route in self.screens and previous_route != route:
            previous_screen = self.screens.get(previous_route)
            cleanup = getattr(previous_screen, "cleanup", None)
            if callable(cleanup):
                cleanup()
        self.current_route = route
        self.content_area.content = self.screens[route]
        on_show = getattr(self.screens[route], "on_show", None)
        if callable(on_show):
            on_show()
        self._build_sidebar_items()
        self._refresh_low_stock_badge()
        self.page.update()

    def _show_chat_screen(self):
        self._show_route("agent")

    def _handle_logout(self):
        self.current_user = None
        self.screens = {}
        self._show_login_screen()


def main():
    """App entry point."""

    def run(page: ft.Page):
        HMSApp(page)

    _assets = _os.path.abspath(
        _os.path.join(_os.path.dirname(__file__), "..", "assets")
    )

    ft.app(
        target=run,
        view=ft.AppView.WEB_BROWSER,
        port=8080,
        assets_dir=_assets,
    )


if __name__ == "__main__":
    main()
