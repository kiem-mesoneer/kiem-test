# ADR-0004: Use at-least-once delivery with idempotent consumers, not exactly-once semantics

## Status
accepted

## Context and Problem Statement
Given Azure Event Hub as the broker (ADR-0003), the pilot needs a delivery-guarantee model and a
dead-letter policy for order-events. Exactly-once semantics across a broker + consumer + database
boundary is a well-known distributed-systems trap; we need to decide deliberately rather than
assume it by default.

## Decision Drivers
* Event Hub does not natively guarantee exactly-once delivery to consumers
* Order-events consumers already write to a Postgres store, which can support idempotency keys
* Simplicity and debuggability matter more than shaving the last bit of duplicate-processing risk

## Considered Options
* At-least-once delivery + idempotent consumers (dedupe on a business key at the consumer)
* Attempt exactly-once via transactional outbox + broker-side dedup (Event Hub doesn't support this natively)
* At-most-once (fire-and-forget, accept event loss)

## Decision Outcome
Chosen option: "at-least-once delivery with idempotent consumers", because it's the only option
that matches what Event Hub actually guarantees, and idempotency is cheap here — the order-events
consumer already has a natural dedupe key (`orderId` + `eventType` + `eventVersion`).

### Consequences
* Good, because consumers are simple to reason about: "process, and if you see this key again,
  no-op" — no distributed transaction coordinator needed
* Good, because retried/duplicate events are safe by construction, which also simplifies the
  dead-letter/retry policy below
* Bad, because every new consumer of this event stream must implement the same dedupe check —
  documented as a required pattern in the Event-driven RA rather than left as tribal knowledge
* **Dead-letter policy**: a message that fails processing is retried 3 times with exponential
  backoff, then moved to the `order-events-dlq` queue for manual triage — chosen over infinite
  retry to avoid a poison message blocking the partition indefinitely
