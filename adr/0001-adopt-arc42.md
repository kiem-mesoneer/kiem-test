# ADR-0001: Adopt arc42 as the standard project documentation structure

## Status
accepted

## Context and Problem Statement
Project-level architecture documentation across mesoneer has no consistent structure: some
projects have a wiki page, some have a stale README, most have nothing beyond diagrams in
someone's head. Engineers joining a new project can't find "how does this system handle auth" or
"what's the deployment topology" in a predictable place. We need one standard table of contents
every project documents against.

## Decision Drivers
* Must cover both static structure (building blocks) and dynamic behavior (runtime view)
* Must have room for quality requirements and known risks/technical debt, not just "how it works"
* Should be an established standard, not something mesoneer invents and has to maintain alone

## Considered Options
* arc42
* C4 model alone (no accompanying narrative structure)
* No standard — each project documents however it prefers

## Decision Outcome
Chosen option: "arc42", combined with C4 for the diagramming notation (arc42 §5 Building Block
View and §6 Runtime View are populated with C4 context/container/component diagrams). arc42 is a
widely adopted, vendor-neutral template with an explicit §9 for architecture decisions (which
links directly to our ADRs) and §10/§11 for quality requirements and risks — exactly the sections
stakeholder interviews (see the Quality Metrics Catalogue) flagged as most often missing today.

### Consequences
* Good, because every reference architecture and every future project doc shares one structure —
  an engineer who's read one arc42 doc can navigate any other
* Good, because §9 (Architecture Decisions) gives ADRs a canonical home inside project docs,
  instead of living disconnected from the artifact they justify
* Bad, because arc42's 12 sections are more ceremony than a one-page README — mitigated by the
  arc42/C4 Adoption Guide explicitly allowing partial adoption for smaller projects
