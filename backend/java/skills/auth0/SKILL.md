---
name: be-java-auth0
description: Use when setting up or modifying Auth0 in a Java 21 + Spring Boot 3 service — JWT validation with a Spring Security resource server, method-level RBAC via `@PreAuthorize`, Client Credentials M2M, custom claim mapping. Triggers: "add Auth0 to my Spring Boot API", "validate Auth0 JWTs in Java", "wire @PreAuthorize with permissions". Do NOT use for SPA flows (`auth/auth0-react`/`auth0-blazor`), Cognito (the `cognito` sibling), or concepts (`auth/_shared/auth0-concepts`).
---

# Auth — Auth0 in Java 21 / Spring Boot 3

Wires Auth0 into a Spring Boot 3 service using the **Spring Security OAuth2 Resource Server**. Validates RS256 JWTs via JWKS, enforces RBAC via authorities derived from the `permissions` claim, and calls outbound APIs with Client Credentials. Reads against the concepts in `auth/_shared/auth0-concepts`.

## Stack

- **Java 21 + Spring Boot 3.x**
- **Spring Security 6** with the OAuth2 Resource Server starter (`spring-boot-starter-oauth2-resource-server`)
- For outbound M2M: Spring Security's `OAuth2AuthorizedClientManager` (or a thin handwritten cache around `WebClient`)
- Configuration via `application.yml` + env vars / Vault — never hardcoded

## When to use

- Protecting a Spring Boot REST API with Auth0 JWTs
- Adding method-level `@PreAuthorize("hasAuthority('SCOPE_orders:read')")` or `hasAuthority('PERM_orders:read')`
- Calling another API with Client Credentials
- Mapping Auth0 custom claims into a `JwtAuthenticationToken`

## When NOT to use

- React SPA → `auth/auth0-react`
- .NET → `backend/dotnet/skills/auth0`
- Blazor → `auth/auth0-blazor`
- AWS Cognito instead of Auth0 → `backend/java/skills/cognito`
- Concepts → `auth/_shared/auth0-concepts`

## Inputs needed

1. **Auth0 tenant domain** per env
2. **API identifier** (the JWT `aud`)
3. **Required permissions** per endpoint
4. **Outbound M2M targets** (other APIs + scopes)
5. **Custom claim namespace** for tenant id / org id etc.

## Inbound — validating Auth0 JWTs

### Dependencies (Gradle)

```groovy
implementation 'org.springframework.boot:spring-boot-starter-web'
implementation 'org.springframework.boot:spring-boot-starter-security'
implementation 'org.springframework.boot:spring-boot-starter-oauth2-resource-server'
```

### application.yml

```yaml
spring:
  security:
    oauth2:
      resourceserver:
        jwt:
          issuer-uri: https://${AUTH0_DOMAIN}/                # e.g. https://yourco-dev.eu.auth0.com/
          audiences:
            - ${AUTH0_AUDIENCE}                                # e.g. https://api.yourco.com
```

`issuer-uri` triggers Spring's auto-discovery of JWKS + algorithm validation. `audiences` enforces the `aud` check.

### Security configuration

```java
@Configuration
@EnableWebSecurity
@EnableMethodSecurity                    // enables @PreAuthorize
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(reg -> reg
                .requestMatchers("/actuator/health", "/actuator/prometheus").permitAll()
                .anyRequest().authenticated())
            .oauth2ResourceServer(oauth -> oauth.jwt(jwt -> jwt.jwtAuthenticationConverter(jwtAuthenticationConverter())))
            .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .csrf(AbstractHttpConfigurer::disable);
        return http.build();
    }

    @Bean
    public JwtAuthenticationConverter jwtAuthenticationConverter() {
        JwtAuthenticationConverter converter = new JwtAuthenticationConverter();
        converter.setJwtGrantedAuthoritiesConverter(jwt -> {
            // Auth0's "Add Permissions in the Access Token" → permissions claim (array)
            List<String> permissions = jwt.getClaimAsStringList("permissions");
            if (permissions == null) return List.of();
            return permissions.stream()
                .map(p -> "PERM_" + p)                          // prefix to distinguish from scopes
                .map(SimpleGrantedAuthority::new)
                .map(GrantedAuthority.class::cast)
                .toList();
        });
        return converter;
    }
}
```

The `PERM_` prefix is convention — pick one and stay consistent. Some teams prefer `SCOPE_orders:read` (Spring's default for `scope` claim) — fine, just don't mix.

### Endpoint authorization

```java
@RestController
@RequestMapping("/orders")
public class OrderController {

    @GetMapping
    @PreAuthorize("hasAuthority('PERM_orders:read')")
    public List<OrderDto> list() { /* ... */ }

    @PostMapping
    @PreAuthorize("hasAuthority('PERM_orders:write')")
    public OrderDto create(@RequestBody CreateOrder cmd) { /* ... */ }

    @GetMapping("/me")
    public Map<String, Object> me(@AuthenticationPrincipal Jwt jwt) {
        return Map.of(
            "sub",      jwt.getSubject(),
            "email",    jwt.getClaimAsString("email"),
            "tenantId", jwt.getClaimAsString("https://yourco.com/tenant_id"),
            "perms",    jwt.getClaimAsStringList("permissions")
        );
    }
}
```

Custom claims read via full namespaced URI. The `@PreAuthorize` expression is the single source of truth — never branch on permissions inside the handler when an authority guard expresses it.

## Outbound — Client Credentials (M2M)

### Spring Security's `OAuth2AuthorizedClientManager`

```yaml
spring:
  security:
    oauth2:
      client:
        registration:
          orders-downstream:
            authorization-grant-type: client_credentials
            client-id: ${AUTH0_M2M_CLIENT_ID}
            client-secret: ${AUTH0_M2M_CLIENT_SECRET}
            scope:
              - orders:write
        provider:
          orders-downstream:
            token-uri: https://${AUTH0_DOMAIN}/oauth/token
```

```java
@Configuration
public class M2MConfig {

    @Bean
    public OAuth2AuthorizedClientManager authorizedClientManager(
            ClientRegistrationRepository registrations,
            OAuth2AuthorizedClientService clients) {
        var provider = OAuth2AuthorizedClientProviderBuilder.builder()
            .clientCredentials()
            .build();
        var manager = new AuthorizedClientServiceOAuth2AuthorizedClientManager(registrations, clients);
        manager.setAuthorizedClientProvider(provider);
        // Add the Auth0 audience parameter (Auth0 requires it, standard OAuth2 doesn't)
        manager.setContextAttributesMapper(req -> Map.of("audience", "https://orders.yourco.com"));
        return manager;
    }

    @Bean
    public WebClient ordersWebClient(OAuth2AuthorizedClientManager mgr) {
        var oauth = new ServletOAuth2AuthorizedClientExchangeFilterFunction(mgr);
        oauth.setDefaultClientRegistrationId("orders-downstream");
        return WebClient.builder()
            .baseUrl("https://orders.yourco.com")
            .apply(oauth.oauth2Configuration())
            .build();
    }
}
```

The `contextAttributesMapper` is the Auth0-specific bit — Spring Security's standard OAuth2 client doesn't know about audience, but Auth0's `/oauth/token` requires it. Spring will cache and refresh tokens automatically.

Use the bean:

```java
@Service
public class OrdersDownstream {
    private final WebClient ordersWebClient;

    public Mono<List<OrderDto>> listOrders() {
        return ordersWebClient.get().uri("/orders").retrieve().bodyToFlux(OrderDto.class).collectList();
    }
}
```

## Rules

- One Auth0 API per backend service
- Permissions are the source of truth (`@PreAuthorize("hasAuthority('PERM_<name>')")`); never branch on string equality inside handlers
- `issuer-uri` + `audiences` configured via env / Vault — never hardcoded
- HTTPS metadata is mandatory in non-local environments (Spring's default)
- `SessionCreationPolicy.STATELESS` — every request authenticates from scratch
- CSRF disabled (you're a stateless API); add CORS for SPA origins separately
- Method security enabled (`@EnableMethodSecurity`)
- Custom claims read via full namespaced URI
- Outbound M2M uses Spring's `OAuth2AuthorizedClientManager` with the audience attribute mapper — token caching is built in
- Distinct M2M Application per downstream consumer — never share secrets

## What NOT to do

- No `permitAll` on production endpoints
- No reading the JWT in business code to extract roles — let the `Authentication` carry authorities
- No `@PreAuthorize("hasRole('ADMIN')")` against Auth0 roles directly — roles bundle permissions; the API authorizes permissions
- No manually constructing the JWKS URI — Spring discovers it from `issuer-uri`
- No `client_secret` in `application.yml` or committed configuration — env vars / Vault only
- No `audience` left off the M2M call — Auth0 issues an opaque token your downstream API can't validate
- No long client-credentials token caches managed by hand — `OAuth2AuthorizedClientManager` handles expiry
- No HS256 — Auth0 issues RS256; Spring rejects anything else by default, keep it that way
- No mixing `SCOPE_` and `PERM_` prefixes inside one project — pick one
- No `csrf().enable()` for a pure API; if you have form posts, scope CSRF carefully

## Generation steps

1. Confirm tenant domain (per env), API audience, required permissions, outbound M2M targets.
2. Add the resource server starter to `build.gradle`.
3. Configure `spring.security.oauth2.resourceserver.jwt.issuer-uri` and `audiences` in `application.yml`.
4. Create `SecurityConfig` with `@EnableMethodSecurity` and the permissions-to-authorities converter.
5. Decorate handlers with `@PreAuthorize("hasAuthority('PERM_<name>')")`.
6. For outbound M2M: add `oauth2.client.registration.<name>` config and the `OAuth2AuthorizedClientManager` bean with the audience mapper; create a typed `WebClient`.
7. Smoke flow: `curl` `/me` with a fresh access token, confirm `perms` array; revoke a role, confirm 403.

## Handoffs

- Concepts → `auth/_shared/auth0-concepts`
- React SPA → `auth/auth0-react`
- .NET equivalent → `backend/dotnet/skills/auth0`
- Blazor → `auth/auth0-blazor`
- AWS Cognito equivalent → `backend/java/skills/cognito`
- Pattern/persistence scaffolding for the rest of the service → `backend/java/skills/{generator,persistence}`
- Storing secrets → `devops/environment-config` + Vault
- API tests with auth → `qa/java/skills/api-test-author/writer` + `qa/java/skills/test-login-tokens`
