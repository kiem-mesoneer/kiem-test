---
status: active
---

# ADR Governance Model

> **Last updated**: 2026-09-01
> **Status**: Active

## Why

A template and lifecycle alone don't stop two problems: decisions getting accepted without anyone
who'd be affected reviewing them, and cross-team conflicts (which broker, which caching strategy)
stalling forever because nobody owns the tie-break. mesoneer's Architecture Conventions project is
also structured so that the PL and the Requirements/Domain owner are the same person (Kiem) — a
governance model that routes every approval through one person is a single point of failure and a
rubber stamp risk, so this convention explicitly designs around that.

## Rules

### Roles

- **Proposer** — anyone: the engineer or team facing the decision. Writes the ADR as `proposed`.
- **Reviewer(s)** — at least one Solution Architect (SA) not on the proposer's team, plus anyone
  named a stakeholder in the ADR's Decision Drivers (e.g. security, another team the choice binds).
- **Approver** — the SA group, not a single individual — see the escalation rule below for why.

**Do this:**
```markdown
## Reviewers
- @toai (SA)
- @security-team (data residency impact)
```

**Not this:**
```markdown
## Reviewers
(none — merged directly by the proposer)
```

### Approval flow

- `proposed` → open a PR against `adr/`. → at least one SA reviewer approves the PR → merge moves
  the ADR to `accepted`. The PR *is* the review; there is no separate approval ceremony.
- A `proposed` ADR that sits without reviewer engagement for more than 5 business days should be
  raised in the SA sync, not left to expire silently.

**Do this:**
```text
PR #142 "ADR-0012: Use Azure Event Hub for order events" — approved by @toai (SA) — merged
→ ADR-0012 status: accepted
```

**Not this:**
```text
PR #142 merged by the author with no review requested, "status: accepted" set in the same commit
```

### Escalation for cross-team / conflicting decisions

- If two teams propose ADRs that conflict (e.g. Team A wants RabbitMQ, Team B — owner of the
  Event-driven RA — wants Azure Event Hub), the proposer raises it as a cross-team ADR and both
  teams' SAs review it together within the agreed SLA (5 business days).
- If no consensus is reached within that window, escalate to the **architecture guild** (all SAs
  plus the PL) for a binding decision — never to the PL alone, precisely because the PL and
  Requirements/Domain owner are the same person here. The guild's decision is recorded as the
  `Decision Outcome` with the guild listed as approver.

**Do this:**
```markdown
## Decision Outcome
Chosen option: "Azure Event Hub", decided by architecture guild vote (2026-08-20)
after Team A/Team B review did not reach consensus within the 5-day SLA.
```

**Not this:**
```markdown
## Decision Outcome
Chosen option: "Azure Event Hub" — Kiem decided.
```

## Tooling & Enforcement

- GitHub branch protection on `main` requires at least one approving review on any PR touching
  `adr/*.md` before merge — this is what makes "the PR is the review" actually enforced rather
  than a convention people can skip.
- CODEOWNERS routes ADR PRs to the SA group so a reviewer is requested automatically.
- Shared with, and reusing role definitions from, the Code Conventions governance model.
