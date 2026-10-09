import asyncio
import os
import sys
import time

_cache: dict = {"at": 0.0, "value": None}


def _kwal_balance() -> dict | None:
    scripts = os.environ.get("KWAL_SCRIPTS")
    if not scripts:
        return None
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from pws_client import CredentialStore, read_funding, resolve_credentials_path

    creds = CredentialStore(resolve_credentials_path()).load()
    if creds.is_expired(int(time.time())):
        return {"balance": None, "source": "kwal", "error": "Kwal session expired"}
    f = read_funding(creds.service_url, creds.token)
    bal = f.available.minor_units / 10 ** f.available.decimals if f.available else 0.0
    return {"balance": bal, "source": "kwal", "state": f.state, "vaultAddress": f.vault_address}


async def balance() -> dict:
    """Live Kwal vault balance when KWAL_SCRIPTS + credentials exist; otherwise a labelled mock."""
    if _cache["value"] and time.time() - _cache["at"] < 10:
        return _cache["value"]
    value = None
    try:
        value = await asyncio.to_thread(_kwal_balance)
    except Exception as e:  # surface, then fall back
        value = {"balance": None, "source": "kwal", "error": str(e)}
    if value is None or value.get("balance") is None:
        mock = {"balance": float(os.environ.get("MOCK_VAULT_BALANCE", "250.00")), "source": "mock"}
        if value and value.get("error"):
            mock["kwalError"] = value["error"]
        value = mock
    _cache.update(at=time.time(), value=value)
    return value
