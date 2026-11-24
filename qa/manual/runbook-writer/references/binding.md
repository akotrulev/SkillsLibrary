# Binding — what the two tables leave open

Step 3 of `runbook-writer`, for three cases: a suite with no group headings, a journey no screen carries, and a case whose expected result is a count, a position or an order across a list. In each the test keeps the suite's expected result unchanged.

## A suite without groups

The layer is read from the technique each case names:

| Technique | Layer |
|---|---|
| Use case | journey |
| Decision table, calculation, state transition, role × action | rule, calculation, state, permission |
| Equivalence classes or boundary values on a field | field validation |
| A boundary on a time threshold, a schedule | temporal |
| CRUD, def-use, chains, concurrency | data, interaction, concurrency |

A case that names no technique takes the layer whose "Asserted on" cell fits its expected result, and the choice is a §14 row for the suite's owner.

## A journey no screen carries

Some use cases have no screen in them: a nightly job emails a reminder for tomorrow's booking, a provider's webhook settles an order. The journey row needs a UI to drive, so such a case is bound by the **data, interaction, concurrency** row, whatever the suite calls it:

- **Arrange** creates the data through the API, in the state the case starts from.
- **Act** is the step that starts the outcome: the user's API call where one starts it, else the **Sim** step that sends the third party's message, else the **Job** step that runs the schedule now. This is the one case in which a Job step is the Act.
- **Assert** is a read-back, the DB rows, and the **Notify** or **Doc** step for each message or document the case names.

The coverage matrix keeps the suite's layer word and names that actor in its Act cell. The test fills no cell of the operation grid unless its Act is a create, read, update or delete of the feature's resource.

A use case with a screen in only part of it (a member books on the web, the job reminds them) stays a journey: the UI drives the part a person does, and the Job and Notify steps follow in the same test.

## A count, a position or an order across a list

A case may assert "first in her list", "3 results" or "sorted newest first". On data other people also use, a record of theirs can arrive between the Act and the Assert, so the test runs on data only the run owns. Take the first of these the environment allows:

1. **An account or container the run creates** through the API or the Admin actor, its name carrying `RUN`. The list then holds the run's records only, and Cleanup removes it.
2. **A fixture §4 marks `exclusive`** in its "What it is" cell: an account or container only this runbook uses. Its required state ("holds no notes") is a precondition and its restore is a Cleanup step.
3. **Neither can be had:** the case is a §13 row naming the exclusive fixture it needs.

The Expect keeps the suite's wording across the whole list: "the first row is *Buy stamps `<RUN>`*", "3 rows". It is never narrowed to the records carrying the marker.
