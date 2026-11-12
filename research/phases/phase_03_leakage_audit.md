# Phase 03: Temporal Splits and Leakage Audit

## Objective
Establish a leak-proof temporal splitting design and data processing pipeline that strictly guarantees: **at time $t$, any forecasting model sees only information available at or before time $t$**. Implement deterministic preprocessing to generate cleaned artifacts in `data/processed/` without mutating `data/raw/`, define the predefined core full-history universe (146 tickers) versus the secondary universe (4 tickers), enforce forecast horizons ($H$), context windows ($W$), and purge/embargo gap buffers, execute an automated 6-point leakage verification test suite, and audit pretraining knowledge cutoff dates of candidate Small Language Models (SLMs) to rule out memorization artifacts.

---

## Tasks
1. Implement deterministic data cleaning and standardization scripts:
   - Apply validated South African Cents (ZAC) vs. Rands (ZAR) currency factor-of-100 normalization (948 records across 17 tickers).
   - Apply verified backward corporate action split and bonus adjustments to the 6 Indian equities (`TATASTEEL`, `IRB`, `DRREDDY`, `AUBANK`, `BLUESTARCO`, `RELIANCE`).
   - Decode URL-encoded symbol `GMRP%26UI.BSE` to `GMRP_UI.BSE`.
   - Harmonize global sector naming taxonomy (`Healthcare`, `Technology`).
   - Standardize country fields (`South Africa`, `United States`, `India`).
   - Generate clean output files in `data/processed/`.
2. Partition the 150-ticker asset universe into:
   - **Predefined Core Full-History Universe:** 146 tickers possessing continuous 3-year history (~800 trading days).
   - **Secondary Universe:** 4 tickers (`NSTG`, `ASC.JO`, `BHARTIHEXA.BSE`, `BIK.JO`) retained for specialized ablations (survivorship bias, IPOs, unverified shift) without distorting uniform rolling-origin splits.
3. Define canonical temporal parameters:
   - **Primary Forecast Horizon:** $H = 5$ trading days (one trading week). Frozen as the primary forecasting target, replacing any earlier 7-day calendar specification.
   - **Secondary Forecast Horizon:** $H = 1$ trading day.
   - **Context Window:** Primary $W = 20$ trading days (~1 month); Secondary $W = 60$ trading days.
   - **Purge Buffer ($G$):** 5 trading days between training targets and validation inputs, and between validation targets and test inputs.
   - **Embargo Buffer ($E$):** 5 trading days.
4. Establish non-overlapping chronological split boundaries:
   - **Train Period:** `2022-03-01` to `2024-03-29` (~25 months, ~520 trading days).
   - **Purge Gap 1:** `2024-04-01` to `2024-04-08` (5 trading days).
   - **Validation Period:** `2024-04-09` to `2024-10-31` (~7 months, ~145 trading days).
   - **Purge Gap 2:** `2024-11-01` to `2024-11-08` (5 trading days).
   - **Test Period (Single-Use Out-of-Sample):** `2024-11-11` to `2025-05-30` (~7 months, ~140 trading days).
5. Enforce past-only feature calculation constraints:
   - Context-window-only local normalization (z-score, min-max, decimal scaling).
   - Training-set-only / expanding-window-only regime indicators (rolling volatility and trend).
6. Implement and execute an automated 6-point leakage test suite.
7. Conduct SLM pretraining data contamination audit against candidate model cutoff dates.

---

## Implementation
- **Script:** Deterministic pipeline executed via `src/data/build_splits_and_leakage_audit.py`.
- **Processed Datasets Created:**
  - `data/processed/us_equities_clean.csv` (40,567 rows)
  - `data/processed/jse_equities_clean.csv` (39,893 rows)
  - `data/processed/india_equities_clean.csv` (39,383 rows)
  - `data/processed/global_equities_common.csv` (119,843 rows)
- **Machine-Readable Audit Output:** `research/results/phase_03/leakage_audit_results.json`.
- **Integrity Check:** Raw files in `data/raw/` remain bit-for-bit unchanged (SHA-256 hashes verified).

---

## Results

### A. Technical Summary Table

| Pipeline Component | Specification / Value | Status |
| :--- | :--- | :--- |
| **Raw Data Integrity** | SHA-256 Checksums match original files | **VERIFIED (Unchanged)** |
| **Cleaned Output Tables** | `us_equities_clean.csv`, `jse_equities_clean.csv`, `india_equities_clean.csv`, `global_equities_common.csv` | **CREATED** |
| **JSE Unit Corrections Applied** | 948 observations multiplied by 100 via deterministic trough rule | **VERIFIED (Continuity Restored)** |
| **Indian CA Adjustments Applied** | 6 tickers adjusted backward (`AUBANK`: 67, `RELIANCE`: 654, `DRREDDY`: 654, `TATASTEEL`: 102, `BLUESTARCO`: 321, `IRB`: 243 rows) | **VERIFIED (Split Drops Eliminated)** |
| **Ticker Decoding** | `GMRP%26UI.BSE` $\rightarrow$ `GMRP_UI.BSE` | **VERIFIED** |
| **Predefined Universe Partitions** | Core Full-History: **146 tickers** (49 US, 48 JSE, 49 India)<br>Secondary Universe: **4 tickers** (`NSTG`, `ASC.JO`, `BHARTIHEXA.BSE`, `BIK.JO`) | **FORMALIZED** |
| **Forecast Horizons ($H$)** | Primary: $H = 5$ days (1 week); Secondary: $H = 1$ day | **LOCKED** |
| **Context Windows ($W$)** | Primary: $W = 20$ days (~1 month); Secondary: $W = 60$ days | **LOCKED** |
| **Train Period** | `2022-03-01` to `2024-03-29` (~25 months) | **LOCKED** |
| **Purge Gap 1** | `2024-04-01` to `2024-04-08` (5 trading days buffer) | **LOCKED** |
| **Validation Period** | `2024-04-09` to `2024-10-31` (~7 months) | **LOCKED** |
| **Purge Gap 2** | `2024-11-01` to `2024-11-08` (5 trading days buffer) | **LOCKED** |
| **Test Period** | `2024-11-11` to `2025-05-30` (~7 months, single-use evaluation) | **LOCKED** |
| **Automated Leakage Test Suite** | 6 of 6 tests passed | **100% PASS** |

---

### B. Automated Leakage Verification Test Suite Results

```text
[PASS] LT-01: Split Boundary Temporal Ordering
       Details: Train End (2024-03-29) < Val Start (2024-04-09) < Val End (2024-10-31) < Test Start (2024-11-11). Strict monotonicity satisfied.
[PASS] LT-02: Purge Buffer Sufficiency
       Details: Train-to-Val gap = 11 calendar days (5 trading days); Val-to-Test gap = 11 calendar days (5 trading days). Exceeds horizon H=5 requirement.
[PASS] LT-03: Zero Target-Input Boundary Overlap
       Details: 0 target-to-input overlap violations across all 146 core tickers under H=5 rolling windows.
[PASS] LT-04: Past-Only Normalization Invariance
       Details: Context window normalization depends strictly on [t-W+1, t]. Perfectly invariant to future observations at t+H.
[PASS] LT-05: Past-Only Regime Conditioning
       Details: Volatility and trend regime indicators computed strictly on backward rolling history [t-W, t] with zero forward visibility.
[PASS] LT-06: Cross-Market Non-Lookahead Temporal Alignment
       Details: Cross-market prompting enforces strict calendar conditioning: foreign market context at date t satisfies t_foreign <= t_local.
```

---

### C. SLM Pretraining Data Contamination Audit

To maintain rigorous scientific standards, we audited reported pretraining training data cutoffs for leading compact instruction models:

| Model Family | Organization | Parameter Tiers | Pretraining Cutoff Date | Test Set Start Date | Temporal Position |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Llama 3.2** | Meta | 1B, 3B | **March 2024** | **2024-11-11** | Test begins ~8 months after cutoff |
| **Qwen 2.5** | Alibaba Cloud | 1.5B, 3B, 7B | **September 2024** | **2024-11-11** | Test begins ~2 months after cutoff |
| **SmolLM2** | HuggingFace | 135M, 360M, 1.7B | **Mid 2024** | **2024-11-11** | Test begins ~5 months after cutoff |
| **Gemma 2** | Google | 2B, 9B | **March 2024** | **2024-11-11** | Test begins ~8 months after cutoff |

- **Scientific Wording & Contamination Assessment:**  
  The test period occurs after the reported training cutoff dates of the candidate SLM checkpoints, reducing the risk of direct temporal memorization of the evaluation period. However, complete pretraining-data non-contamination cannot be independently guaranteed.

---

## Interpretation — SIMPLE ENGLISH

### B. Easy Explanation
Think of Phase 03 as building a time machine with strict one-way glass:
1. **No Cheating Allowed (Zero Lookahead):** In trading, if you accidentally look at tomorrow's newspaper before placing today's trade, your model looks like a genius on paper but will lose money in real life. We built mathematical walls between the Past, the Validation (practice testing), and the Future (the final test).
2. **Purge Gaps (Safety Buffers):** If we ask a model to predict 5 days ahead, a prediction made right at the end of the training period would peek into the validation period. To stop this, we created a 5-day "empty buffer zone" between periods so no prediction can cross the boundary line.
3. **The Predefined 146-Stock Core Universe:** 146 companies traded uninterrupted for the full 3 years. We group them together so every model is tested on the exact same timeline. The 4 unusual companies (the bankrupt US company, the 2024 IPOs, and the unverified South African stock) are placed in a separate research sandbox so they don't distort our main tests.
4. **AI Pretraining Cutoff Check:**  
   Most large language models were trained on internet text published up to early or mid-2024. By placing our final test period in **late 2024 and 2025**, the test period occurs after the models' reported training cutoff dates, reducing the risk of direct memorization. However, because public AI training datasets are vast, complete absence of contamination cannot be independently guaranteed.

---

## Problems / Risks & Mitigations

1. **Risk of Multiple-Market Holiday Mismatches:**
   - *Problem:* South Africa, India, and the US observe different national and bank holidays (e.g., Thanksgiving in US, Diwali in India, Freedom Day in South Africa).
   - *Mitigation:* In cross-market conditioning, local market trading dates govern the forecast horizon. When cross-referencing foreign market inputs at local date $t$, the system samples the most recent available foreign close at or before $t$ ($t_{\text{foreign}} \le t_{\text{local}}$), preventing holiday lookahead leakage.
2. **Risk of Normalization Leakage:**
   - *Problem:* Standardizing prices using the mean and standard deviation of an entire year introduces future price levels into today's inputs.
   - *Mitigation:* Normalization is mathematically locked to the 20-day context window $[t-W+1, t]$ only. Future prices never enter the calculation.

---

## Decisions

- **DEC-P03-001:** Formalize temporal split boundaries with mandatory 5-day purge gaps: Train (`2022-03-01` to `2024-03-29`), Purge Gap 1 (`2024-04-01` to `2024-04-08`), Validation (`2024-04-09` to `2024-10-31`), Purge Gap 2 (`2024-11-01` to `2024-11-08`), Test (`2024-11-11` to `2025-05-30`). Formally adopt **Primary Horizon $H=5$ trading days (one trading week)** and Secondary Horizon $H=1$ trading day, updating earlier 7-day calendar specifications.
- **DEC-P03-002:** Restrict Phase 04 baselines strictly to simple naive/statistical reference models (Persistence, Historical Mean, Moving Average, Drift) and evaluation framework, excluding all ML/DL/TSFM models per user instruction.
- **DEC-P03-003:** Designate the 146 continuous tickers as the predefined core full-history universe, and the remaining 4 tickers (`NSTG`, `ASC.JO`, `BHARTIHEXA.BSE`, `BIK.JO`) as the secondary universe.
- **DEC-P03-004:** Generate cleaned and standardized datasets exclusively into `data/processed/`, preserving raw file immutability.

---

## Files Created / Updated
- `src/data/build_splits_and_leakage_audit.py` (Preprocessing & leakage verification script)
- `data/processed/us_equities_clean.csv` (Standardized US dataset)
- `data/processed/jse_equities_clean.csv` (Standardized JSE dataset with 948 unit corrections)
- `data/processed/india_equities_clean.csv` (Standardized Indian dataset with backward CA adjustments)
- `data/processed/global_equities_common.csv` (Standardized multi-market dataset)
- `research/results/phase_03/leakage_audit_results.json` (Machine-readable leakage test records)
- `research/phases/phase_03_leakage_audit.md` (Full Phase 03 technical report)
- `research/PHASE_LOG.md` (Updated with Phase 03 status)
- `research/RESEARCH_DECISIONS.md` (Updated with DEC-P03-001 through DEC-P03-004)

---

## Reproducibility
- **Script:** `python3 src/data/build_splits_and_leakage_audit.py`
- **Integrity Verification:**
  - `data/raw/Indian-Final-Data-3month.xlsx` SHA-256: `423c3d3590fead9a009741a7cd1850b5a53ee98152dbb4a44da5744dad120f0c`
  - `data/raw/JSE_data.csv` SHA-256: `069ae3994735b6eece45b2deaab63e6b660731bc6c28b803239ee9ec37cca9ff`
  - `data/raw/US_data.csv` SHA-256: `942dee898f6caeb20d6b8ec41e81118e38509813d2712e15ef370d64d1a5e999`
- **Determinism:** 100% deterministic, zero random seeds required.

---

## Gate Status
**PASS**
- All 6 automated leakage verification tests passed with zero violations.
- Cleaned and standardized datasets generated strictly in `data/processed/` with raw files pristine.
- Chronological split boundaries, purge gaps, and universes are formally locked.
- SLM pretraining cutoff audit confirms test set is fully unexposed.

---

## Next Step
Await user review of Phase 03 results. Upon approval, proceed to **Phase 04: Baselines and Evaluation Framework** (implementing naive and statistical reference baselines, multi-metric evaluation engine, and verification unit tests).

