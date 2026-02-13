"""
Agent Architecture Smoke Tests

End-to-end tests verifying the full order lifecycle flows through
the event bus (API → EventBus → OrderAgent → SalesService → DB).

These tests use FastAPI's TestClient to exercise the actual HTTP routes,
confirming that the event-driven wiring produces identical results to
the old direct-service calls.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app


@pytest.fixture
def client(test_db, sample_user, stocked_item):
    """Create a TestClient with an isolated test DB, user, and stocked item."""
    app = create_app()
    return TestClient(app)


class TestFullOrderViaEventBus:
    """Smoke tests: full order lifecycle through event bus."""

    def test_create_order_via_http(self, client, sample_user):
        """POST /api/sales/orders creates a draft order through the event bus."""
        resp = client.post("/api/sales/orders", json={
            "table_id": "5",
            "user_id": str(sample_user.id),
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "draft"
        assert data["table_id"] is not None
        assert data["id"]  # Non-empty order ID

    def test_add_item_via_http(self, client, sample_user, stocked_item):
        """POST /api/sales/orders/{id}/items adds item through event bus."""
        # Create order first
        create_resp = client.post("/api/sales/orders", json={
            "table_id": "1",
            "user_id": str(sample_user.id),
        })
        order_id = create_resp.json()["id"]

        # Add item
        resp = client.post(f"/api/sales/orders/{order_id}/items", json={
            "item_id": str(stocked_item.id),
            "quantity": 2,
            "user_id": str(sample_user.id),
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["line_items"]) == 1
        assert data["line_items"][0]["quantity"] == 2
        assert data["total_amount"] > 0

    def test_finalize_order_via_http(self, client, sample_user, stocked_item):
        """Full lifecycle: create → add_item → finalize through event bus."""
        # Create
        create_resp = client.post("/api/sales/orders", json={
            "table_id": "3",
            "user_id": str(sample_user.id),
        })
        assert create_resp.status_code == 200
        order_id = create_resp.json()["id"]

        # Add item
        add_resp = client.post(f"/api/sales/orders/{order_id}/items", json={
            "item_id": str(stocked_item.id),
            "quantity": 1,
            "user_id": str(sample_user.id),
        })
        assert add_resp.status_code == 200

        # Finalize
        total = add_resp.json()["total_amount"]
        fin_resp = client.post(f"/api/sales/orders/{order_id}/finalize", json={
            "payment_method": "CASH",
            "paid_amount": total,
            "user_id": str(sample_user.id),
        })
        assert fin_resp.status_code == 200
        data = fin_resp.json()
        assert data["status"] == "finalized"
        assert data["receipt_number"]  # Should have a receipt number

    def test_void_order_via_http(self, client, sample_user, stocked_item):
        """Create → add_item → void through event bus."""
        # Create
        create_resp = client.post("/api/sales/orders", json={
            "table_id": "2",
            "user_id": str(sample_user.id),
        })
        order_id = create_resp.json()["id"]

        # Add item
        client.post(f"/api/sales/orders/{order_id}/items", json={
            "item_id": str(stocked_item.id),
            "quantity": 1,
            "user_id": str(sample_user.id),
        })

        # Void
        void_resp = client.post(f"/api/sales/orders/{order_id}/void", json={
            "reason": "Customer cancelled",
            "user_id": str(sample_user.id),
        })
        assert void_resp.status_code == 200
        assert void_resp.json()["status"] == "voided"

    def test_hold_and_resume_via_http(self, client, sample_user, stocked_item):
        """Create → add_item → hold → resume through event bus."""
        # Create
        create_resp = client.post("/api/sales/orders", json={
            "table_id": "7",
            "user_id": str(sample_user.id),
        })
        order_id = create_resp.json()["id"]

        # Add item
        client.post(f"/api/sales/orders/{order_id}/items", json={
            "item_id": str(stocked_item.id),
            "quantity": 1,
            "user_id": str(sample_user.id),
        })

        # Hold
        hold_resp = client.post(f"/api/sales/orders/{order_id}/hold", json={
            "user_id": str(sample_user.id),
        })
        assert hold_resp.status_code == 200
        assert hold_resp.json()["status"] == "held"

        # Resume
        resume_resp = client.post(f"/api/sales/orders/{order_id}/resume", json={
            "user_id": str(sample_user.id),
        })
        assert resume_resp.status_code == 200
        assert resume_resp.json()["status"] == "draft"

    def test_discount_via_http(self, client, sample_user, stocked_item):
        """Create → add_item → apply discount through event bus."""
        # Create
        create_resp = client.post("/api/sales/orders", json={
            "table_id": "4",
            "user_id": str(sample_user.id),
        })
        order_id = create_resp.json()["id"]

        # Add item
        add_resp = client.post(f"/api/sales/orders/{order_id}/items", json={
            "item_id": str(stocked_item.id),
            "quantity": 2,
            "user_id": str(sample_user.id),
        })
        assert add_resp.status_code == 200

        # Apply 10% discount
        disc_resp = client.patch(f"/api/sales/orders/{order_id}/discount", json={
            "discount_type": "percentage",
            "amount": 10.0,
            "user_id": str(sample_user.id),
        })
        assert disc_resp.status_code == 200
        data = disc_resp.json()
        assert data["discount_amount"] > 0

    def test_edit_quantity_via_http(self, client, sample_user, stocked_item):
        """Create → add_item → edit quantity through event bus."""
        # Create
        create_resp = client.post("/api/sales/orders", json={
            "table_id": "6",
            "user_id": str(sample_user.id),
        })
        order_id = create_resp.json()["id"]

        # Add item (qty 1)
        add_resp = client.post(f"/api/sales/orders/{order_id}/items", json={
            "item_id": str(stocked_item.id),
            "quantity": 1,
            "user_id": str(sample_user.id),
        })
        line_item_id = add_resp.json()["line_items"][0]["id"]

        # Edit quantity to 5
        edit_resp = client.patch(
            f"/api/sales/orders/{order_id}/items/{line_item_id}",
            json={"quantity": 5, "user_id": str(sample_user.id)},
        )
        assert edit_resp.status_code == 200
        assert edit_resp.json()["line_items"][0]["quantity"] == 5

    def test_remove_item_via_http(self, client, sample_user, stocked_item):
        """Create → add_item → remove_item through event bus."""
        # Create
        create_resp = client.post("/api/sales/orders", json={
            "table_id": "8",
            "user_id": str(sample_user.id),
        })
        order_id = create_resp.json()["id"]

        # Add item
        add_resp = client.post(f"/api/sales/orders/{order_id}/items", json={
            "item_id": str(stocked_item.id),
            "quantity": 1,
            "user_id": str(sample_user.id),
        })
        line_item_id = add_resp.json()["line_items"][0]["id"]

        # Remove it
        del_resp = client.delete(
            f"/api/sales/orders/{order_id}/items/{line_item_id}",
        )
        assert del_resp.status_code == 200
        assert len(del_resp.json()["line_items"]) == 0


class TestEventBusWiring:
    """Verify the event bus is actually wired and events are persisted."""

    def test_event_bus_on_app_state(self, test_db, sample_user, stocked_item):
        """Event bus should be accessible on app.state."""
        app = create_app()
        assert hasattr(app.state, "event_bus")
        assert app.state.event_bus is not None

    def test_events_persisted_to_store(self, client, sample_user, stocked_item):
        """After creating an order, events should appear in the event store."""
        # Create order
        resp = client.post("/api/sales/orders", json={
            "table_id": "1",
            "user_id": str(sample_user.id),
        })
        assert resp.status_code == 200

        # Check that events were stored
        from src.events import EventStore
        store = EventStore()
        create_events = store.query(event_type="order.create")
        created_events = store.query(event_type="order.created")
        assert len(create_events) >= 1, "order.create event should be persisted"
        assert len(created_events) >= 1, "order.created response event should be persisted"

    def test_read_routes_still_work(self, client, sample_user, stocked_item):
        """GET routes (non-event) should still function normally."""
        # Create an order first
        create_resp = client.post("/api/sales/orders", json={
            "table_id": "1",
            "user_id": str(sample_user.id),
        })
        order_id = create_resp.json()["id"]

        # GET order by ID (direct service call, not event-driven)
        get_resp = client.get(f"/api/sales/orders/{order_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == order_id

        # GET list orders
        list_resp = client.get("/api/sales/orders")
        assert list_resp.status_code == 200
        assert len(list_resp.json()) >= 1

    def test_health_endpoint(self, client):
        """Health check should still work."""
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestCompleteWorkflowViaEvents:
    """End-to-end smoke: login → order → discount → finalize → receipt → events → logout."""

    def test_complete_workflow_login_to_logout(
        self, client, sample_user, stocked_item
    ):
        """Full workflow via HTTP: login, create order, add items, discount, finalize, verify receipt and events, logout."""
        # Login
        login_resp = client.post(
            "/api/auth/login",
            json={"username": "testmanager", "pin": "1234"},
        )
        assert login_resp.status_code == 200
        login_data = login_resp.json()
        assert login_data.get("user_id") == str(sample_user.id)
        user_id = login_data["user_id"]
        token = login_data.get("token", "")

        # Create order
        create_resp = client.post(
            "/api/sales/orders",
            json={"table_id": "5", "user_id": user_id},
        )
        assert create_resp.status_code == 200
        order_id = create_resp.json()["id"]

        # Add two items (same item twice with quantity 1 each, or one add with qty 2)
        add1 = client.post(
            f"/api/sales/orders/{order_id}/items",
            json={
                "item_id": str(stocked_item.id),
                "quantity": 1,
                "user_id": user_id,
            },
        )
        assert add1.status_code == 200
        add2 = client.post(
            f"/api/sales/orders/{order_id}/items",
            json={
                "item_id": str(stocked_item.id),
                "quantity": 1,
                "user_id": user_id,
            },
        )
        assert add2.status_code == 200
        # Apply discount
        disc_resp = client.patch(
            f"/api/sales/orders/{order_id}/discount",
            json={
                "discount_type": "percentage",
                "amount": 10.0,
                "user_id": user_id,
            },
        )
        assert disc_resp.status_code == 200
        data_after_discount = disc_resp.json()
        assert data_after_discount.get("discount_amount", 0) >= 0

        # Finalize
        total = data_after_discount["total_amount"]
        fin_resp = client.post(
            f"/api/sales/orders/{order_id}/finalize",
            json={
                "payment_method": "CASH",
                "paid_amount": total,
                "user_id": user_id,
            },
        )
        assert fin_resp.status_code == 200
        fin_data = fin_resp.json()
        assert fin_data["status"] == "finalized"
        assert fin_data.get("receipt_number")

        # Verify final state via GET
        get_resp = client.get(f"/api/sales/orders/{order_id}")
        assert get_resp.status_code == 200
        order_data = get_resp.json()
        assert order_data["id"] == order_id
        assert order_data["status"] == "finalized"
        assert len(order_data.get("line_items", [])) >= 1

        # Verify events persisted in EventStore
        from src.events import EventStore
        store = EventStore()
        create_events = store.query(event_type="order.create", limit=50)
        created_events = store.query(event_type="order.created", limit=50)
        finalized_events = store.query(event_type="order.finalized", limit=50)
        assert len(create_events) >= 1
        assert len(created_events) >= 1
        assert len(finalized_events) >= 1

        # Logout
        logout_resp = client.post(
            "/api/auth/logout",
            json={"token": token, "user_id": user_id},
        )
        assert logout_resp.status_code == 200
        assert logout_resp.json().get("status") == "logged_out"


class TestInsightAgentDegradation:
    """InsightAgent is degradable: system works when LLM times out or is unavailable."""

    def test_system_works_when_insight_agent_times_out(self, test_db, sample_user, stocked_item):
        """Mock LLMClient.query to return None (timeout); order flow still works."""
        from unittest.mock import patch
        with patch("src.agents.llm_client.LLMClient.query", return_value=None):
            app = create_app()
            api_client = TestClient(app)
            create_resp = api_client.post("/api/sales/orders", json={
                "table_id": "1",
                "user_id": str(sample_user.id),
            })
            assert create_resp.status_code == 200
            order_id = create_resp.json()["id"]
            add_resp = api_client.post(f"/api/sales/orders/{order_id}/items", json={
                "item_id": str(stocked_item.id),
                "quantity": 1,
                "user_id": str(sample_user.id),
            })
            assert add_resp.status_code == 200
            total = add_resp.json()["total_amount"]
            fin_resp = api_client.post(f"/api/sales/orders/{order_id}/finalize", json={
                "payment_method": "CASH",
                "paid_amount": total,
                "user_id": str(sample_user.id),
            })
            assert fin_resp.status_code == 200
            assert fin_resp.json()["status"] == "finalized"
            upsell_resp = api_client.get(f"/api/insights/upsell/{order_id}")
            assert upsell_resp.status_code == 200
            data = upsell_resp.json()
            assert data.get("suggestions") == []
            assert "Insight unavailable" in data.get("message", "")

    def test_system_works_when_llm_unavailable(self, test_db, sample_user, stocked_item):
        """LLM always returns None; create orders and verify everything works."""
        from unittest.mock import patch
        with patch("src.agents.llm_client.LLMClient.query", return_value=None):
            app = create_app()
            api_client = TestClient(app)
            create_resp = api_client.post("/api/sales/orders", json={
                "table_id": "2",
                "user_id": str(sample_user.id),
            })
            assert create_resp.status_code == 200
            order_id = create_resp.json()["id"]
            api_client.post(f"/api/sales/orders/{order_id}/items", json={
                "item_id": str(stocked_item.id),
                "quantity": 2,
                "user_id": str(sample_user.id),
            })
            total = api_client.get(f"/api/sales/orders/{order_id}").json()["total_amount"]
            fin_resp = api_client.post(f"/api/sales/orders/{order_id}/finalize", json={
                "payment_method": "CASH",
                "paid_amount": total,
                "user_id": str(sample_user.id),
            })
            assert fin_resp.status_code == 200
            assert fin_resp.json()["status"] == "finalized"
            query_resp = api_client.post("/api/insights/query", json={"question": "What were sales today?"})
            assert query_resp.status_code == 200
            assert query_resp.json().get("message") == "Insight unavailable"


class TestOfflineOperation:
    """Verify agent flows work without network (offline)."""

    def test_all_agent_flows_work_offline(self, client, sample_user, stocked_item):
        """Mock httpx so no network calls occur; full order flow via HTTP (in-process) should still succeed."""
        from unittest.mock import patch

        with patch("httpx.post"), patch("httpx.get"), patch("httpx.request"):
            # Create order
            create_resp = client.post(
                "/api/sales/orders",
                json={"table_id": "1", "user_id": str(sample_user.id)},
            )
            assert create_resp.status_code == 200
            order_id = create_resp.json()["id"]

            # Add item
            add_resp = client.post(
                f"/api/sales/orders/{order_id}/items",
                json={
                    "item_id": str(stocked_item.id),
                    "quantity": 1,
                    "user_id": str(sample_user.id),
                },
            )
            assert add_resp.status_code == 200

            # Finalize
            total = add_resp.json()["total_amount"]
            fin_resp = client.post(
                f"/api/sales/orders/{order_id}/finalize",
                json={
                    "payment_method": "CASH",
                    "paid_amount": total,
                    "user_id": str(sample_user.id),
                },
            )
            assert fin_resp.status_code == 200
            assert fin_resp.json()["status"] == "finalized"


class TestVoicePipelineOffline:
    """A138: Voice pipeline works offline (intent parsing without network)."""

    def test_voice_pipeline_works_offline(self, test_db, sample_item):
        """Intent parser works without network (no STT/HTTP); uses local DB for item lookup."""
        from src.voice.intent_parser import IntentParser

        parser = IntentParser()
        intent = parser.parse("2 biryani for table 3")
        assert intent["action"] == "create_order"
        assert intent["table_id"] == "3"
        assert len(intent["items"]) >= 1
        assert any(
            it["name"].lower() == "biryani" and it["quantity"] == 2
            for it in intent["items"]
        )
