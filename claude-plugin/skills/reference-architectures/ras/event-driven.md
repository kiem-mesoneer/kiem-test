---
status: active
---

# Event-Driven / Message-Based Architecture

> **Last updated**: 2026-09-01
> **Status**: Active

## Why

Event-driven architecture is the first Tier-1 Reference Architecture mesoneer has formalized
because a broker choice fans out into more cross-team decisions than almost any other pattern —
schema ownership, delivery semantics, and retry behavior all depend on it, and every team that
adopts messaging independently re-derives the same answers if we don't write them down once. The
order-events pilot (ADR-0003, ADR-0004, ADR-0005) already made these decisions for its own domain;
this RA generalizes them into a reusable blueprint so the next team building an event-driven
service starts from a settled pattern instead of re-litigating broker selection, versioning, and
delivery guarantees from scratch.

## Rules

### Broker choice

- Use **Azure Event Hub** as the default broker for event-driven RAs. It is an approved Cloud
  Platform MVP capability today — no new procurement or security review is needed to adopt it —
  and it needs no team to operate a broker cluster. See
  [ADR-0003](../adr/0003-use-azure-event-hub-for-order-events-pilot.md) for the full decision
  record from the pilot.
- Do not introduce a self-managed broker (Kafka on OpenShift, self-hosted RabbitMQ) for a new
  event-driven service without a new ADR that documents why Event Hub's consumer-group model or
  retention window doesn't fit that specific workload.
- Size the partition count deliberately at namespace creation — Event Hub partition count cannot
  be changed without a data migration, so undersizing it is expensive to fix later.

**Do this:**
```yaml
# infra/eventhub/order-events.yaml (Bicep/ARM-style, illustrative)
resource: Microsoft.EventHub/namespaces/eventhubs
name: order-events
properties:
  partitionCount: 8          # sized for projected peak throughput, not the current pilot load
  messageRetentionInDays: 7  # Event Hub's max under Standard tier — see ADR-0003 consequences
consumerGroups:
  - order-fulfillment-service
  - order-analytics-service   # each competing-consumer group gets its own named consumer group
```

**Not this:**
```yaml
# Standing up a self-managed Kafka cluster "because we might need Kafka features later",
# with no ADR justifying the extra operational surface over the already-approved Event Hub
resource: openshift/statefulset/kafka
replicas: 3
# ...cluster ops now owned by a team with no prior Kafka operational experience
```

### Event schema & versioning strategy

- Every event carries an explicit `eventVersion` field in its envelope. Schema changes are
  **additive-only** — new optional fields — never a rename, retype, or removal of an existing
  field. See [ADR-0005](../adr/0005-event-schema-versioning-strategy.md) for the full rationale.
- A breaking change ships as a new `eventVersion`, published alongside the old version until every
  known consumer has migrated — never as an in-place mutation of an existing version's shape.
- No schema registry is required for this pattern; compatibility is enforced by PR review
  convention. Revisit only if event volume or consumer count grows enough to justify the
  operational cost of a registry (flagged as a Tier-2 candidate in ADR-0005).

**Do this:**
```java
public record OrderPlacedEvent(
    String orderId,
    String eventType,      // "OrderPlaced"
    int eventVersion,      // bump only for a breaking change; additive fields don't bump this
    Instant occurredAt,
    BigDecimal totalAmount,
    String currency,
    @Nullable String promoCode  // added in v1 as an *optional* field — not a version bump
) {}
```

**Not this:**
```java
// v1 shape
public record OrderPlacedEvent(String orderId, BigDecimal totalAmount) {}

// v2 "fix" that silently changes the meaning of an existing field in place —
// any consumer still on the old deploy now misparses totalAmount as a String
public record OrderPlacedEvent(String orderId, String totalAmount) {}
```

### Delivery guarantees & idempotency

- Assume **at-least-once delivery**, not exactly-once. Event Hub does not natively guarantee
  exactly-once delivery to consumers, and building your own exactly-once layer on top of it is a
  well-known distributed-systems trap — see
  [ADR-0004](../adr/0004-at-least-once-delivery-idempotent-consumers.md).
- Every consumer must be idempotent: dedupe on a business key (typically
  `orderId` + `eventType` + `eventVersion`) before applying side effects. This is a required
  pattern for every new consumer of an event stream, not an optional optimization.
- Do not attempt at-most-once (fire-and-forget) delivery for anything that isn't genuinely
  disposable telemetry — silent event loss is rarely an acceptable tradeoff for business events.

**Do this:**
```java
@Service
public class OrderPlacedConsumer {

    private final ProcessedEventRepository processedEvents; // Postgres-backed dedupe table
    private final OrderFulfillmentService fulfillmentService;

    public void handle(OrderPlacedEvent event) {
        var dedupeKey = event.orderId() + ":" + event.eventType() + ":" + event.eventVersion();
        if (processedEvents.existsByKey(dedupeKey)) {
            return; // duplicate delivery — safe no-op, not an error
        }
        fulfillmentService.startFulfillment(event);
        processedEvents.markProcessed(dedupeKey);
    }
}
```

**Not this:**
```java
@Service
public class OrderPlacedConsumer {
    public void handle(OrderPlacedEvent event) {
        // No dedupe check — a redelivered event (retry, consumer restart, rebalance)
        // silently double-charges fulfillment or double-sends a customer notification
        fulfillmentService.startFulfillment(event);
    }
}
```

### Retry & dead-letter-queue (DLQ) patterns

- A message that fails processing is retried **3 times with exponential backoff**, then moved to
  a dedicated DLQ (e.g. `order-events-dlq`) for manual triage — this is the pilot's settled policy
  from ADR-0004, chosen to bound retry cost while avoiding an infinite-retry poison message that
  blocks a partition indefinitely.
- Name each DLQ after its source stream (`<stream-name>-dlq`), not a shared catch-all queue, so
  triage tooling and alerts can be scoped per producing domain.
- DLQ'd messages must retain their original envelope (including `eventVersion`) so a triager can
  replay them once the underlying issue is fixed.

**Do this:**
```java
@Bean
public RetryPolicy orderEventsRetryPolicy() {
    return RetryPolicy.builder()
        .maxAttempts(3)
        .backoff(ExponentialBackoff.of(Duration.ofSeconds(2), 2.0))
        .onExhausted(event -> deadLetterProducer.send("order-events-dlq", event))
        .build();
}
```

**Not this:**
```java
@Bean
public RetryPolicy orderEventsRetryPolicy() {
    // Unbounded retry on a poison message stalls the whole partition for every
    // other event behind it — and there is no DLQ to fall back to for triage
    return RetryPolicy.builder()
        .maxAttempts(Integer.MAX_VALUE)
        .backoff(FixedBackoff.of(Duration.ofSeconds(1)))
        .build();
}
```

### Data-plane / control-plane region alignment

- The Event Hub's **data-plane endpoint** — the namespace that carries message payloads — is
  regionally pinned to the tenant's residency requirement (e.g. Switzerland North for
  Swiss-residency tenants). The RA's **control-plane** concerns — CI/CD pipelines that deploy
  producers/consumers, Terraform state, monitoring/alerting config — carry no such constraint and
  can run wherever is cheapest to operate. See
  [Data-Plane / Control-Plane Separation](../crosscutting/data-control-plane-separation.md) for
  the full crosscutting rule.
- Do not log full event payloads to a centrally-hosted (non-Swiss) log aggregator — that leaks
  tenant data through the control plane and defeats the residency guarantee even when the Event
  Hub namespace itself is correctly pinned.

**Do this:**
```hcl
module "order_events_hub" {
  source = "../modules/eventhub"
  region = "switzerlandnorth"   # data plane: hardcoded to the tenant's residency requirement
}

module "order_events_cicd" {
  source = "../modules/azure-devops-pipeline"
  region = var.control_plane_region   # control plane: free to run in West Europe, cheapest tier
}
```

**Not this:**
```hcl
# A single "region" variable applied to both the Event Hub namespace and the
# pipeline/monitoring stack — one config change away from moving tenant payload
# data out of its required residency region
module "order_events_hub" {
  source = "../modules/eventhub"
  region = var.default_region
}
```

### Producer/consumer stack alignment

- Producers and consumers of event-driven services follow mesoneer's Standard Stack: **Spring
  Boot** services publish/consume via the Event Hub SDK, backed by **Postgres** for both business
  state and the idempotency/dedupe table; any user-facing surface is an **Angular** frontend that
  talks to its own BFF, never a direct Event Hub consumer.
- Producer and consumer deploy independently — do not assume they upgrade in lockstep. This is
  exactly why the additive-only schema rule above exists.
- CI/CD for producer and consumer services runs through GitHub Actions or Azure DevOps pipelines
  per mesoneer's standard service pipeline, not a bespoke deploy script per event-driven service.

**Do this:**
```java
// Spring Boot producer, publishing via the Event Hub SDK
@Component
public class OrderEventPublisher {
    private final EventHubProducerClient producerClient;

    public void publishOrderPlaced(OrderPlacedEvent event) {
        var eventData = new EventData(objectMapper.writeValueAsBytes(event));
        producerClient.send(List.of(eventData));
    }
}
```

**Not this:**
```typescript
// Angular frontend consuming Event Hub directly — bypasses the BFF, exposes broker
// credentials to the browser, and skips the idempotency/dedupe layer entirely
const consumerClient = new EventHubConsumerClient(connectionString, 'order-events');
consumerClient.subscribe({ processEvents: (events) => renderOrderUpdates(events) });
```

## Tooling & Enforcement

- ADRs [0003](../adr/0003-use-azure-event-hub-for-order-events-pilot.md),
  [0004](../adr/0004-at-least-once-delivery-idempotent-consumers.md), and
  [0005](../adr/0005-event-schema-versioning-strategy.md) are the accepted decision records this
  RA generalizes — deviating from broker choice, delivery model, or versioning strategy for a new
  event-driven service requires a new ADR, not a silent departure from this doc.
- [Data-Plane / Control-Plane Separation](../crosscutting/data-control-plane-separation.md)
  crosscutting convention governs the region split for the broker namespace vs. deployment/CI
  config; its shared Terraform modules (`modules/eventhub`) are the enforcement point.
- Additive-only schema compatibility is currently enforced by PR review convention, not automated
  tooling — a schema-diff CI check is a tracked follow-up (see ADR-0005), not solved by this
  document alone.
- Idempotent-consumer and DLQ patterns are referenced from each event-driven service's arc42 §8
  (Crosscutting Concepts) so they show up in project-level documentation, not just this
  company-wide convention.
