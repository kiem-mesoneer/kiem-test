---
status: active
---

# ADR Template & Lifecycle

> **Last updated**: 2026-09-01
> **Status**: Active

## Why

Before this convention, architecture decisions at mesoneer were made in Slack threads, meeting
notes, or a single engineer's head — especially costly across our multi-cloud (Azure + AWS),
multi-runtime (OpenShift, Azure App Service, serverless), and multi-pipeline (GitHub Actions,
Azure DevOps) footprint, where the same class of decision (which broker, which caching strategy)
gets re-litigated by every new team because no record of the first decision survives. Architecture
Decision Records (ADRs) give every significant decision a permanent, reviewable document with an
unambiguous current status, so a new engineer can find out *what was decided and why* instead of
re-opening the debate.

## Rules

### ADR format (MADR)

- Base every ADR on [MADR](https://adr.github.io/madr/) (Markdown Architecture Decision Records)
  rather than inventing a bespoke format — it is the de-facto standard, tooling-friendly, and
  lets ADRs stay reviewable as plain PR diffs.
- Every ADR must contain: **Context and Problem Statement**, **Decision Drivers**, **Considered
  Options**, **Decision Outcome**, and **Consequences**. Use `adr/0000-adr-template.md` as the
  literal starting file — copy it, don't write from a blank page.

**Do this:**
```markdown
# ADR-0003: Use Azure Event Hub as the event backbone for the pilot

## Status
accepted

## Context and Problem Statement
The Event-driven RA pilot needs a message broker...

## Considered Options
* Azure Event Hub
* Apache Kafka (self-hosted)
* RabbitMQ

## Decision Outcome
Chosen option: "Azure Event Hub", because it is already available on Cloud Platform MVP...

## Consequences
* Good, because no new infra to operate
* Bad, because partition count is fixed at creation time
```

**Not this:**
```text
Slack message from #team-payments, 2026-03-14:
"yeah let's just go with event hub, kafka is overkill for now"
(decision lost once the channel is archived; no record of alternatives considered)
```

### File naming and numbering

- One file per decision under `adr/`, named `NNNN-kebab-case-title.md` — a zero-padded, strictly
  increasing sequence number followed by a short kebab-case title.
- Numbers are never reused or renumbered, even if an ADR is later superseded or withdrawn — the
  number is a permanent identity, not a sort key you're allowed to compact.

**Do this:**
```text
adr/0001-adopt-arc42.md
adr/0002-store-adrs-in-git.md
adr/0012-use-azure-event-hub-for-order-events.md   ← next number is 0012, even though
                                                       0007 was later marked superseded
```

**Not this:**
```text
adr/adopt-arc42.md                 ← no sequence number, can't tell reading order
adr/0007-use-azure-event-hub.md    ← reusing 0007 after ADR-0007 was superseded and "freed up"
```

### Lifecycle states

- Every ADR carries exactly one `Status` at a time, drawn from: `proposed` → `accepted` →
  `deprecated` → `superseded`. `deprecated` means the decision no longer applies and nothing
  replaced it; `superseded` means a specific later ADR replaces it — link to that ADR's number.
- Moving from `proposed` to `accepted` requires review per the [ADR Governance
  Model](adr-governance-model.md) — never self-merge a `proposed` ADR straight to `accepted`.
- An ADR is never deleted once `accepted`; its file stays in Git even after being superseded, so
  the history of *why* something changed remains readable.

**Do this:**
```markdown
## Status
superseded by ADR-0012
```

**Not this:**
```bash
git rm adr/0004-use-rabbitmq.md   # deleting the record instead of marking it superseded
```

## Tooling & Enforcement

- `adr/0000-adr-template.md` — the literal template to copy for every new ADR.
- Review and approval flow: [ADR Governance Model](adr-governance-model.md).
- Sync pipeline: every ADR merged to `main` under `adr/*.md` is fanned out to Confluence (human
  read surface) and to the `adr-lookup` Claude plugin skill (AI read surface) — see
  `scripts/package_claude_plugin.py` and [claude-integration/adoption-review.md](../claude-integration/adoption-review.md).
- Seed ADRs dogfooding this template: [ADR-0001](0001-adopt-arc42.md), [ADR-0002](0002-store-adrs-in-git.md).
