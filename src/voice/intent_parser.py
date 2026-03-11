"""
Intent Parser — Parse natural language into structured intents for OrchestratorAgent.

Two-tier parsing strategy:
1. LLM-first (if configured): Uses Groq/OpenAI/Ollama to understand natural language
2. Rule-based fallback: Keyword matching when LLM is unavailable

Supports follow-up detection for conversational command flows.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import settings

logger = logging.getLogger("hms.intent_parser")


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
    "en": {
        "table_id": "Which table number?",
        "items": "What items would you like? (e.g., '2 biryani and 1 coke')",
        "payment_method": "Payment method? (cash, card, or voucher)",
        "name": "What is the product name?",
        "price": "What is the unit price (in ₹)?",
        "category": "What category? (food, beverage, dessert, other)",
        "item_name": "Which product?",
        "quantity": "How many units?",
        "reason": "Reason for voiding?",
    },
    "te": {
        "table_id": "ఏ టేబుల్ కోసం?",
        "items": "ఎలాంటి ఐటమ్స్ కావాలి? ఉదా: '2 బిర్యానీ 1 నాన్'.",
        "payment_method": "చెల్లింపు విధానం? (క్యాష్, కార్డ్, వౌచర్)",
        "name": "ఉత్పత్తి పేరు ఏమిటి?",
        "price": "యూనిట్ ధర ఎంత? (రూపాయల్లో)",
        "category": "వర్గం ఏమిటి? (ఆహారం, పానీయం మొదలైనవి)",
        "item_name": "ఎలాంటి ఉత్పత్తి?",
        "quantity": "ఎన్ని యూనిట్లు?",
        "reason": "రద్దు కారణం ఏమిటి?",
    },
}

TELUGU_NUMERAL_MAP = {
    "ఒకటి": "1",
    "ఒక": "1",
    "ఒక్క": "1",
    "రెండు": "2",
    "మూడు": "3",
    "నాలుగు": "4",
    "ఐదు": "5",
    "ఆరు": "6",
    "ఏడు": "7",
    "ఎనిమిది": "8",
    "తొమ్మిది": "9",
    "పది": "10",
}


class IntentParser:
    """Parse natural language into structured intents for the OrchestratorAgent.

    Uses LLM when available; falls back to rule-based parsing.
    """

    # LLM system prompt for command parsing (returns structured JSON)
    LLM_COMMAND_SYSTEM_PROMPT = """You are an intent parser for a hotel/restaurant management system.
Parse the user's natural language command into a structured JSON intent.

You MUST return ONLY valid JSON (no markdown, no explanation, no code fences).

Available actions and their required fields:
- create_order: table_id (string), items (array of {item_id, name, quantity}), payment_method (optional: CASH/CARD/VOUCHER)
- add_item: items (array of {item_id, name, quantity})
- finalize_order: payment_method (CASH/CARD/VOUCHER)
- void_order: reason (optional string)
- hold_order: (no extra fields)
- create_product: name (string), price (number), category (food/beverage/dessert/other)
- stock_in: item_name (string), quantity (number)
- report: type (daily_sales)

For items, use the item names as provided. Set item_id to empty string "" if unknown.
If the user mentions both items AND payment, set action to "create_order" with payment_method included.
If the user only says "pay cash" or "finalize", set action to "finalize_order".

Examples:
Input: "order 3 biryani and 2 coke for table 5 pay cash"
Output: {"action": "create_order", "table_id": "5", "items": [{"item_id": "", "name": "biryani", "quantity": 3}, {"item_id": "", "name": "coke", "quantity": 2}], "payment_method": "CASH"}

Input: "finalize order, pay by card"
Output: {"action": "finalize_order", "payment_method": "CARD"}

Input: "add 50 units of biryani to stock"
Output: {"action": "stock_in", "item_name": "biryani", "quantity": 50}

Input: "what are today's sales?"
Output: {"action": "report", "type": "daily_sales"}

Input: "new product paneer tikka at 350 food"
Output: {"action": "create_product", "name": "Paneer Tikka", "price": 350, "category": "food"}

    Input: "void the current order"
    Output: {"action": "void_order", "reason": "Customer request"}

    Return ONLY the JSON object. No other text."""
    LLM_COMMAND_SYSTEM_PROMPT_TE = """నీవు ఒక హోటల్/రెస్టారెంట్ మేనేజ్‌మెంట్ సిస్టం కోసం ఇంటెంట్ పార్సర్‌వి.
వాడుకరి చెప్పిన ఆదేశాన్ని స్ట్రక్చర్డ్ JSON లోకి మార్చాలి.

ప్రతిసారీ కేవలం చెల్లుబాటు అయ్యే JSON మాత్రమే ఇవ్వాలి. వివరణలు, కోడ్ బ్లాక్స్ వద్దు.

అందుబాటులో ఉన్న చర్యలు:
- create_order: table_id, items (పేరు, పరిమాణం), payment_method (CASH/CARD/VOUCHER)
- add_item: items
- finalize_order: payment_method
- void_order: reason (ఐచ్చికం)
- hold_order
- create_product: name, price, category
- stock_in: item_name, quantity
- report: type (daily_sales)

ఉదాహరణలు (Telugu, Hinglish రెండూ అనుమతించబడతాయి) ఇవ్వబడినవి. JSON మాత్రమే తిరిగి ఇవ్వాలి."""

    def __init__(self, item_repo=None, llm_client=None):
        from src.infrastructure import ItemRepository
        self.item_repo = item_repo or ItemRepository()
        self._llm = llm_client  # Lazy-loaded if None
        self._llm_loaded = llm_client is not None
        self.primary_language = settings.voice_primary_language
        self.fallback_languages = settings.voice_fallback_languages
        self._synonym_map = self._load_synonym_map(settings.menu_synonyms_file)

    @property
    def llm(self):
        """Lazy-load LLM client."""
        if not self._llm_loaded:
            self._llm_loaded = True
            try:
                from src.agents.llm_client import LLMClient
                client = LLMClient()
                if client.is_available:
                    self._llm = client
                    logger.info(f"IntentParser: LLM enabled ({client.provider}/{client.model})")
                else:
                    logger.info("IntentParser: LLM not available (no API key), using rule-based only")
            except Exception as e:
                logger.debug(f"IntentParser: Could not load LLM client: {e}")
        return self._llm

    def parse(self, text: str, language: Optional[str] = None) -> Dict[str, Any]:
        """Parse text into an intent dict using LLM (if available) with rule-based fallback.

        Returns:
            e.g. {"action": "create_order", "table_id": "5", "items": [...]}
        """
        language = language or self.primary_language
        lang_key = self._language_key(language)
        normalized_text = self._normalize_text(text, lang_key)

        # Try LLM first
        if self.llm:
            llm_result = self._parse_with_llm(text, lang_key)
            if llm_result and llm_result.get("action") != "unknown":
                llm_result["_parsed_by"] = "llm"
                # Enrich item_ids from inventory if LLM returned item names
                self._enrich_item_ids(llm_result)
                return llm_result

        # Fall back to rule-based parsing
        result = self._parse_rule_based(normalized_text, lang_key)
        result["_parsed_by"] = "rules"
        return result

    def _parse_with_llm(self, text: str, language: str) -> Optional[Dict[str, Any]]:
        """Use LLM to parse natural language into a structured intent."""
        try:
            # Build the prompt with available item catalog for context
            catalog_hint = self._get_catalog_hint()
            prompt = text
            if catalog_hint:
                prompt = f"Available menu items: {catalog_hint}\n\nUser command: {text}"

            system_prompt = self._build_system_prompt(language)
            raw = self.llm.query(prompt, system_prompt=system_prompt)
            if not raw:
                logger.debug("LLM returned empty response for intent parsing")
                return None

            # Parse JSON from LLM response (handle markdown code fences)
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                # Strip markdown code fences
                lines = cleaned.split("\n")
                cleaned = "\n".join(
                    line for line in lines
                    if not line.strip().startswith("```")
                )

            parsed = json.loads(cleaned)
            if isinstance(parsed, dict) and "action" in parsed:
                logger.info(f"LLM parsed intent: action={parsed.get('action')}")
                return parsed
            logger.debug(f"LLM returned invalid intent structure: {parsed}")
            return None
        except json.JSONDecodeError as e:
            logger.debug(f"LLM returned non-JSON: {e}")
            return None
        except Exception as e:
            logger.debug(f"LLM intent parsing failed: {e}")
            return None

    def _get_catalog_hint(self) -> str:
        """Get a compact list of available items for LLM context."""
        try:
            items = self.item_repo.list()
            if not items:
                return ""
            return ", ".join(item.name for item in items[:30])
        except Exception:
            return ""

    def _build_system_prompt(self, language: str) -> str:
        """Return bilingual system prompt based on language preference."""
        if language.startswith("te"):
            return self.LLM_COMMAND_SYSTEM_PROMPT_TE
        return self.LLM_COMMAND_SYSTEM_PROMPT

    def _enrich_item_ids(self, intent: Dict[str, Any]):
        """Fill in item_ids from inventory for items matched by name."""
        items = intent.get("items", [])
        if not items:
            return

        try:
            all_items = self.item_repo.list()
            name_to_id = {item.name.lower(): str(item.id) for item in all_items}
        except Exception:
            return

        for item in items:
            if not item.get("item_id") or item["item_id"] == "":
                name_lower = (item.get("name") or "").lower()
                # Exact match
                if name_lower in name_to_id:
                    item["item_id"] = name_to_id[name_lower]
                else:
                    # Partial match
                    for inv_name, inv_id in name_to_id.items():
                        if name_lower in inv_name or inv_name in name_lower:
                            item["item_id"] = inv_id
                            item["name"] = inv_name.title()
                            break

    def _parse_rule_based(self, text: str, language: str) -> Dict[str, Any]:
        """Rule-based intent parsing (original keyword-matching approach)."""
        text_lower = text.lower().strip()
        lang_key = self._language_key(language)

        # ── Specific compound phrases checked FIRST (before item-name matching) ──

        # Void order
        if any(kw in text_lower for kw in ["void", "cancel order", "రద్దు", "రద్దు చేయి"]):
            return self._parse_void_intent(text_lower)

        # Hold order
        if any(kw in text_lower for kw in ["hold order", "put on hold", "pause order", "హోల్డ్", "ఆపి పెట్టు"]):
            return {"action": "hold_order"}

        # Create product / new product  (must be before order check)
        if any(kw in text_lower for kw in ["new product", "create product", "add product", "new item"]):
            return self._parse_create_product_intent(text_lower)

        # Stock-in  (must be before order check — "add 50 biryani to stock" is stock, not order)
        if any(kw in text_lower for kw in ["stock in", "restock", "add stock", "add to stock",
                                             "to stock", "units of", "add inventory"]):
            return self._parse_stock_intent(text_lower)

        # Report
        if any(kw in text_lower for kw in ["report", "summary", "analytics", "sales", "రిపోర్ట్", "వివరాలు"]):
            return {"action": "report", "type": "daily_sales"}

        # ── Now check ordering vs finalize ──

        has_item_names = self._text_mentions_items(text_lower)
        finalize_keywords = [
            "finalize",
            "pay ",
            "payment",
            "checkout",
            "bill",
            "చెల్లించు",
            "బిల్లు",
        ]
        order_keywords = ["order", "want", "give me", "table", "ఆర్డర్", "కావాలి", "టేబుల్"]
        if lang_key == "te":
            order_keywords.extend(["ఇవ్వు", "పెట్టండీ"])
        has_finalize_kw = any(kw in text_lower for kw in finalize_keywords)
        has_order_kw = any(kw in text_lower for kw in order_keywords)

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
        if has_order_kw or any(kw in text_lower for kw in ["add", "get", "జోడించు"]):
            return self._parse_order_intent(text_lower)

        # Fallback: standalone pay/bill
        if has_finalize_kw:
            return self._parse_finalize_intent(text_lower)

        return {"action": "unknown", "original_text": text}

    def parse_followup(
        self, pending_intent: Dict[str, Any], text: str, language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Merge a follow-up answer into a pending (incomplete) intent.

        Uses LLM if available to understand the follow-up in context,
        then falls back to rule-based extraction.

        Args:
            pending_intent: The incomplete intent from a previous parse
            text: The user's follow-up answer

        Returns:
            Updated intent with the missing fields filled in
        """
        # Try LLM for follow-up understanding
        language = language or self.primary_language
        lang_key = self._language_key(language)

        if self.llm:
            llm_result = self._followup_with_llm(pending_intent, text, lang_key)
            if llm_result:
                self._enrich_item_ids(llm_result)
                llm_result["_parsed_by"] = "llm"
                return llm_result

        action = pending_intent.get("action", "")
        text_lower = self._normalize_text(text, lang_key)
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
            if "cash" in text_lower or "నగదు" in text_lower:
                pending_intent["payment_method"] = "CASH"
            elif "card" in text_lower or "కార్డ్" in text_lower or "కార్డు" in text_lower:
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

    def _followup_with_llm(
        self, pending_intent: Dict[str, Any], text: str, language: str
    ) -> Optional[Dict[str, Any]]:
        """Use LLM to merge follow-up answer into the pending intent."""
        try:
            missing = self.get_missing_fields(pending_intent)
            if not missing:
                return pending_intent

            prompt = (
                f"Previous incomplete command: {json.dumps(pending_intent)}\n"
                f"Missing fields: {missing}\n"
                f"User's follow-up answer: {text}\n\n"
                f"Merge the follow-up answer into the command and return the complete JSON intent. "
                f"Return ONLY valid JSON."
            )
            system_prompt = self._build_system_prompt(language)
            raw = self.llm.query(prompt, system_prompt=system_prompt)
            if not raw:
                return None

            cleaned = raw.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(
                    line for line in lines if not line.strip().startswith("```")
                )

            parsed = json.loads(cleaned)
            if isinstance(parsed, dict) and "action" in parsed:
                return parsed
        except Exception as e:
            logger.debug(f"LLM followup parsing failed: {e}")
        return None

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

    def get_followup_prompt(
        self, intent: Dict[str, Any], language: Optional[str] = None
    ) -> Optional[str]:
        """Generate a follow-up question for the first missing required field.

        Returns None if no fields are missing (intent is complete).
        """
        missing = self.get_missing_fields(intent)
        if not missing:
            return None

        lang_key = self._language_key(language or self.primary_language)
        prompts = [
            self._get_followup_prompt_text(lang_key, f) for f in missing
        ]
        return " ".join(prompts)

    def _language_key(self, language: Optional[str]) -> str:
        if not language:
            return "en"
        return language.split("-")[0].lower()

    def _normalize_text(self, text: str, lang_key: str) -> str:
        normalized = text.lower().strip()
        if lang_key == "te":
            normalized = self._replace_telugu_numbers(normalized)
        # Replace menu synonyms
        for canonical, synonyms in self._synonym_map.items():
            for synonym in synonyms:
                normalized = re.sub(
                    rf"\b{re.escape(synonym.lower())}\b", canonical, normalized
                )
        return normalized

    def _replace_telugu_numbers(self, text: str) -> str:
        updated = text
        for telugu, digit in TELUGU_NUMERAL_MAP.items():
            updated = updated.replace(telugu, digit)
        return updated

    def _get_followup_prompt_text(self, lang_key: str, field: str) -> str:
        prompt_map = FOLLOW_UP_PROMPTS.get(lang_key) or FOLLOW_UP_PROMPTS["en"]
        return (
            prompt_map.get(field)
            or FOLLOW_UP_PROMPTS["en"].get(field)
            or f"Please provide: {field}"
        )

    def _load_synonym_map(self, file_path: str) -> Dict[str, List[str]]:
        try:
            path = Path(file_path)
            if not path.exists():
                return {}
            data = json.loads(path.read_text(encoding="utf-8"))
            return {k.lower(): [s.lower() for s in v] for k, v in data.items()}
        except Exception:
            return {}

    # ---- Private parsing methods ----

    def _text_mentions_items(self, text: str) -> bool:
        """Quick check: does the text mention any known inventory item names?"""
        try:
            return bool(self._extract_items(text))
        except Exception:
            return False

    def _extract_items(self, text: str) -> List[Dict[str, Any]]:
        """Extract item names and quantities from text using fuzzy matching against inventory."""
        try:
            all_items = self.item_repo.list()
        except Exception:
            all_items = []

        item_names = {item.name.lower(): item for item in all_items}
        for canonical, synonyms in self._synonym_map.items():
            if canonical in item_names:
                for synonym in synonyms:
                    item_names.setdefault(synonym, item_names[canonical])
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
        table_match = re.search(r"(?:table|టేబుల్)\s*(\d+)", text)
        if table_match:
            intent["table_id"] = table_match.group(1)

        # Extract payment method
        if "cash" in text:
            intent["payment_method"] = "CASH"
        elif "card" in text:
            intent["payment_method"] = "CARD"
        elif "నగదు" in text:
            intent["payment_method"] = "CASH"
        elif "కార్డ్" in text or "కార్డు" in text:
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
        elif "నగదు" in text:
            intent["payment_method"] = "CASH"
        elif "కార్డ్" in text or "కార్డు" in text:
            intent["payment_method"] = "CARD"

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
