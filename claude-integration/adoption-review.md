# Claude Plugin Sync — Adoption Review

> Deliverable for DS-278. Internal review doc, not a Confluence-published convention page.

## Scope actually synced

DS-278's original scope (Phase 3, written before the other Tier-1 RAs existed) was: all ADRs, the
arc42/C4 template, and the two RAs that existed at that point (Event-driven, Multi-tenant
isolation). By project completion, all six Tier-1 RAs and the metrics catalogue exist, so the
synced scope was widened to match — see `scripts/package_claude_plugin.py` (ADRs) and the
equivalent packaging for the arc42 template and reference-architecture skills below.

| Skill | Source | Contents |
|---|---|---|
| `adr-lookup` | `adr/000N-*.md` | 5 accepted ADRs (excludes the template and the two process docs) |
| `arc42-template` | `documentation-template/arc42-c4-template.md` | The 12-section template, for Claude to scaffold new project docs from |
| `reference-architectures` | `reference-architectures/*.md` | All 6 Tier-1 RAs |

## Validation against a sample architectural question

**Prompt**: "What message broker should I use for a new order-events integration, and what
delivery guarantees should I design for?"

**Expected answer shape** (validated manually against the packaged skill content): the response
should cite the Event-driven RA's broker choice and link [ADR-0003](../adr/0003-use-azure-event-hub-for-order-events-pilot.md)
(Azure Event Hub) and [ADR-0004](../adr/0004-at-least-once-delivery-idempotent-consumers.md)
(at-least-once + idempotent consumers), rather than giving a generic "it depends, here are four
options with no mesoneer-specific recommendation" answer. This is the acceptance bar: a generic
answer means the plugin sync isn't actually being consulted, not that the RA content is wrong.

## Adoption metrics (at project close-out)

| Metric | Value | Notes |
|---|---|---|
| Projects using the arc42 template | 1 (pilot) | Per the adoption guide's "pilot before rollout" rule — org-wide push happens via the socialization workshop series |
| ADRs accepted | 5 | 2 dogfooding (arc42 adoption, Git-as-source-of-truth), 3 from the Event-driven RA pilot |
| RAs finalized | 6 / 6 Tier-1 | Event-driven, Standard stack, Multi-tenant isolation, Serverless, SPA+BFF, Workflow automation |
| Claude plugin skills live | 3 | `adr-lookup`, `arc42-template`, `reference-architectures` |

## Retrospective — what to carry into the next cycle

- **Working well**: the fan-out sync design (Git as sole source of truth, Confluence and the
  plugin as independent read surfaces) meant the plugin sync could be validated without touching
  the Confluence publish path at all — the two never needed to be tested together.
- **Gap**: there's no automated check that a Claude answer actually cites the RA/ADR — the
  validation above was a manual spot-check. A regression test (a fixed set of architectural
  questions with expected-citation assertions) is a reasonable follow-up, not solved in this
  round.
- **Gap**: adoption is measured by counting artifacts (RAs finalized, ADRs accepted), not by
  whether project teams actually consulted them before making a decision. That's a harder metric
  and is intentionally left for the future IDP integration (see the metrics catalogue's IDP
  boundary section) rather than invented ad hoc here.
