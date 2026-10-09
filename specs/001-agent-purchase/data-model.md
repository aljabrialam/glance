# Data Model: Agent Purchase, End to End

All money is integer cents in one currency per session (`SGD` for the demo).
Fields are the backend's JSON names.

## Intent
| Field | Type | Notes |
|---|---|---|
| query | string | search text derived from the sentence |
| maxPriceCents | int \| null | null → caller uses the per-purchase limit |

## Product (search result)
| Field | Type | Notes |
|---|---|---|
| id | string | Reap product id |
| name, merchant, imageUrl | string | display |
| priceCents | int \| null | from `defaultVariant.price`, else preview/min |
| variantId | string | `defaultVariant.id` (no variant selection in scope) |
| requiresShipping | bool | drives whether a shipping address is sent |
| rank | int | 0 = agent's pick (cheapest within ceiling) |

## Quote
| Field | Type | Notes |
|---|---|---|
| quoteId | string | Reap quote id |
| itemCents, shippingCents, taxCents, discountCents, totalCents | int | from `amountBreakdown` |
| currency | string | from `finalAmount.currency` |
| shippingOptions[] | {id, name, priceCents, selected} | |
| expiresAt | ISO datetime | checkout refused after this |
| limit | LimitDecision | evaluated against the current limit |

## LimitDecision (pure)
| Field | Type | Rule |
|---|---|---|
| limitCents | int | current per-purchase limit |
| totalCents | int | quote total |
| allowed | bool | `totalCents <= limitCents` (inclusive) |
| overByCents | int | `max(0, total - limit)` |
| remainingCents | int | `max(0, limit - total)` |

## Checkout
| Field | Type | Notes |
|---|---|---|
| checkoutId | string | Reap checkout id |
| status | enum | `REQUIRES_ACTION` → terminal (`COMPLETED`, `FAILED`, `CANCELED`, `EXPIRED`, `DECLINED`) |
| approvalUrl | string | `nextAction.url`; opened in the WebView |
| orderId | string \| null | present when COMPLETED |
| finalAmountCents | int \| null | amount actually charged; the only figure shown on Paid |
| vaultBeforeCents, vaultAfterCents | int \| null | from vault source |

State transitions: `REQUIRES_ACTION --approve--> COMPLETED`; `--decline/cancel--> DECLINED|CANCELED`; `--time--> EXPIRED` (to observe).

## Order (session)
| Field | Type |
|---|---|
| checkoutId, orderId | string |
| finalAmountCents | int |
| item | {name, merchant, imageUrl} |
| deliveryOption | {name, priceCents} |
| at | unix seconds |

## Home (session overview)
| Field | Type | Notes |
|---|---|---|
| vaultBalanceCents | int \| null | |
| vaultSource | `"kwal"` \| `"mock"` | UI labels mock explicitly |
| cardLast4 | string | from enrollment `paymentMethod.last4` when available |
| limitCents | int | default 15000 |
| orders[] | Order | this session only |
| enrollmentActive | bool | |

## Persisted state (JSON file)
`{ limitCents, orders[], quotes{quoteId: {variantId, totalCents}}, checkouts{checkoutId: {...}}, enrollmentId }`

## Validation rules
- `PUT /api/limit`: `perPurchaseCents` integer, `> 0`.
- `POST /api/checkout`: 409 if no enrollment; 403 with `overByCents` if `!allowed`; 410 if `expiresAt` passed.
- Amount parsing: reject non-numeric; parse via `Decimal`, never `float()`.
