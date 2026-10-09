# Glance Constitution

Glance is a mobile app where an AI agent finds a product, prices it, checks it
against the user's spending limit, and pays with a card backed by the user's
stablecoin vault.

## Core Principles

### I. User Approves Every Charge

No payment completes without the user approving it on the payment provider's
own approval page. The app MUST NOT recreate, bypass, or automate that page.

### II. The Agent Never Touches Card Details

Card numbers MUST NOT reach the app, the server, logs, or any AI model.
Merchant checkouts MUST NOT be scraped.

### III. Limit Before Checkout

A purchase whose total exceeds the user's per-purchase limit MUST be blocked
before any checkout is opened, and the user MUST be told by how much it is
over.

### IV. Sandbox Only

Test funds, test cards, simulated checkout only. API keys and test card
details are secrets: they MUST NOT appear in the repository, logs, or the
frontend.

### V. Honest Amounts

Money is held as whole cents; floating point MUST NOT be used for money. The
user is always shown the amount actually charged, never an estimate.

### VI. Specification First

No code without an approved spec. Every acceptance criterion has an ID of the
form AC-<spec>-<nn> and exactly one level tag: [api], [ui], or [e2e]. Every
acceptance criterion has at least one test whose name contains its ID, or a
noted manual check.

### VII. Test Pyramid

Limit and amount rules are pure functions with unit tests, written before any
screen uses them. Prefer [api] wherever a rule can be proven without a screen.
One [e2e] journey only: the happy path purchase.

### VIII. Living Documentation

The spec is amended before behaviour changes.

### IX. Stop and Report

After implementing a spec, the agent stops and reports what was built, test
results, and traceability status.

## Out of Scope

Real purchases, production keys, recurring purchases, travel booking,
restricted categories, glasses hardware, multi-user accounts.

## Governance

This constitution supersedes all other practices. Three gates per spec:

- **G1** approves the specification.
- **G2** approves the plan.
- **G3** approves the release.

Gates are approved by a named human, recorded in `specs/<spec>/gates/`, and
never approved retroactively. Amendments to this constitution are made before
dependent behaviour changes and bump the version per semantic versioning
(MAJOR: principle removal/redefinition; MINOR: new or materially expanded
principle; PATCH: clarification).

**Version**: 1.0.0 | **Ratified**: 2026-10-09 | **Last Amended**: 2026-10-09
