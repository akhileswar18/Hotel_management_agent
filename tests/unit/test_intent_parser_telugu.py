import uuid

from src.voice.intent_parser import IntentParser


class _FakeItem:
    def __init__(self, name: str):
        self.id = uuid.uuid4()
        self.name = name


class _FakeItemRepo:
    def __init__(self):
        self._items = [
            _FakeItem("biryani"),
            _FakeItem("naan"),
        ]

    def list(self):
        return self._items


def test_telugu_order_parsing_defaults_to_create_order():
    parser = IntentParser(item_repo=_FakeItemRepo())
    intent = parser.parse("రెండు బిర్యానీ, ఒక్క నాన్ టేబుల్ 5 నగదు", language="te-IN")

    assert intent["action"] == "create_order"
    assert intent["table_id"] == "5"
    assert intent["payment_method"] == "CASH"
    assert len(intent["items"]) == 2
    quantities = sorted(i["quantity"] for i in intent["items"])
    assert quantities == [1, 2]


def test_telugu_followup_prompt_uses_localized_text():
    parser = IntentParser(item_repo=_FakeItemRepo())
    pending = {"action": "create_order", "items": []}
    prompt = parser.get_followup_prompt(pending, language="te-IN")
    assert "టేబుల్" in prompt or "ఎలాంటి ఐటమ్స్" in prompt
