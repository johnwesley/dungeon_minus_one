"""Location data loading utilities.

Loads static location definitions from JSON files in this directory.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

LOCATIONS_DIR = Path(__file__).parent


@lru_cache(maxsize=64)
def load_location(location_id: str) -> Optional[dict]:
    """Load a location by ID from its JSON file.

    Args:
        location_id: The location identifier (filename without .json)

    Returns:
        Location data dict or None if not found
    """
    location_path = LOCATIONS_DIR / f"{location_id}.json"
    if not location_path.exists():
        return None
    return json.loads(location_path.read_text(encoding="utf-8"))


def list_locations() -> list[str]:
    """List all available location IDs."""
    return [p.stem for p in LOCATIONS_DIR.glob("*.json")]


def clear_location_cache() -> None:
    """Clear the location cache (useful after editing location files)."""
    load_location.cache_clear()
