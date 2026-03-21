"""
Shared menu image helpers for Flet UI cards.

Loads local asset files via Flet's static assets directory so card rendering
does not send large base64 payloads over websockets.
"""

import base64
from functools import lru_cache
from pathlib import Path
from typing import Optional
IMAGE_DIR = Path(__file__).resolve().parent.parent / "assets" / "images"
IMAGE_MAP = {
    "Paneer Tikka": "paneer_tikka.jpg",
    "Samosa": "samosa.jpg",
    "Coke": "coke.jpg",
    "Lassi": "lassi.jpg",
    "Mango Juice": "mango_juice.jpg",
    "Naan": "butter_naan.jpg",
    "Butter Chicken": "butter_chicken.jpg",
    "Biryani": "biriyani.jpg",
    "Dosa": "dosa.jpg",
    "Masala Dosa": "masala_dosa.jpg",
    "Idli": "idli.jpg",
    "Ghee Dosa": "ghee_dosa.jpg",
}


@lru_cache(maxsize=None)
def get_menu_image_src(item_name: str) -> Optional[str]:
    """Return the relative src path for an image, e.g. /images/coke.jpg"""
    filename = IMAGE_MAP.get(item_name)
    if not filename:
        return None

    image_path = IMAGE_DIR / filename
    if not image_path.exists():
        return None

    return f"/images/{filename}"
