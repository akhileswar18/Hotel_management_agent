"""
AI Agent Interaction Screen

Three-panel layout:
- Left: agent health/status + helper commands
- Center: ask/command/voice chat with pipeline trace and clarification chips
- Right: live EventBus activity feed from /api/audit/log
"""

from datetime import datetime
import os
import threading
from typing import Any, Callable, Dict, List, Optional

import flet as ft
import httpx

from src.ui.components.ui_helpers import (
    HMSColors,
    build_header,
    section_header,
    status_tag,
    tag_chip,
    activity_item,
)


class ChatScreen(ft.Column):
    """AI operational console with traceable command execution."""

    API_BASE = "http://127.0.0.1:8000"

    def __init__(
        self,
        page: ft.Page,
        user_role: str = "WAITER",
        user_id: str = "",
        user_info: Optional[dict] = None,
        on_kitchen_update: Optional[Callable[[dict], None]] = None,
        on_order_change: Optional[Callable[[str, dict], None]] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._page = page
        self.user_role = str(user_role or "WAITER").upper()
        self.user_id = user_id or ""
        self.user_info = user_info or {
            "username": "staff",
            "role": self.user_role,
            "user_id": self.user_id,
        }
        self._on_kitchen_update = on_kitchen_update
        self._on_order_change = on_order_change

        self.expand = True
        self.mode = "ask"  # ask | command | voice
        self._pending_intent: Optional[Dict[str, Any]] = None
        self._event_refresh_timer: Optional[threading.Timer] = None
        self._events: List[Dict[str, Any]] = []
        self._item_suggestions_cache: List[str] = []

        self._agent_status: Dict[str, str] = {
            "OrchestratorAgent": "active",
            "IntentParser": "active",
            "InsightAgent": "standby",
            "OrderAgent": "standby",
            "PaymentAgent": "standby",
            "InventoryAgent": "standby",
            "AuditAgent": "active",
            "ReportingAgent": "standby",
            "AuthAgent": "standby",
            "NotificationAgent": "standby",
            "WatchdogAgent": "active",
        }

        # Left panel controls
        self.agent_rows = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

        # Center panel controls
        self.mode_banner = ft.Text("", size=12, color=HMSColors.TEXT_SECONDARY)
        self.message_list = ft.ListView(expand=True, spacing=10, auto_scroll=True)
        self.input_field = ft.TextField(
            hint_text="Type a command or question...",
            expand=True,
            multiline=True,
            min_lines=1,
            max_lines=3,
            bgcolor=HMSColors.SURFACE2,
            border_color=HMSColors.BORDER,
            color=HMSColors.TEXT_PRIMARY,
            on_submit=self._handle_send,
        )
        self.send_btn = ft.IconButton(icon=ft.icons.SEND, on_click=self._handle_send, tooltip="Send")
        self.mic_btn = ft.IconButton(
            icon=ft.icons.MIC,
            on_click=self._handle_mic,
            tooltip="Voice input",
            icon_color=HMSColors.BLUE,
            visible=False,
        )
        self.loading = ft.ProgressRing(width=20, height=20, stroke_width=2, visible=False, color=HMSColors.ACCENT)

        # Right panel controls
        self.event_counter = ft.Text("0 events", size=11, color=HMSColors.TEXT_SECONDARY, font_family="DM Mono")
        self.event_error_counter = ft.Text("0 errors", size=11, color=HMSColors.TEXT_SECONDARY, font_family="DM Mono")
        self.event_list = ft.ListView(expand=True, spacing=0, auto_scroll=False)

        self.controls = [
            build_header("AI Agent", self.user_info),
            ft.Container(
                expand=True,
                bgcolor=HMSColors.BG,
                padding=16,
                content=ft.Row(
                    [
                        self._build_left_panel(),
                        self._build_center_panel(),
                        self._build_right_panel(),
                    ],
                    spacing=12,
                    expand=True,
                ),
            ),
        ]

        self._render_agent_rows()
        self._set_mode("ask")
        self._append_system_message(
            "AI workspace ready. Use Ask for insights, Command for operations, or Voice for hands-free flow."
        )
        self._append_system_message("Example: 2 biryani and 1 coke for table 5, cash payment")
        self._load_item_suggestions()
        self._load_events()
        self._schedule_event_refresh()

    # ---------- Layout ----------
    def _surface(self, content: ft.Control, width: Optional[int] = None, expand: int = 0) -> ft.Container:
        return ft.Container(
            width=width,
            expand=expand,
            bgcolor=HMSColors.SURFACE,
            border=ft.border.all(1, HMSColors.BORDER),
            border_radius=12,
            padding=12,
            content=content,
        )

    def _build_left_panel(self) -> ft.Container:
        examples = ft.Row(
            [
                self._example_chip("2 biryani and 1 coke for table 5, cash"),
                self._example_chip("What are today's total sales?"),
                self._example_chip("How much paneer is left in stock?"),
                self._example_chip("Finalize table 3 by card"),
            ],
            wrap=True,
            spacing=8,
        )
        content = ft.Column(
            [
                section_header("Agents"),
                self.agent_rows,
                ft.Divider(color=HMSColors.BORDER),
                section_header("LLM Provider"),
                self._provider_card(),
                ft.Divider(color=HMSColors.BORDER),
                section_header("Try a Command"),
                examples,
            ],
            spacing=10,
            expand=True,
        )
        return self._surface(content=content, width=260)

    def _build_center_panel(self) -> ft.Container:
        tabs = ft.Row(
            [
                self._mode_tab("ask", "💬 Ask"),
                self._mode_tab("command", "⚡ Command"),
                self._mode_tab("voice", "🎙 Voice"),
            ],
            spacing=8,
        )
        content = ft.Column(
            [
                tabs,
                ft.Container(
                    bgcolor=HMSColors.SURFACE2,
                    border=ft.border.all(1, HMSColors.BORDER),
                    border_radius=10,
                    padding=10,
                    content=self.mode_banner,
                ),
                ft.Container(
                    expand=True,
                    border=ft.border.all(1, HMSColors.BORDER),
                    border_radius=12,
                    bgcolor=HMSColors.BG,
                    padding=12,
                    content=self.message_list,
                ),
                ft.Container(
                    border=ft.border.only(top=ft.BorderSide(1, HMSColors.BORDER)),
                    padding=ft.padding.only(top=10),
                    content=ft.Row(
                        [self.input_field, self.loading, self.mic_btn, self.send_btn],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.END,
                    ),
                ),
            ],
            spacing=10,
            expand=True,
        )
        return self._surface(content=content, expand=1)

    def _build_right_panel(self) -> ft.Container:
        footer = ft.Row(
            [
                self.event_counter,
                ft.Container(expand=True),
                self.event_error_counter,
            ],
            spacing=8,
        )
        content = ft.Column(
            [
                section_header("EventBus Live Log", status_tag("LIVE", HMSColors.GREEN)),
                self.event_list,
                ft.Divider(color=HMSColors.BORDER),
                footer,
            ],
            spacing=8,
            expand=True,
        )
        return self._surface(content=content, width=280)

    # ---------- Agent panel ----------
    def _agent_badge_color(self, label: str) -> str:
        if label == "CORE":
            return HMSColors.ACCENT
        if label == "LLM":
            return HMSColors.BLUE
        if label == "READY":
            return HMSColors.GREEN
        return HMSColors.TEXT_MUTED

    def _status_dot(self, state: str) -> ft.Container:
        color = HMSColors.GREEN if state == "active" else HMSColors.YELLOW if state == "standby" else HMSColors.SURFACE3
        return ft.Container(width=8, height=8, bgcolor=color, border_radius=8)

    def _agent_row(self, name: str, group: str, state: str) -> ft.Container:
        return ft.Container(
            padding=8,
            border_radius=8,
            bgcolor=HMSColors.SURFACE2 if state == "active" else "00000000",
            border=ft.border.all(1, HMSColors.ACCENT + "44" if state == "active" else HMSColors.BORDER),
            content=ft.Row(
                [
                    self._status_dot(state),
                    ft.Text(name, size=12, color=HMSColors.TEXT_PRIMARY, expand=True),
                    status_tag(group, self._agent_badge_color(group)),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _render_agent_rows(self):
        mapping = [
            ("OrchestratorAgent", "CORE"),
            ("IntentParser", "CORE"),
            ("OrderAgent", "CORE"),
            ("PaymentAgent", "CORE"),
            ("InventoryAgent", "CORE"),
            ("AuditAgent", "CORE"),
            ("InsightAgent", "LLM"),
            ("ReportingAgent", "READY"),
            ("AuthAgent", "READY"),
            ("NotificationAgent", "STANDBY"),
            ("WatchdogAgent", "READY"),
        ]
        self.agent_rows.controls.clear()
        for name, group in mapping:
            self.agent_rows.controls.append(self._agent_row(name, group, self._agent_status.get(name, "standby")))
        self._safe_update(self.agent_rows)

    def _provider_card(self) -> ft.Container:
        provider_name = os.environ.get("LLM_PROVIDER", "openrouter").title()
        model_name = os.environ.get("LLM_MODEL", "meta-llama/llama-3.3-70b-instruct")
        return ft.Container(
            bgcolor=HMSColors.SURFACE2,
            border=ft.border.all(1, HMSColors.BORDER),
            border_radius=10,
            padding=10,
            content=ft.Column(
                [
                    ft.Text(f"Provider: {provider_name}", size=12, color=HMSColors.TEXT_PRIMARY),
                    ft.Text(f"Model: {model_name}", size=11, color=HMSColors.TEXT_SECONDARY, font_family="DM Mono"),
                    ft.Text("Fallback: Rules enabled", size=11, color=HMSColors.TEXT_SECONDARY),
                    ft.Text("Offline-ready", size=11, color=HMSColors.GREEN),
                ],
                spacing=3,
                tight=True,
            ),
        )

    def _example_chip(self, text: str) -> ft.Container:
        return ft.Container(
            content=tag_chip(text, HMSColors.SURFACE2, HMSColors.TEXT_SECONDARY),
            on_click=lambda e, t=text: self._fill_input(t),
        )

    def _fill_input(self, text: str):
        self.input_field.value = text
        self._safe_update(self.input_field)

    # ---------- Mode controls ----------
    def _mode_tab(self, mode: str, label: str) -> ft.Container:
        active = self.mode == mode
        return ft.Container(
            height=36,
            border_radius=8,
            bgcolor=HMSColors.ACCENT if active else HMSColors.SURFACE2,
            border=ft.border.all(1, HMSColors.ACCENT + "60" if active else HMSColors.BORDER),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            content=ft.Text(label, size=12, color=HMSColors.TEXT_LIGHT if active else HMSColors.TEXT_SECONDARY),
            on_click=lambda e, m=mode: self._set_mode(m),
        )

    def _set_mode(self, mode: str):
        self.mode = mode
        self.mic_btn.visible = mode == "voice"
        if mode == "ask":
            self.mode_banner.value = "Ask anything about sales, stock, or operations."
        elif mode == "command":
            self.mode_banner.value = "Give a direct instruction and I will execute it."
        else:
            self.mode_banner.value = "Voice mode active. Use mic or type your instruction."
        # Rebuild tabs to update active state.
        center = self.controls[1].content.controls[1].content  # main row -> center panel container -> content column
        center.controls[0] = ft.Row(
            [
                self._mode_tab("ask", "💬 Ask"),
                self._mode_tab("command", "⚡ Command"),
                self._mode_tab("voice", "🎙 Voice"),
            ],
            spacing=8,
        )
        self._safe_page_update()

    def _handle_mic(self, e):
        self._append_system_message("Voice capture is simulated in web mode. Type command text and send.")

    # ---------- Messaging ----------
    def _append_user_message(self, text: str):
        self.message_list.controls.append(
            ft.Row(
                [
                    ft.Container(expand=True),
                    ft.Container(
                        bgcolor=HMSColors.ACCENT + "20",
                        border=ft.border.all(1, HMSColors.ACCENT + "55"),
                        border_radius=12,
                        padding=12,
                        width=480,
                        content=ft.Text(text, color=HMSColors.TEXT_PRIMARY),
                    ),
                ]
            )
        )

    def _append_system_message(self, text: str):
        self.message_list.controls.append(
            ft.Row(
                [
                    ft.Container(
                        bgcolor=HMSColors.SURFACE,
                        border=ft.border.all(1, HMSColors.BORDER),
                        border_radius=12,
                        padding=12,
                        width=520,
                        content=ft.Text(text, color=HMSColors.TEXT_SECONDARY, size=12),
                    ),
                    ft.Container(expand=True),
                ]
            )
        )
        self._safe_update(self.message_list)

    def _append_agent_message(
        self,
        text: str,
        ok: bool = True,
        trace_steps: Optional[List[Dict[str, str]]] = None,
        chips: Optional[List[str]] = None,
    ):
        bubble = ft.Container(
            bgcolor=HMSColors.SURFACE if ok else HMSColors.RED_DIM,
            border=ft.border.all(1, HMSColors.BORDER if ok else HMSColors.RED + "66"),
            border_radius=12,
            padding=12,
            width=540,
            content=ft.Text(text, color=HMSColors.TEXT_PRIMARY if ok else HMSColors.RED),
        )
        controls: List[ft.Control] = [bubble]

        if trace_steps:
            rows = []
            for step in trace_steps:
                color = step.get("color", HMSColors.ACCENT)
                rows.append(
                    ft.Row(
                        [
                            ft.Text("✓", color=color, size=12),
                            ft.Text(step.get("label", "Step"), size=12, color=HMSColors.TEXT_PRIMARY, width=180),
                            status_tag(step.get("engine", "Rules"), HMSColors.BLUE if step.get("engine") == "LLM" else HMSColors.TEXT_MUTED),
                            ft.Text(step.get("detail", ""), size=11, color=HMSColors.TEXT_SECONDARY, expand=True),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    )
                )
            controls.append(
                ft.ExpansionTile(
                    title=ft.Text("Pipeline Trace", size=12, color=HMSColors.TEXT_SECONDARY),
                    maintain_state=True,
                    controls=[ft.Container(content=ft.Column(rows, spacing=8), padding=8)],
                )
            )

        if chips:
            chip_row = ft.Row(
                [ft.Container(content=tag_chip(ch, HMSColors.SURFACE2, HMSColors.TEXT_PRIMARY), on_click=lambda e, c=ch: self._fill_input(c)) for ch in chips],
                spacing=8,
                wrap=True,
            )
            controls.append(ft.Container(content=chip_row, padding=ft.padding.only(top=6)))

        self.message_list.controls.append(
            ft.Row(
                [
                    ft.Column(controls, spacing=6, tight=True),
                    ft.Container(expand=True),
                ],
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
        )
        self._safe_update(self.message_list)

    def _set_loading(self, loading: bool):
        self.loading.visible = loading
        self.send_btn.disabled = loading
        self.input_field.disabled = loading
        self.mic_btn.disabled = loading
        self._safe_page_update()

    def _handle_send(self, e):
        text = (self.input_field.value or "").strip()
        if not text:
            return

        if text.lower() in ("cancel", "stop", "reset", "nevermind"):
            self._pending_intent = None
            self.input_field.value = ""
            self._append_system_message("Pending command cleared. You can start a new request.")
            return

        self._append_user_message(text)
        self.input_field.value = ""
        self._set_loading(True)
        try:
            if self.mode == "ask":
                self._handle_insight(text)
            else:
                self._handle_command(text)
        finally:
            self._set_loading(False)
            self._safe_page_update()

    def _handle_insight(self, text: str):
        try:
            response = httpx.post(
                f"{self.API_BASE}/api/insights/query",
                json={"question": text, "user_id": self.user_id},
                timeout=12.0,
            )
            if response.status_code == 200:
                data = response.json()
                answer = data.get("answer", "") or data.get("message", "No response")
                source = str(data.get("source", "rules")).upper()
                trace = self._build_trace_steps("insight", "success", {"engine": source})
                self._append_agent_message(answer, ok=True, trace_steps=trace)
                self._mark_agent_activity(["InsightAgent", "AuditAgent"])
            else:
                self._append_agent_message(f"Insight error {response.status_code}", ok=False)
        except Exception as ex:
            self._append_agent_message(f"Insight request failed: {str(ex)[:120]}", ok=False)

    def _handle_command(self, text: str):
        payload: Dict[str, Any] = {"text": text, "user_id": self.user_id}
        if self._pending_intent:
            payload["pending_intent"] = self._pending_intent

        try:
            response = httpx.post(
                f"{self.API_BASE}/api/voice/text-command",
                json=payload,
                timeout=20.0,
            )
            if response.status_code != 200:
                self._pending_intent = None
                detail = "Command failed"
                try:
                    detail = response.json().get("detail", detail)
                except Exception:
                    pass
                self._append_agent_message(f"Error: {detail}", ok=False)
                return

            data = response.json()
            status = str(data.get("status", "")).lower()
            message = str(data.get("message", "Done"))
            intent = data.get("intent", {}) or {}
            parsed_by = str(data.get("parsed_by", "rules")).upper()

            if status == "followup":
                self._pending_intent = intent
                chips = self._build_followup_chips(data.get("missing_fields", []), intent)
                trace = self._build_trace_steps("command", "followup", {"engine": parsed_by, "action": intent.get("action", "unknown")})
                self._append_agent_message(message, ok=True, trace_steps=trace, chips=chips)
                self._mark_agent_activity(["IntentParser", "OrchestratorAgent"])
            elif status == "success":
                self._pending_intent = None
                trace = self._build_trace_steps("command", "success", {"engine": parsed_by, "action": intent.get("action", "unknown")})
                self._append_agent_message(message, ok=True, trace_steps=trace)
                self._mark_agent_activity(["OrchestratorAgent", "OrderAgent", "PaymentAgent", "AuditAgent"])
                event_type = self._map_action_to_order_event(intent.get("action"))
                if event_type:
                    self._emit_order_change(event_type, data)
                self._emit_kitchen_update(data)
            elif status == "error":
                self._pending_intent = None
                trace = self._build_trace_steps("command", "error", {"engine": parsed_by, "action": intent.get("action", "unknown")})
                self._append_agent_message(message or "Command failed", ok=False, trace_steps=trace)
                self._mark_agent_activity(["OrchestratorAgent", "AuditAgent"])
            else:
                self._pending_intent = None
                trace = self._build_trace_steps("command", "success", {"engine": parsed_by, "action": intent.get("action", "unknown")})
                self._append_agent_message(message, ok=True, trace_steps=trace)
                self._mark_agent_activity(["OrchestratorAgent", "AuditAgent"])
        except Exception as ex:
            self._pending_intent = None
            self._append_agent_message(f"Command request failed: {str(ex)[:120]}", ok=False)

    def _emit_kitchen_update(self, payload: Optional[dict] = None):
        """Forward order workflow updates so KDS can refresh immediately."""
        if not self._on_kitchen_update:
            return
        try:
            self._on_kitchen_update(payload or {})
        except Exception:
            pass

    def _emit_order_change(self, event_type: str, payload: Optional[dict] = None):
        if not self._on_order_change:
            return
        try:
            self._on_order_change(event_type, payload or {})
        except Exception:
            pass

    @staticmethod
    def _map_action_to_order_event(action: Optional[str]) -> Optional[str]:
        action_name = str(action or "").lower()
        mapping = {
            "create_order": "order.created",
            "finalize_order": "order.finalized",
            "void_order": "order.voided",
            "add_item": "order.updated",
        }
        return mapping.get(action_name)

    def _build_followup_chips(self, missing_fields: List[str], intent: Dict[str, Any]) -> List[str]:
        chips: List[str] = []
        missing = {str(x).lower() for x in missing_fields}
        if "payment_method" in missing:
            chips.extend(["cash", "card", "voucher"])
        if "table_id" in missing:
            chips.extend(["table 1", "table 2", "table 3"])
        if "quantity" in missing:
            chips.extend(["1", "2", "3"])
        if "item_name" in missing or "items" in missing:
            for name in self._item_suggestions_cache[:3]:
                chips.append(name)
        if "reason" in missing:
            chips.extend(["customer request", "duplicate order", "wrong table"])
        # Ensure deterministic and compact.
        uniq: List[str] = []
        for c in chips:
            if c not in uniq:
                uniq.append(c)
        return uniq[:6]

    def _build_trace_steps(self, mode: str, status: str, meta: Dict[str, Any]) -> List[Dict[str, str]]:
        engine = str(meta.get("engine", "RULES")).upper()
        action = str(meta.get("action", "command")).replace("_", " ").title()
        steps: List[Dict[str, str]] = []

        if mode == "voice":
            steps.append({"label": "STT", "engine": "Rules", "detail": "Voice to text", "color": HMSColors.BLUE})
        steps.append({"label": "Intent Parser", "engine": "LLM" if engine == "LLM" else "Rules", "detail": "Intent extracted", "color": HMSColors.ACCENT})
        steps.append({"label": "Orchestrator", "engine": "Rules", "detail": action, "color": HMSColors.ACCENT})
        if status == "followup":
            steps.append({"label": "Clarification", "engine": "Rules", "detail": "Additional input required", "color": HMSColors.YELLOW})
        elif status == "error":
            steps.append({"label": "Execution", "engine": "Rules", "detail": "Command failed", "color": HMSColors.RED})
        else:
            steps.append({"label": "Execution", "engine": "Rules", "detail": "Completed successfully", "color": HMSColors.GREEN})
        steps.append({"label": "AuditAgent", "engine": "Rules", "detail": "Event recorded", "color": "#8B5CF6"})
        return steps

    def _mark_agent_activity(self, active_agents: List[str]):
        for key in list(self._agent_status.keys()):
            if key in ("OrchestratorAgent", "IntentParser", "AuditAgent", "WatchdogAgent"):
                self._agent_status[key] = "active"
            else:
                self._agent_status[key] = "standby"
        for name in active_agents:
            self._agent_status[name] = "active"
        self._render_agent_rows()

    # ---------- Event log ----------
    def _event_color(self, event_type: str) -> str:
        et = event_type.lower()
        if et.startswith("workflow."):
            return HMSColors.ACCENT
        if et.startswith("order."):
            return HMSColors.GREEN
        if et.startswith("payment."):
            return HMSColors.BLUE
        if et.startswith("inventory."):
            return HMSColors.YELLOW
        if et.startswith("audit."):
            return "#8B5CF6"
        if et.startswith("insight."):
            return "#EC4899"
        if et.startswith("error."):
            return HMSColors.RED
        return HMSColors.TEXT_MUTED

    def _load_events(self):
        try:
            with httpx.Client(timeout=4.0) as client:
                response = client.get(f"{self.API_BASE}/api/audit/log", params={"limit": 50, "offset": 0})
                if response.status_code == 200:
                    self._events = response.json()
                else:
                    self._events = []
        except Exception:
            self._events = []
        self._render_events()

    def _render_events(self):
        self.event_list.controls.clear()
        error_count = 0
        for evt in self._events:
            etype = str(evt.get("event_type", "audit.event"))
            if etype.startswith("error."):
                error_count += 1
            ts_raw = str(evt.get("created_at", ""))
            ts = ts_raw[11:19] if "T" in ts_raw else ts_raw[:8]
            self.event_list.controls.append(
                activity_item(
                    etype,
                    str(evt.get("description", "")) or etype,
                    ts,
                    self._event_color(etype),
                )
            )
        self.event_counter.value = f"{len(self._events)} events"
        self.event_error_counter.value = f"{error_count} errors"
        self._safe_update(self.event_list)
        self._safe_update(self.event_counter)
        self._safe_update(self.event_error_counter)

    def _schedule_event_refresh(self):
        def _tick():
            self._load_events()
            self._schedule_event_refresh()

        timer = threading.Timer(30.0, _tick)
        timer.daemon = True
        timer.start()
        self._event_refresh_timer = timer

    # ---------- Helpers ----------
    def _load_item_suggestions(self):
        try:
            with httpx.Client(timeout=4.0) as client:
                response = client.get(f"{self.API_BASE}/api/inventory/items")
                if response.status_code == 200:
                    rows = response.json()
                    self._item_suggestions_cache = [str(r.get("name", "")).strip() for r in rows if str(r.get("name", "")).strip()]
        except Exception:
            self._item_suggestions_cache = []

    def _safe_update(self, control: Optional[ft.Control]):
        try:
            if control and getattr(control, "page", None):
                control.update()
        except Exception:
            pass

    def _safe_page_update(self):
        try:
            self._page.update()
        except Exception:
            pass

    def cleanup(self):
        if self._event_refresh_timer:
            self._event_refresh_timer.cancel()
            self._event_refresh_timer = None
