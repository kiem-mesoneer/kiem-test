---
status: active
---

# Reference Architecture: Serverless Workloads

> **Last updated**: 2026-09-01
> **Status**: Active

## Why

mesoneer runs workloads on two compute models side by side: containers on OpenShift and
serverless functions on Azure Functions / AWS Lambda. Both are legitimate — the failure mode isn't
picking the "wrong" one in the abstract, it's picking serverless for steady high-throughput
traffic (racking up cold-start latency and a surprise consumption-plan bill) or picking
OpenShift for a workload that fires twice a day (paying for an always-on pod to do nothing).
This RA exists so that choice, the timeout/memory/concurrency numbers that make serverless
functions actually reliable, and the observability/cost guardrails that keep them operable are
decided once, consistently, rather than re-litigated per team. It complements the
[Event-driven RA](./event-driven.md) (delivery guarantees for the queues/topics that trigger
functions) and the [Data/Control-Plane Separation](../crosscutting/data-control-plane-separation.md)
principle (region pinning for any data a function reads or writes).

## Rules

### When to choose serverless vs. containers (OpenShift)

- Default to **serverless** when traffic is bursty/event-driven and sustained load stays under
  roughly **50 req/s per function** with tolerable idle periods (minutes to hours between
  invocations) — you pay per execution instead of for idle pod capacity.
- Default to **OpenShift (containers)** when traffic is steady/high-throughput (sustained load
  above ~50 req/s), when a single request routinely runs longer than the platform's hard timeout
  (10 minutes on Azure Functions Premium, 15 minutes on AWS Lambda), or when the workload needs a
  long-lived in-memory state/connection pool that a cold-started function can't amortize.
- If a workload is borderline, prototype it as a function first — moving a stateless function to
  a container later is cheap; the reverse (decomposing a monolithic Deployment into functions)
  is not.

**Do this:**
```text
Nightly settlement-file import (runs 3x/day, ~200 files, done in <2 min): Azure Function,
timer-triggered. No idle cost outside the 3 runs/day.

Payment-authorization API (sustained 300 req/s, p99 < 150ms required): OpenShift Deployment
with HPA. Consumption-plan cold starts would blow the latency budget; container keeps a warm pool.
```

**Not this:**
```text
Payment-authorization API deployed as a consumption-plan Azure Function "because serverless
is cheaper" — cold starts push p99 past 2s under bursty load, and at 300 req/s sustained the
per-execution billing costs more than a right-sized container anyway.
```

### Cold-start mitigation, timeout budgets, memory sizing

- Every function declares an explicit **timeout budget** and **cold-start budget** in its
  deployment manifest — not the platform default.
- A **queue-triggered** Azure Function targets a **5s p99 cold-start budget**; the consumption
  plan is acceptable here because the caller (the queue) tolerates a few seconds of added latency
  and retries on visibility-timeout expiry.
- A **latency-sensitive HTTP-triggered** function (anything a user or another synchronous service
  waits on) uses **provisioned concurrency / Premium plan (Azure)** or **provisioned concurrency
  (AWS Lambda)** instead of the consumption plan — the consumption plan's cold start (1-10s+ on a
  cold instance) is not acceptable in a synchronous request path.
- Memory is sized from measured peak RSS plus 25% headroom, not left at the platform default
  (128 MB on Lambda, 1.5 GB on Azure Functions) — both platforms bill CPU proportionally to
  memory, so under-sizing silently slows the function and over-sizing silently inflates cost.

**Do this:**
```bicep
resource httpFunction 'Microsoft.Web/sites@2023-01-01' = {
  name: 'checkout-api-fn'
  properties: {
    serverFarmId: premiumPlan.id   // Premium plan: pre-warmed instances, no cold start
    siteConfig: {
      functionAppScaleLimit: 20
      minimumElasticInstanceCount: 1   // always-warm floor
    }
  }
}

resource queueFunction 'Microsoft.Web/sites@2023-01-01' = {
  name: 'order-settlement-fn'
  properties: {
    serverFarmId: consumptionPlan.id   // consumption OK: queue trigger tolerates cold start
    siteConfig: {
      functionAppScaleLimit: 10
    }
  }
}
```

**Not this:**
```bicep
resource httpFunction 'Microsoft.Web/sites@2023-01-01' = {
  name: 'checkout-api-fn'
  properties: {
    serverFarmId: consumptionPlan.id   // synchronous checkout call on a cold-startable plan
  }
  // no memory or concurrency sizing set — left at platform default
}
```

### Event source patterns: HTTP, queue, timer, blob

Each trigger type has a default posture — deviating from it needs a documented reason in the
function's README, not a silent choice.

- **HTTP trigger** — synchronous request/response (e.g. a BFF calling an internal API). Requires
  auth (Azure AD / IAM, never anonymous in production) and an explicit timeout budget passed to
  the caller.
- **Queue trigger** — asynchronous work handed off by another service (e.g. order events). See
  the [Event-driven RA](./event-driven.md) for at-least-once delivery guarantees and idempotency
  requirements the function must honor.
- **Timer trigger** — scheduled batch/maintenance work (reconciliation, cleanup, report
  generation). Uses a cron expression checked into the function's IaC, never a manually-configured
  schedule in the portal.
- **Blob/object-storage trigger** — reactive processing of an uploaded file (e.g. a document
  landing in blob storage triggers OCR). Must be idempotent against re-delivery, since both Azure
  Blob triggers and AWS S3 event notifications can fire more than once for the same object.

**Do this:**
```yaml
# function.json (queue trigger) — explicit idempotency key from the message
bindings:
  - type: queueTrigger
    queueName: order-events
    connection: OrderEventsStorage
# handler dedupes on message.orderId + message.eventVersion before processing
```

**Not this:**
```yaml
# blob trigger handler that re-runs the full OCR pipeline (and re-emits downstream
# events) every time the platform redelivers the same blob-created notification,
# because it has no idempotency check
```

### Observability: correlation IDs across async triggers

- Every function propagates a **correlation ID** (`x-correlation-id` on HTTP, a
  `correlationId` field on queue/event payloads) end to end — this is the same pattern used in the
  Standard Stack RA and must not be dropped just because the hop is asynchronous.
- An HTTP-triggered function that enqueues a message for a queue-triggered function to pick up
  **must copy the inbound correlation ID onto the outbound message** — without this, a trace
  breaks at the async boundary and incident response loses the ability to follow one request
  through the whole chain.
- Structured logs (JSON) always include: `correlationId`, `functionName`, `invocationId`,
  `coldStart` (bool). `coldStart` is what lets you separate "slow because cold" from "slow
  because broken" in dashboards.

**Do this:**
```csharp
[Function("EnqueueOrder")]
public async Task Run(HttpRequestData req)
{
    var correlationId = req.Headers.TryGetValues("x-correlation-id", out var v)
        ? v.First()
        : Guid.NewGuid().ToString();

    await _queueClient.SendMessageAsync(new OrderEvent
    {
        OrderId = order.Id,
        CorrelationId = correlationId   // propagated across the async boundary
    });

    _logger.LogInformation("Order enqueued {CorrelationId} {ColdStart}",
        correlationId, ExecutionContext.FunctionAppDirectory is null);
}
```

**Not this:**
```csharp
[Function("EnqueueOrder")]
public async Task Run(HttpRequestData req)
{
    // no correlation ID read from the inbound request, none set on the outbound message —
    // the downstream queue-triggered function logs with a fresh, unrelated invocationId
    await _queueClient.SendMessageAsync(new OrderEvent { OrderId = order.Id });
}
```

### Cost model and guardrails

- Every consumption-plan function app has a **budget alert** (Azure Cost Management budget /
  AWS Budgets) at 80% and 100% of its expected monthly spend, routed to the owning team's alert
  channel — not just to a shared platform inbox nobody watches.
- Every function declares a **`functionAppScaleLimit` (Azure) or reserved/provisioned concurrency
  cap (AWS Lambda)** — an unbounded scale-out is exactly how a retry storm or a misconfigured
  event source turns into the classic "serverless surprise bill": one runaway trigger fans out
  to thousands of concurrent, billed executions before anyone notices.
- Timer- and queue-triggered functions that call a paid downstream API (e.g. a third-party
  enrichment service) cap their own throughput independently of the platform's scale limit, so a
  burst in the queue doesn't silently multiply the downstream bill too.

**Do this:**
```hcl
resource "azurerm_consumption_budget_resource_group" "fn_budget" {
  name    = "order-settlement-fn-budget"
  amount  = 500   # CHF/month, based on measured historical spend + 20%
  notification {
    threshold      = 80
    contact_emails = ["team-payments@mesoneer.io"]
  }
  notification {
    threshold      = 100
    contact_emails = ["team-payments@mesoneer.io", "platform-oncall@mesoneer.io"]
  }
}
```

**Not this:**
```text
A consumption-plan function with no scale limit and no budget alert processes a queue that
gets accidentally flooded by an upstream retry bug — 40,000 concurrent executions run
overnight before the monthly invoice surfaces the problem.
```

### Deployment via GitHub Actions / Azure DevOps

- Function deployments go through the same pipeline discipline as every other mesoneer
  workload: build → test → deploy-to-staging → smoke test → promote — a function app is not a
  "just click deploy from the portal" exception.
- Infrastructure (plan, memory, scale limit, budget alert) is defined in the same IaC change as
  the code that runs on it, so a memory bump or a scale-limit change is reviewed like any other
  production change, not click-fixed in the Azure portal.
- Deployment slots (Azure) or aliases (AWS Lambda) are used for zero-downtime promotion —
  deploy to a staging slot, run the smoke test against it, swap.

**Do this:**
```yaml
# .github/workflows/deploy-function.yml
jobs:
  deploy:
    steps:
      - run: func azure functionapp publish order-settlement-fn --slot staging
      - name: smoke test staging slot
        run: ./scripts/smoke-test.sh https://order-settlement-fn-staging.azurewebsites.net
      - name: swap staging into production
        run: az functionapp deployment slot swap -n order-settlement-fn -g rg-orders --slot staging
```

**Not this:**
```text
A developer deploys straight to the production function app from their local machine via
`func azure functionapp publish` because "it's just a small function" — no smoke test, no
review of the memory/scale-limit change, no rollback slot to swap back to.
```

## Tooling & Enforcement

- Bicep/Terraform modules for Azure Functions and Lambda enforce `functionAppScaleLimit` /
  concurrency cap and a linked budget alert as required parameters — a function app module without
  them fails `terraform plan` / `bicep build` review.
- GitHub Actions / Azure DevOps pipeline templates (`deploy-function.yml`) are the only sanctioned
  path to production for function apps; direct `func azure functionapp publish` to production is
  blocked by environment protection rules.
- Correlation-ID propagation and structured JSON logging (`correlationId`, `functionName`,
  `invocationId`, `coldStart`) are checked in the shared function-app logging middleware, not
  hand-rolled per function.
- Cost guardrails (budget alerts, scale limits) are reviewed quarterly against actual spend by the
  owning team, per the same cadence used for the Standard Stack RA's cost review.
