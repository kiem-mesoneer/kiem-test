---
status: active
---

# Architecture Support Request Process

> **Last updated**: 2026-09-01
> **Status**: Active

## Why

Teams facing an ambiguous architectural decision (which isolation model, which broker, whether an
existing Reference Architecture even applies to their case) had no defined way to pull in a
Solution Architect — support happened ad hoc, through whoever the requester happened to know,
which meant uneven response times and decisions that never made it into a reusable ADR. This
process gives every team the same entry point, the same expected response time, and a guaranteed
link back into the ADR pipeline so a one-off answer can become a reusable precedent.

## Rules

### When to request support (trigger criteria)

- Request support when a decision (a) isn't already covered by an existing [Reference
  Architecture](../reference-architectures/) or [ADR](../adr/), (b) affects more than one team or
  is hard to reverse (e.g. a data store choice, a multi-region topology), or (c) two teams
  disagree and can't resolve it within their own review.
- Do **not** use this process for decisions a team is fully equipped to make on their own using an
  existing RA/ADR as-is — that's normal engineering work, not an escalation.

**Do this:**
```text
"Our service needs multi-region failover and none of the Tier-1 RAs cover active-active vs
active-passive trade-offs for our case — requesting SA input before we commit."
```

**Not this:**
```text
"Should we name this variable `orderId` or `order_id`?" (a naming-convention question, not
an architecture decision — routed to Code Conventions instead)
```

### Intake channel and SLA

- Submit via the `Architecture Support Request` Jira request type (routes to the SA group's
  queue). Slack (`#architecture-support`) is fine for a quick sanity check but does not start the
  SLA clock — only the Jira request does, so there's a durable record.
- SLA: an SA acknowledges within **2 business days** and gives an initial response (which may be
  "here's the relevant RA/ADR, you're unblocked" or "this needs a working session") within **5
  business days**.

**Do this:**
```text
Jira DS-SUP-14 opened Monday 09:00 → SA acknowledgment Tuesday 14:00 → initial response
(pointer to existing Multi-tenant Data Isolation RA, unblocks the team) Wednesday.
```

**Not this:**
```text
Question asked in a DM to one SA who happens to be on holiday for two weeks — no SLA,
no visibility for anyone else to pick it up
```

### Interaction with the ADR process

- If the resolution sets a **reusable precedent** (the same question will plausibly come up for
  another team), the SA and requester jointly write it up as a new ADR — following the [ADR
  Template & Lifecycle](../adr/adr-template-lifecycle.md) — rather than letting the answer live
  only in the closed support ticket.
- If the resolution is genuinely one-off (specific to that team's legacy constraints), record it
  as a comment on the Jira ticket only — don't force every support request into an ADR.

**Do this:**
```text
Support request about multi-region failover resolves into ADR-0031 "Active-passive failover
for regionally-pinned data" — future teams find it via adr-lookup instead of re-asking.
```

**Not this:**
```text
Same multi-region question gets asked and answered from scratch by three different teams
over six months because the first answer only exists in a closed Jira ticket
```

### Roles & responsibilities

- **Requester**: opens the ticket with enough context to act on (what's been tried, what RA/ADR
  was checked and found insufficient).
- **SA (assigned via queue rotation)**: acknowledges, responds within SLA, and decides jointly
  with the requester whether the outcome becomes an ADR.
- **Escalation**: if the SA and requester can't agree, or the SA capacity is exhausted, escalate
  to the architecture guild — the same escalation path defined in the [ADR Governance
  Model](../adr/adr-governance-model.md).

## Tooling & Enforcement

- Jira request type: `Architecture Support Request` (SA group queue), with the SLA fields above
  configured on the request type itself so breaches are visible without manual tracking.
- `#architecture-support` Slack channel for informal triage — not a substitute for the Jira ticket.
- Precedent-setting resolutions flow into [adr/](../adr/) and, once accepted, into the
  `adr-lookup` Claude plugin skill automatically via the sync pipeline.
