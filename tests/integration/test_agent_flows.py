"""
Integration tests for agent-based event flows.
"""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from src.events.event import Event
from src.events.bus import EventBus
from src.events.store import EventStore
from src.agents.order_agent import OrderAgent
from src.agents.audit_agent import AuditAgent
from src.agents.payment_agent import PaymentAgent
from src.agents.auth_agent import AuthAgent
from src.agents.print_agent import PrintAgent
from src.agents.inventory_agent import InventoryAgent
from src.agents.orchestrator_agent import OrchestratorAgent
from src.agents.registry import AgentRegistry


class TestOrderAgentFlow:
    """A032 + A033: Order agent integration tests."""

    def _setup_bus(self):
        """Create a bus with OrderAgent and AuditAgent registered."""
        bus = EventBus()
        order_agent = OrderAgent()
        audit_agent = AuditAgent()

        # Register handlers
        for event_type in order_agent.subscribes_to:
            bus.subscribe(event_type, order_agent.handle)
        bus.subscribe("*", audit_agent.handle)

        return bus

    def test_create_order_via_event(self, sample_user, stocked_item):
        """A032: order.create via EventBus creates order in DB."""
        bus = self._setup_bus()

        event = Event.create(
            type="order.create",
            payload={"table_id": "5", "user_id": str(sample_user.id)},
            user_id=str(sample_user.id),
        )
        result = bus.publish_sync(event)

        assert result.success, f"Failed: {result.error}"
        assert result.event is not None
        assert result.event.type == "order.created"
        assert result.event.payload["table_id"] == "5"
        assert result.event.payload["status"] == "draft"
        assert result.event.payload["order_id"]  # UUID string

    def test_full_order_lifecycle_via_events(self, sample_user, stocked_item):
        """A033: Full order lifecycle: create -> add_item -> finalize."""
        bus = self._setup_bus()
        user_id = str(sample_user.id)

        # 1. Create order
        create_result = bus.publish_sync(Event.create(
            type="order.create",
            payload={"table_id": "7", "user_id": user_id},
            user_id=user_id,
        ))
        assert create_result.success
        order_id = create_result.event.payload["order_id"]

        # 2. Add item
        add_result = bus.publish_sync(Event.create(
            type="order.add_item",
            payload={"order_id": order_id, "item_id": str(stocked_item.id), "quantity": 2},
            user_id=user_id,
        ))
        assert add_result.success
        assert add_result.event.type == "order.updated"
        assert add_result.event.payload["total_amount"] > 0

        # 3. Finalize
        total = add_result.event.payload["total_amount"]
        finalize_result = bus.publish_sync(Event.create(
            type="order.finalize",
            payload={
                "order_id": order_id,
                "payment_method": "CASH",
                "amount_tendered": total + 100,
            },
            user_id=user_id,
        ))
        assert finalize_result.success
        assert finalize_result.event.type == "order.finalized"
        assert finalize_result.event.payload["status"] == "finalized"
        assert finalize_result.event.payload["receipt_number"]

    def test_audit_agent_records_events(self, sample_user):
        """A036: AuditAgent records all events to event_log."""
        store = EventStore()
        initial_count = store.count()
        
        bus = self._setup_bus()
        user_id = str(sample_user.id)

        bus.publish_sync(Event.create(
            type="order.create",
            payload={"table_id": "1", "user_id": user_id},
            user_id=user_id,
        ))

        # At least the original event + response event should be stored
        new_count = store.count()
        assert new_count > initial_count


class TestPaymentAgentFlow:
    """PaymentAgent handles payment.process event."""

    def test_payment_agent_handles_payment_process(self):
        bus = EventBus()
        payment_agent = PaymentAgent()
        for event_type in payment_agent.subscribes_to:
            bus.subscribe(event_type, payment_agent.handle)

        event = Event.create(
            type="payment.process",
            payload={
                "order_id": "test-order-123",
                "payment_method": "CASH",
                "amount": 150.50,
            },
            user_id="user-1",
        )
        result = bus.publish_sync(event)

        assert result.success, f"Failed: {result.error}"
        assert result.event is not None
        assert result.event.type == "payment.completed"
        assert result.event.payload["order_id"] == "test-order-123"
        assert result.event.payload["payment_method"] == "CASH"
        assert result.event.payload["amount"] == 150.50


class TestAuthAgentFlow:
    """AuthAgent handles auth.login event."""

    def test_auth_agent_handles_auth_login(self, sample_user):
        bus = EventBus()
        auth_agent = AuthAgent()
        for event_type in auth_agent.subscribes_to:
            bus.subscribe(event_type, auth_agent.handle)

        event = Event.create(
            type="auth.login",
            payload={
                "username": "testmanager",
                "pin": "1234",
            },
            user_id=None,
        )
        result = bus.publish_sync(event)

        assert result.success, f"Failed: {result.error}"
        assert result.event is not None
        assert result.event.type == "auth.logged_in"
        assert result.event.payload["username"] == "testmanager"
        assert result.event.payload["role"] == "MANAGER"
        assert result.event.payload["token"]


class TestPrintAgentFlow:
    """PrintAgent handles receipt.print event (printer mocked)."""

    @patch("src.agents.print_agent.ESCPOSPrinter")
    def test_print_agent_handles_receipt_print(self, mock_printer_class):
        mock_printer = MagicMock()
        mock_printer.print_receipt.return_value = "/receipts/receipt_001_20250212.txt"
        mock_printer_class.return_value = mock_printer

        bus = EventBus()
        print_agent = PrintAgent()
        print_agent.printer = mock_printer
        for event_type in print_agent.subscribes_to:
            bus.subscribe(event_type, print_agent.handle)

        event = Event.create(
            type="receipt.print",
            payload={
                "order_id": "ord-1",
                "receipt_number": "R-001",
                "table_id": "5",
                "line_items": [],
                "subtotal": 100.0,
                "discount_amount": 0.0,
                "tax_amount": 18.0,
                "total_amount": 118.0,
            },
            user_id="user-1",
        )
        result = bus.publish_sync(event)

        assert result.success, f"Failed: {result.error}"
        assert result.event is not None
        assert result.event.type == "receipt.printed"
        assert result.event.payload["receipt_number"] == "R-001"
        mock_printer.print_receipt.assert_called_once()


class TestInventoryAgentFlow:
    """A057–A059: InventoryAgent integration tests."""

    def test_stock_in_via_event_stock_updated(self, sample_user, stocked_item):
        """Stock-in via event updates stock correctly and returns inventory.stocked_in."""
        bus = EventBus()
        inventory_agent = InventoryAgent()
        for event_type in inventory_agent.subscribes_to:
            bus.subscribe(event_type, inventory_agent.handle)

        from src.application.services import InventoryService
        inv = InventoryService()
        stock_before = inv.get_stock_on_hand(stocked_item.id)

        event = Event.create(
            type="inventory.stock_in",
            source="API",
            payload={
                "item_id": str(stocked_item.id),
                "quantity": 20,
                "reference": "PO-TEST",
            },
            user_id=str(sample_user.id),
        )
        result = bus.publish_sync(event)

        assert result.success, f"Failed: {result.error}"
        assert result.event is not None
        assert result.event.type == "inventory.stocked_in"
        assert result.event.payload["item_id"] == str(stocked_item.id)
        assert result.event.payload["quantity_change"] == 20
        assert result.event.payload["stock_on_hand"] == stock_before + 20

        stock_after = inv.get_stock_on_hand(stocked_item.id)
        assert stock_after == stock_before + 20

    def test_order_finalized_publishes_low_stock_when_applicable(self, sample_user, stocked_item):
        """Order finalized triggers low_stock event when item falls below reorder level."""
        bus = EventBus()
        order_agent = OrderAgent()
        inventory_agent = InventoryAgent(event_bus=bus)
        for event_type in order_agent.subscribes_to:
            bus.subscribe(event_type, order_agent.handle)
        for event_type in inventory_agent.subscribes_to:
            bus.subscribe(event_type, inventory_agent.handle)

        low_stock_events = []
        def collect_low_stock(ev):
            low_stock_events.append(ev)
        bus.subscribe("inventory.low_stock", collect_low_stock)
        bus.subscribe("inventory.out_of_stock", collect_low_stock)

        user_id = str(sample_user.id)
        # stocked_item has 100 stock, reorder_level=10 (from sample_item). Sell 95 → 5 left < 10 → low_stock
        create_result = bus.publish_sync(Event.create(
            type="order.create",
            payload={"table_id": "1", "user_id": user_id},
            user_id=user_id,
        ))
        assert create_result.success
        order_id = create_result.event.payload["order_id"]

        add_result = bus.publish_sync(Event.create(
            type="order.add_item",
            payload={"order_id": order_id, "item_id": str(stocked_item.id), "quantity": 95},
            user_id=user_id,
        ))
        assert add_result.success
        total = add_result.event.payload["total_amount"]

        finalize_result = bus.publish_sync(Event.create(
            type="order.finalize",
            payload={"order_id": order_id, "payment_method": "CASH", "amount_tendered": total + 100},
            user_id=user_id,
        ))
        assert finalize_result.success and finalize_result.event
        bus.publish_sync(finalize_result.event)

        low_or_out = [e for e in low_stock_events if e.type in ("inventory.low_stock", "inventory.out_of_stock")]
        assert len(low_or_out) >= 1, "Expected at least one low_stock or out_of_stock after finalize"
        alert = low_or_out[0]
        assert alert.payload["item_id"] == str(stocked_item.id)
        assert alert.payload["stock_on_hand"] <= alert.payload["reorder_level"]


class TestOrchestratorMultiStepWorkflow:
    """A137: OrchestratorAgent multi-step workflow integration."""

    def test_orchestrator_multi_step_workflow(self, sample_user, stocked_item):
        """workflow.multi_step with create_order intent -> order created and finalized."""
        bus = EventBus()
        order_agent = OrderAgent()
        inventory_agent = InventoryAgent(event_bus=bus)
        orchestrator_agent = OrchestratorAgent(event_bus=bus)

        for event_type in order_agent.subscribes_to:
            bus.subscribe(event_type, order_agent.handle)
        for event_type in inventory_agent.subscribes_to:
            bus.subscribe(event_type, inventory_agent.handle)
        for event_type in orchestrator_agent.subscribes_to:
            bus.subscribe(event_type, orchestrator_agent.handle)

        intent = {
            "action": "create_order",
            "table_id": "5",
            "user_id": str(sample_user.id),
            "items": [
                {"item_id": str(stocked_item.id), "name": stocked_item.name, "quantity": 1},
            ],
            "payment_method": "CASH",
            "amount": 500.0,
        }
        event = Event.create(
            type="workflow.multi_step",
            source="Test",
            payload={"intent": intent},
            user_id=str(sample_user.id),
        )
        result = bus.publish_sync(event)

        assert result.success, f"Failed: {result.error}"
        assert result.event is not None
        assert result.event.type == "workflow.completed"
        assert result.event.payload.get("steps_completed") >= 2
        assert result.event.payload.get("order_id")


class TestInsightAgentFlow:
    """A104: InsightAgent integration — upsell with mock LLM."""

    @pytest.mark.parametrize("mock_response", ['["Coffee", "Dessert"]', '["Side salad"]'])
    def test_insight_upsell_with_mock_llm(self, sample_user, stocked_item, mock_response):
        """Mock LLMClient.query to return a suggestion; verify insight.suggestion flow."""
        from unittest.mock import patch
        from src.agents.insight_agent import InsightAgent

        bus = EventBus()
        order_agent = OrderAgent()
        for event_type in order_agent.subscribes_to:
            bus.subscribe(event_type, order_agent.handle)

        # Create order and add item so order exists
        create_result = bus.publish_sync(
            Event.create(
                type="order.create",
                payload={"table_id": "1", "user_id": str(sample_user.id)},
                user_id=str(sample_user.id),
            )
        )
        assert create_result.success
        order_id = create_result.event.payload["order_id"]
        bus.publish_sync(
            Event.create(
                type="order.add_item",
                payload={"order_id": order_id, "item_id": str(stocked_item.id), "quantity": 1},
                user_id=str(sample_user.id),
            )
        )

        insight_agent = InsightAgent()
        for event_type in insight_agent.subscribes_to:
            bus.subscribe(event_type, insight_agent.handle)

        with patch.object(insight_agent.llm, "query", return_value=mock_response):
            event = Event.create(
                type="insight.suggest_upsell",
                payload={"order_id": order_id},
                source="test",
            )
            result = bus.publish_sync(event)

        assert result.success, f"Failed: {result.error}"
        assert result.event is not None
        assert result.event.type == "insight.suggestion"
        assert "suggestions" in result.event.payload
        assert result.event.payload["order_id"] == order_id
        suggestions = result.event.payload["suggestions"]
        assert isinstance(suggestions, list)
        assert len(suggestions) >= 1, "Mock LLM should produce at least one suggestion"
