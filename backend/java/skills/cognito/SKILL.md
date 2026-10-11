---
name: cognito
description: Use when setting up AWS Cognito (user pools) in a Java 21 + Spring Boot 3 service — validating Cognito access-token JWTs with a Spring Security resource server (issuer-uri, no `aud`, `token_use=access`), scope + `cognito:groups` authorities, `@PreAuthorize`, Client Credentials M2M. Triggers: "add Cognito to my Spring Boot API", "why does my Cognito token have no audience". Do NOT use for the React SPA flow (`auth/cognito-react`), Auth0 (the `auth0` sibling), or generic OIDC concepts.
---

# Auth — AWS Cognito in Java 21 / Spring Boot 3

Wires an Amazon Cognito **user pool** into a Spring Boot 3 service using the **Spring Security OAuth2 Resource Server**. Validates RS256 access-token JWTs via the pool's JWKS, authorizes by **resource-server scope** and **`cognito:groups`**, and calls outbound APIs with Client Credentials. The Java sibling of `auth/cognito-blazor`; the Auth0 equivalent is `backend/java/skills/auth0`.

> Generic OIDC/JWT concepts + the Auth0-vs-Cognito comparison: `auth/_shared/oidc-concepts`.

## The Cognito deltas vs Auth0 (Java)

| Concern | Auth0 (`backend/java/skills/auth0`) | **Cognito (here)** |
|---|---|---|
| `issuer-uri` | `https://{domain}/` | **`https://cognito-idp.{region}.amazonaws.com/{userPoolId}`** |
| Audience | `audiences:` enforces `aud` | **no `aud` claim** → don't set `audiences`; add a **custom validator** for `token_use == "access"` + **`client_id`** allow-list |
| Permissions | `permissions` claim → `PERM_` | **`scope` claim** → Spring's default `SCOPE_` authorities |
| Roles | namespaced claim | **`cognito:groups`** → custom `GROUP_` authorities |
| Outbound M2M | `/oauth/token` + `audience` attribute mapper | **`{hostedDomain}/oauth2/token`** + `scope`; **no audience mapper** (simpler); `client_secret_basic` |

## Stack

- **Java 21 + Spring Boot 3.x**, Spring Security 6 (`spring-boot-starter-oauth2-resource-server`)
- Outbound M2M: `OAuth2AuthorizedClientManager` + `WebClient`
- Config via `application.yml` + env vars / Secrets Manager / Vault — never hardcoded

## When to use

- Protecting a Spring Boot REST API with Cognito user-pool access tokens
- `@PreAuthorize("hasAuthority('SCOPE_https://api.yourco.com/orders.read')")` or `hasAuthority('GROUP_Admins')`
- Calling another Cognito-protected API with Client Credentials

## When NOT to use

- React SPA → `auth/cognito-react`
- .NET → `backend/dotnet/skills/cognito`
- Blazor → `auth/cognito-blazor`
- Auth0 → `backend/java/skills/auth0`
- Cognito **identity pools** → out of scope
- Concepts → `auth/_shared/oidc-concepts`

## Inputs needed

1. **Region** + **`userPoolId`** per env
2. **Allowed `client_id`(s)** whose tokens the API accepts
3. **Resource server** identifier + **scopes** enforced
4. **Outbound M2M** targets (scopes + hosted domain + a machine app client with secret)

## Inbound — validating Cognito access tokens

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
          issuer-uri: https://cognito-idp.${COGNITO_REGION}.amazonaws.com/${COGNITO_USER_POOL_ID}
          # NOTE: no `audiences:` — Cognito access tokens carry no `aud`. token_use + client_id validated in code.
cognito:
  allowed-client-ids: ${COGNITO_ALLOWED_CLIENT_IDS}      # comma-separated
```

`issuer-uri` triggers JWKS auto-discovery + issuer/signature/expiry validation.

### Security configuration

```java
@Configuration
@EnableWebSecurity
@EnableMethodSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(reg -> reg
                .requestMatchers("/actuator/health", "/actuator/prometheus").permitAll()
                .anyRequest().authenticated())
            .oauth2ResourceServer(o -> o.jwt(jwt -> jwt.jwtAuthenticationConverter(authConverter())))
            .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .csrf(AbstractHttpConfigurer::disable);
        return http.build();
    }

    // Add token_use=access + client_id allow-list on top of the issuer-uri defaults (which give iss + timestamp).
    @Bean
    public JwtDecoder jwtDecoder(OAuth2ResourceServerProperties props,
                                 @Value("${cognito.allowed-client-ids}") String allowedCsv) {
        String issuer = props.getJwt().getIssuerUri();
        NimbusJwtDecoder decoder = JwtDecoders.fromIssuerLocation(issuer);
        var allowed = Set.of(allowedCsv.split(","));
        OAuth2TokenValidator<Jwt> cognito = new DelegatingOAuth2TokenValidator<>(
            JwtValidators.createDefaultWithIssuer(issuer),
            jwt -> "access".equals(jwt.getClaimAsString("token_use"))
                ? OAuth2TokenValidatorResult.success()
                : OAuth2TokenValidatorResult.failure(new OAuth2Error("invalid_token", "token_use != access", null)),
            jwt -> allowed.contains(jwt.getClaimAsString("client_id"))
                ? OAuth2TokenValidatorResult.success()
                : OAuth2TokenValidatorResult.failure(new OAuth2Error("invalid_token", "client_id not allowed", null)));
        decoder.setJwtValidator(cognito);
        return decoder;
    }

    // SCOPE_ authorities from `scope` (Spring default) + GROUP_ authorities from `cognito:groups`.
    @Bean
    public JwtAuthenticationConverter authConverter() {
        var scopes = new JwtGrantedAuthoritiesConverter();               // emits SCOPE_<scope>
        JwtAuthenticationConverter converter = new JwtAuthenticationConverter();
        converter.setJwtGrantedAuthoritiesConverter(jwt -> {
            var authorities = new ArrayList<GrantedAuthority>(scopes.convert(jwt));
            List<String> groups = jwt.getClaimAsStringList("cognito:groups");
            if (groups != null) groups.forEach(g -> authorities.add(new SimpleGrantedAuthority("GROUP_" + g)));
            return authorities;
        });
        return converter;
    }
}
```

### Endpoint authorization

```java
@RestController
@RequestMapping("/orders")
public class OrderController {

    @GetMapping
    @PreAuthorize("hasAuthority('SCOPE_https://api.yourco.com/orders.read')")
    public List<OrderDto> list() { /* ... */ }

    @PostMapping
    @PreAuthorize("hasAuthority('GROUP_Admins')")
    public OrderDto create(@RequestBody CreateOrder cmd) { /* ... */ }

    @GetMapping("/me")
    public Map<String, Object> me(@AuthenticationPrincipal Jwt jwt) {
        return Map.of(
            "sub",    jwt.getSubject(),
            "groups", Optional.ofNullable(jwt.getClaimAsStringList("cognito:groups")).orElse(List.of()),
            "scope",  jwt.getClaimAsString("scope"));
    }
}
```

Client-credentials tokens have **no user**, so `cognito:groups` is absent — authorize machine callers by `SCOPE_`.

## Outbound — Client Credentials (M2M)

```yaml
spring:
  security:
    oauth2:
      client:
        registration:
          orders-downstream:
            authorization-grant-type: client_credentials
            client-id: ${COGNITO_M2M_CLIENT_ID}
            client-secret: ${COGNITO_M2M_CLIENT_SECRET}
            client-authentication-method: client_secret_basic
            scope:
              - https://api.yourco.com/orders.write        # resource-server scope, NOT "audience"
        provider:
          orders-downstream:
            token-uri: https://yourco.auth.${COGNITO_REGION}.amazoncognito.com/oauth2/token
```

```java
@Configuration
public class M2MConfig {

    @Bean
    public OAuth2AuthorizedClientManager authorizedClientManager(
            ClientRegistrationRepository registrations, OAuth2AuthorizedClientService clients) {
        var provider = OAuth2AuthorizedClientProviderBuilder.builder().clientCredentials().build();
        var manager = new AuthorizedClientServiceOAuth2AuthorizedClientManager(registrations, clients);
        manager.setAuthorizedClientProvider(provider);
        return manager;                                      // no audience mapper needed (Cognito uses scope)
    }

    @Bean
    public WebClient ordersWebClient(OAuth2AuthorizedClientManager mgr) {
        var oauth = new ServletOAuth2AuthorizedClientExchangeFilterFunction(mgr);
        oauth.setDefaultClientRegistrationId("orders-downstream");
        return WebClient.builder().baseUrl("https://api.yourco.com")
            .apply(oauth.oauth2Configuration()).build();
    }
}
```

Simpler than the Auth0 sibling — Cognito uses `scope` on the token request, so no `contextAttributesMapper`. Spring caches and refreshes automatically.

## Rules

- `issuer-uri` = the user-pool URL; **JWKS auto-discovered** — never build the URI by hand.
- **Do not set `audiences`** (no `aud`); enforce **`token_use == "access"`** + a **`client_id` allow-list** via a custom `OAuth2TokenValidator` on the `JwtDecoder`.
- Authorize by **`SCOPE_`** (from `scope`) and **`GROUP_`** (from `cognito:groups`) authorities; `@PreAuthorize` is the single source of truth.
- `SessionCreationPolicy.STATELESS`; CSRF disabled for a pure API; CORS for SPA origins configured separately.
- HTTPS metadata mandatory in non-local envs; HS256 rejected (keep the default).
- M2M via `OAuth2AuthorizedClientManager` against `{hostedDomain}/oauth2/token` with `scope` + `client_secret_basic`; secret in Vault / Secrets Manager only.

## What NOT to do

- No `audiences:` for a Cognito access token — it has no `aud`; validation fails or is meaningless.
- No skipping the `token_use` validator — the only guard against an ID token replayed as a bearer.
- No `audience` on the M2M registration — Cognito authorizes M2M by `scope`.
- No `hasRole(...)` semantics mismatched with your prefix — pick `GROUP_`/`SCOPE_` and stay consistent.
- No manual JWKS URI; no HS256; no `client_secret` in `application.yml`.
- No branching on scope/group strings inside handlers when `@PreAuthorize` expresses it.
- No `permitAll` on production endpoints.

## Generation steps

1. Confirm region + pool id (per env), allowed `client_id`s, resource server + scopes, outbound M2M targets.
2. Add the resource-server starter; set `issuer-uri` (no `audiences`) in `application.yml`.
3. Add `SecurityConfig` with the custom `JwtDecoder` (`token_use` + `client_id` validators) and the `SCOPE_`+`GROUP_` authorities converter; `@EnableMethodSecurity`.
4. Guard handlers with `@PreAuthorize("hasAuthority('SCOPE_…')")` / `hasAuthority('GROUP_…')`.
5. For outbound M2M: add the `client_credentials` registration (`token-uri` = hosted domain, `scope`) + the `OAuth2AuthorizedClientManager`/`WebClient` beans.
6. Smoke: `curl /me` with a fresh access token → confirm `scope`/`groups`; present an ID token → expect 401 (`token_use`).

## Handoffs

- Blazor / React / .NET siblings → `auth/cognito-blazor`, `auth/cognito-react`, `backend/dotnet/skills/cognito`
- Auth0 equivalent → `backend/java/skills/auth0`
- Concepts → `auth/_shared/oidc-concepts`
- Pattern/persistence scaffolding for the rest of the service → `backend/java/skills/{generator,persistence}`
- Storing secrets → `devops/environment-config` + Vault / Secrets Manager
- API tests with auth → `qa/java/skills/api-test-author/writer` + `qa/java/skills/test-login-tokens`
