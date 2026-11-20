# Deep-dive details — `qa-java:api-tests-grpc`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## The contract + two layers

### 1. Proto — `src/main/proto/user.proto`

The `.proto` is the contract. Codegen produces the messages **and** the stub; tests assert on the **typed
message**, never on bytes.

```protobuf
syntax = "proto3";
package user.v1;
option java_package = "com.example.user.v1";
option java_multiple_files = true;

service UserService {
  rpc GetUser     (GetUserRequest)    returns (User);              // unary (read)
  rpc CreateUser  (CreateUserRequest) returns (User);              // unary (write)
  rpc ListUsers   (ListUsersRequest)  returns (stream User);       // server-streaming
  rpc ImportUsers (stream CreateUserRequest) returns (ImportSummary); // client-streaming
}

message GetUserRequest    { string id = 1; }
message CreateUserRequest { string email = 1; string first_name = 2; string last_name = 3; }
message User              { string id = 1; string email = 2; string first_name = 3; string last_name = 4; }
message ListUsersRequest  { int32 page_size = 1; }
message ImportSummary     { int32 imported = 1; }
```

### 2. Action — `src/main/java/action/GrpcCallResult.java` + `UserGrpcAction.java`

`GrpcCallResult<T>` is the **uniform outcome** for *any* unary call — it holds the message on `OK` or the
`Status` + trailers on a failure. The action wraps each RPC so the test never has to `try/catch`.

```java
package action;

import io.grpc.Metadata;
import io.grpc.Status;

/** Uniform outcome of a unary gRPC call: the message on OK, or the status (+ trailers) on a non-OK result. */
public final class GrpcCallResult<T> {
    private final T value;
    private final Status status;
    private final Metadata trailers;

    private GrpcCallResult(T value, Status status, Metadata trailers) {
        this.value = value; this.status = status; this.trailers = trailers;
    }

    public static <T> GrpcCallResult<T> ok(T value)               { return new GrpcCallResult<>(value, Status.OK, null); }
    public static <T> GrpcCallResult<T> error(Status s, Metadata t) { return new GrpcCallResult<>(null, s, t); }

    public boolean isOk()           { return status.getCode() == Status.Code.OK; }
    public T value()                { return value; }            // null on a non-OK result
    public Status.Code code()       { return status.getCode(); } // the gRPC status code — the gate
    public Status status()          { return status; }
    public Metadata trailers()      { return trailers; }         // trailing metadata / rich-error details
}
```

```java
package action;

import io.grpc.Channel;
import io.grpc.Metadata;
import io.grpc.StatusRuntimeException;
import io.grpc.stub.MetadataUtils;
import java.util.function.Supplier;

/** Base for stub wrappers: runs a unary RPC and converts the throw-on-non-OK contract into a GrpcCallResult. */
public abstract class GrpcAction {
    protected static final Metadata.Key<String> AUTHORIZATION =
        Metadata.Key.of("authorization", Metadata.ASCII_STRING_MARSHALLER);

    /** Build a leading-metadata interceptor carrying the bearer — attach to the stub when authenticated. */
    protected static io.grpc.ClientInterceptor bearer(String token) {
        Metadata md = new Metadata();
        md.put(AUTHORIZATION, "Bearer " + token);
        return MetadataUtils.newAttachHeadersInterceptor(md);
    }

    /** Invoke a unary RPC; never let StatusRuntimeException escape — return it as a GrpcCallResult. */
    protected <T> GrpcCallResult<T> call(Supplier<T> rpc) {
        try {
            return GrpcCallResult.ok(rpc.get());
        } catch (StatusRuntimeException e) {
            return GrpcCallResult.error(e.getStatus(), e.getTrailers());
        }
    }
}
```

```java
package action;

import com.example.user.v1.*;
import io.grpc.Channel;
import io.grpc.ClientInterceptors;
import config.Env;

public class UserGrpcAction extends GrpcAction {
    private final UserServiceGrpc.UserServiceBlockingStub blocking;
    private final UserServiceGrpc.UserServiceStub async;   // for client-/bidi-streaming

    public static UserGrpcAction authenticated(Channel channel) {
        return new UserGrpcAction(ClientInterceptors.intercept(channel, bearer(Env.required("GRPC_TOKEN"))));
    }

    public static UserGrpcAction anonymous(Channel channel) {
        return new UserGrpcAction(channel);
    }

    private UserGrpcAction(Channel channel) {
        this.blocking = UserServiceGrpc.newBlockingStub(channel);
        this.async    = UserServiceGrpc.newStub(channel);
    }


    public GrpcCallResult<User> getUser(String id) {
        return call(() -> blocking.getUser(GetUserRequest.newBuilder().setId(id).build()));
    }

    public GrpcCallResult<User> createUser(String email, String first, String last) {
        return call(() -> blocking.createUser(CreateUserRequest.newBuilder()
            .setEmail(email).setFirstName(first).setLastName(last).build()));
    }

    // Server-streaming: the blocking stub returns an Iterator — drained by the test (see streaming section).
    public java.util.Iterator<User> listUsers(int pageSize) {
        return blocking.listUsers(ListUsersRequest.newBuilder().setPageSize(pageSize).build());
    }

    UserServiceGrpc.UserServiceStub async() { return async; }   // exposed for the streaming tests
}
```

### 3. Test — `src/test/java/user/UserGrpcTest.java`

Assert `isOk()` (or the failure `code()`) **first** — that's the gate — then the typed message fields. The
channel points at the service stood up by Testcontainers.

```java
package user;

import action.GrpcCallResult;
import action.UserGrpcAction;
import base.BaseGrpcTest;            // owns the ManagedChannel lifecycle (see Testcontainers section)
import com.example.user.v1.User;
import io.grpc.Status;
import org.testng.annotations.Test;

import static org.assertj.core.api.Assertions.assertThat;

public class UserGrpcTest extends BaseGrpcTest {

    @Test
    public void getUserWhenExistsReturnsUserWithOkStatus() {
        UserGrpcAction action = UserGrpcAction.authenticated(channel);

        GrpcCallResult<User> result = action.getUser("1");

        assertThat(result.isOk()).isTrue();                       // THE gate: the gRPC status, not an HTTP code
        assertThat(result.value().getEmail()).isEqualTo("george.bluth@example.com");
    }

    @Test
    public void getUserWhenUnknownIdReturnsNotFound() {
        UserGrpcAction action = UserGrpcAction.authenticated(channel);

        GrpcCallResult<User> result = action.getUser("999999");

        assertThat(result.isOk()).isFalse();
        assertThat(result.code()).isEqualTo(Status.Code.NOT_FOUND);   // the outcome lives in the status code
        assertThat(result.value()).isNull();                          // no message on a non-OK result
    }

    @Test
    public void createUserWhenEmailBlankReturnsInvalidArgument() {
        UserGrpcAction action = UserGrpcAction.authenticated(channel);

        GrpcCallResult<User> result = action.createUser("", "A", "B");

        assertThat(result.code()).isEqualTo(Status.Code.INVALID_ARGUMENT);
    }

    @Test
    public void getUserWhenNoBearerReturnsUnauthenticated() {
        UserGrpcAction action = UserGrpcAction.anonymous(channel);

        GrpcCallResult<User> result = action.getUser("1");

        assertThat(result.code()).isEqualTo(Status.Code.UNAUTHENTICATED);
    }
}
```

## Client- and bidi-streaming — async stub + a bounded latch

The blocking stub can't drive client- or bidi-streaming (the client itself produces a stream). Use the **async
stub** with a `StreamObserver`, and wait on a **`CountDownLatch` with a bounded `await(timeout)`** — the
sanctioned no-sleep wait — never an unbounded `latch.await()`.

```java
import com.example.user.v1.*;
import io.grpc.stub.StreamObserver;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

@Test
public void importUsersAggregatesAllSentRequests() throws InterruptedException {
    UserGrpcAction action = UserGrpcAction.authenticated(channel);

    CountDownLatch done = new CountDownLatch(1);
    AtomicReference<ImportSummary> summary = new AtomicReference<>();
    AtomicReference<Throwable> failure = new AtomicReference<>();

    StreamObserver<ImportSummary> responseObserver = new StreamObserver<>() {
        @Override public void onNext(ImportSummary s) { summary.set(s); }
        @Override public void onError(Throwable t)    { failure.set(t); done.countDown(); }
        @Override public void onCompleted()           { done.countDown(); }
    };

    StreamObserver<CreateUserRequest> requestObserver = action.async().importUsers(responseObserver);
    requestObserver.onNext(CreateUserRequest.newBuilder().setEmail("a@example.com").build());
    requestObserver.onNext(CreateUserRequest.newBuilder().setEmail("b@example.com").build());
    requestObserver.onCompleted();

    assertThat(done.await(5, TimeUnit.SECONDS)).as("server completed within deadline").isTrue();  // bounded wait
    assertThat(failure.get()).isNull();
    assertThat(summary.get().getImported()).isEqualTo(2);
}
```

> Bidi-streaming follows the same shape — interleave `requestObserver.onNext(...)` with messages collected in
> `onNext`, all gated by a bounded latch. For richer bidi-stream-lifecycle assertions (ordering, mid-stream close
> codes), cross-link `qa-java:realtime-stream-testing` — gRPC streaming and WebSocket/SSE share the
> drain-then-assert-on-a-bounded-condition discipline.
