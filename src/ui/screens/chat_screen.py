"""
Chat / Voice Order Screen

Text-based chat interface for insights AND ordering commands.
- Insight queries → /api/insights/query (InsightAgent)
- Order commands → /api/voice/text-command (IntentParser → OrchestratorAgent)
"""

import flet as ft
import httpx
from src.ui.components.ui_helpers import RefreshButton, HMSColors


class ChatScreen(ft.Column):
    """Chat interface for insights and natural language ordering."""

    API_BASE = "http://127.0.0.1:8000"

    def __init__(self, page: ft.Page, user_role: str = "WAITER", user_id: str = "", **kwargs):
        super().__init__(**kwargs)
        self._page = page
        self.user_role = user_role
        self.user_id = user_id
        self.expand = True

        # Conversation context for follow-up questions
        self._pending_intent = None  # Stores incomplete intent awaiting follow-up

        self.chat_history = ft.ListView(expand=True, spacing=8, auto_scroll=True)
        self.input_field = ft.TextField(
            hint_text="Type a command or question...",
            expand=True,
            on_submit=self._handle_send,
        )
        self.send_button = ft.IconButton(
            ft.Icons.SEND,
            on_click=self._handle_send,
            tooltip="Send message",
        )

        # Loading indicator
        self._loading = ft.ProgressRing(
            width=20, height=20, stroke_width=2,
            color=HMSColors.PRIMARY, visible=False,
        )

        # Mode toggle: insights vs command
        self.mode_toggle = ft.Dropdown(
            label="Mode",
            options=[
                ft.dropdown.Option("insight", "Ask / Insights"),
                ft.dropdown.Option("command", "Command"),
            ],
            value="insight",
            width=160,
            height=48,
            text_size=13,
            on_change=self._handle_mode_change,
        )

        # Refresh button — clears chat history for fresh context
        self.refresh_button = RefreshButton(
            on_refresh=self._clear_chat,
            page=self._page,
            tooltip="Clear chat history",
        )

        self.controls = [
            ft.Row(
                [
                    ft.Text("Chat / Voice", size=20, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    self.mode_toggle,
                    self.refresh_button,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Divider(),
            self.chat_history,
            ft.Row([self.input_field, self._loading, self.send_button]),
        ]

        # Show welcome message
        self.chat_history.controls.append(
            self._system_bubble(
                "Welcome! Choose a mode:\n"
                "• Ask / Insights — ask questions about sales, inventory, etc.\n"
                "• Command — create orders, finalize, add items, manage inventory"
            )
        )

    def _user_bubble(self, text: str) -> ft.Container:
        """Create a user message bubble."""
        return ft.Container(
            content=ft.Text(f"You: {text}", selectable=True),
            bgcolor=ft.colors.BLUE_50,
            padding=10,
            border_radius=8,
        )

    def _hms_bubble(self, text: str, success: bool = True) -> ft.Container:
        """Create an HMS response bubble."""
        return ft.Container(
            content=ft.Text(f"HMS: {text}", selectable=True),
            bgcolor=ft.colors.GREEN_50 if success else ft.colors.RED_50,
            padding=10,
            border_radius=8,
        )

    def _system_bubble(self, text: str) -> ft.Container:
        """Create a system info bubble."""
        return ft.Container(
            content=ft.Text(text, size=12, color=HMSColors.TEXT_SECONDARY),
            bgcolor=HMSColors.BG_SECONDARY,
            padding=10,
            border_radius=8,
        )

    def _clear_chat(self):
        """Clear chat history for a fresh context."""
        self.chat_history.controls.clear()
        self.chat_history.controls.append(
            self._system_bubble("Chat cleared. Type a new message to begin.")
        )
        try:
            self.chat_history.update()
        except Exception:
            pass

    def _set_loading(self, loading: bool):
        """Show/hide the loading spinner."""
        self._loading.visible = loading
        self.send_button.disabled = loading
        self.input_field.disabled = loading
        try:
            self._page.update()
        except Exception:
            pass

    def _handle_mode_change(self, e):
        """Clear pending intent when mode changes."""
        self._pending_intent = None
        mode_label = "Ask / Insights" if self.mode_toggle.value == "insight" else "Command"
        self.chat_history.controls.append(
            self._system_bubble(f"Switched to {mode_label} mode.")
        )
        if self.mode_toggle.value == "command":
            self.chat_history.controls.append(
                self._system_bubble(
                    "Command mode examples:\n"
                    "• 'create order for table 5 with 2 biryani'\n"
                    "• 'finalize order, pay cash'\n"
                    "• 'add 3 coke to order'\n"
                    "• 'void order'\n"
                    "• 'new product biryani at 250 food'\n"
                    "• 'add 50 units of biryani to stock'\n"
                    "• 'show today's sales'"
                )
            )
        try:
            self.chat_history.update()
        except Exception:
            pass

    def _handle_send(self, e):
        text = self.input_field.value.strip()
        if not text:
            return

        # Allow user to cancel a pending follow-up
        if text.lower() in ("cancel", "nevermind", "stop", "reset"):
            if self._pending_intent:
                self._pending_intent = None
                self.chat_history.controls.append(self._user_bubble(text))
                self.chat_history.controls.append(
                    self._system_bubble("Command cancelled. Start a new command anytime.")
                )
                self.input_field.value = ""
                self.input_field.hint_text = "Type a command or question..."
                try:
                    self._page.update()
                except Exception:
                    pass
                return

        self.chat_history.controls.append(self._user_bubble(text))
        self.input_field.value = ""
        self._set_loading(True)

        mode = self.mode_toggle.value

        try:
            if mode == "command":
                self._handle_command(text)
            else:
                # If there's a pending intent but user is in insight mode, clear it
                self._pending_intent = None
                self._handle_insight_query(text)
        finally:
            self._set_loading(False)
            # Update hint text based on pending state
            if self._pending_intent:
                self.input_field.hint_text = "Answer the question above (or type 'cancel')..."
            else:
                self.input_field.hint_text = "Type a command or question..."

    def _handle_insight_query(self, text: str):
        """Send an insight/question query to the InsightAgent."""
        try:
            response = httpx.post(
                f"{self.API_BASE}/api/insights/query",
                json={"question": text, "user_id": self.user_id},
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                answer = data.get("answer", "") or data.get("message", "No response")
                source = data.get("source", "")
                tag = " [AI]" if source == "llm" else " [Data]" if source == "rules" else ""
                self.chat_history.controls.append(self._hms_bubble(f"{answer}{tag}"))
            else:
                self.chat_history.controls.append(
                    self._hms_bubble(f"Error {response.status_code}", success=False)
                )
        except httpx.ConnectError:
            self.chat_history.controls.append(
                self._hms_bubble("Server unavailable. Is the backend running?", success=False)
            )
        except httpx.TimeoutException:
            self.chat_history.controls.append(
                self._hms_bubble("Request timed out. Try again.", success=False)
            )
        except Exception as ex:
            self.chat_history.controls.append(
                self._hms_bubble(f"Error: {str(ex)[:80]}", success=False)
            )

    def _handle_command(self, text: str):
        """Send a command through the text-command API with follow-up support."""
        try:
            payload = {"text": text, "user_id": self.user_id}
            # If there's a pending intent from a previous follow-up, include it
            if self._pending_intent:
                payload["pending_intent"] = self._pending_intent

            response = httpx.post(
                f"{self.API_BASE}/api/voice/text-command",
                json=payload,
                timeout=15,
            )
            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "")
                intent = data.get("intent", {})
                message = data.get("message", "")

                if status == "followup":
                    # Store the incomplete intent and show the follow-up question
                    self._pending_intent = intent
                    action_label = intent.get("action", "").replace("_", " ").title()
                    parsed_by = data.get("parsed_by", "")
                    tag = " [AI]" if parsed_by == "llm" else ""
                    self.chat_history.controls.append(
                        self._hms_bubble(
                            f"[{action_label}]{tag} I need more info:\n{message}"
                        )
                    )

                elif status == "success":
                    # Clear pending intent on success
                    self._pending_intent = None
                    parsed_by = data.get("parsed_by", "")
                    tag = " [AI]" if parsed_by == "llm" else ""
                    self.chat_history.controls.append(self._hms_bubble(f"{message}{tag}"))

                elif status == "error":
                    self._pending_intent = None
                    self.chat_history.controls.append(
                        self._hms_bubble(message or "Command failed", success=False)
                    )

                elif status == "info":
                    self._pending_intent = None
                    self.chat_history.controls.append(self._hms_bubble(message))

                else:
                    self._pending_intent = None
                    self.chat_history.controls.append(
                        self._hms_bubble(message or f"Understood: {intent.get('action', '?')}")
                    )
            else:
                self._pending_intent = None
                detail = "Command failed"
                try:
                    detail = response.json().get("detail", detail)
                except Exception:
                    pass
                self.chat_history.controls.append(
                    self._hms_bubble(f"Error: {detail}", success=False)
                )
        except httpx.ConnectError:
            self.chat_history.controls.append(
                self._hms_bubble("Server unavailable. Is the backend running?", success=False)
            )
        except httpx.TimeoutException:
            self.chat_history.controls.append(
                self._hms_bubble("Request timed out. Try again.", success=False)
            )
        except Exception as ex:
            self.chat_history.controls.append(
                self._hms_bubble(f"Error: {str(ex)[:80]}", success=False)
            )
