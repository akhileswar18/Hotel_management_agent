"""
Chat Order Screen

Natural-language order input with parse-then-confirm flow.
Calls POST /api/voice/parse; when intent is create_order and complete,
navigates to OrderConfirmationScreen via on_show_confirmation(intent).
On parse error shows: "Sorry, couldn't understand. Try again or use the menu buttons."
"""

import flet as ft
import httpx
from typing import Callable, Optional
from src.ui.components.ui_helpers import RefreshButton, HMSColors


class ChatOrderScreen(ft.Column):
    """Chat interface for natural language orders; parse only, then show confirmation."""

    API_BASE = "http://127.0.0.1:8000"

    def __init__(
        self,
        page: ft.Page,
        user_id: str = "",
        on_show_confirmation: Optional[Callable[[dict], None]] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._page = page
        self.user_id = user_id
        self.on_show_confirmation = on_show_confirmation or (lambda _: None)
        self.expand = True

        self._pending_intent = None

        self.chat_history = ft.ListView(expand=True, spacing=8, auto_scroll=True)
        self.input_field = ft.TextField(
            hint_text="Type your order, e.g. '2 butter chicken, 1 naan, table 5'",
            expand=True,
            on_submit=self._handle_send,
            min_lines=1,
            max_lines=3,
        )
        self.send_button = ft.IconButton(
            ft.icons.SEND,
            on_click=self._handle_send,
            tooltip="Send",
        )
        self._loading = ft.ProgressRing(
            width=24, height=24, stroke_width=2,
            color=HMSColors.PRIMARY, visible=False,
        )

        suggestion_tips = [
            "2 Dosa Table 3",
            "Stock status?",
            "Today's revenue",
        ]
        self.suggestion_row = ft.Row(
            controls=[
                ft.TextButton(
                    tip,
                    on_click=lambda e, t=tip: self._set_input(t),
                    style=ft.ButtonStyle(
                        padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    ),
                )
                for tip in suggestion_tips
            ],
            wrap=True,
            spacing=8,
        )

        self.controls = [
            ft.Row(
                [
                    ft.Text("Chat Order", size=20, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    RefreshButton(
                        on_refresh=self._clear_chat,
                        page=self._page,
                        tooltip="Clear chat",
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Divider(),
            self.chat_history,
            ft.Container(content=self.suggestion_row, padding=ft.padding.only(bottom=8)),
            ft.Row(
                [self.input_field, self._loading, self.send_button],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ]

        self.chat_history.controls.append(
            self._system_bubble(
                "Type your order in plain language, e.g. \"2 butter chicken, 1 naan, table 5\". "
                "You'll get a confirmation screen before the order is placed."
            )
        )

    def _set_input(self, text: str):
        self.input_field.value = text
        self.input_field.update()

    def _user_bubble(self, text: str) -> ft.Container:
        return ft.Container(
            content=ft.Text(f"You: {text}", selectable=True, size=14),
            bgcolor="#27272a",
            padding=12,
            border_radius=12,
        )

    def _hms_bubble(self, text: str, success: bool = True) -> ft.Container:
        return ft.Container(
            content=ft.Text(f"HMS: {text}", selectable=True, size=14),
            bgcolor="#166534" if success else "#7f1d1d",
            padding=12,
            border_radius=12,
        )

    def _system_bubble(self, text: str) -> ft.Container:
        return ft.Container(
            content=ft.Text(text, size=12, color="#a1a1aa"),
            bgcolor="#27272a",
            padding=12,
            border_radius=12,
        )

    def _clear_chat(self):
        self.chat_history.controls.clear()
        self._pending_intent = None
        self.chat_history.controls.append(
            self._system_bubble("Chat cleared. Type your order to continue.")
        )
        self.input_field.hint_text = "Type your order, e.g. '2 butter chicken, 1 naan, table 5'"
        try:
            self.chat_history.update()
        except Exception:
            pass

    def _set_loading(self, loading: bool):
        self._loading.visible = loading
        self.send_button.disabled = loading
        self.input_field.disabled = loading
        try:
            self._page.update()
        except Exception:
            pass

    def _handle_send(self, e):
        text = (self.input_field.value or "").strip()
        if not text:
            return

        if text.lower() in ("cancel", "nevermind", "stop", "reset"):
            if self._pending_intent:
                self._pending_intent = None
                self.chat_history.controls.append(self._user_bubble(text))
                self.chat_history.controls.append(
                    self._system_bubble("Cancelled. Type a new order.")
                )
                self.input_field.value = ""
                self.input_field.hint_text = "Type your order, e.g. '2 butter chicken, 1 naan, table 5'"
                try:
                    self._page.update()
                except Exception:
                    pass
            return

        self.chat_history.controls.append(self._user_bubble(text))
        self.input_field.value = ""
        self._set_loading(True)

        try:
            payload = {"text": text}
            if self._pending_intent:
                payload["pending_intent"] = self._pending_intent

            response = httpx.post(
                f"{self.API_BASE}/api/voice/parse",
                json=payload,
                timeout=15,
            )
            data = response.json() if response.status_code == 200 else {}

            status = data.get("status", "error")
            intent = data.get("intent", {})
            message = data.get("message", "")
            parsed_by = data.get("parsed_by", "rules")

            if status == "followup":
                self._pending_intent = intent
                tag = " [AI]" if parsed_by == "llm" else ""
                self.chat_history.controls.append(
                    self._hms_bubble(f"{message}{tag}")
                )
                self.input_field.hint_text = "Answer the question above (or type 'cancel')..."

            elif status == "ok":
                action = intent.get("action", "")
                if action == "create_order" and intent.get("items"):
                    self._pending_intent = None
                    self.chat_history.controls.append(
                        self._hms_bubble("Got it! Confirm your order on the next screen.")
                    )
                    self.on_show_confirmation(intent)
                else:
                    self._pending_intent = None
                    self.chat_history.controls.append(
                        self._hms_bubble(
                            message or f"Understood: {action}. Use POS or command for other actions."
                        )
                    )
                self.input_field.hint_text = "Type your order, e.g. '2 butter chicken, 1 naan, table 5'"

            else:
                self._pending_intent = None
                err_msg = message or "Sorry, couldn't understand. Try again or use the menu buttons."
                self.chat_history.controls.append(self._hms_bubble(err_msg, success=False))
                self.input_field.hint_text = "Type your order, e.g. '2 butter chicken, 1 naan, table 5'"

        except httpx.ConnectError:
            self._pending_intent = None
            self.chat_history.controls.append(
                self._hms_bubble("Server unavailable. Is the backend running?", success=False)
            )
        except httpx.TimeoutException:
            self._pending_intent = None
            self.chat_history.controls.append(
                self._hms_bubble("Sorry, couldn't understand. Try again or use the menu buttons.", success=False)
            )
        except Exception as ex:
            self._pending_intent = None
            self.chat_history.controls.append(
                self._hms_bubble("Sorry, couldn't understand. Try again or use the menu buttons.", success=False)
            )
        finally:
            self._set_loading(False)
            try:
                self._page.update()
            except Exception:
                pass
