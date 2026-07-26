# Deep-dive details — `qa-api-test-graphql-java`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## Three layers

### 1. Operation — `src/main/java/operation/UserOperations.java`

Operations are **parameterized documents**: variable values travel in a separate `variables` map passed in the
request body, **never interpolated into the query string** (interpolation invites injection and defeats
server-side query caching / APQ).

```java
package operation;

public final class UserOperations {
    private UserOperations() {}

    public static final String GET_USER = """
        query GetUser($id: ID!) {
          user(id: $id) {
            id
            email
            firstName
            lastName
          }
        }
        """;

    public static final String CREATE_USER = """
        mutation CreateUser($input: CreateUserInput!) {
          createUser(input: $input) {
            id
            email
            firstName
            lastName
          }
        }
        """;
}
```

### 2. Action — `src/main/java/action/GraphQLAction.java` + `UserGraphQLAction.java`

`execute` POSTs `{ query, variables }` and returns the deserialized **raw `GraphQLResponse<T>`** — it never
throws on a GraphQL error, because the test decides whether errors are expected.

```java
package action;

import io.restassured.builder.RequestSpecBuilder;
import io.restassured.common.mapper.TypeRef;
import io.restassured.specification.RequestSpecification;
import pojo.GraphQLResponse;
import utility.SystemPropertyUtil;

import java.util.HashMap;
import java.util.Map;

import static io.restassured.RestAssured.given;

public abstract class GraphQLAction {
    private static final String ENDPOINT = SystemPropertyUtil.getGraphQLEndpoint();   // e.g. https://api.example.com/graphql
    protected final Map<String, String> headers = new HashMap<>();

    protected <T> GraphQLResponse<T> execute(String query, Map<String, Object> variables, TypeRef<GraphQLResponse<T>> typeRef) {
        return send(Map.of("query", query, "variables", variables == null ? Map.of() : variables), typeRef);
    }

    // Forwards `extensions` too — used by the persisted-query tests.
    protected <T> GraphQLResponse<T> executeRaw(Map<String, Object> payload, TypeRef<GraphQLResponse<T>> typeRef) {
        return send(payload, typeRef);
    }

    private <T> GraphQLResponse<T> send(Map<String, Object> payload, TypeRef<GraphQLResponse<T>> typeRef) {
        RequestSpecification spec = new RequestSpecBuilder()
                .addHeaders(headers)
                .setContentType("application/json")
                .setBody(payload)
                .build();
        // Capture the HTTP status onto the envelope, then return it raw — NO assertion, NO throw on errors[].
        var response = given().spec(spec).when().post(ENDPOINT);
        GraphQLResponse<T> envelope = response.as(typeRef);
        envelope.setStatus(response.getStatusCode());
        return envelope;
    }
}
```

```java
package action;

import io.restassured.common.mapper.TypeRef;
import operation.UserOperations;
import pojo.CreateUserData;
import pojo.CreateUserInput;
import pojo.GetUserData;
import pojo.GraphQLResponse;
import utility.SystemPropertyUtil;

import java.util.Map;

public class UserGraphQLAction extends GraphQLAction {

    public UserGraphQLAction(boolean isAuthenticated) {
        if (isAuthenticated) {
            headers.put("authorization", "Bearer " + SystemPropertyUtil.getGraphQLToken());
        }
    }

    public GraphQLResponse<GetUserData> getUser(String id) {
        return execute(UserOperations.GET_USER, Map.of("id", id), new TypeRef<>() {});
    }

    public GraphQLResponse<CreateUserData> createUser(CreateUserInput input) {
        return execute(UserOperations.CREATE_USER, Map.of("input", input), new TypeRef<>() {});
    }
}
```

### 3. POJO — `src/main/java/pojo/`

Lombok data classes. The `*Data` POJO models the **selection set**; the error envelope is shared. Use
`@JsonProperty` where a JSON name differs from the Java field.

```java
package pojo;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

// The envelope as it arrives: { "data": {...}, "errors": [...] }. `status` is set by the action (not in the JSON).
@Data @NoArgsConstructor @AllArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class GraphQLResponse<T> {
    private int status;            // HTTP — set by the action, almost always 200
    private T data;                // present on success AND on partial success
    private List<GraphQLError> errors;   // present on full OR partial failure
}
```

```java
package pojo;

import lombok.Data;
import java.util.List;

@Data
@com.fasterxml.jackson.annotation.JsonIgnoreProperties(ignoreUnknown = true)
public class GraphQLError {
    private String message;
    private List<Object> path;             // names the failing field, e.g. ["billingProfile"]
    private GraphQLErrorExtensions extensions;
}
```

```java
package pojo;

import lombok.Data;

@Data
@com.fasterxml.jackson.annotation.JsonIgnoreProperties(ignoreUnknown = true)
public class GraphQLErrorExtensions {
    private String code;                   // "NOT_FOUND", "FORBIDDEN", "BAD_USER_INPUT", ...
}
```

```java
package pojo;

import lombok.AllArgsConstructor; import lombok.Builder; import lombok.Data; import lombok.NoArgsConstructor;

@Data @NoArgsConstructor @AllArgsConstructor @Builder
public class UserPojo { private String id; private String email; private String firstName; private String lastName; }

// Per-operation data shapes (the selection set):
@Data @NoArgsConstructor @AllArgsConstructor
class GetUserData { private UserPojo user; }          // `user` nullable — not-found returns null + an errors[] entry

@Data @NoArgsConstructor @AllArgsConstructor
class CreateUserData { private UserPojo createUser; }

@Data @AllArgsConstructor
class CreateUserInput { private String email; private String firstName; private String lastName; }
```

### 4. Test — `src/test/java/user/UserGraphQLTest.java`

Status first (it's 200 — assert it, but it is *not* the gate), then the **envelope** is the gate.

```java
package user;

import action.UserGraphQLAction;
import base.BaseTest;
import org.apache.http.HttpStatus;
import org.testng.annotations.Test;
import pojo.GetUserData;
import pojo.GraphQLResponse;

import static org.assertj.core.api.Assertions.assertThat;

public class UserGraphQLTest extends BaseTest {

    @Test
    public void getUserWhenExistsReturnsUserWithoutErrors() {
        UserGraphQLAction userAction = new UserGraphQLAction(true);

        GraphQLResponse<GetUserData> response = userAction.getUser("1");

        assertThat(response.getStatus()).isEqualTo(HttpStatus.SC_OK);   // 200 even when wrong — assert, not the gate
        assertThat(response.getErrors()).isNull();                      // THE gate for a happy path
        assertThat(response.getData().getUser()).isNotNull();
        assertThat(response.getData().getUser().getEmail()).isEqualTo("george.bluth@example.com");
    }

    @Test
    public void getUserWhenUnknownIdReturnsNotFoundErrorWithHttp200() {
        UserGraphQLAction userAction = new UserGraphQLAction(true);

        GraphQLResponse<GetUserData> response = userAction.getUser("999999");

        assertThat(response.getStatus()).isEqualTo(HttpStatus.SC_OK);   // NOT 404 — GraphQL keeps the 200
        assertThat(response.getErrors()).isNotEmpty();                  // assert on the ENVELOPE
        assertThat(response.getErrors().get(0).getExtensions().getCode()).isEqualTo("NOT_FOUND");
        assertThat(response.getErrors().get(0).getPath()).containsExactly("user");   // error names the failing field
        assertThat(response.getData().getUser()).isNull();             // data present; failing field null
    }

    @Test
    public void getUserWhenNoTokenReturnsUnauthenticated() {
        UserGraphQLAction userAction = new UserGraphQLAction(false);

        GraphQLResponse<GetUserData> response = userAction.getUser("1");

        // Two valid server designs: a 200 with an errors[] code, OR a transport 401. Assert the contract you have.
        if (response.getStatus() == HttpStatus.SC_OK) {
            assertThat(response.getErrors().get(0).getExtensions().getCode()).isEqualTo("UNAUTHENTICATED");
        } else {
            assertThat(response.getStatus()).isEqualTo(HttpStatus.SC_UNAUTHORIZED);
        }
    }
}
```

> The unauthenticated test shows the **one place a GraphQL response legitimately varies its HTTP status** — auth
> middleware may reject at the transport (401) before any resolver runs, or the schema may surface
> `UNAUTHENTICATED` in `errors[]` with a 200. This is the *only* conditional you'll see in these tests; pin it to
> your server's actual contract and delete the branch you don't use. (CLAUDE.md bans conditionals that *drive
> assertions* across cases; this single contract-pinning branch is the documented exception, not a loop.)
