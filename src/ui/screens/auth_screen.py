"""
Login/Authentication Screen

PIN-based login for staff. Minimal friction, large touch targets.
"""

import flet as ft
import httpx
from src.ui.components.ui_helpers import (
    HMSButton, NumericKeypad, HMSColors, show_error_dialog, show_success_dialog
)


class AuthScreen(ft.Column):
    """Login screen with username and PIN input."""

    def __init__(self, page: ft.Page, on_login_success):
        self._page = page  # Store as _page to avoid conflict with Flet's read-only page property
        self.on_login_success = on_login_success
        self.api_base = "http://127.0.0.1:8000"

        # Username field
        self.username_field = ft.TextField(
            label="Username",
            width=400,
            height=56,
            text_size=20,
            autofocus=True,
        )

        # PIN display (masked)
        self.pin_display = ft.TextField(
            label="PIN (4-6 digits)",
            width=400,
            height=56,
            text_size=24,
            text_align=ft.TextAlign.CENTER,
            password=True,
            read_only=True,
        )

        self.pin_value = ""  # Actual PIN (not displayed)

        # Numeric keypad
        self.keypad = NumericKeypad(on_key_press=self._handle_keypad_press)

        # Login button
        self.login_button = HMSButton(
            "Login",
            self._handle_login,
            width=400,
            color=HMSColors.SUCCESS,
        )

        self.login_button.disabled = True

        # Loading indicator
        self.loading = ft.ProgressRing(visible=False)

        super().__init__(
            [
                ft.Container(height=20),
                ft.Text(
                    "Hotel Management System",
                    size=28,
                    weight="bold",
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    "Phase 1 - Point of Sale",
                    size=16,
                    color=HMSColors.TEXT_SECONDARY,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=40),
                ft.Text("Username", size=16, weight="bold"),
                self.username_field,
                ft.Container(height=10),
                ft.Text("PIN Code", size=16, weight="bold"),
                self.pin_display,
                ft.Container(height=10),
                self.keypad,
                ft.Container(height=20),
                ft.Row(
                    [
                        self.login_button,
                        self.loading,
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=20,
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
            expand=True,
        )

    def _handle_keypad_press(self, key: str):
        """Handle numeric keypad input."""
        if key == "CLR":
            # Clear all
            self.pin_value = ""
            self.pin_display.value = ""
        elif key == "⌫":
            # Backspace
            if self.pin_value:
                self.pin_value = self.pin_value[:-1]
                self.pin_display.value = "*" * len(self.pin_value)
        elif key.isdigit():
            # Add digit
            if len(self.pin_value) < 6:
                self.pin_value += key
                self.pin_display.value = "*" * len(self.pin_value)

        # Enable login button if PIN is 4-6 digits
        self.login_button.disabled = not (4 <= len(self.pin_value) <= 6)
        self.pin_display.update()
        self.login_button.update()

    def _handle_login(self, e):
        """Handle login button click."""
        username = self.username_field.value.strip()
        pin = self.pin_value

        if not username:
            show_error_dialog(self._page, "Error", "Please enter username")
            return

        if not (4 <= len(pin) <= 6):
            show_error_dialog(self._page, "Error", "PIN must be 4-6 digits")
            return

        # Show loading
        self.loading.visible = True
        self._page.update()

        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.post(
                    f"{self.api_base}/api/auth/login",
                    json={"username": username, "pin": pin},
                )

                if response.status_code == 200:
                    user_data = response.json()
                    self.loading.visible = False
                    self._page.update()
                    # Trigger success callback
                    self.on_login_success(user_data)
                else:
                    error_data = response.json()
                    show_error_dialog(
                        self._page,
                        "Login Failed",
                        error_data.get("detail", "Invalid credentials")
                    )
        except Exception as ex:
            show_error_dialog(
                self._page,
                "Connection Error",
                f"Failed to connect: {str(ex)}"
            )
        finally:
            self.loading.visible = False
            self._page.update()


# TODO: Add offline login (cache credentials)
# TODO: Add "forgot PIN" recovery
# TODO: Add session management
