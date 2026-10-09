# Glance — pitch video script (62 s)

Source: `design/glance-app-mockup.html?play=1` (auto-plays the pitch on load).
Record the browser in fullscreen; the narration card above the phone shows the
same beats, so the voice-over below can be read as-is or paraphrased.

## Prompt for the voice-over tool (screendub.io or similar)

> Voice: calm, confident founder pitching to investors; not salesy, no hype
> words. Neutral or Singapore-English accent, medium-slow pace (about 140 words
> per minute), short pauses at each cue. Product name is "Glance". Read "S$"
> as "Singapore dollars" the first time, then "dollars". Read "USDC" as
> "U-S-D-C". Keep each cue inside its time window; do not add words.

## Cues

| Time | On screen | Voice-over |
|---|---|---|
| 0:00 | Home: vault 250 USDC, card •••• 4242, limit S$150, no orders | Glance. An AI agent that shops for you — inside a limit you set, with money you own. This is the home screen: a USDC vault, the card it backs, and one number the agent can never exceed. |
| 0:05 | Ask → Glasses tab: Meta Display HUD, "Find me the best price for this, under S$150" | Two ways in. Through Meta Display glasses — look at the product, say the most you'll pay. That's the concept. |
| 0:10 | Ask → Scan tab: photo attached | Or, built tonight: scan it with your phone camera. The model only turns a photo or a sentence into a search query and a price ceiling. Nothing else. |
| 0:13 | Progress lines → Results: 3 Anker hubs, agent's pick | The agent searches real merchant catalogues through Reap's Agentic API — Singapore market. Three matches under the ceiling, best one preselected. It recommends; it doesn't decide. |
| 0:20 | Quote: item 72.90, delivery 5.00, GST 6.56, total S$84.46, meter 65.54 under | Now the real number: the merchant's live quote with delivery and GST. Eighty-four forty-six. A pure rule in our code checks it against the limit — before any checkout exists. |
| 0:25 | Delivery switches to Express, total re-prices, then back to Standard | Change delivery, and it re-prices and re-checks. |
| 0:29 | Approve: Reap's hosted approval page inside the app | Money moves only here — on Reap's own approval page, inside the app. The agent never sees the card. Decline, and nothing is charged. |
| 0:34 | Approve tapped → "Confirming with Reap…" → Paid | Approve. |
| 0:36 | Paid: S$84.46 actually charged, order ORD-SG-1003, delivery, vault 250 → 165.54 USDC | An honest receipt: the amount actually charged, not the estimate. Order reference, delivery, and the vault balance after the spend. Stablecoins in a wallet you own just paid a merchant that has never heard of crypto. |
| 0:42 | Home: order listed, vault 165.54 | Back home, the order is there. |
| 0:46 | Spending limit slider moves to S$80 | Now the part judges should probe. Set the limit to eighty dollars. |
| 0:49 | Quote: "S$4.46 over your limit", pay disabled, Change limit | Same quote. Four dollars forty-six over. The agent stops. No checkout is created, the user sees exactly how much over, and can pick cheaper delivery or change the limit. |
| 0:55 | Limit back to S$150 | The permission is one number, and the user owns it. |
| 0:58 | Home | Glance. Your agent shops. You approve. Your stablecoins pay. |

## Right-hand panel (for a second pass or B-roll)

The trace panel shows, per screen: the Reap calls (`products/search`, `products/details`,
`quotes`, `checkouts`, `checkouts/:id`), the Kwal vault reads, `limits.evaluate()` with the
cents in and the decision out, and the guarantees — card never seen, limit before checkout,
honest amounts. If the video has a second pass, zoom on this panel at 0:20 (quote) and
0:49 (blocked).

## Honesty notes to keep in the voice-over

- Say "concept" for the glasses; say "built" for the phone camera, Reap flow and limit rule.
- Sandbox: nothing is really bought or shipped.
- Vault balance is live from Kwal when configured; otherwise the app labels it as a mock.
