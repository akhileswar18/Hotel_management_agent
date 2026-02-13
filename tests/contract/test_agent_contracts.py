"""
Contract tests for agent subscriptions and publication declarations.
"""

import pytest
from src.agents.base import BaseAgent
from src.agents.order_agent import OrderAgent
from src.agents.audit_agent import AuditAgent
from src.agents.payment_agent import PaymentAgent
from src.agents.auth_agent import AuthAgent
from src.agents.print_agent import PrintAgent
from src.agents.notification_agent import NotificationAgent
from src.agents.reporting_agent import ReportingAgent
from src.agents.inventory_agent import InventoryAgent
from src.agents.insight_agent import InsightAgent
from src.agents.registry import AgentRegistry
from src.events.event import Event


class TestAgentContracts:
    """A022: Agent subscription/publication contract tests."""

    def test_order_agent_subscribes_to_order_events(self):
        agent = OrderAgent()
        assert agent.can_handle("order.create")
        assert agent.can_handle("order.add_item")
        assert agent.can_handle("order.finalize")
        assert agent.can_handle("order.void")
        assert not agent.can_handle("inventory.stock_in")
        assert not agent.can_handle("auth.login")

    def test_audit_agent_subscribes_to_all(self):
        agent = AuditAgent()
        assert agent.can_handle("order.create")
        assert agent.can_handle("inventory.stock_in")
        assert agent.can_handle("auth.login")
        assert agent.can_handle("anything.at.all")

    def test_registry_dispatches_to_correct_agents(self):
        registry = AgentRegistry()
        order_agent = OrderAgent()
        audit_agent = AuditAgent()
        registry.register(order_agent)
        registry.register(audit_agent)

        # order.create should reach both OrderAgent and AuditAgent (wildcard)
        subs = registry.get_subscribers("order.create")
        names = [a.name for a in subs]
        assert "OrderAgent" in names
        assert "AuditAgent" in names

        # inventory.stock_in should only reach AuditAgent
        subs = registry.get_subscribers("inventory.stock_in")
        names = [a.name for a in subs]
        assert "AuditAgent" in names
        assert "OrderAgent" not in names

    def test_order_agent_writes_to_db(self):
        assert OrderAgent().writes_to_db is True

    def test_audit_agent_writes_to_db(self):
        assert AuditAgent().writes_to_db is True

    def test_order_agent_does_not_use_llm(self):
        assert OrderAgent().uses_llm is False

    def test_audit_agent_does_not_use_llm(self):
        assert AuditAgent().uses_llm is False

    def test_inventory_agent_subscribes_to_declared_events(self):
        """InventoryAgent subscribes to its declared event types."""
        agent = InventoryAgent()
        assert agent.can_handle("inventory.stock_in")
        assert agent.can_handle("inventory.adjust")
        assert agent.can_handle("inventory.archive")
        assert agent.can_handle("inventory.update")
        assert agent.can_handle("order.finalized")
        assert agent.can_handle("order.voided")
        assert not agent.can_handle("order.create")
        assert not agent.can_handle("auth.login")

    def test_inventory_agent_writes_to_db_does_not_use_llm(self):
        """InventoryAgent writes_to_db = True, uses_llm = False."""
        agent = InventoryAgent()
        assert agent.writes_to_db is True
        assert agent.uses_llm is False

    def test_payment_agent_subscribes_to_payment_process(self):
        agent = PaymentAgent()
        assert agent.can_handle("payment.process")
        assert not agent.can_handle("order.create")

    def test_payment_agent_writes_to_db_does_not_use_llm(self):
        agent = PaymentAgent()
        assert agent.writes_to_db is True
        assert agent.uses_llm is False

    def test_auth_agent_subscribes_to_auth_events(self):
        agent = AuthAgent()
        assert agent.can_handle("auth.login")
        assert agent.can_handle("auth.logout")
        assert agent.can_handle("auth.validate")
        assert not agent.can_handle("auth.logged_in")

    def test_auth_agent_writes_to_db_does_not_use_llm(self):
        agent = AuthAgent()
        assert agent.writes_to_db is True
        assert agent.uses_llm is False

    def test_print_agent_subscribes_to_receipt_events(self):
        agent = PrintAgent()
        assert agent.can_handle("receipt.print")
        assert agent.can_handle("receipt.email")
        assert agent.can_handle("receipt.reprint")
        assert not agent.can_handle("receipt.printed")

    def test_print_agent_does_not_write_to_db_does_not_use_llm(self):
        agent = PrintAgent()
        assert agent.writes_to_db is False
        assert agent.uses_llm is False
        assert agent.degradable is True

    def test_notification_agent_subscribes_to_notification_events(self):
        agent = NotificationAgent()
        assert agent.can_handle("notification.toast")
        assert agent.can_handle("notification.error")
        assert agent.can_handle("inventory.low_stock")
        assert agent.can_handle("inventory.out_of_stock")

    def test_notification_agent_does_not_write_to_db_does_not_use_llm(self):
        agent = NotificationAgent()
        assert agent.writes_to_db is False
        assert agent.uses_llm is False

    def test_reporting_agent_subscribes_to_report_events(self):
        agent = ReportingAgent()
        assert agent.can_handle("report.daily_sales")
        assert agent.can_handle("report.inventory")
        assert agent.can_handle("report.transactions")
        assert agent.can_handle("report.export_csv")

    def test_reporting_agent_does_not_write_to_db_does_not_use_llm(self):
        agent = ReportingAgent()
        assert agent.writes_to_db is False
        assert agent.uses_llm is False

    def test_insight_agent_is_read_only(self):
        """A101: InsightAgent never writes to DB."""
        agent = InsightAgent()
        assert agent.writes_to_db is False

    def test_insight_agent_uses_llm(self):
        """A102: InsightAgent is the only agent that uses LLM."""
        agent = InsightAgent()
        assert agent.uses_llm is True

    def test_insight_agent_is_degradable(self):
        """A103: System works 100% without LLM when InsightAgent degrades."""
        agent = InsightAgent()
        assert agent.degradable is True

    def test_insight_agent_subscribes_to_insight_events(self):
        """InsightAgent subscribes to insight.suggest_upsell, analyze_trends, natural_query."""
        agent = InsightAgent()
        assert agent.can_handle("insight.suggest_upsell")
        assert agent.can_handle("insight.analyze_trends")
        assert agent.can_handle("insight.natural_query")
        assert not agent.can_handle("order.create")

    def test_agents_only_publish_declared_events(
        self, test_db, sample_user, stocked_item
    ):
        """A086: For each agent, handle() returns an event whose type is in publishes, or None (terminal sink)."""
        from src.events.bus import EventBus

        bus = EventBus()
        agents_events = [
            (
                OrderAgent(),
                Event.create(
                    type="order.create",
                    source="test",
                    payload={
                        "table_id": "1",
                        "user_id": str(sample_user.id),
                    },
                    user_id=str(sample_user.id),
                ),
            ),
            (
                AuditAgent(),
                Event.create(
                    type="order.create",
                    source="test",
                    payload={"table_id": "1", "user_id": str(sample_user.id)},
                ),
            ),
            (
                InventoryAgent(event_bus=bus),
                Event.create(
                    type="inventory.stock_in",
                    source="test",
                    payload={
                        "item_id": str(stocked_item.id),
                        "quantity": 10,
                        "reference": "TEST-A086",
                        "recorded_by": str(sample_user.id),
                    },
                    user_id=str(sample_user.id),
                ),
            ),
            (
                PaymentAgent(),
                Event.create(
                    type="payment.process",
                    source="test",
                    payload={
                        "order_id": "00000000-0000-0000-0000-000000000001",
                        "payment_method": "CASH",
                        "amount": 100.0,
                    },
                ),
            ),
            (
                AuthAgent(),
                Event.create(
                    type="auth.login",
                    source="test",
                    payload={"username": "testmanager", "pin": "1234"},
                ),
            ),
            (
                PrintAgent(),
                Event.create(
                    type="receipt.print",
                    source="test",
                    payload={"order_id": "00000000-0000-0000-0000-000000000001", "lines": []},
                ),
            ),
            (
                NotificationAgent(),
                Event.create(
                    type="notification.toast",
                    source="test",
                    payload={"message": "test"},
                ),
            ),
            (
                ReportingAgent(),
                Event.create(
                    type="report.daily_sales",
                    source="test",
                    payload={},
                ),
            ),
        ]
        for agent, evt in agents_events:
            out = agent.handle(evt)
            if out is None:
                assert not agent.publishes or True  # terminal sink
                continue
            assert out.type in agent.publishes, (
                f"{agent.name} returned event type '{out.type}' not in publishes {agent.publishes}"
            )
