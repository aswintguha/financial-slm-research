# Phase 01: Data Inspection

## Objective
Perform an audit and inspection of all raw financial time-series data files (`Indian-Final-Data-3month.xlsx`, `JSE_data.csv`, `US_data.csv`) without modifying the files, altering values, or applying any machine learning or fine-tuning code. Verify file integrity, column schemas, temporal boundaries, missing value prevalence, categorical cardinality, and inter-dataset structural compatibility for a downstream forecasting pipeline.

---

## Tasks
1. Verify presence and file types of the three specified raw datasets in `data/raw/`.
2. Determine dimensions: exact row counts and column counts for each file.
3. Extract header schemas and record all column names.
4. Extract the first 5 rows and last 5 rows of each dataset to verify data alignment.
5. Identify date columns and compute minimum and maximum timestamps per market.
6. Check for missing (null/empty/NaN) values across all columns.
7. Profile key categorical attributes (`Ticker`, `Sector`, `Country`, `Cap Size`) for cardinality and distribution.
8. Assess whether the datasets share a compatible structure for unified time-series experimentation.
9. Preserve strict file immutability: zero modifications to `data/raw/`.

---

## Implementation
- **Tooling:** Python 3 standard library (`zipfile`, `xml.etree.ElementTree`, `csv`, `collections.Counter`, `json`).
- **Safety Constraints:** Executed strictly in read-only mode without external dependencies (no mutation, no Pandas overwrites).
- **Artifacts Generated:** Machine-readable inspection summary: `research/results/phase_01/inspection_summary.json`.

---

## Results

### A. Technical Result Summary

| Metric / Attribute | India (`Indian-Final-Data-3month.xlsx`) | South Africa (`JSE_data.csv`) | United States (`US_data.csv`) |
| :--- | :--- | :--- | :--- |
| **File Format** | Microsoft Excel (`.xlsx`) | Comma-Separated Values (`.csv`) | Comma-Separated Values (`.csv`) |
| **Row Count (excl. header)** | 39,383 rows | 39,893 rows | 40,567 rows |
| **Column Count** | 10 | 6 (includes unnamed index) | 6 (includes unnamed index) |
| **Header Columns** | `Date`, `Sector`, `Ticker`, `Cap Size`, `Country`, `1. open`, `2. high`, `3. low`, `4. close`, `5. volume` | `""`, `Date`, `Ticker`, `Sector`, `Country`, `Close` | `""`, `Date`, `Ticker`, `Sector`, `Country`, `Close` |
| **Date Column** | `Date` | `Date` | `Date` |
| **Start Date** | `2022-03-02` | `2022-03-01` | `2022-03-01` |
| **End Date** | `2025-05-30` | `2025-05-30` | `2025-05-30` |
| **Missing Values** | 0 across all 10 columns | 0 across all 6 columns | 0 across all 6 columns |
| **Unique Tickers** | 50 (BSE listed, `.BSE`) | 50 (JSE listed, `.JO`) | 50 (US listed tickers) |
| **Unique Sectors** | 10 sectors | 10 sectors | 10 sectors |
| **Country Values** | `India` (100%) | `USA` (100% — label anomaly) | `USA` (100%) |
| **Price Channels** | Full OHLCV | Closing price only (`Close`) | Closing price only (`Close`) |

#### Sample Head & Tail Observations

- **Indian Data (`Indian-Final-Data-3month.xlsx`):**
  - Head (Row 1): `['2022-03-02', 'Financials', 'HDFCBANK.BSE', 'LARGE', 'India', '1385', '1397.95', '1355', '1374.55', '854944']`
  - Tail (Row 39383): `['2025-05-30', 'Communication Services', 'MTNL.BSE', 'SMALL', 'India', '48.49', '49.95', '47.1', '48.13', '630292']`
- **JSE Data (`JSE_data.csv`):**
  - Head (Row 1): `['0', '2022-03-01', 'ACL.JO', 'Materials', 'USA', '879.0']`
  - Tail (Row 39893): `['39892', '2025-05-30', 'VOD.JO', 'Communication Services', 'USA', '13773.5048828125']`
- **US Data (`US_data.csv`):**
  - Head (Row 1): `['0', '2022-03-01', 'AAPL', 'Technology', 'USA', '160.38743591308594']`
  - Tail (Row 40567): `['40566', '2025-05-30', 'XOM', 'Energy', 'USA', '102.3000030517578']`

---

## Interpretation — SIMPLE ENGLISH

### B. Easy Explanation
Think of this inspection as opening three boxes of financial data to see what is inside before we try to build anything with them:
1. **Three Global Markets:** We have three sets of stock market data: Indian stocks (like HDFC Bank and Infosys), South African stocks (like Vodacom on the Johannesburg Stock Exchange), and American stocks (like Apple, Amazon, and ExxonMobil).
2. **50 Stocks Per Market:** Each market has exactly 50 companies, spread evenly across 10 major industries (like Technology, Banking, Energy, and Healthcare).
3. **Same Time Period:** All three files cover roughly 3 full years of daily trading, from early March 2022 to the end of May 2025.
4. **No Missing Days/Entries in the Raw Files:** Every column is completely filled with values; there are no empty gaps or blank cells.
5. **A Unified Foundation:** Because all three datasets share dates, company tickers, sectors, and daily closing prices over the exact same 3-year period, they are well suited to be processed together in a single forecasting project.

---

## Problems / Anomalies

1. **JSE Country Tag Artifact:**
   - *Observation:* In `data/raw/JSE_data.csv`, every row lists `'USA'` in the `Country` column, even though all tickers clearly end in `.JO` (Johannesburg Stock Exchange, South Africa).
   - *Diagnosis:* An export script artifact from the original source.
   - *Resolution Plan:* Do NOT edit the raw file. Handle this cleanly during preprocessing code (Phase 02/03) by mapping `.JO` stocks to `'South Africa'` in `data/processed/`.

2. **Column Schema Discrepancy:**
   - *Observation:* The Indian file has 10 columns containing full Open, High, Low, Close, and Volume (`1. open`, `2. high`, `3. low`, `4. close`, `5. volume`) plus `Cap Size`. In contrast, the US and JSE files have only 6 columns with an unnamed export row number and just the final daily price (`Close`).
   - *Diagnosis:* The raw datasets were collected from different API endpoints or providers.
   - *Resolution Plan:* Align the master forecasting pipeline on the common shared fields: `[Date, Ticker, Sector, Country, Close]`. The Indian dataset's additional columns will be retained in a supplementary processed dataset for extended ablations.

3. **File Format Heterogeneity:**
   - *Observation:* Two datasets are `.csv` files; one is an Excel spreadsheet (`.xlsx`).
   - *Resolution Plan:* In Phase 02/03, compile clean, standardized `.csv` and `.parquet` files into `data/processed/` using deterministic automated scripts.

---

## Decisions

- **DEC-P01-001:** Keep `data/raw/` strictly immutable. Zero manual edits.
- **DEC-P01-002:** Adopt a unified core schema `[date, ticker, sector, country, close]` for universal cross-market SLM training and evaluation, while preserving Indian OHLCV in a specialized multi-feature table.
- **DEC-P01-003:** Programmatically correct the JSE country label in `data/processed/` without altering `data/raw/JSE_data.csv`.

---

## Research Significance
Establishing complete clarity on raw dataset structures ensures that:
- Baseline models and SLM fine-tuning experiments evaluate genuinely identical time horizons (~March 2022 – May 2025).
- Zero cross-market data contamination occurs.
- Anomalies (such as the JSE country label) are documented before modeling, eliminating potential bugs when prompting language models with country-level context.

---

## Files Created
- `research/MASTER_RESEARCH_PLAN.md`
- `research/RESEARCH_DECISIONS.md`
- `research/PHASE_LOG.md`
- `research/phases/phase_01_data_inspection.md`
- `research/results/phase_01/inspection_summary.json`

---

## Reproducibility
- **Python Version:** 3.14.3
- **Environment:** Standard library execution (`csv`, `zipfile`, `xml.etree.ElementTree`)
- **Deterministic Check:** Verified exact row and column parity with zero modifications to source storage.

---

## Gate Status
**PASS**
- All three raw files have been thoroughly inspected and profiled.
- No files were modified, moved, deleted, or overwritten.
- All 11 checklist requirements for Phase 1 have been fulfilled and documented in machine-readable and human-readable formats.

---

## Next Step
Await user approval. Upon authorization, proceed to **Phase 02: Data Audit & Health Check** to evaluate calendar consistency, trading day alignments, non-trading day gaps, and time-split boundaries.

