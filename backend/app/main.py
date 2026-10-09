import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import HTMLResponse, JSONResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from . import vault  # noqa: E402
from .intent import parse_intent  # noqa: E402
from .limits import evaluate  # noqa: E402
from .money import to_cents  # noqa: E402
from .reap import ReapError, call  # noqa: E402

app = FastAPI(title="Glance backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def public_url(request: Request) -> str:
    env = os.environ.get("PUBLIC_URL")
    if env:
        return env.rstrip("/")
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
    return f"{proto}://{host}"


COUNTRY = os.environ.get("SHOP_COUNTRY", "SG")
CURRENCY = os.environ.get("SHOP_CURRENCY", "SGD")
EMAIL = os.environ.get("BUYER_EMAIL", "demo@glance.app")
SIMULATE = os.environ.get("REAP_SIMULATE_CHECKOUT", "COMPLETED")
STATE_FILE = Path(os.environ.get("STATE_FILE", "/tmp/glance-state.json"))
DEFAULT_LIMIT_CENTS = 15000

SHIPPING_ADDRESS = {
    "firstName": os.environ.get("SHIP_FIRST_NAME", "Avery"),
    "lastName": os.environ.get("SHIP_LAST_NAME", "Tan"),
    "phone": os.environ.get("SHIP_PHONE", "+6591234567"),
    "addressLine1": os.environ.get("SHIP_LINE1", "65 Mohamed Sultan Road"),
    "city": os.environ.get("SHIP_CITY", "Singapore"),
    "state": os.environ.get("SHIP_STATE", "Singapore"),
    "postalCode": os.environ.get("SHIP_POSTAL", "239015"),
    "country": os.environ.get("SHIP_COUNTRY", "SG"),
}


def _load() -> dict:
    s = {"limitCents": DEFAULT_LIMIT_CENTS, "orders": [], "quotes": {}, "checkouts": {}, "enrollmentId": None}
    if STATE_FILE.exists():
        s.update(json.loads(STATE_FILE.read_text()))
    if "limit" in s:  # migrate float-era state
        s["limitCents"] = to_cents(s.pop("limit")) or DEFAULT_LIMIT_CENTS
    return s


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


_enrollment_cache: dict = {"at": 0.0, "value": None}


async def _enrollment() -> dict | None:
    eid = enrollment_id()
    if not eid:
        return None
    if _enrollment_cache["value"] and time.time() - _enrollment_cache["at"] < 60:
        return _enrollment_cache["value"]
    try:
        value = await call("GET", f"/agentic/enrollments/{eid}")
    except ReapError:
        return _enrollment_cache["value"]
    _enrollment_cache.update(at=time.time(), value=value)
    return value


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
    maxPriceCents: int | None = None


def _merchant(name) -> str | None:
    return None if not name or str(name).strip("-— ") == "" else name


def _product_out(p: dict) -> dict:
    pv = p.get("previewVariant") or {}
    pr = p.get("priceRange") or {}
    return {
        "id": p.get("id"),
        "name": p.get("name"),
        "merchant": _merchant((p.get("merchant") or {}).get("name")),
        "imageUrl": p.get("imageUrl"),
        "priceCents": to_cents(pv.get("price")) or to_cents(pr.get("min")),
        "variantId": pv.get("id"),
        "requiresShipping": True,
        "available": p.get("available", True),
    }


@app.post("/api/search")
async def search(body: SearchIn):
    filters: dict = {"availability": "AVAILABLE_ONLY"}
    if body.maxPriceCents:
        filters["price"] = {"max": f"{body.maxPriceCents // 100}.{body.maxPriceCents % 100:02d}"}
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
                p["priceCents"] = to_cents(dv.get("price")) or p["priceCents"]
                p["requiresShipping"] = dv.get("requiresShipping", True)
                p["description"] = d.get("description")
    priced = [p for p in products if p["priceCents"] is not None]
    within = [p for p in priced if body.maxPriceCents is None or p["priceCents"] <= body.maxPriceCents]
    pick = min(within or priced or products, key=lambda p: p["priceCents"] if p["priceCents"] is not None else 10**12)["id"] if products else None
    for i, p in enumerate(sorted(products, key=lambda p: (p["id"] != pick, p["priceCents"] if p["priceCents"] is not None else 10**12))):
        p["rank"] = i
    return {"searchId": data.get("id"), "products": products, "pickId": pick, "currency": CURRENCY, "warnings": data.get("warnings", [])}


class QuoteIn(BaseModel):
    variantId: str | None = None
    quoteId: str | None = None
    shippingOptionId: str | None = None
    requiresShipping: bool = True


def _quote_out(q: dict, meta: dict | None = None) -> dict:
    ab = q.get("amountBreakdown") or {}
    total = to_cents(ab.get("finalAmount"))
    decision = evaluate(total, int(STATE["limitCents"])).to_dict() if total is not None else None
    options = [
        {"id": o.get("id"), "name": o.get("name"), "priceCents": to_cents(o.get("price")), "selected": bool(o.get("selected", False))}
        for o in q.get("shippingOptions") or []
    ]
    return {
        "quoteId": q.get("id"),
        "shippingOptions": options,
        "itemCents": to_cents(ab.get("itemsSubtotal")),
        "shippingCents": to_cents(ab.get("shipping")),
        "taxCents": to_cents(ab.get("tax")),
        "discountCents": sum(to_cents(d) or 0 for d in ab.get("discounts") or []),
        "totalCents": total,
        "currency": ((ab.get("finalAmount") or {}).get("currency") if isinstance(ab.get("finalAmount"), dict) else None) or CURRENCY,
        "expiresAt": q.get("expiresAt"),
        "limit": decision,
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
        selected = next((o["id"] for o in q.get("shippingOptions") or [] if o.get("selected")), None)
        if body.shippingOptionId and body.shippingOptionId != selected:
            q = await call("POST", f"/agentic/quotes/{q['id']}/shipping-option", {"shippingOptionId": body.shippingOptionId})
    else:
        raise HTTPException(400, "variantId or quoteId+shippingOptionId required")
    out = _quote_out(q, meta)
    STATE["quotes"][q["id"]] = {**meta, "totalCents": out["totalCents"]}
    _save(STATE)
    return out


class ItemMeta(BaseModel):
    name: str | None = None
    merchant: str | None = None
    imageUrl: str | None = None


class CheckoutIn(BaseModel):
    quoteId: str
    item: ItemMeta | None = None
    deliveryName: str | None = None


def _expired(expires_at: str | None) -> bool:
    if not expires_at:
        return False
    try:
        return datetime.fromisoformat(expires_at.replace("Z", "+00:00")) <= datetime.now(timezone.utc)
    except ValueError:
        return False


@app.post("/api/checkout")
async def checkout(body: CheckoutIn, request: Request):
    eid = enrollment_id()
    if not eid:
        raise HTTPException(409, "no ACTIVE enrollment configured")
    q = await call("GET", f"/agentic/quotes/{body.quoteId}")
    out = _quote_out(q)
    if out["totalCents"] is None:
        raise HTTPException(502, "quote has no final amount")
    decision = evaluate(out["totalCents"], int(STATE["limitCents"]))
    if not decision.allowed:
        raise HTTPException(403, detail={"message": "total exceeds your per-purchase limit", **decision.to_dict()})
    if _expired(out["expiresAt"]):
        raise HTTPException(410, "quote expired, re-quote")
    extra = {"X-Simulate-Checkout": SIMULATE} if SIMULATE else None
    c = await call(
        "POST",
        "/agentic/checkouts",
        {"quoteId": body.quoteId, "enrollmentId": eid, "presentation": {"type": "REDIRECT", "returnUrl": f"{public_url(request)}/done?kind=checkout"}},
        idempotent=True,
        extra_headers=extra,
    )
    bal = await vault.balance()
    STATE["checkouts"][c["id"]] = {
        "quoteId": body.quoteId,
        "item": body.item.model_dump() if body.item else None,
        "deliveryName": body.deliveryName,
        "totalCents": out["totalCents"],
        "balanceBeforeCents": bal.get("balanceCents"),
    }
    _save(STATE)
    na = c.get("nextAction") or {}
    return {"checkoutId": c["id"], "status": c.get("status"), "approvalUrl": na.get("url"), "amountCents": to_cents(c.get("amount"))}


TERMINAL = {"COMPLETED", "FAILED", "CANCELED", "CANCELLED", "EXPIRED", "DECLINED"}


@app.get("/api/checkout/{cid}")
async def checkout_status(cid: str):
    c = await call("GET", f"/agentic/checkouts/{cid}")
    status = c.get("status")
    final = to_cents(c.get("finalAmount"))
    meta = STATE["checkouts"].get(cid, {})
    if status == "COMPLETED" and not any(o["checkoutId"] == cid for o in STATE["orders"]):
        STATE["orders"].insert(
            0,
            {
                "checkoutId": cid,
                "orderId": c.get("orderId"),
                "finalAmountCents": final,
                "item": meta.get("item"),
                "deliveryName": meta.get("deliveryName"),
                "at": int(time.time()),
            },
        )
        _save(STATE)
    bal = await vault.balance()
    return {
        "status": status,
        "terminal": status in TERMINAL,
        "orderId": c.get("orderId"),
        "finalAmountCents": final,
        "currency": CURRENCY,
        "item": meta.get("item"),
        "deliveryName": meta.get("deliveryName"),
        "vaultBeforeCents": meta.get("balanceBeforeCents"),
        "vaultAfterCents": bal.get("balanceCents"),
        "vaultSource": bal.get("source"),
    }


@app.get("/api/home")
async def home():
    bal = await vault.balance()
    enr = await _enrollment()
    last4 = ((enr or {}).get("paymentMethod") or {}).get("last4") or os.environ.get("CARD_LAST4")
    return {
        "vaultBalanceCents": bal.get("balanceCents"),
        "vaultSource": bal.get("source"),
        "vaultAddress": bal.get("vaultAddress"),
        "cardLast4": last4,
        "currency": CURRENCY,
        "limitCents": STATE["limitCents"],
        "orders": STATE["orders"][:20],
        "enrollmentActive": (enr or {}).get("status") == "ACTIVE",
    }


class LimitIn(BaseModel):
    perPurchaseCents: int


@app.put("/api/limit")
async def set_limit(body: LimitIn):
    if body.perPurchaseCents <= 0:
        raise HTTPException(400, "limit must be positive")
    STATE["limitCents"] = body.perPurchaseCents
    _save(STATE)
    return {"limitCents": STATE["limitCents"]}


@app.get("/done", response_class=HTMLResponse)
async def done(kind: str = "checkout"):
    deeplink = os.environ.get("APP_SCHEME", "glance") + f"://done?kind={kind}"
    return f"""<!doctype html><html><head><meta name=viewport content="width=device-width,initial-scale=1">
<title>Glance</title><style>body{{font-family:-apple-system,Segoe UI,Arial,sans-serif;display:flex;align-items:center;
justify-content:center;height:100vh;margin:0;background:#F3F5F8;color:#101828;text-align:center}}a{{color:#2343E0}}</style></head>
<body><div><h2>Done</h2><p>Returning to Glance&hellip;</p><p><a href="{deeplink}">Open Glance</a></p></div>
<script>try{{window.parent&&window.parent.postMessage({{glance:'done',kind:'{kind}'}},'*')}}catch(e){{}}
setTimeout(function(){{location.href='{deeplink}'}},300)</script></body></html>"""
