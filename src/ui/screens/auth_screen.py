"""
Login/Authentication Screen

Dark-themed role-first PIN login.
"""

import flet as ft
import httpx

from src.ui.components.ui_helpers import (
    HMSButton,
    NumericKeypad,
    HMSColors,
    tag_chip,
    show_error_dialog,
    show_error_toast,
)


class AuthScreen(ft.Column):
    """Role-first login with keypad PIN entry."""

    ROLES = ["WAITER", "CASHIER", "MANAGER", "KITCHEN", "CLERK", "ADMIN"]

    def __init__(self, page: ft.Page, on_login_success):
        self._page = page
        self.on_login_success = on_login_success
        self.api_base = "http://127.0.0.1:8000"
        self.selected_role = "WAITER"
        self.pin_value = ""
        self.role_buttons = {}

        self.username_field = ft.TextField(
            label="Username",
            value="waiter",
            width=360,
            height=48,
            bgcolor=HMSColors.SURFACE2,
            color=HMSColors.TEXT_PRIMARY,
            border_color=HMSColors.BORDER,
        )

        self.pin_dots = ft.Row(spacing=8, alignment=ft.MainAxisAlignment.CENTER)
        self._render_pin_dots()

        self.keypad = NumericKeypad(on_key_press=self._handle_keypad_press)

        self.login_button = HMSButton(
            "Sign In",
            self._handle_login,
            width=360,
            height=50,
            color=HMSColors.ACCENT,
        )
        self.login_button.disabled = True

        self.api_status_text = ft.Text(
            "Checking API...",
            size=11,
            color=HMSColors.TEXT_SECONDARY,
            text_align=ft.TextAlign.CENTER,
        )
        self.loading = ft.ProgressRing(visible=False, color=HMSColors.ACCENT)

        role_grid = self._build_role_grid()

        login_card = ft.Container(
            width=520,
            bgcolor=HMSColors.SURFACE,
            border=ft.border.all(1, HMSColors.BORDER),
            border_radius=16,
            padding=24,
            content=ft.Column(
                [
                    ft.Text("HMS", size=28, weight=ft.FontWeight.W_800, color=HMSColors.ACCENT, font_family="Syne"),
                    ft.Text("Hotel Management System", size=13, color=HMSColors.TEXT_SECONDARY),
                    ft.Container(height=8),
                    role_grid,
                    ft.Container(height=8),
                    self.username_field,
                    ft.Text("PIN", size=12, color=HMSColors.TEXT_SECONDARY),
                    self.pin_dots,
                    self.keypad,
                    ft.Row([self.login_button, self.loading], spacing=12, alignment=ft.MainAxisAlignment.CENTER),
                    self.api_status_text,
                ],
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        offline_badge = ft.Container(
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
            bgcolor=HMSColors.GREEN_DIM,
            border=ft.border.all(1, HMSColors.GREEN + "60"),
            border_radius=8,
            content=ft.Row(
                [
                    ft.Container(width=8, height=8, bgcolor=HMSColors.GREEN, border_radius=8),
                    ft.Text("OFFLINE READY", size=11, color=HMSColors.GREEN, font_family="DM Mono"),
                ],
                spacing=6,
                tight=True,
            ),
        )

        super().__init__(
            [
                ft.Container(
                    expand=True,
                    alignment=ft.alignment.center,
                    content=ft.Stack(
                        [
                            ft.Container(
                                expand=True,
                                gradient=ft.LinearGradient(
                                    begin=ft.alignment.top_left,
                                    end=ft.alignment.bottom_right,
                                    colors=[HMSColors.BG, "#101828", "#0A0F1A"],
                                ),
                            ),
                            ft.Container(
                                alignment=ft.alignment.top_right,
                                padding=20,
                                content=offline_badge,
                            ),
                            ft.Container(expand=True, alignment=ft.alignment.center, content=login_card),
                        ],
                        expand=True,
                    ),
                )
            ],
            expand=True,
            spacing=0,
        )

        self._check_api_health()

    def _build_role_grid(self) -> ft.Control:
        rows = []
        for i in range(0, len(self.ROLES), 3):
            row_controls = []
            for role in self.ROLES[i : i + 3]:
                chip = ft.Container(
                    content=tag_chip(role.title(), HMSColors.SURFACE2, HMSColors.TEXT_SECONDARY),
                    on_click=lambda e, r=role: self._select_role(r),
                )
                self.role_buttons[role] = chip
                row_controls.append(chip)
            rows.append(ft.Row(row_controls, spacing=8, alignment=ft.MainAxisAlignment.CENTER))
        self._sync_role_chips()
        return ft.Column(rows, spacing=8)

    def _select_role(self, role: str):
        self.selected_role = role
        self._sync_role_chips()
        # Keep login convenient for default users.
        self.username_field.value = role.lower()
        self.username_field.update()

    def _sync_role_chips(self):
        for role, container in self.role_buttons.items():
            active = role == self.selected_role
            container.content = tag_chip(
                role.title(),
                HMSColors.ACCENT if active else HMSColors.SURFACE2,
                HMSColors.TEXT_LIGHT if active else HMSColors.TEXT_SECONDARY,
            )
            if container.page:
                container.update()

    def _render_pin_dots(self):
        self.pin_dots.controls = []
        for i in range(6):
            filled = i < len(self.pin_value)
            self.pin_dots.controls.append(
                ft.Container(
                    width=12,
                    height=12,
                    border_radius=10,
                    bgcolor=HMSColors.ACCENT if filled else HMSColors.SURFACE3,
                    border=ft.border.all(1, HMSColors.ACCENT if filled else HMSColors.BORDER),
                )
            )

    def _handle_keypad_press(self, key: str):
        if key == "CLR":
            self.pin_value = ""
        elif key == "⌫":
            self.pin_value = self.pin_value[:-1]
        elif key.isdigit() and len(self.pin_value) < 6:
            self.pin_value += key

        self.login_button.disabled = not (4 <= len(self.pin_value) <= 6)
        self._render_pin_dots()
        self.pin_dots.update()
        self.login_button.update()

    def _check_api_health(self):
        try:
            with httpx.Client(timeout=2.0) as client:
                response = client.get(f"{self.api_base}/health")
                if response.status_code == 200:
                    self.api_status_text.value = "API connected"
                    self.api_status_text.color = HMSColors.GREEN
                else:
                    self.api_status_text.value = "API unavailable"
                    self.api_status_text.color = HMSColors.YELLOW
        except Exception:
            self.api_status_text.value = "API server not reachable"
            self.api_status_text.color = HMSColors.RED
        if self.api_status_text.page:
            self.api_status_text.update()

    def _handle_login(self, e):
        username = (self.username_field.value or "").strip()
        pin = self.pin_value

        if not username:
            show_error_dialog(self._page, "Error", "Please enter username")
            return
        if not (4 <= len(pin) <= 6):
            show_error_dialog(self._page, "Error", "PIN must be 4-6 digits")
            return

        self.loading.visible = True
        self.login_button.disabled = True
        self._page.update()

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    f"{self.api_base}/api/auth/login",
                    json={"username": username, "pin": pin},
                )
                if response.status_code == 200:
                    self.on_login_success(response.json())
                    return
                detail = response.json().get("detail", "Invalid credentials")
                show_error_dialog(self._page, "Login Failed", str(detail))
                show_error_toast(self._page, "Login failed")
        except Exception as ex:
            show_error_dialog(self._page, "Error", str(ex))
            show_error_toast(self._page, "Login failed")
            self._check_api_health()
        finally:
            self.loading.visible = False
            self.login_button.disabled = False
            self._page.update()
