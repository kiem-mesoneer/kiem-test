---
status: active
---

# Reference Architecture: Multi-Tenant Data Isolation

> **Last updated**: 2026-09-01
> **Status**: Active

## Why

Most mesoneer SaaS products run many tenants on one deployment for cost and operational reasons,
but a data leak between tenants — even a single row — is a breach, not a bug. This RA extends the
[Standard Stack RA](standard-stack.md) (Angular + Spring Boot + Postgres, JWT auth, structured
logging already in place) with the tenancy layer on top: which isolation model to pick per tenant,
how a request's tenant is determined and enforced so a missing check fails closed instead of
leaking, and how that connects to the [data-plane/control-plane split](../crosscutting/data-control-plane-separation.md)
when a tenant like Swiss Olympic needs data pinned to Switzerland. The goal is a default that a
new service can adopt without re-deriving tenant isolation from scratch, and that survives a
developer forgetting to add a `WHERE tenant_id = ?` clause.

## Rules

### Isolation models and their trade-offs

Three models cover practically every tenant we onboard. Pick per-tenant, not per-product — a single
product can run tenants under different models simultaneously.

- **Row-level / shared schema**: all tenants share one schema and one set of tables, distinguished
  by a `tenant_id` column. Cheapest to run and easiest to migrate schema changes for (one migration
  applies to everyone), but isolation depends entirely on every query correctly filtering by
  `tenant_id` — which is why we never rely on application code alone (see the RLS rule below).
- **Schema-per-tenant**: one Postgres schema per tenant inside a shared database instance.
  Stronger blast-radius containment than shared rows (a bug in one tenant's queries can't touch
  another schema without an explicit `search_path`/cross-schema reference), and gives each tenant
  an independently restorable backup unit, at the cost of N schemas to migrate and a connection
  pool that has to route by tenant.
- **Database-per-tenant**: one Postgres database (or instance) per tenant. Strongest isolation and
  the only model that gives a hard guarantee for data residency and independent scaling/failover,
  but the most expensive to operate and the slowest to provision — reserve it for tenants who
  contractually or regulatorily require it.

**Do this — shared schema with Postgres Row-Level Security enforcing the boundary at the database, not just in application code:**
```sql
-- Every tenant-owned table carries tenant_id and RLS is mandatory, not optional
CREATE TABLE bookings (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   uuid NOT NULL,
    athlete_id  uuid NOT NULL,
    starts_at   timestamptz NOT NULL
);

ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;
ALTER TABLE bookings FORCE ROW LEVEL SECURITY; -- applies even to the table owner

CREATE POLICY tenant_isolation ON bookings
    USING (tenant_id = current_setting('app.tenant_id', false)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', false)::uuid);

-- The app sets this once per connection/transaction, from the tenant context (see below)
SET app.tenant_id = '3fa85f64-5717-4562-b3fc-2c963f66afa6';
```

**Not this:**
```sql
-- Isolation that exists only as an application-level convention
SELECT * FROM bookings WHERE tenant_id = :tenantId;
-- One repository method, one code review, one new developer away from
-- `SELECT * FROM bookings` with no WHERE clause at all — and nothing in the
-- database stops it.
```

### Decision rule: which isolation model for a given tenant

Default to the cheapest model that meets the tenant's contractual and regulatory requirements —
don't over-isolate every tenant "just in case," and don't under-isolate a regulated tenant to save
infrastructure cost.

- **Standard SaaS-tier tenants** (the majority): shared schema, `tenant_id` column, enforced by
  Postgres RLS as shown above. This is the default for every new tenant unless a rule below says
  otherwise.
- **Enterprise tenants with contractual isolation requirements** (e.g. "your data must never share
  a table with another customer's"): schema-per-tenant in the shared instance.
- **Regulated tenants with data-residency requirements** — mesoneer's example is **Swiss Olympic**,
  whose athlete health and performance data must stay resident in Switzerland and be
  demonstrably isolated for audit purposes: dedicated schema or dedicated database, provisioned in
  a Swiss region, per the [data-plane/control-plane split](../crosscutting/data-control-plane-separation.md).
  Row-level sharing is not acceptable here even with RLS, because the audit and residency
  requirement is about the physical/logical boundary of the data store, not just query-time access
  control.

**Do this:**
```yaml
# tenant-registry.yaml — isolation model is a per-tenant decision, driven by tenant tier
tenants:
  - id: acme-corp
    tier: standard
    isolation_model: shared-schema-rls
  - id: contoso-enterprise
    tier: enterprise
    isolation_model: schema-per-tenant
  - id: swiss-olympic
    tier: regulated
    isolation_model: dedicated-database
    region: switzerlandnorth   # data-plane resource — see data-control-plane-separation.md
```

**Not this:**
```yaml
# One isolation model for every tenant regardless of tier — either wastes money isolating
# tenants who don't need it, or under-isolates a regulated tenant who does
tenants:
  - id: acme-corp
    isolation_model: dedicated-database
  - id: swiss-olympic
    isolation_model: dedicated-database
```

### Tenant context propagation is mandatory, not opt-in

A request's tenant must be resolved exactly once, by infrastructure the request cannot bypass —
never left to each controller or repository method to figure out. On the Standard Stack, the
tenant ID is a claim in the JWT already validated by the auth layer; a single `OncePerRequestFilter`
resolves it into a request-scoped `TenantContext` before any controller code runs, and that context
is what sets the Postgres session variable the RLS policy reads.

**Do this:**
```java
// Runs for every request, registered as infrastructure — not an annotation
// individual controllers opt into.
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 10) // after JWT auth, before everything else
public class TenantContextFilter extends OncePerRequestFilter {

    private final TenantContextHolder tenantContextHolder;

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                     HttpServletResponse response,
                                     FilterChain chain) throws IOException, ServletException {
        Jwt jwt = (Jwt) SecurityContextHolder.getContext().getAuthentication().getPrincipal();
        UUID tenantId = UUID.fromString(jwt.getClaimAsString("tenant_id"));

        tenantContextHolder.set(tenantId); // request-scoped, cleared in finally
        try {
            chain.doFilter(request, response);
        } finally {
            tenantContextHolder.clear();
        }
    }
}

// A single connection-acquisition hook sets the DB session variable from the same context —
// every query on this connection is now scoped by RLS, with no per-repository code needed.
@Bean
public DataSource tenantAwareDataSource(DataSource delegate, TenantContextHolder ctx) {
    return new TenantAwareDataSourceProxy(delegate, () ->
        "SET app.tenant_id = '" + ctx.require() + "'");
}
```

**Not this:**
```java
// Tenant ID passed around as a method parameter that every caller must remember to supply
public List<Booking> findBookings(UUID tenantId) {
    return bookingRepository.findByTenantId(tenantId);
}
// Works fine until one call site — a batch job, a new endpoint, a background
// reconciliation task — forgets to pass it, or passes the wrong tenant's ID.
```

### Security boundary: missing tenant context must fail closed

If `TenantContextFilter` cannot resolve a tenant (missing claim, malformed JWT, an internal job
that forgot to set a system context explicitly), the request must be rejected — never silently
proceed as if unscoped, and never fall back to "return everything." Combine this with `FORCE ROW
LEVEL SECURITY` from the isolation rule above: even if a code path somehow reaches the database
without an application-level check, the missing `app.tenant_id` session variable makes the RLS
policy evaluate to false for every row, not true.

**Do this:**
```java
public UUID require() {
    UUID tenantId = threadLocal.get();
    if (tenantId == null) {
        // Fail closed: no tenant context means no data access, full stop.
        throw new TenantContextMissingException(
            "No tenant context on this thread — refusing to execute a tenant-scoped operation");
    }
    return tenantId;
}
```
```sql
-- With no app.tenant_id set, current_setting(..., false) raises an error rather than
-- returning NULL, so the RLS policy comparison fails and FORCE ROW LEVEL SECURITY means
-- even the table owner gets zero rows back — deny by default, not allow by default.
```

**Not this:**
```java
public UUID getOrDefault() {
    UUID tenantId = threadLocal.get();
    return tenantId != null ? tenantId : GLOBAL_ADMIN_TENANT; // fail-open "just to be safe"
}
```
```sql
-- current_setting('app.tenant_id', true) -- the `true` (missing_ok) turns a missing
-- session variable into NULL instead of an error, and `tenant_id = NULL` is neither
-- true nor false in SQL — some drivers/ORMs then silently treat the policy as satisfied
-- for superuser/BYPASSRLS roles. Never grant BYPASSRLS to the application's DB role.
```

### Tenant provisioning is control plane; the tenant's data store is data plane

Provisioning a new tenant's schema or database is orchestration — it can run from wherever the
provisioning service is deployed, per the [data-plane/control-plane separation
principle](../crosscutting/data-control-plane-separation.md). The database or schema it creates is
the data plane, and must be provisioned in the region the tenant's residency requirement demands.
Don't let the provisioning pipeline's own region leak into the resource it creates.

**Do this:**
```hcl
module "tenant_provisioning_service" {
  source = "../modules/app-service"
  region = "westeurope"          # control plane — runs the onboarding workflow, no tenant data
}

module "tenant_database" {
  source    = "../modules/postgres"
  for_each  = var.tenants
  region    = each.value.residency_region  # e.g. "switzerlandnorth" for swiss-olympic
  isolation = each.value.isolation_model    # shared-schema-rls | schema-per-tenant | dedicated-database
}
```

**Not this:**
```hcl
module "tenant_onboarding_pipeline" {
  source = "../modules/app-service"
  region = var.default_region   # provisioning logic AND every tenant database it creates
}                                 # inherit one region — a Swiss Olympic database ends up
                                  # wherever "default_region" happens to point today
```

## Tooling & Enforcement

- `tenant-registry.yaml` (or equivalent config service) is the single source of truth for each
  tenant's tier and isolation model — Terraform and the provisioning service both read from it,
  so the decision isn't made twice and drift-checked separately.
- `FORCE ROW LEVEL SECURITY` and `NOT NULL tenant_id` are enforced by a required database migration
  lint check before a new tenant-owned table can be merged.
- `TenantContextFilter` is registered as infrastructure in the shared Spring Boot starter used by
  all Standard Stack services, not copy-pasted per service — a service can't "forget" to include it.
- Integration tests (`@SpringBootTest` + Testcontainers, per the backend-testing convention) must
  include at least one cross-tenant isolation test per tenant-owned table: seed two tenants' rows,
  assert tenant A's context never sees tenant B's rows, and assert a request with no tenant context
  is rejected rather than returned empty.
- The application's Postgres role must never have `BYPASSRLS`; grant it only to the migration role.
- Region parameters for tenant databases follow the same Terraform module pattern documented in
  [Data-Plane / Control-Plane Separation](../crosscutting/data-control-plane-separation.md).
