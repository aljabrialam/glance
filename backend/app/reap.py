import os
import uuid
from typing import Any

import httpx

REAP_BASE = os.environ.get("REAP_BASE_URL", "https://sandbox.api.reap.global")


class ReapError(Exception):
    def __init__(self, method: str, path: str, body: Any, status: int, response: Any):
        self.method, self.path, self.body, self.status, self.response = method, path, body, status, response
        super().__init__(f"{method} {path} -> {status}: {response}")

    def detail(self) -> dict:
        return {
            "request": {"method": self.method, "path": self.path, "body": self.body},
            "status": self.status,
            "response": self.response,
        }


def _headers(idempotent: bool, extra: dict | None = None) -> dict:
    h = {
        "Authorization": f"Bearer {os.environ.get('REAP_API_KEY', '')}",
        "Reap-Version": os.environ.get("REAP_VERSION", "2025-02-14"),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if idempotent:
        h["Idempotency-Key"] = str(uuid.uuid4())
    if extra:
        h.update(extra)
    return h


async def call(method: str, path: str, body: Any = None, idempotent: bool = False, extra_headers: dict | None = None) -> Any:
    async with httpx.AsyncClient(base_url=REAP_BASE, timeout=60) as client:
        r = await client.request(method, path, json=body, headers=_headers(idempotent, extra_headers))
    try:
        data = r.json()
    except ValueError:
        data = r.text
    if r.status_code >= 400:
        raise ReapError(method, path, body, r.status_code, data)
    return data
