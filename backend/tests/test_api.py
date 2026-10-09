"""Endpoint tests with Reap mocked at app.main.call. Test names carry the AC they prove."""
import pytest
from httpx import ASGITransport, AsyncClient

import app.main as m
from app.reap import ReapError

pytestmark = pytest.mark.asyncio

SEARCH = {
    "id": "srch_1",
    "products": [
        {"id": "p1", "name": "Anker Nano USB-C Hub 8-in-1", "merchant": {"name": "anker.com.sg"}, "previewVariant": {"id": "v1", "price": {"amount": "72.90", "currency": "SGD"}}},
        {"id": "p2", "name": "Anker 7-in-1 Hub", "merchant": {"name": "anker.com.sg"}, "previewVariant": {"id": "v2", "price": {"amount": "59.90", "currency": "SGD"}}},
        {"id": "p3", "name": "Anker Dock", "merchant": {"name": "anker.com.sg"}, "previewVariant": {"id": "v3", "price": {"amount": "189.00", "currency": "SGD"}}},
        {"id": "p4", "name": "Fourth thing", "merchant": {"name": "x"}, "previewVariant": {"id": "v4", "price": {"amount": "1.00", "currency": "SGD"}}},
    ],
}
DETAILS = {"products": [{"id": "p1", "defaultVariant": {"id": "v1", "price": {"amount": "72.90", "currency": "SGD"}, "requiresShipping": True}}]}


def quote_doc(total="84.90", shipping="5.00", selected="std", expires="2999-01-01T00:00:00Z"):
    return {
        "id": "q1",
        "amountBreakdown": {
            "itemsSubtotal": {"amount": "72.90", "currency": "SGD"},
            "shipping": {"amount": shipping, "currency": "SGD"},
            "tax": {"amount": "7.00", "currency": "SGD"},
            "finalAmount": {"amount": total, "currency": "SGD"},
        },
        "shippingOptions": [
            {"id": "std", "name": "Standard", "price": {"amount": "5.00", "currency": "SGD"}, "selected": selected == "std"},
            {"id": "exp", "name": "Express", "price": {"amount": "13.00", "currency": "SGD"}, "selected": selected == "exp"},
        ],
        "expiresAt": expires,
    }


class FakeReap:
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    async def __call__(self, method, path, body=None, idempotent=False, extra_headers=None):
        self.calls.append({"method": method, "path": path, "body": body, "idempotent": idempotent, "headers": extra_headers or {}})
        for (meth, prefix), resp in self.routes.items():
            if method == meth and path.startswith(prefix):
                if isinstance(resp, Exception):
                    raise resp
                return resp
        raise AssertionError(f"unexpected Reap call {method} {path}")


@pytest.fixture
def state(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(m, "STATE", {"limitCents": 15000, "orders": [], "quotes": {}, "checkouts": {}, "enrollmentId": "enr_1"})
    monkeypatch.setenv("REAP_ENROLLMENT_ID", "enr_1")
    monkeypatch.setenv("PUBLIC_URL", "https://glance.example.com")
    m._enrollment_cache.update(at=0.0, value=None)

    async def mock_balance():
        return {"balanceCents": 25000, "source": "mock"}

    monkeypatch.setattr(m.vault, "balance", mock_balance)
    return m.STATE


@pytest.fixture
def reap(monkeypatch):
    def install(routes):
        fake = FakeReap(routes)
        monkeypatch.setattr(m, "call", fake)
        return fake

    return install


@pytest.fixture
async def client(state):
    async with AsyncClient(transport=ASGITransport(app=m.app), base_url="http://t") as c:
        yield c


async def test_AC_001_01_intent_returns_query_and_ceiling_in_cents(client):
    r = await client.post("/api/intent", json={"text": "Buy an Anker Nano USB-C hub, under S$150"})
    assert r.status_code == 200
    assert r.json()["query"] == "an Anker Nano USB-C hub"
    assert r.json()["maxPriceCents"] == 15000


async def test_AC_001_01_intent_without_price_returns_null_ceiling(client):
    r = await client.post("/api/intent", json={"text": "Buy an Anker Nano USB-C hub"})
    assert r.json()["maxPriceCents"] is None


async def test_AC_001_02_search_returns_at_most_three_products_with_cheapest_within_ceiling_picked(client, reap):
    fake = reap({("POST", "/agentic/products/search"): SEARCH, ("POST", "/agentic/products/details"): DETAILS})
    r = await client.post("/api/search", json={"query": "Anker hub", "maxPriceCents": 15000})
    body = r.json()
    assert r.status_code == 200
    assert len(body["products"]) == 3
    assert body["pickId"] == "p2"  # cheapest within ceiling among the top three
    p1 = next(p for p in body["products"] if p["id"] == "p1")
    assert p1["priceCents"] == 7290 and p1["variantId"] == "v1"
    search_call = fake.calls[0]
    assert search_call["body"]["context"] == {"country": "SG", "currency": "SGD"}
    assert search_call["body"]["filters"]["price"] == {"max": "150.00"}


async def test_AC_001_03_quote_is_itemised_in_cents_with_delivery_options_and_total(client, reap):
    fake = reap({("POST", "/agentic/quotes"): quote_doc()})
    r = await client.post("/api/quote", json={"variantId": "v1"})
    q = r.json()
    assert r.status_code == 200
    assert (q["itemCents"], q["shippingCents"], q["taxCents"], q["totalCents"]) == (7290, 500, 700, 8490)
    assert [o["id"] for o in q["shippingOptions"]] == ["std", "exp"]
    assert q["limit"] == {"limitCents": 15000, "totalCents": 8490, "allowed": True, "overByCents": 0, "remainingCents": 6510}
    assert fake.calls[0]["idempotent"] is True
    assert fake.calls[0]["body"]["shippingAddress"]["country"] == "SG"


async def test_AC_001_04_checkout_within_limit_starts_provider_approval_with_https_return_url(client, reap):
    fake = reap({
        ("GET", "/agentic/quotes/q1"): quote_doc(),
        ("POST", "/agentic/checkouts"): {"id": "co_1", "status": "REQUIRES_ACTION", "nextAction": {"url": "https://pay.reap.test/approve/co_1"}},
    })
    r = await client.post("/api/checkout", json={"quoteId": "q1", "item": {"name": "Anker Nano"}, "deliveryName": "Standard"})
    assert r.status_code == 200
    assert r.json()["approvalUrl"] == "https://pay.reap.test/approve/co_1"
    co = fake.calls[-1]
    assert co["body"]["enrollmentId"] == "enr_1"
    assert co["body"]["presentation"]["returnUrl"].startswith("https://glance.example.com/done")
    assert co["idempotent"] is True


async def test_AC_001_05_status_reports_order_reference_and_amount_actually_charged(client, reap, state):
    state["checkouts"]["co_1"] = {"quoteId": "q1", "totalCents": 8490, "item": {"name": "Anker Nano"}, "deliveryName": "Standard", "balanceBeforeCents": 25000}
    reap({("GET", "/agentic/checkouts/co_1"): {"id": "co_1", "status": "COMPLETED", "orderId": "ORD-42", "finalAmount": {"amount": "84.50", "currency": "SGD"}}})
    r = await client.get("/api/checkout/co_1")
    s = r.json()
    assert s["terminal"] is True and s["orderId"] == "ORD-42"
    assert s["finalAmountCents"] == 8450  # provider's figure, not the 8490 quote
    assert state["orders"][0]["orderId"] == "ORD-42" and state["orders"][0]["finalAmountCents"] == 8450


async def test_AC_001_08_checkout_over_limit_is_refused_before_any_provider_checkout(client, reap, state):
    state["limitCents"] = 8000
    fake = reap({("GET", "/agentic/quotes/q1"): quote_doc(total="84.90")})
    r = await client.post("/api/checkout", json={"quoteId": "q1"})
    assert r.status_code == 403
    assert r.json()["detail"]["overByCents"] == 490
    assert all(c["path"] != "/agentic/checkouts" for c in fake.calls)


async def test_AC_001_10_new_limit_applies_to_next_quote_evaluation(client, reap):
    reap({("POST", "/agentic/quotes"): quote_doc(total="84.90")})
    assert (await client.post("/api/quote", json={"variantId": "v1"})).json()["limit"]["allowed"] is True
    r = await client.put("/api/limit", json={"perPurchaseCents": 8000})
    assert r.json() == {"limitCents": 8000}
    q = (await client.post("/api/quote", json={"variantId": "v1"})).json()
    assert q["limit"]["allowed"] is False and q["limit"]["overByCents"] == 490


async def test_AC_001_10_limit_must_be_positive_integer_cents(client):
    assert (await client.put("/api/limit", json={"perPurchaseCents": 0})).status_code == 400
    assert (await client.put("/api/limit", json={"perPurchaseCents": 150.5})).status_code == 422


async def test_AC_001_11_changing_delivery_option_reprices_and_reevaluates(client, reap, state):
    state["quotes"]["q1"] = {"variantId": "v1", "totalCents": 8490}
    reap({("POST", "/agentic/quotes/q1/shipping-option"): quote_doc(total="92.90", shipping="13.00", selected="exp")})
    r = await client.post("/api/quote", json={"quoteId": "q1", "shippingOptionId": "exp"})
    q = r.json()
    assert q["shippingCents"] == 1300 and q["totalCents"] == 9290
    assert q["limit"]["remainingCents"] == 5710
    assert next(o for o in q["shippingOptions"] if o["selected"])["id"] == "exp"


async def test_AC_001_13_home_reports_vault_card_limit_and_session_orders(client, reap, state):
    state["orders"] = [{"checkoutId": "co_1", "orderId": "ORD-42", "finalAmountCents": 8450, "item": None, "deliveryName": "Standard", "at": 1}]
    reap({("GET", "/agentic/enrollments/enr_1"): {"id": "enr_1", "status": "ACTIVE", "paymentMethod": {"last4": "1712"}}})
    h = (await client.get("/api/home")).json()
    assert h["vaultBalanceCents"] == 25000 and h["vaultSource"] == "mock"
    assert h["cardLast4"] == "1712" and h["enrollmentActive"] is True
    assert h["limitCents"] == 15000 and h["orders"][0]["orderId"] == "ORD-42"


async def test_AC_001_15_provider_error_is_surfaced_verbatim_and_not_retried(client, reap):
    err = ReapError("POST", "/agentic/products/search", {"query": "x"}, 400, {"code": "INVALID_VERSION", "message": "Reap-Version required"})
    fake = reap({("POST", "/agentic/products/search"): err})
    r = await client.post("/api/search", json={"query": "x"})
    assert r.status_code == 502
    assert r.json()["response"] == {"code": "INVALID_VERSION", "message": "Reap-Version required"}
    assert r.json()["request"]["path"] == "/agentic/products/search"
    assert len(fake.calls) == 1


async def test_checkout_without_enrollment_is_refused(client, reap, state, monkeypatch):
    monkeypatch.delenv("REAP_ENROLLMENT_ID")
    state["enrollmentId"] = None
    reap({})
    assert (await client.post("/api/checkout", json={"quoteId": "q1"})).status_code == 409


async def test_checkout_with_expired_quote_is_refused(client, reap):
    reap({("GET", "/agentic/quotes/q1"): quote_doc(expires="2000-01-01T00:00:00Z")})
    assert (await client.post("/api/checkout", json={"quoteId": "q1"})).status_code == 410
