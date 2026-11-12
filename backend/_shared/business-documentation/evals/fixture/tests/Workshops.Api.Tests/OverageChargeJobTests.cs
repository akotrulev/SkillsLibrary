using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Workshops.Api.Credits;
using Workshops.Api.Data;

namespace Workshops.Api.Tests;

public class OverageChargeJobTests
{
    private SqliteConnection _connection = null!;
    private WorkshopsDbContext _db = null!;

    [SetUp]
    public void SetUp()
    {
        _connection = new SqliteConnection("DataSource=:memory:");
        _connection.Open();
        _db = new WorkshopsDbContext(new DbContextOptionsBuilder<WorkshopsDbContext>().UseSqlite(_connection).Options);
        _db.Database.EnsureCreated();
    }

    [TearDown]
    public void TearDown()
    {
        _db.Dispose();
        _connection.Dispose();
    }

    [Test]
    public async Task Should_PostOneChargePerMember_When_MemberHasUnpostedAccruals()
    {
        var memberId = Guid.NewGuid();
        _db.AccruedOverages.AddRange(
            new AccruedOverage { Id = Guid.NewGuid(), MemberId = memberId, BookingId = Guid.NewGuid(), Credits = 1, Amount = 6.00m },
            new AccruedOverage { Id = Guid.NewGuid(), MemberId = memberId, BookingId = Guid.NewGuid(), Credits = 2, Amount = 12.00m });
        await _db.SaveChangesAsync();

        await OverageChargeJob.PostMonthAsync(_db, new DateTimeOffset(2026, 9, 1, 0, 0, 0, TimeSpan.Zero), CancellationToken.None);

        var charge = await _db.LedgerCharges.SingleAsync();
        Assert.That(charge.Amount, Is.EqualTo(18.00m));
    }
}
