# ADR-0005: Additive-only event schema evolution with an explicit version field

## Status
accepted

## Context and Problem Statement
Order-events will be consumed by services owned by other teams over time. We need a schema
evolution policy decided up front — before a second consumer exists — so a producer change can
never silently break a consumer that hasn't redeployed yet.

## Decision Drivers
* Producers and consumers deploy independently and cannot be assumed to upgrade in lockstep
* Team has no existing schema registry infrastructure to build on
* Must be simple enough to document as a rule other RAs (workflow automation, serverless) can reuse

## Considered Options
* Additive-only changes (new optional fields only) + an explicit `eventVersion` field in the envelope
* A schema registry (e.g. Avro + Confluent-style registry) enforcing compatibility at write time
* No formal policy — consumers defensively parse whatever arrives

## Decision Outcome
Chosen option: "additive-only changes + explicit `eventVersion` field", because it needs no new
infrastructure, is simple enough to enforce by PR review convention today, and still gives
consumers a concrete field to branch on if a breaking change ever becomes unavoidable. A schema
registry is noted as a Tier-2 candidate if event volume/consumer count grows enough to justify the
operational cost.

### Consequences
* Good, because existing consumers never break from a producer-side additive change — no
  coordination required for the common case
* Good, because `eventVersion` gives a documented escape hatch: a breaking change ships as a new
  version, old consumers keep reading the old version until they migrate
* Bad, because there's no automated enforcement yet (relies on PR review) — flagged as a follow-up
  candidate for the doc-structure CI lint work, not solved by this ADR
