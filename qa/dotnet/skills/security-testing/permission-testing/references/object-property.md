# Object property level (API3) — `qa-dotnet:permission-testing`

```csharp
// Tests/Security/AccessControl/InvoicePropertyTests.cs
using System.Net;
using ApiTests.Clients;
using ApiTests.Models.Billing.InvoiceModels;
using NUnit.Framework;
using RestSharp;

namespace Tests.Security.AccessControl;

[TestFixture]
public class InvoicePropertyTests // API3:2023 — object property level authorization
{
    // Mass-assignment: a client must NOT be able to set a privileged field via the normal write path.
    [Test]
    public async Task Should_IgnoreOwnerId_When_UserAttemptsMassAssignment()
    {
        InvoiceClient client = new InvoiceClient(await Actor.Alice.Token());

        // The attacker-controlled privileged field is carried as a raw extra property.
        RestResponse created = client.CreateRaw(new InvoiceCreateWithOwner(
            Amount: 50, Currency: "EUR", OwnerId: Actor.Bob.Name));
        Assert.That(created.StatusCode, Is.EqualTo(HttpStatusCode.Created));

        // The server must have ignored OwnerId — the invoice belongs to Alice, not Bob.
        string id = Deserialize<InvoiceDto>(created).Id;
        InvoiceDto readBack = client.GetById(id, HttpStatusCode.OK);
        Assert.That(readBack.OwnerId, Is.Not.EqualTo(Actor.Bob.Name));
    }

    // Over-read: a sensitive property must not be serialized to a caller who may not see it.
    [Test]
    public async Task Should_NotExposeInternalNotes_When_NonOwnerRoleReads()
    {
        RestResponse response = new InvoiceClient(await Actor.Alice.Token())
            .GetByIdRaw(/* a shared, readable id */ "inv_shared");
        Assert.That(response.Content ?? string.Empty, Does.Not.Contain("\"internalNotes\""));
    }
}
```

`InvoiceCreateWithOwner` is a throwaway record carrying the privileged `OwnerId` the legitimate
`InvoiceInDto` deliberately omits — that is the whole point of mass-assignment: send a field the contract
does not expose and prove the server drops it.
