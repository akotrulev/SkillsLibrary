# Building the matrix from a policy table

For a real API, express the policy once as data and generate the rows — one source of truth that doubles as
documentation of intended access:

```java
// src/test/java/.../security/accesscontrol/PolicyRow.java
package security.accesscontrol;

import io.restassured.response.Response;
import java.util.List;

@FunctionalInterface
interface ProtectedCall { Response invoke(String token, String id) throws Exception; }

/** One PolicyRow per protected operation; a @DataProvider emits one test per (row × denied actor). */
public record PolicyRow(
    String endpoint,                 // for the test name
    ProtectedCall call,
    Actor owner,                     // who may (200)
    List<Denied> others) {           // who may not, and how it's denied

    public record Denied(Actor actor, int expected) {} // 401 | 403 | 404
}
// Adding an endpoint = adding a row. A new endpoint with no row is a visible coverage gap.
```
