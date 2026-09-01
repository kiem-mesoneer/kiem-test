# ADR-0003: Use Azure Event Hub as the event backbone for the Event-driven RA pilot

## Status
accepted

## Context and Problem Statement
The Event-driven / message-based Reference Architecture (DS-276) needs a concrete broker choice
for its pilot — order-events — before delivery semantics (ADR-0004) or schema evolution
(ADR-0005) can be decided. This is deliberately the first RA and first seed ADR set: it dogfoods
the ADR pipeline end-to-end before any other team commits to a broker.

## Decision Drivers
* Must be available on Cloud Platform MVP without a new procurement/security review
* Team has no in-house operational experience running a broker (rules out self-hosted options)
* Must support both HTTP/AMQP producers and a consumer-group model for competing consumers

## Considered Options
* Azure Event Hub
* Apache Kafka (self-managed on OpenShift)
* RabbitMQ (Cloud Platform MVP add-on)

## Decision Outcome
Chosen option: "Azure Event Hub", because it is already an approved Cloud Platform MVP capability
(no new vendor/security review), needs no team to operate a broker cluster, and its consumer-group
model covers the pilot's competing-consumers requirement without extra infrastructure.

### Consequences
* Good, because zero new operational surface — Cloud Platform owns patching/scaling
* Good, because native Azure AD-based auth reuses existing service-principal patterns
* Bad, because partition count is fixed at Event Hub creation and requires a data migration to
  change later — the RA document records a starting partition count and the reasoning behind it
* Bad, because Event Hub's retention window is shorter than Kafka's — acceptable for this pilot's
  at-least-once/idempotent-consumer model (ADR-0004), revisit if a future RA needs event replay
  beyond 7 days
