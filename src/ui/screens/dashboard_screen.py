"""
Dashboard Screen

Target-style operational dashboard with greeting, KPI cards, quick actions,
active orders, recent activity, and payment breakdown.
"""

from datetime import date
from typing import Callable, Dict, List

import flet as ft
import httpx

from src.ui.components.ui_helpers import (
    HMSColors,
    build_header,
    stat_card,
    status_tag,
    activity_item,
    section_header,
)


class DashboardScreen(ft.Column):
    """Operational dashboard for shift awareness."""

    NAME_MAP = {
        "waiter": "Suresh",
        "cashier": "Rajesh",
        "manager": "Rajesh Kumar",
        "clerk": "Clerk",
        "kitchen": "Kitchen",
        "admin": "Admin",
    }

    def __init__(self, page: ft.Page, user_info: dict, on_nav: Callable[[str], None]):
        self._page = page
        self.user_info = user_info or {}
        self.on_nav = on_nav
        self.api_base = "http://127.0.0.1:8000"

        self.display_name = self._resolve_display_name()
        self.header_user = dict(self.user_info)
        self.header_user["username"] = self.display_name

        self._summary: Dict[str, object] = {
            "revenue": "—",
            "orders_today": "—",
            "low_stock": "—",
            "avg_order": "—",
        }
        self._active_orders: List[dict] = []
        self._activity: List[dict] = []
        self._payment_breakdown: Dict[str, float] = {"cash": 0.0, "card": 0.0, "voucher": 0.0}

        self.date_text = ft.Text(
            date.today().strftime("%A, %d %B %Y"),
            size=14,
            color=HMSColors.TEXT_SECONDARY,
        )
        self.greeting = ft.Text(
            f"Good morning, {self.display_name} 👋",
            size=42,
            weight=ft.FontWeight.W_800,
            color=HMSColors.TEXT_LIGHT,
            font_family="Syne",
        )
        self.subtitle = ft.Text(
            "Here's what's happening at your hotel today.",
            size=16,
            color=HMSColors.TEXT_SECONDARY,
        )

        self.stats_row = ft.Row(spacing=12)
        self.quick_actions = ft.Row(spacing=12)
        self.active_orders_list = ft.Column(spacing=8)
        self.activity_list = ft.Column(spacing=0)
        self.payment_rows = ft.Column(spacing=10)

        super().__init__(
            controls=[
                build_header("Dashboard", self.header_user),
                ft.Container(
                    expand=True,
                    bgcolor=HMSColors.BG,
                    padding=16,
                    content=ft.Row(
                        [
                            ft.Container(
                                expand=3,
                                content=ft.Column(
                                    [
                                        self.date_text,
                                        self.greeting,
                                        self.subtitle,
                                        ft.Row(
                                            [
                                                ft.Container(expand=True),
                                                self._tiny_button("View Reports", "reports", HMSColors.BLUE),
                                                self._tiny_button("+ New Order", "pos", HMSColors.ACCENT),
                                            ],
                                            spacing=8,
                                        ),
                                        self.stats_row,
                                        self._section_card("Quick Actions", self.quick_actions, fixed_height=170),
                                        self._section_card("Active Orders", self.active_orders_list, fixed_height=440),
                                    ],
                                    spacing=12,
                                    expand=True,
                                ),
                            ),
                            ft.Container(
                                expand=1,
                                content=ft.Column(
                                    [
                                        self._section_card("Recent Activity", self.activity_list, fixed_height=420, live=True),
                                        self._section_card("Payment Breakdown", self.payment_rows, fixed_height=260),
                                    ],
                                    spacing=12,
                                ),
                            ),
                        ],
                        spacing=14,
                        expand=True,
                    ),
                ),
            ],
            spacing=0,
            expand=True,
        )

        self._build_quick_actions()
        self._load_data()
        self._render()

    def _resolve_display_name(self) -> str:
        username = str(self.user_info.get("username", "")).strip()
        full_name = str(self.user_info.get("full_name", "")).strip()
        if full_name:
            return full_name
        if not username:
            return "Rajesh"
        mapped = self.NAME_MAP.get(username.lower())
        if mapped:
            return mapped
        return username.replace("_", " ").title()

    def _safe_update(self, control: ft.Control):
        try:
            if control.page:
                control.update()
        except Exception:
            pass

    def _tiny_button(self, text: str, route: str, color: str) -> ft.Container:
        return ft.Container(
            bgcolor=color,
            border_radius=10,
            padding=ft.padding.symmetric(horizontal=14, vertical=8),
            on_click=lambda e, r=route: self.on_nav(r),
            content=ft.Text(text, size=12, color=HMSColors.TEXT_LIGHT, weight=ft.FontWeight.W_600),
        )

    def _section_card(self, title: str, body: ft.Control, fixed_height: int, live: bool = False) -> ft.Container:
        action = status_tag("LIVE", HMSColors.BLUE) if live else None
        return ft.Container(
            height=fixed_height,
            bgcolor=HMSColors.SURFACE,
            border=ft.border.all(1, HMSColors.BORDER),
            border_radius=14,
            padding=12,
            content=ft.Column(
                [
                    section_header(title, action),
                    ft.Divider(color=HMSColors.BORDER),
                    ft.Container(expand=True, content=body),
                ],
                spacing=8,
                expand=True,
            ),
        )

    def _quick_action_card(self, icon: str, title: str, subtitle: str, nav_key: str, color: str) -> ft.Container:
        return ft.Container(
            expand=1,
            height=112,
            bgcolor=HMSColors.SURFACE2,
            border=ft.border.all(1, HMSColors.BORDER),
            border_radius=12,
            padding=12,
            on_click=lambda e, key=nav_key: self.on_nav(key),
            content=ft.Column(
                [
                    ft.Container(
                        width=36,
                        height=36,
                        border_radius=8,
                        bgcolor=color + "25",
                        alignment=ft.alignment.center,
                        content=ft.Text(icon, size=16),
                    ),
                    ft.Text(title, size=14, weight=ft.FontWeight.W_700, color=HMSColors.TEXT_PRIMARY),
                    ft.Text(subtitle, size=12, color=HMSColors.TEXT_SECONDARY),
                ],
                spacing=6,
                tight=True,
            ),
        )

    def _build_quick_actions(self):
        self.quick_actions.controls = [
            self._quick_action_card("🛒", "New Order", "Start a table order", "pos", HMSColors.ACCENT),
            self._quick_action_card("📦", "Add Stock", "Record stock-in", "inventory", HMSColors.BLUE),
            self._quick_action_card("📊", "Daily Report", "Sales and inventory", "reports", HMSColors.GREEN),
            self._quick_action_card("🍳", "Kitchen View", "Open KDS board", "kitchen", HMSColors.YELLOW),
        ]

    def _load_data(self):
        today = date.today().isoformat()
        try:
            with httpx.Client(timeout=4.0) as client:
                sales = client.get(f"{self.api_base}/api/reports/daily-sales", params={"date": today})
                if sales.status_code == 200:
                    data = sales.json()
                    self._summary["revenue"] = f"₹{float(data.get('total_sales', 0.0)):,.0f}"
                    self._summary["orders_today"] = str(data.get("transactions_count", 0))
                    self._summary["avg_order"] = f"₹{float(data.get('avg_order_value', 0.0)):,.0f}"
                    pb = data.get("payment_breakdown", {}) or {}
                    self._payment_breakdown = {
                        "cash": float(pb.get("cash", 0.0)),
                        "card": float(pb.get("card", 0.0)),
                        "voucher": float(pb.get("voucher", 0.0)),
                    }

                items = client.get(f"{self.api_base}/api/inventory/items")
                if items.status_code == 200:
                    all_items = items.json()
                    low = [x for x in all_items if int(x.get("stock_on_hand", 0)) < int(x.get("reorder_level", 0))]
                    self._summary["low_stock"] = str(len(low))

                orders = client.get(f"{self.api_base}/api/sales/orders", params={"status": "draft"})
                if orders.status_code == 200:
                    self._active_orders = orders.json()[:8]

                activity = client.get(f"{self.api_base}/api/audit/log", params={"limit": 12, "offset": 0})
                if activity.status_code == 200:
                    self._activity = activity.json()
        except Exception:
            pass

    def _render(self):
        self.stats_row.controls = [
            ft.Container(expand=1, content=stat_card("$", str(self._summary["revenue"]), "Today's Revenue", HMSColors.GREEN)),
            ft.Container(expand=1, content=stat_card("✓", str(self._summary["orders_today"]), "Orders Today", HMSColors.ACCENT)),
            ft.Container(expand=1, content=stat_card("⬡", str(self._summary["low_stock"]), "Low Stock Alerts", HMSColors.YELLOW)),
            ft.Container(expand=1, content=stat_card("▣", str(self._summary["avg_order"]), "Avg Order Value", HMSColors.BLUE)),
        ]

        self.active_orders_list.controls.clear()
        if not self._active_orders:
            self.active_orders_list.controls.append(
                ft.Text("No active orders right now.", color=HMSColors.TEXT_SECONDARY, size=13)
            )
        else:
            for order in self._active_orders:
                kstatus = (order.get("kitchen_status") or "PENDING").upper()
                status_color = HMSColors.YELLOW
                if kstatus in ("READY", "SERVED"):
                    status_color = HMSColors.GREEN
                elif kstatus == "LATE":
                    status_color = HMSColors.RED
                row = ft.Container(
                    padding=10,
                    border_radius=10,
                    bgcolor=HMSColors.SURFACE2,
                    border=ft.border.all(1, HMSColors.BORDER),
                    content=ft.Row(
                        [
                            ft.Container(
                                width=38,
                                height=38,
                                border_radius=10,
                                bgcolor=HMSColors.BG,
                                alignment=ft.alignment.center,
                                content=ft.Text(f"T{order.get('table_id', '?')}", color=HMSColors.ACCENT, weight=ft.FontWeight.W_700),
                            ),
                            ft.Column(
                                [
                                    ft.Text(
                                        ", ".join(
                                            [f"{i.get('item_name', '')} x{i.get('quantity', 1)}" for i in order.get("line_items", [])][:3]
                                        ) or f"Order {str(order.get('id', ''))[:8]}",
                                        size=13,
                                        color=HMSColors.TEXT_PRIMARY,
                                    ),
                                    ft.Text(
                                        f"{len(order.get('line_items', []))} items",
                                        size=11,
                                        color=HMSColors.TEXT_SECONDARY,
                                    ),
                                ],
                                spacing=2,
                                expand=True,
                                tight=True,
                            ),
                            ft.Text(
                                f"₹{float(order.get('total_amount', 0.0)):.0f}",
                                size=14,
                                color=HMSColors.ACCENT2,
                                font_family="DM Mono",
                                weight=ft.FontWeight.W_700,
                            ),
                            status_tag(kstatus, status_color),
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
                self.active_orders_list.controls.append(row)

        self.activity_list.controls.clear()
        if not self._activity:
            self.activity_list.controls.append(ft.Text("No recent activity", color=HMSColors.TEXT_SECONDARY))
        else:
            for evt in self._activity[:10]:
                etype = str(evt.get("event_type", "audit.event"))
                ts = str(evt.get("created_at", ""))[11:16] if evt.get("created_at") else "--:--"
                color = HMSColors.ACCENT
                if etype.startswith("order."):
                    color = HMSColors.GREEN
                elif etype.startswith("payment."):
                    color = HMSColors.BLUE
                elif etype.startswith("inventory."):
                    color = HMSColors.YELLOW
                elif etype.startswith("error."):
                    color = HMSColors.RED
                self.activity_list.controls.append(
                    activity_item(etype, str(evt.get("description", "Activity")), ts, color)
                )

        total = max(
            self._payment_breakdown["cash"] + self._payment_breakdown["card"] + self._payment_breakdown["voucher"],
            1.0,
        )
        self.payment_rows.controls.clear()
        for label, key, color in [
            ("Cash", "cash", HMSColors.GREEN),
            ("Card", "card", HMSColors.BLUE),
            ("Voucher", "voucher", HMSColors.ACCENT),
        ]:
            amt = float(self._payment_breakdown.get(key, 0.0))
            pct = (amt / total) * 100.0
            self.payment_rows.controls.append(
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(label, size=13, color=HMSColors.TEXT_SECONDARY),
                                ft.Container(expand=True),
                                ft.Text(f"₹{amt:,.0f} ({pct:.0f}%)", size=12, color=HMSColors.TEXT_PRIMARY, font_family="DM Mono"),
                            ]
                        ),
                        ft.Stack(
                            [
                                ft.Container(height=5, bgcolor=HMSColors.SURFACE3, border_radius=5, width=320),
                                ft.Container(height=5, bgcolor=color, border_radius=5, width=max(8, int(320 * (pct / 100.0)))),
                            ],
                            width=320,
                            height=5,
                        ),
                    ],
                    spacing=5,
                    tight=True,
                )
            )

        self._safe_update(self.stats_row)
        self._safe_update(self.quick_actions)
        self._safe_update(self.active_orders_list)
        self._safe_update(self.activity_list)
        self._safe_update(self.payment_rows)
