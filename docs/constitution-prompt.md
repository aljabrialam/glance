# Constitution (run once, after `specify init`)

Paste the block below into Devin. Spec Kit writes the result to
`.specify/memory/constitution.md`. Then commit:
`git add -A && git commit -m "docs: constitution v1.0.0"`

```
/speckit-constitution

Glance is a mobile app where an AI agent finds a product, prices it,
checks it against the user's spending limit, and pays with a card backed
by the user's stablecoin vault. Principles:

1. User Approves Every Charge. No payment completes without the user
   approving it on the payment provider's own approval page.

2. The Agent Never Touches Card Details. Card numbers never reach the
   app, the server, logs, or any AI model. Merchant checkouts are never
   scraped.

3. Limit Before Checkout. A purchase whose total exceeds the user's
   per-purchase limit is blocked before any checkout is opened, and the
   user is told by how much.

4. Sandbox Only. Test funds, test cards, simulated checkout. API keys and
   test card details are secrets: never in the repository, logs, or the
   frontend.

5. Honest Amounts. Money is held as whole cents; floating point is never
   used for money. The user is always shown the amount actually charged,
   not an estimate.

6. Specification First. No code without an approved spec. Every
   acceptance criterion has an ID of the form AC-<spec>-<nn> and exactly
   one level tag: [api], [ui], or [e2e]. Every acceptance criterion has at
   least one test whose name contains its ID, or a noted manual check.

7. Test Pyramid. Limit and amount rules are pure functions with unit
   tests, written before any screen uses them. Prefer [api] wherever a
   rule can be proven without a screen. One [e2e] journey only: the happy
   path purchase.

8. Living Documentation. The spec is amended before behaviour changes.

9. Stop and Report. After implementing a spec, the agent stops and
   reports what was built, test results, and traceability status.

Out of scope: real purchases, production keys, recurring purchases,
travel booking, restricted categories, glasses hardware, multi-user
accounts.

Governance: three gates per spec. G1 approves the specification, G2
approves the plan, G3 approves the release. Gates are approved by a named
human, recorded in specs/<spec>/gates/, and never approved retroactively.
```
