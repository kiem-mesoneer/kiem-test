---
status: active
---

# Reference Architecture: Frontend SPA with BFF (Backend-for-Frontend)

> **Last updated**: 2026-09-01
> **Status**: Active

## Why

This RA extends the [Standard Stack RA](./standard-stack.md) (Angular + Spring Boot + Postgres)
for products whose SPA needs to talk to more than one backend, or where we don't want the
browser holding a bearer token at all. It assumes the Standard Stack's baseline is already in
place — a Spring Security resource server that issues and validates JWTs, structured logging
with correlation IDs — and adds a Backend-for-Frontend layer in front of it. The BFF terminates
the browser session as an httpOnly cookie and translates it into the bearer-token calls the
backend already expects, so the token itself never reaches client-side JavaScript. Teams default
to bolting a BFF onto every SPA "for security"; this doc also states when that extra hop isn't
worth it, so the pattern is applied where it earns its keep rather than everywhere by habit.

## Rules

### BFF responsibilities: what it does and doesn't do

- The BFF owns three things: **auth aggregation** (holding the browser session and exchanging it
  for backend credentials), **response shaping** (returning view-model-shaped payloads the SPA
  can render directly, not raw backend DTOs), and **backend orchestration** (fanning out to
  multiple downstream APIs and composing one response).
- The BFF is not a second copy of business logic. Validation rules, authorization decisions on
  domain data, and persistence stay in the backend resource server(s). The BFF composes and
  reshapes; it doesn't decide.
- One BFF per SPA (or per closely related family of SPAs) — it is presentation-tier
  infrastructure, not a shared platform API. Don't let other clients (mobile apps, other teams)
  start depending on it; give them the underlying resource server APIs instead.

**Do this:**
```java
@RestController
@RequestMapping("/bff/dashboard")
class DashboardBffController {

    private final ProjectClient projectClient;
    private final NotificationClient notificationClient;

    @GetMapping("/summary")
    DashboardSummaryView getSummary(@AuthenticationPrincipal BffSession session) {
        var token = session.downstreamAccessToken();
        var projects = projectClient.listActiveProjects(token);
        var notifications = notificationClient.listUnread(token);
        // orchestration + response shaping for exactly what the SPA's dashboard needs
        return DashboardSummaryView.of(projects, notifications);
    }
}
```

**Not this:**
```java
@RestController
@RequestMapping("/bff/dashboard")
class DashboardBffController {

    @GetMapping("/summary")
    DashboardSummaryView getSummary(@AuthenticationPrincipal BffSession session) {
        // Re-implements project ownership rules here instead of asking the backend —
        // now authorization logic exists in two places and can drift out of sync.
        var projects = projectRepository.findAll().stream()
            .filter(p -> p.getOwnerId().equals(session.userId()))
            .toList();
        return DashboardSummaryView.of(projects, List.of());
    }
}
```

### Session/token handling: cookie in the browser, bearer token behind the BFF

- The BFF issues the browser an **httpOnly, `Secure`, `SameSite=Strict` session cookie**. The SPA
  never reads or stores this cookie's value — the browser attaches it automatically.
- On each incoming request, the BFF resolves the session to a downstream **bearer access token**
  (obtained via the standard OAuth2/OIDC code flow the BFF runs on the user's behalf) and attaches
  it when calling the resource server(s) from the Standard Stack RA. The SPA never sees this
  token — it exists only server-side, inside the BFF process/session store.
- Session lifetime and token refresh are the BFF's problem: when the downstream access token
  expires, the BFF refreshes it transparently using the stored refresh token; the SPA just sees
  its calls keep succeeding (or a 401 if the session itself is gone).

**Do this:**
```java
// Spring Session config: cookie is the only thing the browser gets
@Configuration
@EnableSpringHttpSession
class BffSessionConfig {

    @Bean
    CookieSerializer cookieSerializer() {
        var serializer = new DefaultCookieSerializer();
        serializer.setCookieName("bff_session");
        serializer.setUseHttpOnlyCookie(true);
        serializer.setUseSecureCookie(true);
        serializer.setSameSite("Strict");
        return serializer;
    }

    @Bean
    SessionRepository<?> sessionRepository(RedisConnectionFactory factory) {
        // distributed session store — see data-control-plane-separation.md
        // for how this store's region is chosen when sessions hold PII
        return new RedisIndexedSessionRepository(
            new RedisTemplate<>() {{ setConnectionFactory(factory); }});
    }
}
```

```
Sequence (per SPA request):
1. Browser -> BFF: GET /bff/projects, cookie "bff_session=..." attached automatically
2. BFF resolves session -> looks up stored OAuth2 tokens for this user in the session store
3. BFF -> Resource server: GET /api/projects, Authorization: Bearer <access_token>
4. Resource server validates JWT (Standard Stack RA baseline), returns data
5. BFF shapes/aggregates the response -> Browser (still only ever sees the session cookie)
```

**Not this:**
```typescript
// SPA fetches a token and holds it itself — exactly what the BFF pattern exists to avoid
async function login() {
  const { accessToken } = await fetch('/auth/token', { method: 'POST' }).then(r => r.json());
  localStorage.setItem('access_token', accessToken); // XSS-readable, defeats the BFF
}
```

### Backend orchestration and response shaping

- Downstream calls that don't depend on each other's results are issued concurrently, not
  chained sequentially, so the BFF's added hop doesn't also add latency.
- The BFF's response DTOs are named and shaped for the SPA view that consumes them (e.g.
  `DashboardSummaryView`), not simply forwarded/renamed backend entities — this is what makes the
  orchestration worth doing instead of letting the SPA call each backend directly.
- Partial-failure handling is explicit: decide per orchestration endpoint whether a failed
  downstream call should fail the whole response or degrade gracefully (e.g. omit that section).

**Do this:**
```java
@GetMapping("/summary")
DashboardSummaryView getSummary(@AuthenticationPrincipal BffSession session) {
    var token = session.downstreamAccessToken();
    var projects = projectClient.listActiveProjectsAsync(token);
    var notifications = notificationClient.listUnreadAsync(token);
    // fan out concurrently, join once
    return DashboardSummaryView.of(projects.join(), notifications.join());
}
```

**Not this:**
```java
@GetMapping("/summary")
DashboardSummaryView getSummary(@AuthenticationPrincipal BffSession session) {
    var token = session.downstreamAccessToken();
    // sequential calls that don't depend on each other — pays the network cost twice for nothing
    var projects = projectClient.listActiveProjects(token);
    var notifications = notificationClient.listUnread(token);
    return DashboardSummaryView.of(projects, notifications);
}
```

### Deployment topology: co-located vs. behind a shared API gateway

- **Co-locate the BFF with the SPA** (same origin, e.g. served from the same domain/app gateway
  as static assets) when this product has its own BFF and no other consumer needs the same
  cross-cutting auth/rate-limit policy applied centrally. This is the default — it gives the
  simplest CORS story (no cross-origin cookie configuration at all) and the fewest moving parts.
- **Put the BFF behind mesoneer's shared API gateway** when the org needs centralized concerns
  across several BFFs/products at once — a single place to enforce rate limiting, WAF rules, or
  an org-wide auth policy — and the extra hop's added latency is acceptable for the product.
- Decision rule: default to co-located. Move behind the shared gateway only when a second,
  concrete cross-cutting requirement (shared rate-limit budget, centralized WAF, multi-product
  auth policy) is actually driving it — not "the gateway exists so we might as well use it."

**Do this:**
```text
Single product, one SPA, one BFF:
  https://app.mesoneer.io/          -> SPA static assets
  https://app.mesoneer.io/bff/**    -> BFF, same origin, no CORS config needed

Multiple products sharing rate-limit/WAF policy:
  https://gateway.mesoneer.io/app-a/bff/**  -> app-a's BFF
  https://gateway.mesoneer.io/app-b/bff/**  -> app-b's BFF
  (gateway enforces one rate-limit/auth policy across both; each hop's added latency
  was an accepted, explicit trade-off for that centralization)
```

**Not this:**
```text
Routing a single product's BFF through the shared gateway "by default" because it's the
company-standard entry point, adding a hop and an extra CORS/config surface with no
cross-cutting requirement actually depending on it.
```

### When a BFF is NOT worth it

- A BFF adds a network hop, a session store to operate, and a codebase to maintain. It earns
  that cost when the SPA needs auth aggregation, orchestration across multiple downstream APIs,
  or must never hold a bearer token client-side.
- A simple CRUD admin tool that talks to exactly one backend, with no response composition and no
  heightened token-exposure concern (e.g. an internal tool behind existing network/VPN controls),
  is a case for the plain Standard Stack RA setup: SPA calls the resource server directly, backed
  by the standard OAuth2/OIDC flow (e.g. PKCE) issuing it a token. Adding a BFF here is extra
  operational surface for no orchestration or security benefit actually being used.
- Revisit the decision when it changes: the day a single-backend admin tool needs to call a
  second API or gains an untrusted-client concern, that's the trigger to introduce a BFF — not a
  reason to have built one upfront "just in case."

**Do this:**
```text
Internal admin CRUD tool, one backend, trusted network:
  SPA -> (OAuth2/PKCE, token in memory, short-lived) -> single resource server
  No BFF. One less service to deploy, patch, and keep session-store-healthy.
```

**Not this:**
```text
Adding a BFF in front of a single-backend internal admin tool "for consistency with the
other RAs", when nothing in the tool orchestrates multiple APIs or needs the cookie/token
split — pure added latency and operational cost.
```

## Tooling & Enforcement

- Spring Session (backed by Redis or the team's chosen distributed store) for the BFF's session
  layer — see [Data-Plane / Control-Plane Separation](../crosscutting/data-control-plane-separation.md)
  for how to pick the session store's region when sessions carry PII or map to a regulated tenant.
- Standard Stack RA's Spring Security resource server config is unchanged — the BFF is purely an
  additional layer in front of it, not a replacement.
- CORS configuration (or its absence, in the co-located case) is reviewed as part of the BFF's
  deployment topology decision, not left to framework defaults.
- No automated linter enforces "no bearer token in browser storage" today — reviewed at PR time
  against this doc; tracked as a follow-up to add a static check on the SPA bundle.
