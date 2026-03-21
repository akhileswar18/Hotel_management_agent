"""
Kitchen Display Screen

Rebuilt KDS ticket board used from the sidebar Kitchen entry.
"""

from datetime import datetime, timezone
import threading
from typing import Callable, Optional

import flet as ft
import httpx

from src.ui.components.ui_helpers import HMSColors


class OrderHistoryScreen(ft.Column):
    """Kitchen Display System board."""

    def __init__(self, page: ft.Page, user_info: Optional[dict], on_back: Callable[[], None]):
        self.page = page
        self._page = page
        self.user_info = user_info or {}
        self.on_back = on_back
        self.api_url = "http://127.0.0.1:8000"
        self._orders: list[dict] = []
        self._refresh_timer: Optional[threading.Timer] = None
        self._clock_timer: Optional[threading.Timer] = None

        self._title = ft.Text(
            "Kitchen Display System",
            font_family="Syne",
            size=18,
            weight=ft.FontWeight.W_800,
            color="#F9FAFB",
        )
        self._urgent_badge = self._status_badge("0 URGENT", "#EF4444")
        self._pending_badge = self._status_badge("0 PENDING", "#EAB308")
        self._ready_badge = self._status_badge("0 READY", "#22C55E")
        self._clock_text = ft.Text(
            datetime.now().strftime("%H:%M:%S"),
            size=22,
            font_family="DM Mono",
            color="#FFB347",
        )
        self._grid = ft.GridView(
            runs_count=4,
            spacing=14,
            run_spacing=14,
            padding=ft.padding.all(16),
            expand=True,
        )
        self.ticket_grid = self._grid
        self.urgent_stat = ft.Text("0", font_family="Syne", size=22, weight=ft.FontWeight.W_800, color="#EF4444")
        self.cooking_stat = ft.Text("0", font_family="Syne", size=22, weight=ft.FontWeight.W_800, color="#EAB308")
        self.ready_stat = ft.Text("0", font_family="Syne", size=22, weight=ft.FontWeight.W_800, color="#22C55E")
        self._stats_row = ft.Row(
            spacing=24,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        super().__init__(
            controls=[
                ft.Container(
                    expand=True,
                    bgcolor="#0A0E14",
                    content=ft.Column(
                        [
                            self._build_header(),
                            self._grid,
                            self._build_stats_bar(),
                        ],
                        spacing=0,
                        expand=True,
                    ),
                )
            ],
            spacing=0,
            expand=True,
        )

        self._load_orders()
        self._render_orders()
        self._update_clock()
        self._schedule_refresh()

    def _build_header(self) -> ft.Container:
        return ft.Container(
            height=60,
            bgcolor="#111827",
            border=ft.border.only(bottom=ft.BorderSide(2, "#1F2937")),
            padding=ft.padding.symmetric(horizontal=16),
            content=ft.Row(
                [
                    ft.Text("🍳", size=18),
                    self._title,
                    self._urgent_badge,
                    self._pending_badge,
                    self._ready_badge,
                    ft.Container(expand=True),
                    ft.Text("AUTO REFRESH: 30s", size=11, color="#4B5675", font_family="DM Mono"),
                    ft.TextButton(
                        "Refresh",
                        on_click=lambda e: self._refresh(),
                        style=ft.ButtonStyle(color="#8B96B0"),
                    ),
                    self._clock_text,
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _build_stats_bar(self) -> ft.Container:
        return ft.Container(
            height=52,
            bgcolor="#111827",
            border=ft.border.only(top=ft.BorderSide(1, "#1F2937")),
            padding=ft.padding.symmetric(horizontal=24),
            content=self._stats_row,
        )

    def _status_badge(self, text: str, color: str) -> ft.Container:
        return ft.Container(
            bgcolor=color + "20",
            border=ft.border.all(1, color),
            border_radius=6,
            padding=ft.padding.symmetric(horizontal=10, vertical=4),
            content=ft.Text(text, size=12, weight=ft.FontWeight.W_700, color=color),
        )

    def _kstat(self, num: str, label: str, color: str) -> ft.Row:
        return ft.Row(
            [
                ft.Text(num, font_family="Syne", size=22, weight=ft.FontWeight.W_800, color=color),
                ft.Text(label, size=10, color="#6B7280"),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _kstat_control(self, num_text: ft.Text, label: str) -> ft.Row:
        return ft.Row(
            [
                num_text,
                ft.Text(label, size=10, color="#6B7280"),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _vert_sep(self) -> ft.Container:
        return ft.Container(width=1, height=30, bgcolor="#1F2937")

    def _safe_update(self, control: ft.Control):
        try:
            if control.page:
                control.update()
        except Exception:
            pass

    def _show_snackbar(self, message: str, bgcolor: str):
        self.page.snack_bar = ft.SnackBar(content=ft.Text(message), bgcolor=bgcolor)
        self.page.snack_bar.open = True
        try:
            self.page.update()
        except Exception:
            pass

    def _parse_created_at(self, order: dict) -> datetime:
        raw = str(order.get("created_at") or "").strip()
        if raw:
            try:
                return datetime.fromisoformat(raw.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                pass
        return datetime.now()

    def _elapsed_parts(self, order: dict) -> tuple[float, float, int]:
        created_at = self._parse_created_at(order)
        elapsed_seconds = max((datetime.now() - created_at).total_seconds(), 0.0)
        elapsed_min = elapsed_seconds / 60.0
        return elapsed_seconds, elapsed_min, int(elapsed_seconds % 60)

    def _load_orders(self):
        try:
            with httpx.Client(base_url=self.api_url, timeout=5.0) as client:
                response = client.get("/api/sales/orders", params={"status": "finalized"})
                if response.status_code == 200:
                    all_orders = response.json()
                    self._orders = [
                        order for order in all_orders
                        if (order.get("kitchen_status") or "PENDING").upper() != "SERVED"
                    ]
                    self._orders.sort(key=lambda o: o.get("created_at", ""))
                else:
                    self._orders = []
        except Exception:
            self._orders = []

    def _compute_stats(self) -> dict:
        urgent_count = 0
        pending_count = 0
        ready_count = 0
        total_seconds = 0.0

        for order in self._orders:
            elapsed_seconds, elapsed_min, _ = self._elapsed_parts(order)
            total_seconds += elapsed_seconds
            kitchen_status = (order.get("kitchen_status") or "PENDING").upper()
            if elapsed_min > 15:
                urgent_count += 1
            if kitchen_status in {"PENDING", "COOKING"}:
                pending_count += 1
            if kitchen_status == "READY":
                ready_count += 1

        count = len(self._orders)
        avg_seconds = int(total_seconds / count) if count else 0
        return {
            "urgent_count": urgent_count,
            "pending_count": pending_count,
            "ready_count": ready_count,
            "in_progress_count": pending_count,
            "avg_prep_min": avg_seconds // 60,
            "avg_prep_sec": avg_seconds % 60,
            "orders_today": count,
        }

    def _build_kds_item(self, item: dict) -> ft.Row:
        qty = item.get("quantity", 1)
        name = item.get("item_name", "Unknown")
        return ft.Row(
            [
                ft.Container(
                    width=28,
                    height=28,
                    border_radius=6,
                    bgcolor="#2D3748",
                    alignment=ft.alignment.center,
                    content=ft.Text(
                        str(qty),
                        font_family="Syne",
                        size=14,
                        weight=ft.FontWeight.W_700,
                        color="white",
                        text_align=ft.TextAlign.CENTER,
                    ),
                ),
                ft.Text(name, size=14, weight=ft.FontWeight.W_500, color="#E5E7EB", expand=True),
            ],
            spacing=8,
        )

    def _table_display_label(self, order: dict) -> str:
        """Return a stable UI label for the order's service location."""
        raw_table = str(order.get("table_id") or "").strip()
        if not raw_table:
            return "Takeaway"
        normalized = raw_table.upper()
        if normalized in {"TAKEAWAY", "TAKE AWAY", "TOGO", "TO-GO"}:
            return "Takeaway"
        if normalized.startswith("T") and raw_table[1:].strip().isdigit():
            return f"Table {raw_table[1:].strip()}"
        return f"Table {raw_table}"

    def _kds_btn(self, label: str, bgcolor: str, color: str, on_click) -> ft.ElevatedButton:
        return ft.ElevatedButton(
            label,
            bgcolor=bgcolor,
            color=color,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=6),
                padding=ft.padding.symmetric(horizontal=8, vertical=0),
            ),
            expand=True,
            height=34,
            on_click=on_click,
        )

    def _elapsed_min(self, order: dict) -> float:
        try:
            created = datetime.fromisoformat(str(order["created_at"]).replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            return (now - created).total_seconds() / 60
        except Exception:
            return 0.0

    def _show_snack(self, msg: str, error: bool = False):
        self._page.snack_bar = ft.SnackBar(
            content=ft.Text(msg, color="white"),
            bgcolor="#EF4444" if error else "#22C55E",
            duration=2000,
        )
        self._page.snack_bar.open = True
        self._page.update()

    def _rebuild_grid(self):
        self.ticket_grid.controls = [self._build_ticket_card(order) for order in self._orders]
        if not self.ticket_grid.controls:
            self.ticket_grid.controls = [
                ft.Container(
                    bgcolor="#111827",
                    border=ft.border.all(1, "#1F2937"),
                    border_radius=12,
                    padding=24,
                    content=ft.Text("No kitchen tickets right now.", size=16, color="#8B96B0"),
                )
            ]
        urgent = sum(1 for order in self._orders if self._elapsed_min(order) > 15)
        cooking = sum(1 for order in self._orders if (order.get("kitchen_status") or "").upper() == "COOKING")
        ready = sum(1 for order in self._orders if (order.get("kitchen_status") or "").upper() == "READY")
        self.urgent_stat.value = str(urgent)
        self.cooking_stat.value = str(cooking)
        self.ready_stat.value = str(ready)
        self._urgent_badge.content.value = f"{urgent} URGENT"
        self._pending_badge.content.value = f"{sum(1 for order in self._orders if (order.get('kitchen_status') or '').upper() in {'PENDING', 'COOKING'})} PENDING"
        self._ready_badge.content.value = f"{ready} READY"
        self._safe_update(self.ticket_grid)
        self._safe_update(self.urgent_stat)
        self._safe_update(self.cooking_stat)
        self._safe_update(self.ready_stat)
        self._safe_update(self._urgent_badge)
        self._safe_update(self._pending_badge)
        self._safe_update(self._ready_badge)

    def _build_ticket_card(self, order: dict) -> ft.Container:
        elapsed_seconds, elapsed_min, elapsed_remainder = self._elapsed_parts(order)
        urgency = "late" if elapsed_min > 15 else ("warn" if elapsed_min > 5 else "ok")
        timer_str = f"{int(elapsed_min):02d}:{elapsed_remainder:02d}"

        border_colors = {
            "ok": "#2D3748",
            "warn": "#EAB30880",
            "late": "#EF444480",
        }
        header_backgrounds = {
            "ok": None,
            "warn": "#EAB30810",
            "late": "#EF444415",
        }
        timer_styles = {
            "ok": ("#16A34A20", "#22C55E"),
            "warn": ("#CA8A0420", "#EAB308"),
            "late": ("#DC262620", "#EF4444"),
        }
        timer_bg, timer_color = timer_styles[urgency]
        items = order.get("line_items", [])
        k_status = (order.get("kitchen_status") or "PENDING").upper()
        if k_status == "PENDING":
            left_btn = self._kds_btn(
                "Start",
                "#EAB308",
                "#0A0A0A",
                lambda e, oid=order["id"]: self._mark_cooking(oid),
            )
            right_btn = self._kds_btn(
                "Bump",
                "#2D3748",
                "#9CA3AF",
                lambda e, oid=order["id"]: self._bump_order(oid),
            )
        elif k_status == "COOKING":
            left_btn = self._kds_btn(
                "Ready",
                "#22C55E",
                "#0A0A0A",
                lambda e, oid=order["id"]: self._mark_ready(oid),
            )
            right_btn = self._kds_btn(
                "Bump",
                "#2D3748",
                "#9CA3AF",
                lambda e, oid=order["id"]: self._bump_order(oid),
            )
        elif k_status == "READY":
            left_btn = self._kds_btn(
                "Served",
                "#3B82F6",
                "#FFFFFF",
                lambda e, oid=order["id"]: self._mark_served(oid),
            )
            right_btn = self._kds_btn(
                "Reopen",
                "#2D3748",
                "#9CA3AF",
                lambda e, oid=order["id"]: self._mark_cooking(oid),
            )
        else:
            left_btn = self._kds_btn(
                "Ready",
                "#22C55E",
                "#0A0A0A",
                lambda e, oid=order["id"]: self._mark_ready(oid),
            )
            right_btn = self._kds_btn(
                "Bump",
                "#2D3748",
                "#9CA3AF",
                lambda e, oid=order["id"]: self._bump_order(oid),
            )

        return ft.Container(
            bgcolor="#1C2333",
            border=ft.border.all(1, border_colors[urgency]),
            border_radius=12,
            content=ft.Column(
                [
                    ft.Container(
                        bgcolor=header_backgrounds[urgency],
                        padding=ft.padding.symmetric(horizontal=14, vertical=12),
                        border=ft.border.only(bottom=ft.BorderSide(1, "#2D3748")),
                        content=ft.Row(
                            [
                                ft.Column(
                                    [
                                        ft.Text(
                                            self._table_display_label(order),
                                            font_family="Syne",
                                            size=18,
                                            weight=ft.FontWeight.W_800,
                                            color="white",
                                        ),
                                        ft.Text(
                                            f"ORD-{str(order.get('id', ''))[:8]} · {len(items)} items",
                                            size=11,
                                            color="#6B7280",
                                            font_family="DM Mono",
                                        ),
                                    ],
                                    spacing=2,
                                    tight=True,
                                ),
                                ft.Container(expand=True),
                                ft.Container(
                                    bgcolor=timer_bg,
                                    border_radius=6,
                                    padding=ft.padding.symmetric(horizontal=8, vertical=3),
                                    content=ft.Text(
                                        timer_str,
                                        font_family="DM Mono",
                                        size=14,
                                        weight=ft.FontWeight.W_500,
                                        color=timer_color,
                                    ),
                                ),
                            ]
                        ),
                    ),
                    ft.Container(
                        expand=True,
                        padding=ft.padding.all(12),
                        content=ft.Column(
                            controls=[self._build_kds_item(item) for item in order.get("line_items", [])] or [
                                ft.Text("No items", size=13, color="#6B7280")
                            ],
                            spacing=8,
                        ),
                    ),
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=10, vertical=10),
                        border=ft.border.only(top=ft.BorderSide(1, "#2D3748")),
                        content=ft.Row(
                            [
                                left_btn,
                                right_btn,
                            ],
                            spacing=8,
                        ),
                    ),
                ],
                spacing=0,
                tight=True,
            ),
        )

    def _render_orders(self):
        stats = self._compute_stats()
        self._urgent_badge.content.value = f"{stats['urgent_count']} URGENT"
        self._pending_badge.content.value = f"{stats['pending_count']} PENDING"
        self._ready_badge.content.value = f"{stats['ready_count']} READY"

        self._grid.controls.clear()
        if self._orders:
            for order in self._orders:
                self._grid.controls.append(self._build_ticket_card(order))
        else:
            self._grid.controls.append(
                ft.Container(
                    bgcolor="#111827",
                    border=ft.border.all(1, "#1F2937"),
                    border_radius=12,
                    padding=24,
                    content=ft.Text("No kitchen tickets right now.", size=16, color="#8B96B0"),
                )
            )

        self._stats_row.controls = [
            self._kstat_control(self.urgent_stat, "Urgent\n(11+ min)"),
            self._vert_sep(),
            self._kstat_control(self.cooking_stat, "In\nProgress"),
            self._vert_sep(),
            self._kstat_control(self.ready_stat, "Ready\nto Serve"),
            self._vert_sep(),
            self._kstat(
                f"{stats['avg_prep_min']:.0f}:{stats['avg_prep_sec']:02d}",
                "Avg Prep\nTime (min)",
                "#8B96B0",
            ),
            self._vert_sep(),
            self._kstat(str(stats["orders_today"]), "Orders\nToday", "#8B96B0"),
            ft.Container(expand=True),
            ft.TextButton(
                "← Back to Dashboard",
                on_click=lambda e: self._on_navigate("dashboard"),
                style=ft.ButtonStyle(color="#8B96B0"),
            ),
        ]
        self.urgent_stat.value = str(stats["urgent_count"])
        self.cooking_stat.value = str(stats["in_progress_count"])
        self.ready_stat.value = str(stats["ready_count"])

        self._safe_update(self._grid)
        self._safe_update(self._stats_row)
        self._safe_update(self._urgent_badge)
        self._safe_update(self._pending_badge)
        self._safe_update(self._ready_badge)

    def _mark_ready(self, order_id: str):
        try:
            with httpx.Client(base_url="http://127.0.0.1:8000") as client:
                resp = client.patch(
                    f"/api/sales/orders/{order_id}/kitchen-status",
                    json={"kitchen_status": "READY"},
                    timeout=5.0,
                )
            if resp.status_code == 200:
                self._load_orders()
                self._rebuild_grid()
                self._page.update()
            else:
                self._show_snack(f"Failed: {resp.status_code}", error=True)
        except Exception as ex:
            self._show_snack(f"Error: {str(ex)[:60]}", error=True)

    def _mark_cooking(self, order_id: str):
        try:
            with httpx.Client(base_url="http://127.0.0.1:8000") as client:
                resp = client.patch(
                    f"/api/sales/orders/{order_id}/kitchen-status",
                    json={"kitchen_status": "COOKING"},
                    timeout=5.0,
                )
                if resp.status_code == 200:
                    self._load_orders()
                    self._rebuild_grid()
                    self._page.update()
                else:
                    self._show_snack(f"Failed: {resp.status_code}", error=True)
        except Exception as ex:
            self._show_snack(f"Error: {str(ex)[:60]}", error=True)

    def _mark_served(self, order_id: str):
        try:
            with httpx.Client(base_url="http://127.0.0.1:8000") as client:
                resp = client.patch(
                    f"/api/sales/orders/{order_id}/kitchen-status",
                    json={"kitchen_status": "SERVED"},
                    timeout=5.0,
                )
                if resp.status_code == 200:
                    self._orders = [order for order in self._orders if order["id"] != order_id]
                    self._rebuild_grid()
                    self._page.update()
                else:
                    self._show_snack(f"Failed: {resp.status_code}", error=True)
        except Exception as ex:
            self._show_snack(f"Error: {str(ex)[:60]}", error=True)

    def _bump_order(self, order_id: str):
        for index, order in enumerate(self._orders):
            if str(order.get("id")) == str(order_id):
                bumped = self._orders.pop(index)
                self._orders.append(bumped)
                self._rebuild_grid()
                self._safe_update(self.ticket_grid)
                return

    def _refresh(self):
        self._load_orders()
        self._render_orders()
        try:
            self.page.update()
        except Exception:
            pass
        self._schedule_refresh()

    def _schedule_refresh(self):
        if self._refresh_timer:
            self._refresh_timer.cancel()
        self._refresh_timer = threading.Timer(30, self._refresh)
        self._refresh_timer.daemon = True
        self._refresh_timer.start()

    def _update_clock(self):
        self._clock_text.value = datetime.now().strftime("%H:%M:%S")
        self._safe_update(self._clock_text)
        if self._clock_timer:
            self._clock_timer.cancel()
        self._clock_timer = threading.Timer(1.0, self._update_clock)
        self._clock_timer.daemon = True
        self._clock_timer.start()

    def _on_navigate(self, route: str):
        if route == "dashboard":
            self.cleanup()
            self.on_back()

    def on_show(self):
        self._refresh()
        self._update_clock()

    def notify_external_update(self, payload: Optional[dict] = None):
        """Refresh KDS immediately when other screens complete order workflows."""
        self._load_orders()
        self._render_orders()
        try:
            self.page.update()
        except Exception:
            pass

    def cleanup(self):
        if self._refresh_timer:
            self._refresh_timer.cancel()
            self._refresh_timer = None
        if self._clock_timer:
            self._clock_timer.cancel()
            self._clock_timer = None
