# Feature Specification: Agent Purchase, End to End

**Feature Branch**: `001-agent-purchase`

**Created**: 2026-10-09

**Status**: Draft

**Input**: User description: "A shopper tells an assistant in one sentence what to buy and the most they will pay. The assistant finds matching products, prices the chosen one in full, checks it against the shopper's per-purchase limit, and sends the shopper to the payment provider's approval page to pay. Visual reference: design/glance-app-mockup.html."

## Clarifications

### Session 2026-10-09

- Q: Which market should the demo purchase run in (search context country +
  currency)? → A: Per the hackathon microsite's merchant sheet: Singapore
  (SG/SGD), demo product Anker Nano USB-C Hub 8-in-1 at anker.com.sg
  (verified in the sheet, 72.90 SGD); fall back to US/USD if the sandbox
  returns nothing for the SG query. The mockup's Sony WH-1000XM5 is not in
  the merchant sheet and is sample copy only.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Happy path purchase (Priority: P1)

A shopper types one sentence saying what to buy and the most they will pay.
The assistant finds matching products, shows up to three with the best match
preselected, prices the chosen one in full (item, shipping, tax), confirms the
total is within the shopper's per-purchase limit, and sends the shopper to the
payment provider's approval page. After approving, the shopper sees the order
reference, the amount actually charged, and their delivery choice.

**Why this priority**: This is the entire product. One polished happy path is
the demo and the submission.

**Independent Test**: Run the full journey from one sentence to a completed
order in the sandbox and observe an order reference and final amount.

**Acceptance Scenarios**:

1. **AC-001-01 [api]** Given a sentence naming a product and a maximum price,
   When the shopper submits it, Then the system produces a search query and a
   price ceiling in whole cents reflecting the sentence.
2. **AC-001-02 [api]** Given a query and price ceiling, When the search runs,
   Then up to three available products at or below the ceiling are returned,
   ordered with the best match first.
3. **AC-001-03 [api]** Given a chosen product, When a quote is requested, Then
   the response itemises item price, shipping, and tax in whole cents, lists
   the available delivery options, and states the total.
4. **AC-001-04 [api]** Given a quote whose total is at or below the limit,
   When the shopper proceeds to pay, Then a payment approval journey is
   started with the payment provider and the shopper is directed to the
   provider's own approval page.
5. **AC-001-05 [api]** Given the shopper approved on the provider's page,
   When the purchase completes, Then the system reports the order reference
   and the amount actually charged by the provider, not the quoted estimate.
6. **AC-001-06 [e2e]** Given a fresh session, When a shopper performs the
   whole journey from sentence to approval on a phone, Then they end on a
   confirmation showing order reference, final amount, delivery choice, and
   updated vault balance.

---

### User Story 2 - Limit blocks an over-budget purchase (Priority: P2)

A shopper's quote total exceeds their per-purchase limit. Payment is
unavailable before any checkout is opened, and the shopper is told exactly how
much over the limit the total is. The shopper can change the limit; the new
limit applies to the next quote evaluation.

**Why this priority**: The limit is the permission story and a constitutional
rule (Limit Before Checkout). It is the one guardrail judges will probe.

**Independent Test**: Request a quote above the limit and verify payment is
blocked with the over-amount stated; raise the limit and verify payment
becomes available.

**Acceptance Scenarios**:

1. **AC-001-07 [api]** Given a limit and a quote total both in whole cents,
   When the total exceeds the limit, Then the evaluation reports blocked and
   the exact amount over; when the total is at or below the limit, it reports
   allowed and the amount remaining. (Pure rule, unit tested.)
2. **AC-001-08 [api]** Given a quote whose total exceeds the limit, When the
   shopper attempts to pay, Then no payment journey is started and the
   response states the amount over the limit.
3. **AC-001-09 [ui]** Given an over-limit quote on screen, Then the pay action
   is disabled, the amount over the limit is shown, and the shopper is offered
   a way to change the limit.
4. **AC-001-10 [api]** Given the shopper changes the per-purchase limit, When
   the next quote is evaluated, Then the new limit is applied.

---

### User Story 3 - Re-pricing, decline, and home overview (Priority: P3)

Changing the delivery option re-prices the order against the limit. Declining
on the provider's page charges nothing and says so. The home screen shows the
vault balance, the last four digits of the backing card, the current limit,
and this session's orders — or, with no orders, how to make the first one.

**Why this priority**: Rounds out the journey and the demo narrative; each
part is small and independently verifiable.

**Acceptance Scenarios**:

1. **AC-001-11 [api]** Given a quote with multiple delivery options, When the
   shopper selects a different option, Then the itemised total is recalculated
   and re-evaluated against the limit.
2. **AC-001-12 [ui]** Given the shopper declines on the provider's approval
   page, Then they are returned to the app, told nothing was charged, and no
   order is recorded. (Manual check if the sandbox cannot simulate a decline.)
3. **AC-001-13 [api]** Given a session, When the home overview is requested,
   Then it reports the vault balance, card last four digits, current limit,
   and orders completed this session.
4. **AC-001-14 [ui]** Given no orders in the session, Then the home screen
   explains how to make the first purchase.
5. **AC-001-15 [api]** Given the merchant or payment provider returns an
   error, Then the failure is reported to the shopper in plain language and
   the operation is not retried silently.

---

### Edge Cases

- Quote total exactly equals the limit: allowed (limit is inclusive).
- The search returns no products at or below the ceiling: the shopper is told
  nothing matched and invited to rephrase or raise the ceiling.
- The sentence has no recognisable price ceiling: the current per-purchase
  limit is used as the ceiling.
- A quote expires before payment starts: the shopper is told the price lapsed
  and a fresh quote is fetched. [NEEDS CLARIFICATION: observe in the sandbox
  what the provider returns for an expired quote at checkout time.]
- The shopper abandons the provider's approval page: the purchase stays
  incomplete, nothing is charged, and no order is recorded. [NEEDS
  CLARIFICATION: observe in the sandbox the checkout status for an abandoned
  approval and whether it reaches a terminal state.]

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST turn one free-text sentence into a product search
  query and a price ceiling; the ceiling defaults to the per-purchase limit
  when the sentence names none.
- **FR-002**: System MUST search supported merchants and present up to three
  available products at or below the ceiling, best match preselected.
- **FR-003**: System MUST obtain the merchant's full price for the chosen
  product — item, shipping, tax, total — and the available delivery options,
  and re-price when the delivery option changes.
- **FR-004**: System MUST evaluate every quote total against the shopper's
  per-purchase limit before any payment journey is started, blocking payment
  and stating the exact amount over when the total exceeds the limit.
- **FR-005**: System MUST let the shopper change the per-purchase limit; the
  new limit applies to the next quote evaluation.
- **FR-006**: System MUST send the shopper to the payment provider's own
  approval page for every charge and MUST NOT recreate or bypass it.
- **FR-007**: System MUST show, after completion, the order reference and the
  amount actually charged by the provider.
- **FR-008**: System MUST hold and display all money as whole cents; no
  floating point for money anywhere.
- **FR-009**: System MUST report merchant or provider failures in plain
  language and never retry silently.
- **FR-010**: System MUST keep payment card details away from the app, the
  server, logs, and any AI model.
- **FR-011**: Home overview MUST show vault balance, card last four digits,
  current limit, and this session's orders, with first-purchase guidance when
  there are none.

### Key Entities

- **Intent**: the parsed sentence — search query and price ceiling (cents).
- **Product match**: name, variant, merchant, item price (cents), rank.
- **Quote**: itemised amounts (cents), delivery options, expiry, total.
- **Limit evaluation**: limit (cents), total (cents), allowed/blocked, amount
  over or remaining (cents).
- **Order**: order reference, final amount charged (cents), delivery choice,
  merchant.
- **Session overview**: vault balance, card last four, limit, orders.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A shopper completes the whole journey — sentence to confirmed
  order — in under 3 minutes on a phone.
- **SC-002**: 100% of purchases whose quote total exceeds the limit are
  blocked before any payment journey starts.
- **SC-003**: 100% of completed purchases display the amount actually charged
  by the provider, matching the provider's own record.
- **SC-004**: Zero payment card details appear in the app, server responses,
  or logs during a full journey.
- **SC-005**: The confirmation screen's amount, order reference, and delivery
  choice match what the shopper approved.

## Assumptions

- Single shopper, single session; no accounts, sign-in, or multi-user state.
- Sandbox environment with test funds and simulated checkout; nothing ships.
- Vault balance is sourced from configuration until the vault integration is
  ready, and is clearly labelled.
- Limit is inclusive: a total exactly equal to the limit may proceed.
- Default limit is $150.00 (15000 cents); shopper-adjustable.
- One currency per session; amounts and limit share that currency. The demo
  session runs in Singapore (SGD); United States (USD) is the fallback market
  if the sandbox returns no results for the Singapore query.
- Demo product: Anker Nano USB-C Hub 8-in-1 from anker.com.sg (verified
  against the supported-merchant sheet). The mockup's Sony headphones are
  sample copy, not a supported product.
- A fixed demo shopper identity (email and shipping address) from
  configuration is used for quotes; there is no address entry screen.
- The default product variant is used; variant selection is out of scope.
- Order history lasts only for the current session.
- The visual reference for all screens is design/glance-app-mockup.html.
