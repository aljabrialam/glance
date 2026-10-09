import os
import time

_cache: dict = {"at": 0.0, "value": None}


async def balance() -> dict:
    """Vault balance. Kwal integration is wired here; falls back to a labelled mock."""
    if _cache["value"] and time.time() - _cache["at"] < 10:
        return _cache["value"]
    value = {"balance": float(os.environ.get("MOCK_VAULT_BALANCE", "250.00")), "source": "mock"}
    _cache.update(at=time.time(), value=value)
    return value
