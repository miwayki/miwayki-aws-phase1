from typing import Any


def safe_get(data: dict[str, Any], *keys: str) -> Any:
    """Navega un dict anidado de forma segura."""
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current
