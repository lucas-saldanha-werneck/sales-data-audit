# sales-data-audit

A small Python script that reads a retail sell-out CSV and lists the data problems in it, so you can fix them before any analysis.

Independent demo, not affiliated with Tata Consultancy Services. I wrote it after applying for a Data Scientist role, because the job post asks for work on mapping and validating data quality. It uses no company data and no company branding.

## What it checks

Input columns: `date, store, sku, product, units, price`.

- empty values in any column
- dates that are not `YYYY-MM-DD`, and numbers that are not numbers
- two rows with the same date, store and SKU
- zero or negative units or price
- prices far from the usual price of the same SKU (median and MAD, so one typo does not hide itself)
- stretches where a store sends no data
- one SKU with several spellings, and different SKUs with almost the same name

The report is Markdown, or JSON with `--json`. It also prints a quality score. The score is a plain rule (100 minus 10 per high finding, 3 per medium, 1 per low). It is a quick signal, not a statistical measure.

## Run it

Python 3.10 or newer. No dependencies.

```
pip install -e .
sales-data-audit --make-sample sample.csv   # invented data with planted problems
sales-data-audit sample.csv
```

The exit code is 1 when there is at least one high finding, so it can gate a pipeline.

Tests (offline):

```
pip install pytest
pytest -q
```

## What was tested

- 8 automated tests, all offline, run in GitHub Actions on every push.
- On the invented sample (1,053 rows, fixed seed), the audit finds every planted problem: 3 duplicate keys, 2 negative units, 2 price typos (a misplaced decimal point), 2 empty product names, 1 bad date, and a 5-day gap in store S02.
- A clean 3-row file gives no high findings.
- A file with missing columns stops with a clear message.
- The sample generator gives identical bytes for the same seed.

## What was not tested

- Real sell-out data. Everything above ran on data I made up, so the thresholds (price outlier at 5 robust deviations, name similarity at 0.8) are guesses.
- Large files. The name comparison checks every pair of SKUs, so it slows down with many thousands of SKUs. I did not measure it.
- Other CSV dialects (semicolon separators, other encodings). Only comma-separated, UTF-8 was tried.
- Promotion prices. A real promo drop can look like a price outlier. The tool does not know about promo calendars.
- The near-duplicate name check flags `Cola Soda 2L` and `Cola Soda Zero 2L` in the sample. They are two different products. The check only points at candidates; a person has to decide.
