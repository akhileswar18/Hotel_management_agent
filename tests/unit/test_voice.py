"""
Unit tests for voice pipeline: IntentParser and OrchestratorAgent decomposition.
"""

import pytest
from src.voice.intent_parser import IntentParser
from src.agents.orchestrator_agent import OrchestratorAgent


class TestIntentParser:
    """A135–A136: Intent parser unit tests."""

    def test_intent_parser_basic_order(self, test_db, sample_item, sample_item_coke):
        """'2 biryani and 1 coke for table 5' -> action=create_order with correct items."""
        parser = IntentParser()
        text = "2 biryani and 1 coke for table 5"
        intent = parser.parse(text)

        assert intent["action"] == "create_order"
        assert intent["table_id"] == "5"
        assert len(intent["items"]) >= 1
        # Should have biryani qty 2 and coke qty 1 (order may vary)
        by_name = {it["name"].lower(): it for it in intent["items"]}
        assert "biryani" in by_name
        assert by_name["biryani"]["quantity"] == 2
        assert "coke" in by_name
        assert by_name["coke"]["quantity"] == 1

    def test_intent_parser_ambiguous(self):
        """'hello' -> action=unknown."""
        parser = IntentParser()
        intent = parser.parse("hello")
        assert intent["action"] == "unknown"
        assert intent.get("original_text") == "hello"


class TestOrchestratorDecompose:
    """A136: OrchestratorAgent _decompose_intent produces correct steps."""

    def test_orchestrator_decompose_order(self):
        """Verify _decompose_intent creates correct steps for create_order intent."""
        agent = OrchestratorAgent(event_bus=None)
        intent = {
            "action": "create_order",
            "table_id": "3",
            "user_id": "user-1",
            "items": [
                {"item_id": "item-a", "name": "Biryani", "quantity": 2},
                {"item_id": "item-b", "name": "Coke", "quantity": 1},
            ],
            "payment_method": "CASH",
            "amount": 100.0,
        }
        steps = agent._decompose_intent(intent)

        assert len(steps) == 4  # create + add_item x2 + finalize
        assert steps[0]["type"] == "order.create"
        assert steps[0]["payload"]["table_id"] == "3"
        assert steps[0]["payload"]["user_id"] == "user-1"
        assert steps[1]["type"] == "order.add_item"
        assert steps[1]["payload"]["item_id"] == "item-a"
        assert steps[1]["payload"]["quantity"] == 2
        assert steps[2]["type"] == "order.add_item"
        assert steps[2]["payload"]["item_id"] == "item-b"
        assert steps[2]["payload"]["quantity"] == 1
        assert steps[3]["type"] == "order.finalize"
        assert steps[3]["payload"]["payment_method"] == "CASH"
        assert steps[3]["payload"]["amount_tendered"] == 100.0
