"""
Intent Parser — Parse natural language into structured intents for OrchestratorAgent.

Rule-based first, with optional LLM fallback for ambiguous input.
Supports follow-up detection for conversational command flows.
"""

import re
from typing import Dict, Any, List, Optional


# Required fields per action — if missing, follow-up questions are needed
REQUIRED_FIELDS = {
    "create_order": ["table_id", "items"],
    "add_item": ["items"],
    "finalize_order": ["payment_method"],
    "void_order": [],
    "hold_order": [],
    "create_product": ["name", "price", "category"],
    "stock_in": ["item_name", "quantity"],
    "report": [],
}

FOLLOW_UP_PROMPTS = {
    "table_id": "Which table number?",
    "items": "What items would you like? (e.g., '2 biryani and 1 coke')",
    "payment_method": "Payment method? (cash, card, or voucher)",
    "name": "What is the product name?",
    "price": "What is the unit price (in ₹)?",
    "category": "What category? (food, beverage, dessert, other)",
    "item_name": "Which product?",
    "quantity": "How many units?",
    "reason": "Reason for voiding?",
}


class IntentParser:
    """Parse natural language into structured intents for the OrchestratorAgent."""

    def __init__(self, item_repo=None):
        from src.infrastructure import ItemRepository
        self.item_repo = item_repo or ItemRepository()

    def parse(self, text: str) -> Dict[str, Any]:
        """Parse text into an intent dict.

        Returns:
            e.g. {"action": "create_order", "table_id": "5", "items": [...]}
        """
        text_lower = text.lower().strip()

        # ── Specific compound phrases checked FIRST (before item-name matching) ──

        # Void order
        if any(kw in text_lower for kw in ["void", "cancel order"]):
            return self._parse_void_intent(text_lower)

        # Hold order
        if any(kw in text_lower for kw in ["hold order", "put on hold", "pause order"]):
            return {"action": "hold_order"}

        # Create product / new product  (must be before order check)
        if any(kw in text_lower for kw in ["new product", "create product", "add product", "new item"]):
            return self._parse_create_product_intent(text_lower)

        # Stock-in  (must be before order check — "add 50 biryani to stock" is stock, not order)
        if any(kw in text_lower for kw in ["stock in", "restock", "add stock", "add to stock",
                                             "to stock", "units of", "add inventory"]):
            return self._parse_stock_intent(text_lower)

        # Report
        if any(kw in text_lower for kw in ["report", "summary", "analytics", "sales"]):
            return {"action": "report", "type": "daily_sales"}

        # ── Now check ordering vs finalize ──

        has_item_names = self._text_mentions_items(text_lower)
        has_finalize_kw = any(kw in text_lower for kw in [
            "finalize", "pay ", "payment", "checkout", "bill",
        ])
        has_order_kw = any(kw in text_lower for kw in [
            "order", "want", "give me", "table",
        ])

        # If text mentions actual product names → it's an order, even with "pay"
        #   e.g. "order 3 biryani for table 7 pay cash"
        if has_item_names:
            return self._parse_order_intent(text_lower)

        # Finalize (standalone — no item names, no ordering context)
        #   e.g. "finalize order", "pay cash", "checkout"
        if has_finalize_kw and not has_order_kw:
            return self._parse_finalize_intent(text_lower)

        # "finalize order" — "finalize" is the primary intent even though "order" is present
        if has_finalize_kw and "finalize" in text_lower:
            return self._parse_finalize_intent(text_lower)

        # Order-related (no specific items yet — will ask follow-up)
        #   e.g. "create order", "order for table 5", "add 3 items"
        if has_order_kw or any(kw in text_lower for kw in ["add", "get"]):
            return self._parse_order_intent(text_lower)

        # Fallback: standalone pay/bill
        if has_finalize_kw:
            return self._parse_finalize_intent(text_lower)

        return {"action": "unknown", "original_text": text}

    def parse_followup(self, pending_intent: Dict[str, Any], text: str) -> Dict[str, Any]:
        """Merge a follow-up answer into a pending (incomplete) intent.

        Args:
            pending_intent: The incomplete intent from a previous parse
            text: The user's follow-up answer

        Returns:
            Updated intent with the missing fields filled in
        """
        action = pending_intent.get("action", "")
        text_lower = text.lower().strip()
        missing = self.get_missing_fields(pending_intent)

        if "table_id" in missing:
            table_match = re.search(r"(\d+)", text_lower)
            if table_match:
                pending_intent["table_id"] = table_match.group(1)

        if "items" in missing:
            items = self._extract_items(text_lower)
            if items:
                pending_intent["items"] = items

        if "payment_method" in missing:
            if "cash" in text_lower:
                pending_intent["payment_method"] = "CASH"
            elif "card" in text_lower:
                pending_intent["payment_method"] = "CARD"
            elif "voucher" in text_lower:
                pending_intent["payment_method"] = "VOUCHER"

        if "name" in missing:
            # Take the whole text as the product name (cleaned)
            pending_intent["name"] = text.strip()

        if "price" in missing:
            price_match = re.search(r"(\d+(?:\.\d+)?)", text_lower)
            if price_match:
                pending_intent["price"] = float(price_match.group(1))

        if "category" in missing:
            for cat in ["food", "beverage", "dessert", "other"]:
                if cat in text_lower:
                    pending_intent["category"] = cat
                    break

        if "item_name" in missing:
            # Try to match against known items
            items = self._extract_items(text_lower)
            if items:
                pending_intent["item_name"] = items[0]["name"]
                pending_intent["item_id"] = items[0]["item_id"]

        if "quantity" in missing:
            qty_match = re.search(r"(\d+)", text_lower)
            if qty_match:
                pending_intent["quantity"] = int(qty_match.group(1))

        if "reason" in missing:
            pending_intent["reason"] = text.strip()

        return pending_intent

    def get_missing_fields(self, intent: Dict[str, Any]) -> List[str]:
        """Return list of required fields that are missing from the intent."""
        action = intent.get("action", "")
        required = REQUIRED_FIELDS.get(action, [])

        missing = []
        for field in required:
            value = intent.get(field)
            if value is None or value == "" or (isinstance(value, list) and len(value) == 0):
                missing.append(field)

        return missing

    def get_followup_prompt(self, intent: Dict[str, Any]) -> Optional[str]:
        """Generate a follow-up question for the first missing required field.

        Returns None if no fields are missing (intent is complete).
        """
        missing = self.get_missing_fields(intent)
        if not missing:
            return None

        prompts = [FOLLOW_UP_PROMPTS.get(f, f"Please provide: {f}") for f in missing]
        return " ".join(prompts)

    # ---- Private parsing methods ----

    def _text_mentions_items(self, text: str) -> bool:
        """Quick check: does the text mention any known inventory item names?"""
        try:
            all_items = self.item_repo.list()
        except Exception:
            return False
        for item in all_items:
            if item.name.lower() in text:
                return True
        return False

    def _extract_items(self, text: str) -> List[Dict[str, Any]]:
        """Extract item names and quantities from text using fuzzy matching against inventory."""
        try:
            all_items = self.item_repo.list()
        except Exception:
            all_items = []

        item_names = {item.name.lower(): item for item in all_items}
        found_items = []

        for item_name, item in item_names.items():
            pattern = rf"(\d+)\s+{re.escape(item_name)}"
            match = re.search(pattern, text)
            if match:
                qty = int(match.group(1))
                found_items.append({
                    "item_id": str(item.id),
                    "name": item.name,
                    "quantity": qty,
                })
            elif item_name in text:
                found_items.append({
                    "item_id": str(item.id),
                    "name": item.name,
                    "quantity": 1,
                })

        return found_items

    def _parse_order_intent(self, text: str) -> Dict[str, Any]:
        """Parse order-related text into structured intent."""
        intent: Dict[str, Any] = {
            "action": "create_order",
            "items": [],
            "table_id": None,
            "payment_method": None,
        }

        # Extract table number
        table_match = re.search(r"table\s+(\d+)", text)
        if table_match:
            intent["table_id"] = table_match.group(1)

        # Extract payment method
        if "cash" in text:
            intent["payment_method"] = "CASH"
        elif "card" in text:
            intent["payment_method"] = "CARD"

        # Extract items
        intent["items"] = self._extract_items(text)

        return intent

    def _parse_finalize_intent(self, text: str) -> Dict[str, Any]:
        """Parse finalize/payment intent."""
        intent: Dict[str, Any] = {
            "action": "finalize_order",
            "payment_method": None,
        }

        if "cash" in text:
            intent["payment_method"] = "CASH"
        elif "card" in text:
            intent["payment_method"] = "CARD"
        elif "voucher" in text:
            intent["payment_method"] = "VOUCHER"

        return intent

    def _parse_void_intent(self, text: str) -> Dict[str, Any]:
        """Parse void order intent."""
        intent: Dict[str, Any] = {
            "action": "void_order",
            "reason": None,
        }

        # Try to extract reason after keywords
        reason_match = re.search(r"(?:because|reason|due to)\s+(.+)", text)
        if reason_match:
            intent["reason"] = reason_match.group(1).strip()

        return intent

    def _parse_create_product_intent(self, text: str) -> Dict[str, Any]:
        """Parse create product intent."""
        intent: Dict[str, Any] = {
            "action": "create_product",
            "name": None,
            "price": None,
            "category": None,
        }

        # Try to extract price
        price_match = re.search(r"(?:at|price|for)\s+(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)", text)
        if price_match:
            intent["price"] = float(price_match.group(1))

        # Try to extract category
        for cat in ["food", "beverage", "dessert", "other"]:
            if cat in text:
                intent["category"] = cat
                break

        # Try to extract name — the text between "product" keyword and price/category
        name_match = re.search(
            r"(?:product|item)\s+(.+?)(?:\s+at\s+|\s+price\s+|\s+for\s+|\s+in\s+|$)", text
        )
        if name_match:
            name = name_match.group(1).strip()
            # Remove category words from name
            for cat in ["food", "beverage", "dessert", "other"]:
                name = name.replace(cat, "").strip()
            if name:
                intent["name"] = name.title()

        return intent

    def _parse_stock_intent(self, text: str) -> Dict[str, Any]:
        """Parse stock-in intent."""
        intent: Dict[str, Any] = {
            "action": "stock_in",
            "item_name": None,
            "item_id": None,
            "quantity": None,
        }

        # Extract quantity
        qty_match = re.search(r"(\d+)\s+(?:units?|pcs?|pieces?|qty)?", text)
        if qty_match:
            intent["quantity"] = int(qty_match.group(1))

        # Try to match item
        items = self._extract_items(text)
        if items:
            intent["item_name"] = items[0]["name"]
            intent["item_id"] = items[0]["item_id"]

        return intent
