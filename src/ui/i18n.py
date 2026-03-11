"""
Internationalization (i18n) Framework

Simple key-based translation system for HMS UI.
Supports English (default) and Hindi.
"""

from typing import Dict, Optional


# Translation dictionaries
_translations: Dict[str, Dict[str, str]] = {
    "en": {
        "app.title": "Hotel Management System",
        "pos.new_order": "New Order",
        "pos.finalize": "Finalize",
        "pos.hold": "Hold",
        "pos.resume": "Resume",
        "pos.void": "Void Order",
        "pos.discount": "Apply Discount",
        "pos.table": "Table",
        "pos.items": "Items",
        "pos.subtotal": "Subtotal",
        "pos.tax": "Tax (18%)",
        "pos.total": "Total",
        "pos.logout": "Logout",
        "nav.pos": "POS",
        "nav.products": "Products",
        "nav.orders": "Orders",
        "nav.reports": "Reports",
        "nav.users": "Users",
        "auth.username": "Username",
        "auth.pin": "PIN Code",
        "auth.login": "Login",
        "products.add": "Add New Product",
        "products.stock_in": "Stock In",
        "reports.sales": "Sales Summary",
        "reports.inventory": "Inventory",
        "reports.export": "Export CSV",
        "users.add": "Add New User",
        "users.edit_role": "Edit Role",
        "users.reset_pin": "Reset PIN",
        "receipt.print": "Print Receipt",
        "receipt.email": "Email Receipt",
        "receipt.thankyou": "Thank you for dining with us!",
        "common.save": "Save",
        "common.cancel": "Cancel",
        "common.ok": "OK",
        "common.error": "Error",
        "common.success": "Success",
        "common.search": "Search",
        "common.back": "Back",
    },
    "te": {
        "app.title": "హోటల్ మేనేజ్‌మెంట్ సిస్టం",
        "pos.new_order": "కొత్త ఆర్డర్",
        "pos.finalize": "ఫైనల్ చేయి",
        "pos.hold": "హోల్డ్",
        "pos.resume": "తిరిగి ప్రారంభించు",
        "pos.void": "ఆర్డర్ రద్దు",
        "pos.discount": "డిస్కౌంట్ పెట్టు",
        "pos.table": "టేబుల్",
        "pos.items": "ఐటమ్స్",
        "pos.subtotal": "సబ్‌టొటల్",
        "pos.tax": "పన్ను (18%)",
        "pos.total": "మొత్తం",
        "pos.logout": "లాగ్ అవుట్",
        "nav.pos": "పీవోఎస్",
        "nav.products": "ఉత్పత్తులు",
        "nav.orders": "ఆర్డర్స్",
        "nav.reports": "రిపోర్ట్స్",
        "nav.users": "యూజర్లు",
        "auth.username": "యూజర్ పేరు",
        "auth.pin": "పిన్ కోడ్",
        "auth.login": "లాగిన్",
        "products.add": "కొత్త ఉత్పత్తి",
        "products.stock_in": "స్టాక్ ఇన్",
        "reports.sales": "సేల్స్ సమ్మరీ",
        "reports.inventory": "ఇన్వెంటరీ",
        "reports.export": "సిఎస్‌వి ఎగుమతి",
        "users.add": "కొత్త యూజర్",
        "users.edit_role": "రోల్ మార్చు",
        "users.reset_pin": "పిన్ రీసెట్",
        "receipt.print": "రశీదు ముద్రించు",
        "receipt.email": "రశీదు మెయిల్ చేయి",
        "receipt.thankyou": "మా దగ్గర భోజనం చేసినందుకు ధన్యవాదాలు!",
        "common.save": "సేవ్",
        "common.cancel": "రద్దు",
        "common.ok": "సరే",
        "common.error": "లోపం",
        "common.success": "విజయం",
        "common.search": "వెతుకు",
        "common.back": "వెంటకు",
    },
    "hi": {
        "app.title": "होटल प्रबंधन प्रणाली",
        "pos.new_order": "नया ऑर्डर",
        "pos.finalize": "अंतिम रूप",
        "pos.hold": "रोकें",
        "pos.resume": "जारी रखें",
        "pos.void": "ऑर्डर रद्द",
        "pos.discount": "छूट लागू करें",
        "pos.table": "टेबल",
        "pos.items": "आइटम",
        "pos.subtotal": "उप-योग",
        "pos.tax": "कर (18%)",
        "pos.total": "कुल",
        "pos.logout": "लॉग आउट",
        "nav.pos": "POS",
        "nav.products": "उत्पाद",
        "nav.orders": "ऑर्डर",
        "nav.reports": "रिपोर्ट",
        "nav.users": "उपयोगकर्ता",
        "auth.username": "उपयोगकर्ता नाम",
        "auth.pin": "पिन कोड",
        "auth.login": "लॉग इन",
        "receipt.thankyou": "हमारे साथ भोजन करने के लिए धन्यवाद!",
        "common.save": "सहेजें",
        "common.cancel": "रद्द करें",
        "common.ok": "ठीक",
        "common.error": "त्रुटि",
        "common.success": "सफलता",
        "common.search": "खोजें",
        "common.back": "वापस",
    },
}

# Current language (default English)
_current_lang = "en"


def set_language(lang: str) -> None:
    """Set the current language."""
    global _current_lang
    if lang in _translations:
        _current_lang = lang
    else:
        raise ValueError(f"Unsupported language: {lang}. Available: {list(_translations.keys())}")


def get_language() -> str:
    """Get the current language code."""
    return _current_lang


def t(key: str, **kwargs) -> str:
    """
    Translate a key to the current language.

    Falls back to English if key not found in current language.
    Falls back to the key itself if not found in any language.

    Args:
        key: Translation key (e.g., "pos.new_order")
        **kwargs: Format arguments for string interpolation
    """
    # Try current language
    text = _translations.get(_current_lang, {}).get(key)

    # Fallback to English
    if text is None:
        text = _translations.get("en", {}).get(key)

    # Fallback to key
    if text is None:
        text = key

    # Apply format args
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass

    return text


def get_available_languages() -> list:
    """Get list of available language codes."""
    return list(_translations.keys())
