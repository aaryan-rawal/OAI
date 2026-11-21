# Belgium OBU dataset — initial technical profile

## Inventory received

- Files: **31**
- Extracted size: **8.80 GiB**
- Extensions: .csv: 28, .json: 2, .gif: 1

## What the file names suggest (not yet verified)

- `And` files appear to cover Anderlecht; `Bxl` appears to cover Brussels; `Bel` appears to cover Belgium-wide records.
- Filenames include 5, 15, 30 and 60 minute intervals and date-window labels such as `0101_0103_2019` and `0506_1610_2021`.
- Two street-network JSON files are present: `Anderlecht_streets.json` and `Bruxelles_streets.json`.
- One GIF named `baseline_predictions.gif` is present.

## Data quality caveat

The first inventory pass incorrectly treated the first CSV data row as column headers. This is why the earlier report showed timestamps and numeric values as field names. The updated inventory script now treats CSV files as headerless and reports positional columns plus coarse type hints. Do not infer field meanings from position or filename alone.

## Likely use in OptiFreight AI

Potential uses, subject to schema validation and documentation: historical traffic intensity profiles, time-of-day/day-of-week congestion features, corridor travel-time calibration, and offline traffic-pattern analysis. The dataset is Belgian and historical (2019/2021 labels), so it must not be treated as live traffic or directly used as Indian road/legal data.

## Integration decision

- Keep the large raw dataset on the user workstation; do not bundle ~9.45 GiB in the project ZIP.
- Do not connect this dataset directly to cargo eligibility or route legality.
- Before training, establish the meaning and units of each positional field, road-segment key, coordinate reference system, timezone, aggregation semantics, missing-value codes, and licensing/redistribution terms.
- Join the CSV time-series to the street JSON only after confirming stable segment identifiers and coordinate/reference compatibility.
- Use it initially as an optional offline research/feature source. A Belgium-specific model must not be presented as an India traffic model without appropriate local validation.

## Next local inventory run

Run the updated script against the extracted folder. It will regenerate JSON and CSV reports with positional column indexes rather than treating row 1 as a header.
