---
status: active
---

# arc42/C4 Adoption Guide

> **Last updated**: 2026-09-01
> **Status**: Active

## Why

Handed only the 12-section arc42 template, teams tend toward one of two failure modes: a new
project ships with zero documentation ("we'll backfill it later," which never happens), or an
existing, years-old service tries to boil the ocean and write all 12 sections from scratch in one
PR, stalls, and the doc rots half-finished. This guide exists to make partial, incremental
adoption an explicitly sanctioned path rather than something that feels like cutting corners.

## Rules

### New projects start from the full skeleton; existing projects retrofit incrementally

- A **new** project copies the [arc42/C4 Template](arc42-c4-template.md) in full before its first
  feature PR merges — the cost of filling in a section is lowest before there's a system to
  describe.
- An **existing** project without arc42 docs retrofits incrementally: pick 2-3 mandatory sections
  (see below) for the first PR, and add the rest opportunistically as those parts of the system
  come up for change — not as a single dedicated "write the docs" sprint.

**Do this:**
```text
Existing "Checkout" service, no prior docs:
PR #1: add §1 (Introduction & Goals) + §8 (Crosscutting Concepts, auth section only)
PR #7 (three weeks later, touches the DB layer anyway): add §5 (Building Block View)
```

**Not this:**
```text
Existing "Checkout" service: "documentation sprint" ticket opened to write all 12 sections
at once — ships three months later, already stale by the time it merges
```

### Mandatory vs optional sections

- **Mandatory for every project, regardless of size**: §1 Introduction & Goals, §3 Context &
  Scope, §8 Crosscutting Concepts (only the concepts that actually apply — see the [Crosscutting
  Design Principles](../crosscutting/data-control-plane-separation.md) for one example), §9
  Architecture Decisions, §11 Risks & Technical Debt.
- **Optional / defer if it doesn't add information**: §2 Constraints (skip if there are none
  beyond "must run on Cloud Platform MVP"), §12 Glossary (skip if the domain has no jargon a
  newcomer wouldn't already know).

**Do this:**
```markdown
## 2. Constraints
N/A — no constraints beyond the standard Cloud Platform MVP baseline.
```

**Not this:**
```markdown
## 2. Constraints
(section heading present, left completely empty — a reader can't tell if that means
"none" or "not written yet")
```

### Pilot before declaring org-wide adoption

- Before rolling arc42 out as a hard requirement, pilot the template and this adoption guide on
  one live project (ideally a mid-size, already-running service rather than a greenfield one — a
  greenfield project doesn't exercise the "retrofit an existing system" rules above). Capture
  friction points from the pilot team and fold them into this guide before the org-wide push in
  [DS-442's socialization workshop](../socialization/arc42-workshop.md).

**Do this:**
```text
Pilot: one existing service, 4-week trial, feedback captured in a short retro doc,
2 rule clarifications folded back into this guide before rollout.
```

**Not this:**
```text
Guide published and mandated org-wide the same week it was written, with no pilot feedback
```

## Tooling & Enforcement

- Starting point: [arc42/C4 Template](arc42-c4-template.md).
- Pilot retrospective and the resulting guide clarifications are captured as part of the
  [Internal Socialization](../socialization/arc42-workshop.md) rollout materials.
- Enforcement is social, not automated, at this stage: SAs check for §1/§3/§8/§9/§11 presence
  during architecture support requests and PR review, rather than a CI gate — a CI doc-structure
  lint is a known gap, tracked as a follow-up rather than solved here.
