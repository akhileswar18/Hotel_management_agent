"""
Main Flet Application

Dark app shell with custom sidebar and dashboard-first routing.
"""

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
            "ai": ChatScreen(
                self.page,
                user_role=str(self.current_user.get("role", "WAITER")),
                user_id=str(self.current_user.get("user_id", "")),
            ),
        }

        self.content_area = ft.Container(expand=True, content=self.screens["dashboard"])

        nav_column = ft.Column(
            controls=[],
            spacing=8,
            expand=True,
            alignment=ft.MainAxisAlignment.START,
        )
        self.nav_column = nav_column
        self._build_sidebar_items()

        self.sidebar = ft.Container(
            width=72,
            bgcolor="#0A0D14",
            border=ft.border.only(right=ft.BorderSide(1, HMSColors.BORDER)),
            padding=ft.padding.symmetric(vertical=16, horizontal=12),
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
            ("dashboard", ft.icons.DASHBOARD, "Dash"),
            ("pos", ft.icons.CHECK_CIRCLE, "POS"),
            ("inventory", ft.icons.INVENTORY_2, "Inv"),
            ("billing", ft.icons.RECEIPT_LONG, "Bill"),
            ("reports", ft.icons.INSIGHTS, "Rpt"),
            ("spacer", None, ""),
            ("kitchen", ft.icons.KITCHEN, "KDS"),
            ("ai", ft.icons.AUTO_AWESOME, "AI"),
            ("logout", ft.icons.LOGOUT, "Out"),
        ]

        self.nav_column.controls.clear()
        self.nav_items.clear()
        for key, icon, label in items:
            if key == "spacer":
                self.nav_column.controls.append(ft.Container(expand=True))
                continue
            nav = self._make_nav_item(key, icon, label)
            self.nav_items[key] = nav
            self.nav_column.controls.append(nav)

    def _make_nav_item(self, key: str, icon_name: str, label: str) -> ft.Container:
        icon = ft.Icon(icon_name, size=18, color=HMSColors.TEXT_MUTED)
        label_text = ft.Text(label, size=9, color=HMSColors.TEXT_MUTED)

        def _click(_):
            if key == "logout":
                self._handle_logout()
                return
            self._show_route(key)

        content = ft.Column(
            [icon, label_text],
            spacing=2,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        )

        item = ft.Container(
            width=48,
            height=48,
            border_radius=10,
            alignment=ft.alignment.center,
            on_click=_click,
            content=ft.Stack([content, ft.Container(content=self.low_stock_badge, alignment=ft.alignment.top_right)] if key == "inventory" else [content]),
        )
        item.data = {"key": key, "icon": icon, "label": label_text}
        return item

    def _refresh_low_stock_badge(self):
        count = 0
        try:
            with httpx.Client(timeout=4.0) as client:
                resp = client.get("http://127.0.0.1:8000/api/inventory/items")
                if resp.status_code == 200:
                    rows = resp.json()
                    count = len([r for r in rows if int(r.get("stock_on_hand", 0)) < int(r.get("reorder_level", 0))])
        except Exception:
            count = 0
        self.low_stock_badge.visible = count > 0
        if self.low_stock_badge.page:
            self.low_stock_badge.update()

    def _show_route(self, route: str):
        if route not in self.screens:
            return
        self.current_route = route
        self.content_area.content = self.screens[route]
        self._style_nav_items()
        self.content_area.update()
        self._refresh_low_stock_badge()

    def _style_nav_items(self):
        for key, item in self.nav_items.items():
            data = item.data or {}
            icon = data.get("icon")
            label = data.get("label")
            active = key == self.current_route
            if key == "ai":
                if active:
                    item.gradient = ft.LinearGradient(colors=[HMSColors.ACCENT + "30", HMSColors.BLUE + "30"])
                    item.bgcolor = None
                    item.border = ft.border.all(1, HMSColors.ACCENT + "70")
                    icon.color = HMSColors.ACCENT
                    label.color = HMSColors.TEXT_PRIMARY
                else:
                    item.gradient = ft.LinearGradient(colors=[HMSColors.ACCENT + "10", HMSColors.BLUE + "10"])
                    item.bgcolor = None
                    item.border = ft.border.all(1, HMSColors.BORDER)
                    icon.color = HMSColors.TEXT_SECONDARY
                    label.color = HMSColors.TEXT_MUTED
            else:
                item.gradient = None
                if active:
                    item.bgcolor = HMSColors.ACCENT + "26"
                    item.border = ft.border.all(1, HMSColors.ACCENT + "60")
                    icon.color = HMSColors.ACCENT
                    label.color = HMSColors.TEXT_PRIMARY
                else:
                    item.bgcolor = None
                    item.border = ft.border.all(1, "00000000")
                    icon.color = HMSColors.TEXT_MUTED
                    label.color = HMSColors.TEXT_MUTED
            item.update()

    def _handle_logout(self):
        self.current_user = None
        self.screens = {}
        self._show_login_screen()


def main():
    """App entry point."""

    def run(page: ft.Page):
        HMSApp(page)

    ft.app(target=run, view=ft.AppView.WEB_BROWSER, port=8080)


if __name__ == "__main__":
    main()
