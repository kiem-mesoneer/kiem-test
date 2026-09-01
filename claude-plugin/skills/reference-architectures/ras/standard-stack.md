---
status: active
---

# Reference Architecture: Standard Stack (Angular SPA + Spring Boot + Postgres)

> **Last updated**: 2026-09-01
> **Status**: Active

## Why

The majority of mesoneer's internal business applications are a browser SPA talking directly to a
single Spring Boot API backed by Postgres — no BFF, no event broker, no per-tenant data isolation
concerns. Without a documented default, every team re-derives its own auth wiring, log format, and
error shape, which makes cross-team support ("why does this endpoint 500 differently than that
one?") and platform tooling (log aggregation, alerting) needlessly hard. This RA is also the
**foundation two other Tier-1 RAs build on**: [Frontend SPA + BFF](frontend-spa-bff.md) adds a
cookie-to-bearer-token exchange layer in front of the auth pattern defined here, and
[Workflow Automation](workflow-automation.md) reuses the same logging/correlation-id and
error-handling baseline across asynchronous steps. Consequently, the patterns below are kept
generic at the backend boundary — resource-server token validation, not "how the browser obtained
the token" — so those two RAs can extend rather than replace them.

## Rules

### Backend authentication & authorization

- The Spring Boot API is an OAuth2 **resource server**: it validates JWT bearer tokens issued by
  the company IdP (Azure AD / Entra ID) and never issues or stores sessions itself.
- Every endpoint requires authentication by default; anonymous access is an explicit, reviewed
  opt-in (e.g. `/actuator/health`), never the default posture of a new controller.
- The resource-server config validates the token (signature, issuer, audience, expiry) and maps
  claims to Spring Security authorities — it does not care whether the bearer token arrived
  straight from the SPA (this RA) or was exchanged from a session cookie by a BFF (see
  [Frontend SPA + BFF](frontend-spa-bff.md)). Don't couple the validation config to
  "token came directly from the browser" assumptions.

**Do this:**
```yaml
# application.yml
spring:
  security:
    oauth2:
      resourceserver:
        jwt:
          issuer-uri: https://login.microsoftonline.com/${TENANT_ID}/v2.0
          audiences: api://mesoneer-standard-stack
```
```java
@Configuration
@EnableWebSecurity
class SecurityConfig {

    @Bean
    SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        return http
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/actuator/health/**").permitAll()
                .anyRequest().authenticated())
            .oauth2ResourceServer(oauth2 -> oauth2.jwt(Customizer.withDefaults()))
            .sessionManagement(sm -> sm.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .csrf(CsrfConfigurer::disable) // stateless bearer-token API, no cookie-based session
            .build();
    }
}
```

**Not this:**
```java
@Configuration
@EnableWebSecurity
class SecurityConfig {

    @Bean
    SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        return http
            .authorizeHttpRequests(auth -> auth.anyRequest().permitAll()) // new endpoints are
            .build();                                                    // open by default —
    }                                                                    // auth bolted on later,
}                                                                         // if at all
```

```typescript
// Angular: attach the bearer token via an HTTP interceptor, not per-call boilerplate
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const token = auth.accessToken();
  return next(token ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } }) : req);
};
```

### Structured logging & correlation IDs

- Logs are structured JSON (Logback `logstash-logback-encoder`), never freeform `%msg` lines —
  log aggregation depends on stable field names.
- Every inbound request is stamped with a correlation ID (from the `X-Correlation-Id` request
  header if present, generated otherwise) and put into the SLF4J MDC so it appears on every log
  line for that request, and echoed back in the response header for client-side correlation.
- The same correlation-id propagation mechanism is what [Workflow Automation](workflow-automation.md)
  threads through its asynchronous steps — don't make the filter HTTP-request-scoped in a way that
  prevents passing the ID along explicitly to a queued job.

**Do this:**
```java
@Component
class CorrelationIdFilter extends OncePerRequestFilter {

    static final String HEADER = "X-Correlation-Id";

    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res,
                                     FilterChain chain) throws IOException, ServletException {
        String correlationId = Optional.ofNullable(req.getHeader(HEADER))
            .orElseGet(() -> UUID.randomUUID().toString());
        MDC.put("correlationId", correlationId);
        res.setHeader(HEADER, correlationId);
        try {
            chain.doFilter(req, res);
        } finally {
            MDC.remove("correlationId"); // never leak MDC across pooled threads
        }
    }
}
```
```xml
<!-- logback-spring.xml -->
<appender name="STDOUT" class="ch.qos.logback.core.ConsoleAppender">
  <encoder class="net.logstash.logback.encoder.LogstashEncoder">
    <includeMdcKeyName>correlationId</includeMdcKeyName>
  </encoder>
</appender>
```

**Not this:**
```java
log.info("Order " + orderId + " failed for user " + userEmail); // unstructured, string-concatenated,
                                                                  // and leaks PII into plain text logs
                                                                  // with no way to correlate across services
```

### Error handling (RFC 9457)

- All error responses use `ProblemDetail` (RFC 9457) via a single `@RestControllerAdvice`
  `GlobalExceptionHandler` — never a hand-rolled JSON error body per controller.
- The `type`/`title`/`status`/`detail` fields are stable and documented; `detail` never contains a
  raw exception message or stack trace (that goes to the structured log, tagged with the same
  correlation ID, not to the client).

**Do this:**
```java
@RestControllerAdvice
class GlobalExceptionHandler {

    @ExceptionHandler(EntityNotFoundException.class)
    ProblemDetail handleNotFound(EntityNotFoundException ex) {
        ProblemDetail problem = ProblemDetail.forStatus(HttpStatus.NOT_FOUND);
        problem.setTitle("Resource not found");
        problem.setType(URI.create("https://mesoneer.io/problems/not-found"));
        problem.setDetail(ex.getMessage()); // safe, user-facing message only
        problem.setProperty("correlationId", MDC.get("correlationId"));
        return problem;
    }
}
```

**Not this:**
```java
@ExceptionHandler(Exception.class)
ResponseEntity<Map<String, Object>> handleAny(Exception ex) {
    return ResponseEntity.status(500).body(Map.of(
        "error", ex.toString(),          // leaks internal class names / stack info to the client
        "stack", ex.getStackTrace()));   // never return a stack trace in an HTTP response
}
```

### Baseline security posture

- TLS is mandatory end-to-end (browser → ingress → pod/app service) — plain HTTP is never a valid
  target for anything beyond a local dev loopback.
- Secrets (DB credentials, IdP client secrets) come from the platform secret store (OpenShift
  `Secret` / Azure App Service Key Vault reference) injected as environment variables — never
  committed to `application.yml`, `.env` files, or Docker images.
- Dependency and container-image scanning runs in CI (Dependabot/Trivy) as a merge gate, not an
  optional report nobody reads.

**Do this:**
```yaml
# application.yml — placeholder resolved from env var backed by the platform secret store
spring:
  datasource:
    username: ${DB_USERNAME}
    password: ${DB_PASSWORD}
```

**Not this:**
```yaml
# application.yml committed to Git
spring:
  datasource:
    username: appuser
    password: Sup3rSecret!   # now in Git history forever, rotates only if someone remembers
```

### Observability baseline

- Every service exposes `/actuator/health/liveness` and `/actuator/health/readiness` (Spring Boot
  Actuator health groups) for the platform's probes — a service that "runs" but can't answer
  readiness is treated as down.
- Only the endpoints actually needed by the platform are exposed (`health`, `info`, `prometheus`)
  — `/actuator/**` is not opened wholesale, since some actuator endpoints leak configuration.
- Structured logs (see above) plus request-scoped correlation IDs are the baseline; metrics
  (Micrometer → Prometheus) are additive, not a substitute for correlatable logs.

**Do this:**
```yaml
management:
  endpoint:
    health:
      probes:
        enabled: true
  endpoints:
    web:
      exposure:
        include: health, info, prometheus
```

**Not this:**
```yaml
management:
  endpoints:
    web:
      exposure:
        include: "*"   # exposes env, beans, heapdump etc. on a production API
```

### Deployment topology

- **Default: OpenShift.** Most standard-stack services run as containers on mesoneer's existing
  OpenShift clusters — it's the platform we already operate, has established CI/CD templates, and
  keeps this workload on the same footprint as everything else we run in containers.
- **Use Azure App Service instead when** the team has no need for OpenShift-specific platform
  features (custom Routes, cluster-scoped policies) and wants a lower-ops-overhead PaaS for a
  single, stateless, single-region service — e.g. a small internal tool with one team maintaining
  it end-to-end. This is a deliberate exception, not a silent drift; write an ADR (see below)
  recording why App Service was chosen over the OpenShift default.
- Regardless of runtime choice, the Postgres data plane is provisioned per the region/residency
  rules in [Data-Plane / Control-Plane Separation](../crosscutting/data-control-plane-separation.md):
  the database is pinned to the tenant's required region; CI/CD state and monitoring config are
  control plane and may run wherever is operationally simplest.

**Do this:**
```text
Decision rule:
  need OpenShift-specific platform features, or already running peer services there? → OpenShift (default)
  single stateless service, one team owns it end-to-end, no cluster features needed? → Azure App Service
  either way: Postgres instance region = tenant's data-residency requirement (see
  crosscutting/data-control-plane-separation.md), independent of where the compute runs
```

**Not this:**
```text
Team picks Azure App Service because "it seemed easier at the time," with no ADR, so the next
team can't tell whether that was a considered exception or accidental drift from the default —
and the Postgres region gets set to match the compute region "for simplicity," ignoring residency
```

## Tooling & Enforcement

- Backend: `spring-boot-starter-oauth2-resource-server`, `spring-boot-starter-actuator`,
  `net.logstash.logback:logstash-logback-encoder`.
- API contract and error-shape conventions: `development-conventions:api-design`,
  `development-conventions:error-handling`, `development-conventions:logging-conventions` (apply
  automatically to backend PRs in this stack).
- CI: dependency/image scanning gate (Dependabot + Trivy) blocks merge on high/critical findings.
- Any deviation from the OpenShift default, or from the auth/logging/error patterns defined here,
  should be recorded as an ADR following the [ADR Template & Lifecycle](../adr/adr-template-lifecycle.md)
  process (`adr/0000-adr-template.md` as the starting file) — this RA does not ship pre-written
  ADRs of its own, but the same MADR-based process applies to decisions made within it.
- Cross-references: [Data-Plane / Control-Plane Separation](../crosscutting/data-control-plane-separation.md)
  for region pinning of the Postgres data plane; [Frontend SPA + BFF](frontend-spa-bff.md) and
  [Workflow Automation](workflow-automation.md) for the two RAs that extend this baseline.
