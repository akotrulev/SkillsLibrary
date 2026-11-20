# Measuring branch coverage of the changed files

```bash
dotnet test --collect:"XPlat Code Coverage" --results-directory TestResults
dotnet tool run reportgenerator -reports:"TestResults/*/coverage.cobertura.xml" \
  -targetdir:TestResults/coverage -reporttypes:"TextSummary;Html" \
  -filefilters:"+*PlaceOrderHandler.cs;+*PricingStrategyResolver.cs"
```

`Branch coverage` in `TestResults/coverage/Summary.txt` is the number; for a method changed in an existing file, that file's page in the HTML report shows its branches. `coverlet.collector` ships in the `dotnet new nunit` template — add it where the test project lacks it. ReportGenerator is the local tool `dotnet-reportgenerator-globaltool`.
