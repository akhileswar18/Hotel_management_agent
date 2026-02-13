"""
User Management Screen

Manage users: view, create, edit roles, reset PINs.
Manager-only functionality (Phase 6).
"""

import flet as ft
import httpx
from src.ui.components.ui_helpers import (
    HMSButton,
    HMSColors,
    show_error_dialog,
    show_success_dialog,
    RefreshButton,
)


class UserManagementScreen(ft.Column):
    """User management screen (manager only)."""

    def __init__(self, page: ft.Page, user_info: dict, on_back):
        self._page = page
        self.user_info = user_info
        self.on_back = on_back
        self.api_base = "http://127.0.0.1:8000"
        self.users = []

        # Header buttons
        add_user_btn = HMSButton(
            "Add New User",
            self._handle_add_user,
            color=HMSColors.SUCCESS,
            width=160,
        )

        refresh_btn = RefreshButton(
            on_refresh=self._load_users,
            page=self._page,
            tooltip="Refresh user list",
        )

        # Users list
        self.users_list = ft.ListView(
            spacing=8,
            expand=True,
            padding=ft.padding.symmetric(horizontal=16),
        )

        super().__init__(
            [
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.icons.PEOPLE, color=HMSColors.PRIMARY, size=28),
                            ft.Text("User Management", size=22, weight="bold"),
                            ft.Container(expand=True),
                            refresh_btn,
                            add_user_btn,
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.padding.all(16),
                ),
                ft.Divider(height=1),
                self.users_list,
            ],
            spacing=0,
            expand=True,
        )

        self._load_users()

    def _load_users(self):
        """Load users from API."""
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.api_base}/api/users")
                if response.status_code == 200:
                    self.users = response.json()
                    self._display_users()
                else:
                    self.users = []
                    self._display_users()
        except Exception as ex:
            show_error_dialog(self.page, "Load Error", f"Could not load users: {ex}")

    def _display_users(self):
        """Render the user cards into the list."""
        self.users_list.controls.clear()

        if not self.users:
            self.users_list.controls.append(
                ft.Container(
                    content=ft.Text(
                        "No users found. Click 'Add New User' to create one.",
                        size=14,
                        color=HMSColors.TEXT_SECONDARY,
                    ),
                    padding=20,
                    alignment=ft.alignment.center,
                )
            )
        else:
            for user in self.users:
                self.users_list.controls.append(self._build_user_card(user))

        try:
            self.users_list.update()
        except Exception:
            pass

    def _build_user_card(self, user: dict) -> ft.Container:
        """Build a single user card widget."""
        role = user.get("role", "WAITER")
        user_id = user.get("id", "")
        username = user.get("username", "")

        # Role styling
        role_colors = {
            "ADMIN": HMSColors.ERROR,
            "MANAGER": HMSColors.WARNING,
            "CASHIER": HMSColors.PRIMARY,
            "WAITER": HMSColors.NEUTRAL,
        }
        role_color = role_colors.get(role, HMSColors.NEUTRAL)

        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.icons.PERSON, color=role_color, size=30),
                    ft.Column(
                        [
                            ft.Text(username, size=16, weight="bold"),
                            ft.Container(
                                content=ft.Text(
                                    role,
                                    size=11,
                                    color=HMSColors.TEXT_LIGHT,
                                    weight="bold",
                                ),
                                bgcolor=role_color,
                                border_radius=4,
                                padding=ft.padding.symmetric(horizontal=8, vertical=2),
                            ),
                        ],
                        spacing=4,
                        expand=True,
                    ),
                    ft.IconButton(
                        icon=ft.icons.EDIT,
                        icon_color=HMSColors.PRIMARY,
                        icon_size=20,
                        tooltip="Edit role",
                        on_click=lambda e, uid=user_id: self._handle_edit_user(uid),
                    ),
                    ft.IconButton(
                        icon=ft.icons.LOCK_RESET,
                        icon_color=HMSColors.WARNING,
                        icon_size=20,
                        tooltip="Reset PIN",
                        on_click=lambda e, uid=user_id: self._handle_reset_pin(uid),
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=12,
            bgcolor=HMSColors.BG_SECONDARY,
            border_radius=8,
            border=ft.border.all(1, role_color),
        )

    # ------------------------------------------------------------------
    # Add User
    # ------------------------------------------------------------------
    def _handle_add_user(self, e):
        """Show dialog to create a new user."""
        username_field = ft.TextField(label="Username", width=300, autofocus=True)
        pin_field = ft.TextField(
            label="PIN (4+ digits)", width=300, password=True, can_reveal_password=True
        )
        role_field = ft.Dropdown(
            label="Role",
            options=[
                ft.dropdown.Option("WAITER", "Waiter"),
                ft.dropdown.Option("CASHIER", "Cashier"),
                ft.dropdown.Option("MANAGER", "Manager"),
                ft.dropdown.Option("ADMIN", "Admin"),
            ],
            value="WAITER",
            width=300,
        )
        error_text = ft.Text("", color=HMSColors.ERROR, size=12, visible=False)

        def _close_dlg(ev=None):
            dlg.open = False
            self._page.update()

        def _confirm_add(ev):
            username = username_field.value.strip()
            pin = pin_field.value.strip()
            if not username or not pin:
                error_text.value = "Username and PIN are required"
                error_text.visible = True
                self._page.update()
                return
            if len(pin) < 4:
                error_text.value = "PIN must be at least 4 digits"
                error_text.visible = True
                self._page.update()
                return

            _close_dlg()

            try:
                with httpx.Client(timeout=5.0) as client:
                    resp = client.post(
                        f"{self.api_base}/api/users",
                        json={
                            "username": username,
                            "pin": pin,
                            "role": role_field.value,
                        },
                    )
                    if resp.status_code == 200:
                        show_success_dialog(
                            self.page,
                            "User Created",
                            f"'{username}' created as {role_field.value}",
                        )
                        self._load_users()
                    else:
                        detail = resp.json().get("detail", "Failed to create user")
                        show_error_dialog(self.page, "Error", detail)
            except Exception as err:
                show_error_dialog(self.page, "Error", str(err))

        dlg = ft.AlertDialog(
            title=ft.Text("Add New User"),
            content=ft.Column(
                [username_field, pin_field, role_field, error_text],
                tight=True,
                spacing=10,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda ev: _close_dlg()),
                ft.ElevatedButton(
                    "Create",
                    on_click=_confirm_add,
                    bgcolor=HMSColors.SUCCESS,
                    color=HMSColors.TEXT_LIGHT,
                ),
            ],
        )

        self._page.dialog = dlg
        dlg.open = True
        self._page.update()

    # ------------------------------------------------------------------
    # Edit Role
    # ------------------------------------------------------------------
    def _handle_edit_user(self, user_id: str):
        """Show dialog to change a user's role."""
        current = next((u for u in self.users if u["id"] == user_id), None)
        if not current:
            return

        role_field = ft.Dropdown(
            label="New Role",
            options=[
                ft.dropdown.Option("WAITER", "Waiter"),
                ft.dropdown.Option("CASHIER", "Cashier"),
                ft.dropdown.Option("MANAGER", "Manager"),
                ft.dropdown.Option("ADMIN", "Admin"),
            ],
            value=current.get("role", "WAITER"),
            width=300,
        )

        def _close_dlg(ev=None):
            dlg.open = False
            self._page.update()

        def _confirm_edit(ev):
            _close_dlg()
            try:
                with httpx.Client(timeout=5.0) as client:
                    resp = client.patch(
                        f"{self.api_base}/api/users/{user_id}",
                        json={"role": role_field.value},
                    )
                    if resp.status_code == 200:
                        show_success_dialog(
                            self.page,
                            "Role Updated",
                            f"{current['username']} is now {role_field.value}",
                        )
                        self._load_users()
                    else:
                        detail = resp.json().get("detail", "Failed to update")
                        show_error_dialog(self.page, "Error", detail)
            except Exception as err:
                show_error_dialog(self.page, "Error", str(err))

        dlg = ft.AlertDialog(
            title=ft.Text(f"Edit: {current['username']}"),
            content=ft.Column(
                [
                    ft.Text(
                        f"Current role: {current.get('role', '?')}",
                        size=13,
                        color=HMSColors.TEXT_SECONDARY,
                    ),
                    role_field,
                ],
                tight=True,
                spacing=10,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda ev: _close_dlg()),
                ft.ElevatedButton(
                    "Save",
                    on_click=_confirm_edit,
                    bgcolor=HMSColors.PRIMARY,
                    color=HMSColors.TEXT_LIGHT,
                ),
            ],
        )

        self._page.dialog = dlg
        dlg.open = True
        self._page.update()

    # ------------------------------------------------------------------
    # Reset PIN
    # ------------------------------------------------------------------
    def _handle_reset_pin(self, user_id: str):
        """Show dialog to reset a user's PIN."""
        current = next((u for u in self.users if u["id"] == user_id), None)
        if not current:
            return

        pin_field = ft.TextField(
            label="New PIN (4+ digits)",
            width=300,
            password=True,
            can_reveal_password=True,
            autofocus=True,
        )

        def _close_dlg(ev=None):
            dlg.open = False
            self._page.update()

        def _confirm_reset(ev):
            pin = pin_field.value.strip()
            if not pin or len(pin) < 4:
                show_error_dialog(self.page, "Error", "PIN must be at least 4 digits")
                return
            _close_dlg()
            try:
                with httpx.Client(timeout=5.0) as client:
                    resp = client.patch(
                        f"{self.api_base}/api/users/{user_id}",
                        json={"pin": pin},
                    )
                    if resp.status_code == 200:
                        show_success_dialog(
                            self.page,
                            "PIN Reset",
                            f"PIN reset for {current['username']}",
                        )
                    else:
                        detail = resp.json().get("detail", "Failed to reset PIN")
                        show_error_dialog(self.page, "Error", detail)
            except Exception as err:
                show_error_dialog(self.page, "Error", str(err))

        dlg = ft.AlertDialog(
            title=ft.Text(f"Reset PIN: {current['username']}"),
            content=ft.Column([pin_field], tight=True, spacing=10),
            actions=[
                ft.TextButton("Cancel", on_click=lambda ev: _close_dlg()),
                ft.ElevatedButton(
                    "Reset PIN",
                    on_click=_confirm_reset,
                    bgcolor=HMSColors.WARNING,
                    color=HMSColors.TEXT_LIGHT,
                ),
            ],
        )

        self._page.dialog = dlg
        dlg.open = True
        self._page.update()
