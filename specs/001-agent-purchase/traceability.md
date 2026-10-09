# Traceability: Spec 001 acceptance criteria → evidence

Constitution VI: every AC has at least one test whose name contains its ID, or a noted manual check.
Run: `cd backend && poetry run pytest -q` · `PUBLIC_URL=… scripts/happy_path.sh`

| AC | Level | Evidence | Status |
|---|---|---|---|
| AC-001-01 | api | `test_api.py::test_AC_001_01_intent_returns_query_and_ceiling_in_cents`, `…_without_price_returns_null_ceiling` | pass |
| AC-001-02 | api | `test_api.py::test_AC_001_02_search_returns_at_most_three_products_with_cheapest_within_ceiling_picked`; live: 3 Anker hubs SG/SGD | pass |
| AC-001-03 | api | `test_api.py::test_AC_001_03_quote_is_itemised_in_cents_with_delivery_options_and_total`; live quote 2690¢ | pass |
| AC-001-04 | api | `test_api.py::test_AC_001_04_checkout_within_limit_starts_provider_approval_with_https_return_url` | pass (live pending enrollment) |
| AC-001-05 | api | `test_api.py::test_AC_001_05_status_reports_order_reference_and_amount_actually_charged` | pass (live pending enrollment) |
| AC-001-06 | e2e | `scripts/happy_path.sh` exit 0 with `orderId` + `finalAmountCents`; phone walk-through video | pending enrollment |
| AC-001-07 | api | `test_limits.py` (8 tests, all named `test_AC_001_07_*`) | pass |
| AC-001-08 | api | `test_api.py::test_AC_001_08_checkout_over_limit_is_refused_before_any_provider_checkout`; quickstart §5 live | pass (live pending) |
| AC-001-09 | ui | Manual check: Quote screen with limit < total → pay button disabled, red alert shows over-amount, "Change limit" ghost button (`App.tsx` lines ~218, ~247–248) | manual |
| AC-001-10 | api | `test_api.py::test_AC_001_10_new_limit_applies_to_next_quote_evaluation`, `…_limit_must_be_positive_integer_cents` | pass |
| AC-001-11 | api | `test_api.py::test_AC_001_11_changing_delivery_option_reprices_and_reevaluates` (sandbox product has one option; rule proven by test) | pass |
| AC-001-12 | ui | Manual check: Cancel on hosted page → "Payment not approved. Nothing was charged." toast; decline status → "Payment declined. Nothing was charged."; no order recorded | manual |
| AC-001-13 | api | `test_api.py::test_AC_001_13_home_reports_vault_card_limit_and_session_orders` | pass |
| AC-001-14 | ui | Manual check: Home with no orders shows "No orders yet. Ask Glance to buy something and it shows up here." | manual |
| AC-001-15 | api | `test_api.py::test_AC_001_15_provider_error_is_surfaced_verbatim_and_not_retried` | pass |

Supporting (not ACs): `test_money.py` (constitution V), `test_checkout_without_enrollment_is_refused`, `test_checkout_with_expired_quote_is_refused`.
