# DynamoDB — client setup per stack

Read the section for the project's stack only. Each shows one shared client per process; credentials come from the IAM role.

## .NET 10 (AWS SDK for .NET v4)

```csharp
builder.Services.AddAWSService<IAmazonDynamoDB>();
builder.Services.AddSingleton<IDynamoDBContext>(sp =>
    new DynamoDBContextBuilder()
        .WithDynamoDBClient(() => sp.GetRequiredService<IAmazonDynamoDB>())
        .ConfigureContext(c =>
        {
            c.ConsistentRead = false;
            c.TableNamePrefix = builder.Configuration["Dynamo:TablePrefix"];
            c.DisableFetchingTableMetadata = true;
        })
        .Build());
```

- v4 builds the context through `DynamoDBContextBuilder`; the public constructors are obsoleted.
- `DisableFetchingTableMetadata` skips the per-type `DescribeTable` call. Declare keys via attributes, and the app needs no `dynamodb:DescribeTable` grant at runtime.
- Use the high-level Object Persistence (`IDynamoDBContext`) for typed CRUD; drop to `IAmazonDynamoDB` for `TransactWriteItems`, conditional updates and batch operations.

## Java 21

```java
DynamoDbClient ddb = DynamoDbClient.builder().region(Region.EU_WEST_1).build();
DynamoDbEnhancedClient enhanced = DynamoDbEnhancedClient.builder().dynamoDbClient(ddb).build();
DynamoDbTable<Order> table = enhanced.table("orders", TableSchema.fromBean(Order.class));
```

`TableSchema.fromBean` discovers `@DynamoDbBean` / `@DynamoDbPartitionKey` annotations.

## Node 24 + TypeScript (AWS SDK v3)

```typescript
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient } from '@aws-sdk/lib-dynamodb';

const client = new DynamoDBClient({});
export const ddb = DynamoDBDocumentClient.from(client, {
  marshallOptions: { removeUndefinedValues: true, convertClassInstanceToMap: true },
});
```

The default credential chain resolves the IAM role. The **DocumentClient** marshals JS objects to and from DynamoDB's `AttributeValue` wire format; the raw `DynamoDBClient` is rarely needed.
