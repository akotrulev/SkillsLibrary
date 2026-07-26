# Deep-dive details — `qa-api-test-grpc-dotnet`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## The contract + two layers

### 1. Proto — `Protos/user.proto`

The `.proto` is the contract. `Grpc.Tools` codegen produces the messages **and** the client; tests assert on the
**typed message**, never on bytes.

```protobuf
syntax = "proto3";
package user.v1;
option csharp_namespace = "Example.User.V1";

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

### 2. Action — `Actions/GrpcCallResult.cs` + `UserGrpcAction.cs`

`GrpcCallResult<T>` is the **uniform outcome** for *any* unary call — it holds the message on `OK` or the
`RpcException` (carrying status + trailers) on a failure. The action wraps each RPC so the test never has to
`try/catch`.

```csharp
using Grpc.Core;

namespace Tests.Actions;

/// <summary>Uniform outcome of a unary gRPC call: the message on OK, or the status (+ trailers) on a non-OK result.</summary>
public sealed record GrpcCallResult<T>(T? Value, RpcException? Exception)
{
    public static GrpcCallResult<T> Ok(T value) => new(value, null);
    public static GrpcCallResult<T> Error(RpcException ex) => new(default, ex);

    public bool IsOk => Exception is null;
    public StatusCode Code => Exception?.StatusCode ?? StatusCode.OK;   // the gRPC status code — the gate
    public Metadata? Trailers => Exception?.Trailers;                   // trailing metadata / rich-error details
}
```

```csharp
using Grpc.Core;

namespace Tests.Actions;

/// <summary>Base for client wrappers: runs a unary RPC and converts the throw-on-non-OK contract into a GrpcCallResult.</summary>
public abstract class GrpcAction
{
    /// <summary>Leading metadata carrying the bearer — attached per call when authenticated.</summary>
    protected static Metadata Bearer(string token) => new() { { "authorization", $"Bearer {token}" } };

    /// <summary>Await a unary RPC; never let RpcException escape — return it as a GrpcCallResult.</summary>
    protected static async Task<GrpcCallResult<T>> CallAsync<T>(Func<Task<T>> rpc)
    {
        try
        {
            return GrpcCallResult<T>.Ok(await rpc());
        }
        catch (RpcException ex)
        {
            return GrpcCallResult<T>.Error(ex);
        }
    }
}
```

```csharp
using Example.User.V1;
using Grpc.Core;
using Grpc.Net.Client;

namespace Tests.Actions;

public sealed class UserGrpcAction : GrpcAction
{
    private readonly UserService.UserServiceClient _client;
    private readonly Metadata _headers;

    public UserGrpcAction(GrpcChannel channel, bool authenticated)
    {
        _client = new UserService.UserServiceClient(channel);
        _headers = authenticated ? Bearer(Env.GrpcToken) : new Metadata();
    }

    public Task<GrpcCallResult<User>> GetUserAsync(string id) =>
        CallAsync(async () => await _client.GetUserAsync(
            new GetUserRequest { Id = id }, headers: _headers));

    public Task<GrpcCallResult<User>> CreateUserAsync(string email, string first, string last) =>
        CallAsync(async () => await _client.CreateUserAsync(
            new CreateUserRequest { Email = email, FirstName = first, LastName = last }, headers: _headers));

    // Server-streaming: hand the call back; the test drains ResponseStream (see streaming section).
    public AsyncServerStreamingCall<User> ListUsers(int pageSize) =>
        _client.ListUsers(new ListUsersRequest { PageSize = pageSize }, headers: _headers);

    public UserService.UserServiceClient Client => _client;   // exposed for the streaming tests
}
```

### 3. Test — `Tests/UserGrpcTests.cs`

Assert `IsOk` (or the failure `Code`) **first** — that's the gate — then the typed message fields. The channel
points at the service stood up by Testcontainers. Tests are `async Task` — **async all the way, no
`.Result`/`.Wait()`**.

```csharp
using Example.User.V1;
using Grpc.Core;
using NUnit.Framework;
using Tests.Actions;

namespace Tests;

[TestFixture]
public class UserGrpcTests : BaseGrpcTest        // owns the GrpcChannel lifecycle (see Testcontainers section)
{
    [Test]
    public async Task GetUser_WhenExists_ReturnsUserWithOkStatus()
    {
        var action = new UserGrpcAction(Channel, authenticated: true);

        GrpcCallResult<User> result = await action.GetUserAsync("1");

        Assert.That(result.IsOk, Is.True);                       // THE gate: the gRPC status, not an HTTP code
        Assert.That(result.Value!.Email, Is.EqualTo("george.bluth@example.com"));
    }

    [Test]
    public async Task GetUser_WhenUnknownId_ReturnsNotFound()
    {
        var action = new UserGrpcAction(Channel, authenticated: true);

        GrpcCallResult<User> result = await action.GetUserAsync("999999");

        Assert.That(result.IsOk, Is.False);
        Assert.That(result.Code, Is.EqualTo(StatusCode.NotFound));   // the outcome lives in the status code
        Assert.That(result.Value, Is.Null);                          // no message on a non-OK result
    }

    [Test]
    public async Task CreateUser_WhenEmailBlank_ReturnsInvalidArgument()
    {
        var action = new UserGrpcAction(Channel, authenticated: true);

        GrpcCallResult<User> result = await action.CreateUserAsync("", "A", "B");

        Assert.That(result.Code, Is.EqualTo(StatusCode.InvalidArgument));
    }

    [Test]
    public async Task GetUser_WhenNoBearer_ReturnsUnauthenticated()
    {
        var action = new UserGrpcAction(Channel, authenticated: false);   // no bearer metadata

        GrpcCallResult<User> result = await action.GetUserAsync("1");

        Assert.That(result.Code, Is.EqualTo(StatusCode.Unauthenticated));
    }
}
```
