"""
Main Flet Application

Coordinates all UI screens for HMS Phase 1.5 MVP.
Touch-first, offline-capable POS interface.
"""

import flet as ft
from src.ui.screens.auth_screen import AuthScreen
from src.ui.screens.pos_screen import POSScreen
from src.ui.screens.products_screen import ProductsScreen
from src.ui.screens.reports_screen import ReportsScreen
from src.ui.screens.receipt_screen import ReceiptScreen


class HMSApp:
    """Main HMS Flet application."""

    def __init__(self, page: ft.Page):
        """Initialize HMS app."""
        self.page = page
        self.page.title = "Hotel Management System (HMS) - Phase 1.5"
        self.page.window_width = 1400
        self.page.window_height = 900
        self.page.window_resizable = True

        # Theme
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 0
        self.page.spacing = 0

        # Current state
        self.current_user = None
        self.current_screen = None

        # Show login screen initially
        self._show_login_screen()

    def _show_login_screen(self):
        """Display login screen."""
        self.page.clean()

        auth_screen = AuthScreen(
            self.page,
            on_login_success=self._handle_login_success,
        )

        self.page.add(auth_screen)
        self.current_screen = "login"

    def _handle_login_success(self, user_data: dict):
        """Handle successful login."""
        self.current_user = user_data
        self._show_pos_screen()

    def _show_pos_screen(self):
        """Display main POS screen."""
        self.page.clean()

        # Create main navigation
        nav_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.icons.SHOPPING_CART,
                    selected_icon=ft.icons.SHOPPING_CART,
                    label="POS",
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.INVENTORY_2,
                    selected_icon=ft.icons.INVENTORY_2,
                    label="Products",
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.ASSESSMENT,
                    selected_icon=ft.icons.ASSESSMENT,
                    label="Reports",
                ),
            ],
            on_change=self._handle_nav_change,
        )

        # POS screen
        pos_screen = POSScreen(
            self.page,
            self.current_user,
            on_logout=self._handle_logout,
        )

        # Products screen
        products_screen = ProductsScreen(
            self.page,
            self.current_user,
            on_back=lambda: self._switch_screen(0),
        )

        # Reports screen
        reports_screen = ReportsScreen(
            self.page,
            self.current_user,
            on_back=lambda: self._switch_screen(0),
        )

        # Store references
        self.screens = [pos_screen, products_screen, reports_screen]
        self.nav_rail = nav_rail
        self.current_nav_index = 0

        # Main content area
        self.content_area = ft.Container(
            content=self.screens[0],
            expand=True,
        )

        # Main layout
        main_layout = ft.Row(
            [
                nav_rail,
                ft.VerticalDivider(width=1),
                self.content_area,
            ],
            spacing=0,
            expand=True,
        )

        self.page.add(main_layout)
        self.current_screen = "pos"

    def _handle_nav_change(self, e):
        """Handle navigation rail selection."""
        self._switch_screen(e.control.selected_index)

    def _switch_screen(self, index: int):
        """Switch to different screen."""
        self.nav_rail.selected_index = index
        self.content_area.content = self.screens[index]
        self.content_area.update()
        self.nav_rail.update()

    def _handle_logout(self):
        """Handle logout."""
        self.current_user = None
        self._show_login_screen()


def main():
    """Main entry point for Flet app."""
    def run(page: ft.Page):
        app = HMSApp(page)

    ft.app(
        target=run,
        view=ft.AppView.WEB_BROWSER,
        port=8080,
    )


if __name__ == "__main__":
    main()


# TODO: Add offline mode indicator
# TODO: Add theme switcher (dark/light)
# TODO: Add accessibility settings
# TODO: Add multi-language support (Phase 2)
