#!/usr/bin/env bash
# AC-001-06 [e2e]: sentence -> search -> quote -> checkout -> approval -> paid, via the Glance backend.
# Usage: PUBLIC_URL=https://... scripts/happy_path.sh ["Buy an Anker USB-C hub, under S$150"]
set -euo pipefail
: "${PUBLIC_URL:?set PUBLIC_URL to the HTTPS backend URL}"
B="${PUBLIC_URL%/}"; TEXT="${1:-Buy an Anker USB-C hub, under S\$150}"
j() { curl -sS -f -X "$1" "$B$2" -H 'content-type: application/json' ${3:+-d "$3"}; }

echo "# health";     j GET /health | jq -c .
echo "# intent";     I=$(j POST /api/intent "$(jq -cn --arg t "$TEXT" '{text:$t}')"); echo "$I" | jq -c .
Q=$(echo "$I" | jq -r .query); MAX=$(echo "$I" | jq '.maxPriceCents // 15000')
echo "# search";     S=$(j POST /api/search "$(jq -cn --arg q "$Q" --argjson m "$MAX" '{query:$q,maxPriceCents:$m}')")
echo "$S" | jq -c '{pickId, products: [.products[] | {id, name, priceCents, variantId}]}'
PICK=$(echo "$S" | jq -r .pickId); [ "$PICK" != null ] || { echo "no products"; exit 2; }
VAR=$(echo "$S" | jq -r --arg p "$PICK" '.products[] | select(.id==$p) | .variantId')
NAME=$(echo "$S" | jq -r --arg p "$PICK" '.products[] | select(.id==$p) | .name')
echo "# quote";      QT=$(j POST /api/quote "$(jq -cn --arg v "$VAR" '{variantId:$v}')")
echo "$QT" | jq -c '{quoteId, itemCents, shippingCents, taxCents, totalCents, currency, expiresAt, limit}'
[ "$(echo "$QT" | jq .limit.allowed)" = true ] || { echo "BLOCKED: over limit by $(echo "$QT" | jq .limit.overByCents) cents (expected for the over-limit check)"; exit 3; }
QID=$(echo "$QT" | jq -r .quoteId); DELIV=$(echo "$QT" | jq -r '[.shippingOptions[] | select(.selected)][0].name // empty')
echo "# checkout";   C=$(j POST /api/checkout "$(jq -cn --arg q "$QID" --arg n "$NAME" --arg d "$DELIV" '{quoteId:$q,item:{name:$n},deliveryName:$d}')")
echo "$C" | jq -c .
CID=$(echo "$C" | jq -r .checkoutId); URL=$(echo "$C" | jq -r '.approvalUrl // empty')
[ -n "$URL" ] && echo "approval page (open on the phone if not simulated): $URL"
echo "# poll";
for i in $(seq 1 30); do
  ST=$(j GET "/api/checkout/$CID"); echo "$ST" | jq -c '{status, terminal, orderId, finalAmountCents}'
  if [ "$(echo "$ST" | jq .terminal)" = true ]; then
    [ "$(echo "$ST" | jq -r .status)" = COMPLETED ] || { echo "checkout ended as $(echo "$ST" | jq -r .status)"; exit 4; }
    echo; echo "PAID  order=$(echo "$ST" | jq -r .orderId)  finalAmountCents=$(echo "$ST" | jq .finalAmountCents) $(echo "$ST" | jq -r .currency)"
    exit 0
  fi
  sleep 2
done
echo "timed out waiting for a terminal status"; exit 5
