"""
Contract tests: event types from specs/main/contracts/*.json are covered by at least one agent.

A085: For each event type defined in the contracts, verify that at least one agent
has it in its subscribes_to list. Insight events are skipped (InsightAgent not implemented).
"""

import json
import pytest
from pathlib import Path

from src.agents.order_agent import OrderAgent
from src.agents.audit_agent import AuditAgent
from src.agents.inventory_agent import InventoryAgent
from src.agents.payment_agent import PaymentAgent
from src.agents.auth_agent import AuthAgent
from src.agents.print_agent import PrintAgent
from src.agents.notification_agent import NotificationAgent
from src.agents.reporting_agent import ReportingAgent


CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "specs" / "main" / "contracts"
INSIGHT_CONTRACT = "insight-events.json"  # Skip: InsightAgent not implemented


def _all_agents():
    """Return list of agent instances (no InsightAgent)."""
    return [
        OrderAgent(),
        AuditAgent(),
        InventoryAgent(event_bus=None),
        PaymentAgent(),
        AuthAgent(),
        PrintAgent(),
        NotificationAgent(),
        ReportingAgent(),
    ]


def _event_types_from_contracts():
    """Yield (filename, event_type) for each event in contract JSON files."""
    if not CONTRACTS_DIR.exists():
        pytest.skip(f"Contracts dir not found: {CONTRACTS_DIR}")
    for path in sorted(CONTRACTS_DIR.glob("*.json")):
        if path.name == INSIGHT_CONTRACT:
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        events = data.get("events") or {}
        for event_type in events:
            yield path.name, event_type


def _some_agent_handles(event_type: str) -> bool:
    """True if at least one agent can_handle(event_type)."""
    for agent in _all_agents():
        if agent.can_handle(event_type):
            return True
    return False


class TestEventContractCoverage:
    """A085: Event type coverage — every contract event type is handled by some agent."""

    @pytest.mark.parametrize("filename,event_type", list(_event_types_from_contracts()))
    def test_contract_event_type_has_subscriber(self, filename, event_type):
        """Each event type (except insight-events) is in at least one agent's subscribes_to."""
        assert _some_agent_handles(event_type), (
            f"Event type '{event_type}' from {filename} is not in any agent's subscribes_to"
        )

    def test_insight_events_skipped(self):
        """Insight contract exists but is excluded from coverage (InsightAgent not implemented)."""
        insight_path = CONTRACTS_DIR / INSIGHT_CONTRACT
        if not insight_path.exists():
            pytest.skip("insight-events.json not present")
        with open(insight_path, encoding="utf-8") as f:
            data = json.load(f)
        events = data.get("events") or {}
        # All insight.* types are expected-unhandled for this test suite
        for event_type in events:
            assert event_type.startswith("insight."), f"Unexpected prefix in {event_type}"
