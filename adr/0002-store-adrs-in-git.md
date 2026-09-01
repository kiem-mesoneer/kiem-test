# ADR-0002: Store ADRs in Git as the single source of truth

## Status
accepted

## Context and Problem Statement
ADRs need one authoritative home. They also need to reach two very different audiences: engineers
working in their IDE / AI coding assistant, and business/PM/CISO stakeholders who live in
Confluence. We need to decide where the source of truth lives before building the sync pipeline
that fans it out (ADR-0003 is downstream of this choice; see also DS-273).

## Decision Drivers
* Must support pull-request review (see the ADR Governance Model's approval flow)
* Must be diffable and versioned without a proprietary history model
* Must be consumable by both a static site (Confluence) and a Claude plugin (raw markdown)

## Considered Options
* Git (this repo, `adr/*.md`), fanned out to read-only mirrors
* Confluence as source of truth, exported to Git for the plugin
* A dedicated ADR tool (e.g. a hosted ADR SaaS) as source of truth

## Decision Outcome
Chosen option: "Git", with Confluence and the Claude plugin as independent, read-only, one-way
mirrors. Git is the only option that gives PR review for free (Confluence commenting is not a
gate), keeps ADRs as portable plain markdown consumable by any tool without a rendering step, and
avoids a dependency on a third-party ADR SaaS as it will not exist in 100 years while the
Markdown files will.

### Consequences
* Good, because ADR review reuses the exact same PR/CODEOWNERS mechanism as code review — no
  separate governance tooling to build
* Good, because both Confluence and the Claude plugin can be regenerated at any time from Git;
  neither is ever edited directly, so there's only one place an ADR can silently drift
* Bad, because business stakeholders who never touch Git depend entirely on the sync pipeline
  being healthy — mitigated by the drift monitor in `scripts/check_sync_drift.py`
