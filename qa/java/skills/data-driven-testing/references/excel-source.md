# Excel source (Apache POI)

Use Excel **only** when non-technical stakeholders own and edit the sheet — it's binary, doesn't diff or
merge in git, and is heavier than CSV. Read `.xlsx` with **Apache POI**, skip the header row, bind cells to
the record. Read cells **by their typed accessor**, and prefer the **cell name/index map** over magic
indexes where you can.

```java
@DataProvider(name = "excelPricingCases")
public static Object[][] excelPricingCases() throws Exception {
    var cases = new ArrayList<TaxCase>();
    try (var in = TaxCaseProviders.class.getResourceAsStream("/data/pricing-cases.xlsx");
         var workbook = WorkbookFactory.create(in)) {
        var sheet = workbook.getSheetAt(0);
        for (int r = 1; r <= sheet.getLastRowNum(); r++) {
            var row = sheet.getRow(r);
            if (row == null) continue;
            var tc = new TaxCase();
            tc.setRegion(row.getCell(0).getStringCellValue());
            tc.setAmountCents((long) row.getCell(1).getNumericCellValue());
            tc.setExpectedTaxCents((long) row.getCell(2).getNumericCellValue());
            cases.add(tc);
        }
    }
    return cases.stream().map(c -> new Object[]{ c }).toArray(Object[][]::new);
}
```

`WorkbookFactory` picks XSSF for `.xlsx`; the loop starts at row 1 to skip the header and tolerates trailing
blank rows.

> **Excel gotchas to encode:** numeric cells come back as `double` (cast deliberately, watch precision on
> money — store cents as integers, never floating dollars); a "number" a user typed may be a *text* cell
> (`getStringCellValue` vs `getNumericCellValue` — use a `DataFormatter` or check `getCellType()` if the
> column is mixed); empty trailing rows return `null`. POI 5.x: use `WorkbookFactory.create` (don't
> hard-code `XSSFWorkbook`) so `.xls`/`.xlsx` both work.
