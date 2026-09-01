---
status: active
---

# arc42/C4 Template

> **Last updated**: 2026-09-01
> **Status**: Active

## Why

Project-level architecture documentation across mesoneer had no consistent structure — every
project put "how does auth work" or "what's the deployment topology" in a different place, or
nowhere at all (see [ADR-0001](../adr/0001-adopt-arc42.md)). This template fixes the *shape* of
that documentation so any engineer who has read one project's arc42 doc can navigate any other
mesoneer project's doc without a tour.

## Rules

### The 12 arc42 sections are the required table of contents

Every project-level architecture doc has these sections, in this order, even if some are marked
"N/A — see adoption guide §Mandatory vs optional":

1. Introduction & Goals
2. Constraints
3. Context & Scope
4. Solution Strategy
5. Building Block View
6. Runtime View
7. Deployment View
8. Crosscutting Concepts
9. Architecture Decisions (links to ADRs — see below)
10. Quality Requirements
11. Risks & Technical Debt
12. Glossary

**Do this:**
```markdown
## 5. Building Block View
### 5.1 Whitebox: Checkout Service
Contains: OrderController, PaymentGateway, InventoryClient (see C4 container diagram below).
```

**Not this:**
```markdown
## 5. Building Block View
[Building block view]

*(section heading present, content is a placeholder that was never filled in)*
```

### Structural and behavioral sections use the C4 model, not free-form diagrams

- §5 (Building Block View) and §6 (Runtime View) use C4 Context / Container / Component diagrams
  rather than an ad-hoc boxes-and-arrows drawing — C4's fixed vocabulary (person, system,
  container, component, relationship) is what lets a reader compare two projects' diagrams
  without a legend each time.

**Do this:**
```text
[C4 Container diagram]
  Person "Customer" --uses--> Container "Checkout SPA" (Angular)
  Container "Checkout SPA" --calls (HTTPS/JSON)--> Container "Checkout API" (Spring Boot)
  Container "Checkout API" --reads/writes--> Container "Checkout DB" (Postgres)
```

**Not this:**
```text
[a screenshot of a whiteboard photo with hand-drawn boxes and no labels on the arrows]
```

### §9 (Architecture Decisions) links to ADRs — it does not restate them

- §9 is an index: one line per relevant ADR, linking to the actual ADR file (`adr/NNNN-*.md` in
  this repo, or the project's own `docs/adr/` directory). Never copy-paste the ADR's content into
  the arc42 doc — that creates two places that can drift out of sync.

**Do this:**
```markdown
## 9. Architecture Decisions
* [ADR-0003](../../adr/0003-use-azure-event-hub-for-order-events-pilot.md) — broker choice
* [ADR-0004](../../adr/0004-at-least-once-delivery-idempotent-consumers.md) — delivery semantics
```

**Not this:**
```markdown
## 9. Architecture Decisions
We decided to use Azure Event Hub because... (full ADR content pasted and now permanently
out of date the moment the source ADR is superseded)
```

## Tooling & Enforcement

- Full section skeleton: copy this file's structure into the project's own repo (e.g.
  `docs/architecture.md`) as the starting point — do not write from a blank page.
- Which sections are mandatory vs optional for a given project size: see the
  [arc42/C4 Adoption Guide](adoption-guide.md).
- §9 cross-links are consumed by the `adr-lookup` Claude plugin skill so AI-assisted guidance can
  cite the same decisions a human reader would follow.
