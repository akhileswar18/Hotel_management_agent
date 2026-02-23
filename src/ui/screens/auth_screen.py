"""
Login/Authentication Screen

PIN-based login for staff. Minimal friction, large touch targets.
"""

import flet as ft
import httpx
from src.ui.components.ui_helpers import (
    HMSButton, NumericKeypad, HMSColors, show_error_dialog, show_error_toast
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

        # API status indicator
        self.api_status_text = ft.Text(
            "Checking API connection...",
            size=12,
            color=HMSColors.TEXT_SECONDARY,
            text_align=ft.TextAlign.CENTER,
        )

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
                self.api_status_text,
            ],
            alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
            expand=True,
        )

        # Check API health on load
        self._check_api_health()

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

    def _check_api_health(self):
        """Check if API server is available."""
        try:
            with httpx.Client(timeout=2.0) as client:
                response = client.get(f"{self.api_base}/health")
                if response.status_code == 200:
                    self.api_status_text.value = "✓ API connected"
                    self.api_status_text.color = HMSColors.SUCCESS
                else:
                    self.api_status_text.value = "⚠ API returned error"
                    self.api_status_text.color = HMSColors.WARNING
        except httpx.ConnectError:
            self.api_status_text.value = "✗ API server not running — please start backend"
            self.api_status_text.color = HMSColors.ERROR
        except httpx.TimeoutException:
            self.api_status_text.value = "⚠ API timeout — server may be slow"
            self.api_status_text.color = HMSColors.WARNING
        except Exception as ex:
            self.api_status_text.value = f"⚠ API check failed: {type(ex).__name__}"
            self.api_status_text.color = HMSColors.WARNING
        
        try:
            self.api_status_text.update()
        except Exception:
            pass  # Page might not be mounted yet

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
        self.login_button.disabled = True
        self._page.update()

        try:
            with httpx.Client(timeout=10.0) as client:  # Increased timeout
                response = client.post(
                    f"{self.api_base}/api/auth/login",
                    json={"username": username, "pin": pin},
                )

                if response.status_code == 200:
                    user_data = response.json()
                    self.loading.visible = False
                    self.login_button.disabled = False
                    self._page.update()
                    # Trigger success callback
                    self.on_login_success(user_data)
                else:
                    error_data = response.json()
                    error_msg = error_data.get("detail", "Invalid credentials")
                    show_error_dialog(
                        self._page,
                        "Login Failed",
                        error_msg
                    )
                    show_error_toast(self._page, f"Login failed: {error_msg}")
        except httpx.ConnectError:
            error_msg = "Cannot connect to API server.\n\nPlease ensure the backend is running:\n1. Run 'python -m src.launcher' (starts both API + UI)\n2. Or run 'python -m src' in a separate terminal for API only\n\nAPI should be available at http://127.0.0.1:8000"
            show_error_dialog(
                self._page,
                "API Server Not Running",
                error_msg
            )
            show_error_toast(self._page, "API server not running - check console")
            self._check_api_health()  # Refresh status
        except httpx.TimeoutException:
            error_msg = "Request timed out. The API server may be slow or unresponsive."
            show_error_dialog(
                self._page,
                "Timeout Error",
                error_msg
            )
            show_error_toast(self._page, "Login request timed out")
        except Exception as ex:
            error_msg = f"Unexpected error: {str(ex)}"
            show_error_dialog(
                self._page,
                "Error",
                error_msg
            )
            show_error_toast(self._page, f"Error: {type(ex).__name__}")
        finally:
            self.loading.visible = False
            self.login_button.disabled = False
            self._page.update()


# TODO: Add offline login (cache credentials)
# TODO: Add "forgot PIN" recovery
# TODO: Add session management
