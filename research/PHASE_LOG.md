# Research Phase Log

A running chronological log of research phases, major milestones, issues encountered, and gate transition statuses.

---

## Log History

### [2026-11-12] — Phase 01: Data Inspection
- **Status:** COMPLETED
- **Gate Status:** PASS
- **Tasks Executed:**
  - Audited raw data folder structure without writing ML code or mutating data.
  - Inspected `Indian-Final-Data-3month.xlsx`, `JSE_data.csv`, `US_data.csv`.
  - Extracted row counts, column schemas, bounds, missing counts, and categorical distributions.
  - Established research documentation architecture (`MASTER_RESEARCH_PLAN.md`, `RESEARCH_DECISIONS.md`, `PHASE_LOG.md`, `phase_01_data_inspection.md`).
- **Key Findings:**
  - India: 50 tickers, 10 sectors, 39,383 rows (2022-03-02 to 2025-05-30). Contains OHLCV + Cap Size.
  - USA: 50 tickers, 10 sectors, 40,567 rows (2022-03-01 to 2025-05-30). Close only.
  - JSE: 50 tickers, 10 sectors, 39,893 rows (2022-03-01 to 2025-05-30). Close only.
  - 0 missing values across all raw files.
- **Next Phase:** Phase 02: Data Audit & Health Check.

---

### [2026-11-12] — Phase 02: Data Audit & Health Check
- **Status:** COMPLETED & VERIFIED
- **Gate Status:** PASS (Anomalies fully verified and approved)
- **Tasks Executed:**
  - Executed deterministic audit script (`src/data/run_audit.py`).
  - Cataloged duplicates (0), chronology violations (0), and price validity.
  - Conducted specialized forensic verification of anomalies (`src/data/verify_anomalies.py`, `src/data/build_complete_resolution_report.py`).
  - Cataloged exact 948 JSE unit-switch observations across 69 trough episodes in 17 tickers.
  - Verified official regulatory terms for 6 Indian corporate actions (Tata Steel, IRB, Dr. Reddy, AU Bank, Blue Star, Reliance).
  - Verified root causes for shortened series (`NSTG` bankruptcy/delisting, `ASC.JO` debt restructuring listing, `BHARTIHEXA.BSE` IPO, `GMRP%26UI.BSE` demerger).
  - Saved machine-readable records: `research/results/phase_02/data_audit_results.json` and `research/results/phase_02/anomaly_resolution_report.json`.
- **Next Phase:** Phase 03: Temporal Splits and Leakage Audit.

---

### [2026-11-12] — Phase 03: Temporal Splits and Leakage Audit
- **Status:** COMPLETED & APPROVED
- **Gate Status:** PASS
- **Tasks Executed:**
  - Executed deterministic data cleaning pipeline (`src/data/build_splits_and_leakage_audit.py`).
  - Applied validated factor-of-100 multiplication to 948 JSE unit-error records.
  - Applied verified backward split/bonus factors to 6 Indian equities.
  - Decoded `GMRP%26UI.BSE` to `GMRP_UI.BSE`.
  - Harmonized global sector naming taxonomy (`Healthcare`, `Technology`) and standardized country labels.
  - Saved processed datasets strictly in `data/processed/` (`us_equities_clean.csv`, `jse_equities_clean.csv`, `india_equities_clean.csv`, `global_equities_common.csv`).
  - Verified SHA-256 raw file checksums to ensure zero raw mutation.
  - Formalized universe partitioning: **Predefined Core Full-History Universe (146 tickers)** vs. **Secondary Universe (4 tickers: `NSTG`, `ASC.JO`, `BHARTIHEXA.BSE`, `BIK.JO`)**. Verified that all 146 core tickers satisfy full history across train, val, and test periods without exception.
  - Formally locked forecast horizons: **Primary $H=5$ trading days (one trading week)** and Secondary $H=1$ trading day, updating earlier 7-day calendar specifications.
  - Established canonical temporal boundaries:
    - Train: `2022-03-01` to `2024-03-29`
    - Purge Gap 1: `2024-04-01` to `2024-04-08` (5 trading days buffer)
    - Validation: `2024-04-09` to `2024-10-31`
    - Purge Gap 2: `2024-11-01` to `2024-11-08` (5 trading days buffer)
    - Test: `2024-11-11` to `2025-05-30` (Single-use out-of-sample)
  - Locked context windows ($W=20$ primary, $W=60$ secondary).
  - Executed 6-point automated leakage verification test suite (all 6 tests passed).
  - Audited candidate SLM pretraining cutoffs: documented that the test period occurs after reported cutoffs, reducing direct memorization risk while noting that complete pretraining non-contamination cannot be independently guaranteed.
- **Next Phase:** Phase 04: Statistical Baselines and Evaluation Framework.

---

### [2026-11-12] — Phase 04: Statistical Baselines and Evaluation Framework
- **Status:** COMPLETED
- **Gate Status:** PASS
- **Tasks Executed:**
  - Formally implemented the unified multi-metric evaluator (`src/evaluation/evaluator.py`) with support for MAE, RMSE, NRMSE, Relative RMSE, MASE, Directional Accuracy, Bias, and transparent invalid prediction tracking.
  - Built and passed synthetic unit test suite (`src/evaluation/test_evaluator.py`) verifying perfect predictions, relative persistence identity, invalid prediction replacement, and price reconstruction roundtrips.
  - Formally locked the mathematical target formulations: Primary $H=5$ trading days log return, Secondary $H=1$ trading day log return, and price forecast reconstruction.
  - Implemented the 4 strictly permitted naive and statistical reference baselines:
    1. **Persistence (Random Walk)** ($\hat{r} = 0$, Directional Accuracy formally reported as `N/A — zero-return forecast has no directional prediction`)
    2. **Historical Mean** ($W=20$ context mean return $\times H$)
    3. **Moving Average (MA-5)** (last 5 daily returns mean $\times H$)
    4. **Drift** (linear slope over $W=20$ context $\times H$)
  - Verified that Historical Mean and Drift produce identical point forecasts due to a telescoping sum mathematical identity under discrete log returns.
  - Verified that the MASE denominator is computed strictly from training in-sample naive persistence error, eliminating lookahead leakage.
  - Excluded all ML, DL, and TSFM models per strict protocol.
  - Evaluated baselines across the Predefined Core Full-History Universe (146 stocks) on Train (72,844 samples), Validation (20,781 samples), and locked Test splits (19,130 samples for H=5).
  - Generated machine-readable artifacts: `baseline_config.json`, `baseline_metrics.json`, and `baseline_sample_predictions.csv`.
- **Key Findings:**
  - **Validation Champion:** Persistence (Random Walk) decisively outperformed all other statistical baselines on point error on Validation $H=5$ ($\text{RMSE} = 0.093042$, $\text{MAE} = 0.037751$, $\text{MASE} = 0.9852$).
  - **Momentum Penalty:** Historical Mean and Drift incurred a 13.1% error penalty ($\text{RelRMSE} = 1.1310$); Moving Average incurred a 44.0% error penalty ($\text{RelRMSE} = 1.4395$).
  - **Directional Accuracy Anchor:** Momentum rules yielded $47.7\%–48.2\%$ directional accuracy (no baseline beat a 50% coin flip).
  - Benchmark targets established for Phase 05 SLM zero-shot evaluation: $\text{RMSE} < 0.093042$ and $\text{DirAcc} > 50.0\%$.
- **Files Created / Updated:**
  - `src/evaluation/evaluator.py`
  - `src/evaluation/test_evaluator.py`
  - `src/benchmark/run_baselines.py`
  - `research/results/phase_04/baseline_config.json`
  - `research/results/phase_04/baseline_metrics.json`
  - `research/results/phase_04/baseline_sample_predictions.csv`
  - `research/phases/phase_04_baselines.md`
  - `research/RESEARCH_DECISIONS.md` (DEC-P04-001)
  - `research/PHASE_LOG.md`
- **Next Phase:** Phase 05: Zero-Shot SLM Benchmark and Backbone Selection (Pending user confirmation).
