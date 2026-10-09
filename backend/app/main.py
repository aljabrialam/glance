import json
import os
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from . import vault
from .intent import parse_intent
from .reap import ReapError, call

app = FastAPI(title="Glance backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])



def public_url(request: Request) -> str:
    env = os.environ.get("PUBLIC_URL")
    if env:
        return env.rstrip("/")
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
    return f"{proto}://{host}"

COUNTRY = os.environ.get("SHOP_COUNTRY", "US")
CURRENCY = os.environ.get("SHOP_CURRENCY", "USD")
EMAIL = os.environ.get("BUYER_EMAIL", "demo@glance.app")
SIMULATE = os.environ.get("REAP_SIMULATE_CHECKOUT", "COMPLETED")
STATE_FILE = Path(os.environ.get("STATE_FILE", "/tmp/glance-state.json"))

SHIPPING_ADDRESS = {
    "firstName": os.environ.get("SHIP_FIRST_NAME", "Avery"),
    "lastName": os.environ.get("SHIP_LAST_NAME", "Tan"),
    "phone": os.environ.get("SHIP_PHONE", "+14155550100"),
    "addressLine1": os.environ.get("SHIP_LINE1", "1 Market St"),
    "city": os.environ.get("SHIP_CITY", "San Francisco"),
    "state": os.environ.get("SHIP_STATE", "CA"),
    "postalCode": os.environ.get("SHIP_POSTAL", "94105"),
    "country": os.environ.get("SHIP_COUNTRY", "US"),
}


def _load() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"limit": 150.0, "orders": [], "quotes": {}, "checkouts": {}, "enrollmentId": None}


def _save(s: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(s))


STATE = _load()


def enrollment_id() -> str | None:
    return os.environ.get("REAP_ENROLLMENT_ID") or STATE.get("enrollmentId")


@app.exception_handler(ReapError)
async def reap_error(_, e: ReapError):
    print(f"REAP ERROR {json.dumps(e.detail())}")
    return JSONResponse(status_code=502, content={"error": "reap", **e.detail()})


def money(m) -> float | None:
    if m is None:
        return None
    if isinstance(m, dict):
        if "amount" in m and isinstance(m["amount"], dict):
            return money(m["amount"])
        return float(m.get("amount")) if m.get("amount") is not None else None
    return float(m)


@app.get("/health")
async def health():
    return {"ok": True, "enrollment": bool(enrollment_id()), "reapKey": bool(os.environ.get("REAP_API_KEY"))}


# ---------- enrollment (one-time setup) ----------

class EnrollIn(BaseModel):
    email: str | None = None
    customerId: str = "glance-demo-user"


@app.post("/api/enroll")
async def enroll(body: EnrollIn, request: Request):
    data = await call(
        "POST",
        "/agentic/enrollments",
        {
            "source": "EXTERNAL",
            "owner": {"type": "CLIENT_REFERENCE", "id": body.customerId, "email": body.email or EMAIL},
            "presentation": {"type": "REDIRECT", "returnUrl": f"{public_url(request)}/done?kind=enrollment"},
        },
        idempotent=True,
    )
    STATE["enrollmentId"] = data.get("id")
    _save(STATE)
    return data


@app.get("/api/enrollment")
async def get_enrollment():
    eid = enrollment_id()
    if not eid:
        raise HTTPException(404, "no enrollment yet")
    return await call("GET", f"/agentic/enrollments/{eid}")


# ---------- purchase flow ----------

class IntentIn(BaseModel):
    text: str


@app.post("/api/intent")
async def intent(body: IntentIn):
    return await parse_intent(body.text)


class SearchIn(BaseModel):
    query: str
    maxPrice: float | None = None


def _product_out(p: dict) -> dict:
    pv = p.get("previewVariant") or {}
    pr = p.get("priceRange") or {}
    return {
        "id": p.get("id"),
        "name": p.get("name"),
        "merchant": (p.get("merchant") or {}).get("name"),
        "imageUrl": p.get("imageUrl"),
        "price": money(pv.get("price")) or money(pr.get("min")),
        "priceMax": money(pr.get("max")),
        "variantId": pv.get("id"),
        "available": p.get("available", True),
    }


@app.post("/api/search")
async def search(body: SearchIn):
    filters: dict = {"availability": "AVAILABLE_ONLY"}
    if body.maxPrice:
        filters["price"] = {"max": str(body.maxPrice)}
    data = await call(
        "POST",
        "/agentic/products/search",
        {"query": body.query, "context": {"country": COUNTRY, "currency": CURRENCY}, "filters": filters, "pagination": {"limit": 10}},
    )
    products = [_product_out(p) for p in data.get("products", [])][:3]
    if products:
        details = await call("POST", "/agentic/products/details", {"productIds": [p["id"] for p in products]})
        by_id = {d["id"]: d for d in details.get("products", [])}
        for p in products:
            d = by_id.get(p["id"])
            if d and d.get("defaultVariant"):
                dv = d["defaultVariant"]
                p["variantId"] = dv.get("id") or p["variantId"]
                p["price"] = money(dv.get("price")) or p["price"]
                p["requiresShipping"] = dv.get("requiresShipping", True)
                p["description"] = d.get("description")
    # agent's pick: cheapest within budget, else cheapest
    within = [p for p in products if p["price"] is not None and (body.maxPrice is None or p["price"] <= body.maxPrice)]
    pick = min(within or products, key=lambda p: p["price"] or 1e9)["id"] if products else None
    return {"searchId": data.get("id"), "products": products, "pickId": pick, "warnings": data.get("warnings", [])}


class QuoteIn(BaseModel):
    variantId: str | None = None
    quoteId: str | None = None
    shippingOptionId: str | None = None
    requiresShipping: bool = True


def _quote_out(q: dict, meta: dict | None = None) -> dict:
    ab = q.get("amountBreakdown") or {}
    total = money(ab.get("finalAmount"))
    limit = float(STATE["limit"])
    return {
        "quoteId": q.get("id"),
        "shippingOptions": [
            {"id": o.get("id"), "name": o.get("name"), "price": money(o.get("price")), "selected": o.get("selected", False)}
            for o in q.get("shippingOptions") or []
        ],
        "subtotal": money(ab.get("itemsSubtotal")),
        "shipping": money(ab.get("shipping")),
        "tax": money(ab.get("tax")),
        "discounts": sum(money(d) or 0 for d in ab.get("discounts") or []),
        "total": total,
        "currency": ((ab.get("finalAmount") or {}).get("currency")) or CURRENCY,
        "expiresAt": q.get("expiresAt"),
        "limit": limit,
        "overLimit": total is not None and total > limit,
        "overBy": round(total - limit, 2) if total is not None and total > limit else 0,
        "item": (meta or {}).get("item"),
    }


@app.post("/api/quote")
async def quote(body: QuoteIn):
    if body.quoteId and body.shippingOptionId:
        q = await call("POST", f"/agentic/quotes/{body.quoteId}/shipping-option", {"shippingOptionId": body.shippingOptionId})
        meta = STATE["quotes"].get(body.quoteId, {})
    elif body.variantId:
        req: dict = {"items": [{"variantId": body.variantId, "quantity": 1}], "email": EMAIL}
        if body.requiresShipping:
            req["shippingAddress"] = SHIPPING_ADDRESS
        q = await call("POST", "/agentic/quotes", req, idempotent=True)
        meta = {"variantId": body.variantId}
        if body.shippingOptionId and body.shippingOptionId != next(
            (o["id"] for o in q.get("shippingOptions") or [] if o.get("selected")), None
        ):
            q = await call("POST", f"/agentic/quotes/{q['id']}/shipping-option", {"shippingOptionId": body.shippingOptionId})
    else:
        raise HTTPException(400, "variantId or quoteId+shippingOptionId required")
    out = _quote_out(q, meta)
    STATE["quotes"][q["id"]] = {**meta, "total": out["total"]}
    _save(STATE)
    return out


class ItemMeta(BaseModel):
    name: str | None = None
    merchant: str | None = None
    imageUrl: str | None = None


class CheckoutIn(BaseModel):
    quoteId: str
    item: ItemMeta | None = None


@app.post("/api/checkout")
async def checkout(body: CheckoutIn, request: Request):
    eid = enrollment_id()
    if not eid:
        raise HTTPException(409, "no ACTIVE enrollment configured")
    q = await call("GET", f"/agentic/quotes/{body.quoteId}")
    out = _quote_out(q)
    if out["overLimit"]:
        raise HTTPException(403, f"total {out['total']} exceeds limit {out['limit']}")
    if out["expiresAt"]:
        from datetime import datetime, timezone

        try:
            if datetime.fromisoformat(out["expiresAt"].replace("Z", "+00:00")) <= datetime.now(timezone.utc):
                raise HTTPException(410, "quote expired, re-quote")
        except ValueError:
            pass
    extra = {"X-Simulate-Checkout": SIMULATE} if SIMULATE else None
    c = await call(
        "POST",
        "/agentic/checkouts",
        {"quoteId": body.quoteId, "enrollmentId": eid, "presentation": {"type": "REDIRECT", "returnUrl": f"{public_url(request)}/done?kind=checkout"}},
        idempotent=True,
        extra_headers=extra,
    )
    STATE["checkouts"][c["id"]] = {
        "quoteId": body.quoteId,
        "item": body.item.model_dump() if body.item else None,
        "total": out["total"],
        "balanceBefore": (await vault.balance()).get("balance"),
    }
    _save(STATE)
    na = c.get("nextAction") or {}
    return {"checkoutId": c["id"], "status": c.get("status"), "approvalUrl": na.get("url"), "amount": money(c.get("amount"))}


TERMINAL = {"COMPLETED", "FAILED", "CANCELED", "CANCELLED", "EXPIRED", "DECLINED"}


@app.get("/api/checkout/{cid}")
async def checkout_status(cid: str):
    c = await call("GET", f"/agentic/checkouts/{cid}")
    status = c.get("status")
    final = money(c.get("finalAmount"))
    meta = STATE["checkouts"].get(cid, {})
    if status == "COMPLETED" and not any(o["checkoutId"] == cid for o in STATE["orders"]):
        STATE["orders"].insert(
            0,
            {
                "checkoutId": cid,
                "orderId": c.get("orderId"),
                "finalAmount": final,
                "item": meta.get("item"),
                "at": int(time.time()),
            },
        )
        _save(STATE)
    bal = await vault.balance()
    return {
        "status": status,
        "terminal": status in TERMINAL,
        "orderId": c.get("orderId"),
        "finalAmount": final,
        "item": meta.get("item"),
        "vaultBefore": meta.get("balanceBefore"),
        "vaultAfter": bal.get("balance"),
        "vaultSource": bal.get("source"),
        "raw": c,
    }


@app.get("/api/home")
async def home():
    bal = await vault.balance()
    return {
        "vaultBalance": bal.get("balance"),
        "vaultSource": bal.get("source"),
        "vaultAddress": bal.get("address"),
        "cardLast4": bal.get("cardLast4") or os.environ.get("CARD_LAST4", "4242"),
        "limit": STATE["limit"],
        "orders": STATE["orders"][:20],
        "enrollmentId": enrollment_id(),
    }


class LimitIn(BaseModel):
    perPurchase: float


@app.put("/api/limit")
async def set_limit(body: LimitIn):
    if body.perPurchase <= 0:
        raise HTTPException(400, "limit must be positive")
    STATE["limit"] = round(body.perPurchase, 2)
    _save(STATE)
    return {"limit": STATE["limit"]}


@app.get("/done", response_class=HTMLResponse)
async def done(kind: str = "checkout"):
    deeplink = os.environ.get("APP_SCHEME", "glance") + f"://done?kind={kind}"
    return f"""<!doctype html><html><head><meta name=viewport content="width=device-width,initial-scale=1">
<title>Glance</title><style>body{{font-family:-apple-system,Segoe UI,Arial,sans-serif;display:flex;align-items:center;
justify-content:center;height:100vh;margin:0;background:#F3F5F8;color:#101828;text-align:center}}a{{color:#2343E0}}</style></head>
<body><div><h2>Done</h2><p>Returning to Glance&hellip;</p><p><a href="{deeplink}">Open Glance</a></p></div>
<script>try{{window.parent&&window.parent.postMessage({{glance:'done',kind:'{kind}'}},'*')}}catch(e){{}}
setTimeout(function(){{location.href='{deeplink}'}},300)</script></body></html>"""
