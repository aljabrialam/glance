# Glance documentation

Start with the root [README](../README.md) for what Glance is and how to run it. These
documents cover how it is built and how it gets to a public beta.

## Technical build

| Document | What it answers |
|---|---|
| [architecture.md](architecture.md) | How the pieces fit: guarantees, system context, trust boundaries, the purchase flow, intent and money handling, hackathon → beta gaps, decisions |
| [infrastructure.md](infrastructure.md) | Where it runs: AWS ECS Fargate in Singapore + Supabase, environments, network, secrets, observability, CI/CD, Terraform, Reap and Kwal cutover, cost, DR, runbooks |
| [persistence.md](persistence.md) | What is stored: Postgres schema, row-level security, checkout state and reconciliation, migrations, retention and deletion |
| [api.md](api.md) | The backend HTTP API: every endpoint with shapes and errors, the Reap calls behind each, planned additions, idempotency |
| [security.md](security.md) | Threat model, the card-data boundary and PCI posture, spending controls, auth, secrets, WebView and webhook hardening, the model boundary, privacy, compliance checklist |
| [mobile-release.md](mobile-release.md) | The Expo app: target structure with Expo Router, EAS build profiles and channels, pipeline, store readiness, quality gates |
| [delivery-plan.md](delivery-plan.md) | The plan: four phases with exit gates, timeline, workstreams, beta service levels, risks, open questions for Reap and Kwal |

## Hackathon context (how the build was run)

| Document | What it is |
|---|---|
| [context.md](context.md) | Product and partner-API facts the build started from |
| [scope-lock.md](scope-lock.md) | What was in and out on the day, the timeline and fallbacks |
| [sdd-runsheet.md](sdd-runsheet.md) | The spec-driven workflow and gates (G1/G2/G3) |
| [constitution-prompt.md](constitution-prompt.md) | The prompt that produced [`.specify/memory/constitution.md`](../.specify/memory/constitution.md) |
| [handoff-bundle.md](handoff-bundle.md) | Notes on the team skeleton the implementation adopted |

The feature specification, plan, research (including live Reap observations), data model,
contracts and traceability live in [`specs/001-agent-purchase/`](../specs/001-agent-purchase/).
