"""Birth-location resolver for 月相羅針 PoC v0.1.

PoC v0.1 is intentionally limited to Japan.  Location text is kept as an
independent concern so it can later be replaced by geocoding + latitude /
longitude + historical time-zone resolution without changing astronomy.py.
"""

from __future__ import annotations


POC_JAPAN_TIMEZONE = "Asia/Tokyo"


def resolve_location(location_text: str) -> dict[str, object]:
    """Resolve a PoC birth location to the fixed Japanese time zone."""
    cleaned = (location_text or "").strip()
    if not cleaned:
        raise ValueError("出生地を入力してください。")

    return {
        "input_name": cleaned,
        "timezone": POC_JAPAN_TIMEZONE,
        "latitude": None,
        "longitude": None,
        "scope": "PoC v0.1: 日本国内として固定処理",
    }
