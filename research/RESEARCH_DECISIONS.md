# Research Decisions Log

This document records every significant methodological, architectural, and data governance decision made throughout the research project.

---

## Log Format Standard

Each decision entry must document:
- **Decision ID:** `DEC-[PHASE]-[NUMBER]`
- **Date:** YYYY-MM-DD
- **Phase:** Phase in which decision occurred
- **Decision:** What was decided
- **Rationale:** Why it was decided
- **Alternatives Considered & Rejected:** Alternative paths and reasons for rejection
- **Timing:** *A Priori* (before seeing results) vs. *Post-Hoc* (after observing empirical results)
- **Impacted Files / Components:** What code, data, or docs are affected

---

## Decision Records

### DEC-P00-001: Language-Model-Only Study Scope (Exclusion of Time-Series Foundation Models)
- **Date:** 2026-11-12
- **Phase:** Phase 00 (Protocol Scoping)
- **Decision:** The project is strictly defined as a **Language-Model-Only study**. Time-series foundation models (TSFMs) such as Chronos and TimesFM are entirely excluded from all phases of the project. Experiment **E05 (TSFM baselines) is removed from scope**. Experiment IDs are not renumbered (E05 remains as an intentional gap) to preserve strict alignment with the master research plan. The manuscript will explicitly state this scope boundary and cite the absence of specialized TSFMs as an intentional research design constraint and limitation.
- **Rationale:** Focuses compute, evaluation, and research narrative squarely on investigating the generative and numeric capabilities of autoregressive Small Language Models (SLMs) without mixing architectures.
- **Alternatives Considered & Rejected:**
  - *Option B (Include Chronos/TimesFM):* *Rejected by User Scope Decision:* Expands compute burden and dilutes the specific scientific investigation into how general-purpose language tokenizers and transformer architectures reason over numerical financial series.
- **Timing:** *A Priori* (decided by user prior to baseline or model training phases).
- **Impacted Files / Components:** `research/MASTER_RESEARCH_PLAN.md`, Phase 04 baselines, Phase 05 zero-shot benchmarks, Phase 09 statistical significance testing.

---

### DEC-P00-002: SLM-Centric Study Scope (Exclusion of ML and Deep Learning Baselines)
- **Date:** 2026-11-12
- **Phase:** Phase 00 (Protocol Scoping)
- **Decision:** All Machine Learning (XGBoost) and Deep Learning (LSTM, GRU, PatchTST, iTransformer) time-series forecasting baselines, as well as ARIMA, are permanently excluded from the benchmark suite. Experiment **E04 (Deep baselines) is removed from scope**. Experiment **E03 is narrowed strictly to simple naive and statistical reference baselines** (Persistence / Random Walk, Historical Mean, Moving Average). Experiment IDs E04 and E05 remain as intentional gaps to preserve consistent numbering across all research phases. The manuscript will explicitly define this scope boundary and discuss the absence of classical ML/DL comparisons as a deliberate research limitation.
- **Rationale:** The research question is whether Small Language Models possess non-trivial forecasting capability and numerical representation reasoning beyond standard trivial reference rules, without diluting the narrative with traditional deep learning model engineering.
- **Alternatives Considered & Rejected:**
  - *Option B (Include LSTM/GRU/XGBoost):* *Rejected by User Scope Decision:* Requires extensive hyperparameter tuning across 150 assets and shifts focus away from the core Small Language Model evaluation.
- **Timing:** *A Priori* (formalized before baseline implementation).
- **Impacted Files / Components:** `research/MASTER_RESEARCH_PLAN.md`, Phase 04 baselines, Phase 09 statistical tests.

---

### DEC-P01-001: Strict Immutability of Raw Datasets
- **Date:** 2026-11-12
- **Phase:** Phase 01 (Data Inspection)
- **Decision:** All files located in `data/raw/` (`Indian-Final-Data-3month.xlsx`, `JSE_data.csv`, `US_data.csv`) must remain 100% read-only and unedited. All schema unifying actions, index drops, country label adjustments, and transformations must be executed purely via deterministic code into `data/processed/`.
- **Rationale:** Preserves pristine auditability and scientific reproducibility. If raw data is manually touched or overwritten, experiments cannot be audited from their source origin.
- **Alternatives Considered & Rejected:**
  - *Option B (In-place manual cleaning):* Edit `.xlsx` into `.csv` and fix column headers by hand. *Rejected:* Introduces non-reproducible manual errors and breaks experiment provenance.
- **Timing:** *A Priori* (established before cleaning).
- **Impacted Files / Components:** `data/raw/`, `data/processed/`, data loaders in `src/data/`.

---

### DEC-P01-002: Establishing Unified Schema Target for Equity Time Series
- **Date:** 2026-11-12
- **Phase:** Phase 01 (Data Inspection)
- **Decision:** The common pipeline across Indian, US, and JSE equities will standardize on the minimal intersection schema: `[date, ticker, sector, country, close]` for universal multi-asset modeling, while retaining Indian full OHLCV and market cap attributes in secondary processed tables for ablation studies.
- **Rationale:** Both US and JSE datasets only contain `Close` prices and categorical identifiers, while India contains `open`, `high`, `low`, `close`, `volume`, and `Cap Size`. To build a universal multi-market benchmark and cross-market transfer pipeline, a common denominator schema is required.
- **Alternatives Considered & Rejected:**
  - *Option B (Drop India OHLCV completely):* Throw away additional Indian columns. *Rejected:* Indian OHLCV offers valuable granular experiments (e.g. evaluating if volume/volatility features boost SLMs).
  - *Option C (Synthesize fake OHLCV for US and JSE):* *Rejected:* Scientific fabrication; strictly forbidden by protocol.
- **Timing:** *Post-Hoc* observation of raw inspection schemas, decided prior to data preprocessing.
- **Impacted Files / Components:** Data processing pipeline specifications in Phase 02 and Phase 03.

---

### DEC-P01-003: Flagging JSE Country Field Label Anomaly
- **Date:** 2026-11-12
- **Phase:** Phase 01 (Data Inspection)
- **Decision:** Document that the raw `JSE_data.csv` contains `'USA'` in its `Country` column despite having `.JO` tickers (Johannesburg Stock Exchange). In Phase 02/03 data cleaning, this field will be programmatically mapped to `'South Africa'` in `data/processed/` without altering `data/raw/JSE_data.csv`.
- **Rationale:** The raw file has an export labeling artifact where the column was set to `'USA'`. Modifying raw files is prohibited. Documenting this transparently prevents confusion or methodological errors during multi-country conditioning experiments.
- **Alternatives Considered & Rejected:**
  - *Option B (Silently modify JSE_data.csv):* *Rejected:* Violates Rule 7 (Never silently fix anomalies) and Rule 8 (Never modify raw files).
- **Timing:** *Post-Hoc* observation from data inspection.
- **Impacted Files / Components:** `data/raw/JSE_data.csv`, `research/phases/phase_01_data_inspection.md`, `src/data/`.

---

### DEC-P02-001: Treating South African Cents vs. Rands Currency Unit Glitches
- **Date:** 2026-11-12
- **Phase:** Phase 02 (Data Audit)
- **Decision:** In Phase 03 preprocessing, programmatically detect single-day and transient 100x pricing anomalies in JSE data (where daily return drops by ~99% and immediately rebounds by ~9900%) and multiply the affected dates by 100 to restore true ZAC cents denomination.
- **Rationale:** Forensic inspection proved that 139 of the 191 extreme return events in JSE data are exact 100x unit mismatches (Rands vs. Cents), caused by data feed collection artifacts. Leaving them uncorrected would introduce artificial 99% crashes that corrupt time-series forecasting.
- **Alternatives Considered & Rejected:**
  - *Option B (Drop JSE stocks with currency errors):* *Rejected:* Would eliminate over 20 top South African companies (including Standard Bank, Vodacom).
  - *Option C (Leave uncorrected):* *Rejected:* Invalidates any model training or baseline evaluation on South African equities.
- **Timing:** *Post-Hoc* discovery from Phase 02 audit.
- **Impacted Files / Components:** `src/data/`, `data/processed/`, Phase 03 pipeline.

---

### DEC-P02-002: Applying Corporate Action Split Adjustments to Indian Equities
- **Date:** 2026-11-12
- **Phase:** Phase 02 (Data Audit)
- **Decision:** Programmatically compute and apply backward split adjustment factors to Indian raw prices in `data/processed/` for verified stock splits and bonus issues (e.g. Tata Steel 10:1 split, Dr. Reddy 5:1 split, Reliance 1:1 bonus).
- **Rationale:** Raw BSE quotes were unadjusted nominal prices. Stock splits are balance-sheet neutral and do not represent economic losses. Unadjusted splits create false 50% to 90% drops that mislead SLMs and statistical models.
- **Alternatives Considered & Rejected:**
  - *Option B (Leave unadjusted):* *Rejected:* Unadjusted prices severely penalize predictive accuracy and directional metrics.
  - *Option C (Filter out tickers with splits):* *Rejected:* Excludes some of India's largest index heavyweights (Reliance, Tata Steel).
- **Timing:** *Post-Hoc* discovery from Phase 02 audit.
- **Impacted Files / Components:** `src/data/`, `data/processed/`, Phase 03 pipeline.

---

### DEC-P02-003: Harmonization of Sector Taxonomies Across Global Markets
- **Date:** 2026-11-12
- **Phase:** Phase 02 (Data Audit)
- **Decision:** Map all market sector strings to a canonical 10-sector taxonomy in `data/processed/`: `Information Technology` and `Technology` $\rightarrow$ `Technology`; `Health Care` and `Healthcare` $\rightarrow$ `Healthcare`.
- **Rationale:** Ensures unified prompting and categorical conditioning for SLMs across markets.
- **Alternatives Considered & Rejected:**
  - *Option B (Retain raw sector strings):* *Rejected:* Causes SLM prompts to treat US "Healthcare" and JSE "Health Care" as distinct concepts.
- **Timing:** *A Priori* establishing cross-market prompt consistency.
- **Impacted Files / Components:** `src/data/`, `data/processed/`.

---

### DEC-P02-004: Handling Truncated Series (IPO and Delisted Tickers)
- **Date:** 2026-11-12
- **Phase:** Phase 02 (Data Audit)
- **Decision:** Clearly partition the 150-ticker universe into:
  1. *Predefined Core Full-History Universe (146 tickers):* Tickers possessing full 3-year history (~800 days) for the primary multi-market cross-validation and rolling-origin benchmarks.
  2. *Secondary Universe (4 tickers: `NSTG`, `ASC.JO`, `BHARTIHEXA.BSE`, `BIK.JO`):* Evaluated on their valid overlapping windows to prevent survivorship bias, but flagged when constructing strict rolling-origin splits.
- **Rationale:** Eliminating shortened tickers entirely introduces survivorship bias. Forcing them into long rolling windows causes lookahead/padding distortion. Partitioning provides full transparency and methodological rigour.
- **Alternatives Considered & Rejected:**
  - *Option B (Zero-fill or forward-fill missing years):* *Rejected:* Creates artificial flat lines or zeros that confuse LLM reasoning.
- **Timing:** *Post-Hoc* discovery from Phase 02 audit.
- **Impacted Files / Components:** Split generators in Phase 03, benchmark evaluation in Phase 04.

---

### DEC-P03-001: Formalization of Temporal Splits, Purge Buffers, and Primary 5-Day Horizon
- **Date:** 2026-11-12
- **Phase:** Phase 03 (Temporal Splits and Leakage Audit)
- **Decision:** Lock the chronological split design:
  - Train: `2022-03-01` to `2024-03-29`
  - Purge Gap 1: `2024-04-01` to `2024-04-08` (5 trading days buffer)
  - Validation: `2024-04-09` to `2024-10-31`
  - Purge Gap 2: `2024-11-01` to `2024-11-08` (5 trading days buffer)
  - Test: `2024-11-11` to `2025-05-30` (Strictly single-use, out-of-sample)
  - **Forecasting Horizons:** Formally establish **Primary Horizon $H = 5$ trading days (one trading week)** and **Secondary Horizon $H = 1$ trading day**. This replaces any earlier 7-day calendar specification to reflect actual trading days.
- **Rationale:** Standardizes non-overlapping partitions and eliminates target-to-input boundary leakage across splits under rolling windows of horizon $H=5$. One trading week consists of 5 market days, providing an economically meaningful and standard horizon for equity time series.
- **Alternatives Considered & Rejected:**
  - *Option B (7-day calendar horizon):* *Rejected:* Calendar 7 days spans weekends and holidays unevenly across jurisdictions, creating varying numbers of trading days. A 5-trading-day horizon represents exactly one trading week.
  - *Option C (Zero purge gap):* *Rejected:* Targets from the end of training overlap with inputs at the start of validation, creating boundary leakage.
- **Timing:** *A Priori* (established before modeling).
- **Impacted Files / Components:** `research/MASTER_RESEARCH_PLAN.md`, `research/phases/phase_03_leakage_audit.md`, `research/results/phase_03/leakage_audit_results.json`.

---

### DEC-P03-002: Strict SLM Benchmark Scope (Exclusion of ML and Deep Learning Baselines)
- **Date:** 2026-11-12
- **Phase:** Phase 03 (Temporal Splits and Leakage Audit)
- **Decision:** Phase 04 baselines are strictly restricted to simple naive and statistical reference models (Persistence / Random Walk, Historical Mean, Moving Average, Drift) and evaluation framework unit testing. All Machine Learning (XGBoost), Deep Learning (LSTM, GRU, PatchTST, iTransformer), and specialized Time-Series Foundation Models are permanently excluded from the benchmark suite.
- **Rationale:** Focuses research exclusively on evaluating the capabilities, representation sensitivities, and fine-tuning dynamics of Small Language Models without diluting compute on non-SLM deep learning baselines.
- **Alternatives Considered & Rejected:**
  - *Option B (Include LSTM/XGBoost):* *Rejected by User Directive:* Diverts resources and shifts paper narrative away from pure language model time-series reasoning.
- **Timing:** *A Priori* (established prior to Phase 04 implementation).
- **Impacted Files / Components:** Phase 04 implementation, `src/benchmark/`, `research/MASTER_RESEARCH_PLAN.md`.

---

### DEC-P03-003: Formal Naming of Asset Universes
- **Date:** 2026-11-12
- **Phase:** Phase 03 (Temporal Splits and Leakage Audit)
- **Decision:** Formally label the 146 continuous tickers as the **Predefined Core Full-History Universe** (not "clean universe"), and the remaining 4 tickers (`NSTG`, `ASC.JO`, `BHARTIHEXA.BSE`, `BIK.JO`) as the **Secondary Universe**.
- **Rationale:** Adheres to precise academic terminology avoiding normative terms like "clean" while transparently classifying continuous versus shortened/unverified equities.
- **Alternatives Considered & Rejected:**
  - *Option B (Label as "clean" and "dirty"):* *Rejected:* Imprecise and unscientific.
- **Timing:** *A Priori*.
- **Impacted Files / Components:** Phase 03, Phase 04, documentation.

---

### DEC-P03-004: Generation of Clean Preprocessed Tables
- **Date:** 2026-11-12
- **Phase:** Phase 03 (Temporal Splits and Leakage Audit)
- **Decision:** Write all cleaned tables strictly to `data/processed/` (`us_equities_clean.csv`, `jse_equities_clean.csv`, `india_equities_clean.csv`, `global_equities_common.csv`). Raw files in `data/raw/` remain 100% immutable and unedited.
- **Rationale:** Preserves pristine raw data provenance and reproducible pipeline execution.
- **Alternatives Considered & Rejected:**
  - *Option B (Mutate raw files in place):* *Rejected:* Destroys provenance.
- **Timing:** *A Priori*.
- **Impacted Files / Components:** `data/processed/`, data loaders.

---

### DEC-P04-001: Baseline Specification, Parameter Freezing, and Evaluator Policies
- **Date:** 2026-11-12
- **Phase:** Phase 04 (Statistical Baselines and Evaluation Framework)
- **Decision:** Freeze baseline specifications and evaluation metrics:
  - **Persistence (Random Walk):** Forecast $\hat{r} = 0.0$ (price equals origin close). Directional Accuracy is formally reported as `N/A — zero-return forecast has no directional prediction`, with the raw zero-return hit rate tracked separately.
  - **Historical Mean vs. Drift Equivalence:** Confirmed mathematically as an exact identity under discrete log returns due to telescoping sums across the context window ($H \cdot \bar{r}_{\text{daily}} \equiv H \cdot \text{drift rate}$). Both are retained for clarity.
  - **Moving Average:** Mean daily return over the most recent 5 trading days inside the context window multiplied by $H$.
  - **MASE Denominator:** Scaled strictly by the in-sample naive Persistence MAE computed exclusively on training data ($0.038318$ for $H=5$; $0.016040$ for $H=1$), guaranteeing zero lookahead leakage from validation/test sets.
- **Rationale:** Ensures mathematically rigorous and unpeeking evaluation baselines across all splits.
- **Alternatives Considered & Rejected:**
  - *Option B (Report Persistence DA as 4.88%):* *Rejected:* Misleading because predicting zero return is not a directional forecast.
  - *Option C (Recompute MASE denominator on test set):* *Rejected:* Severe methodological flaw violating Hyndman's out-of-sample MASE definition.
- **Timing:** *A Priori*.
- **Impacted Files / Components:** `src/evaluation/evaluator.py`, `src/benchmark/run_baselines.py`, `research/results/phase_04/`.

---

### DEC-P05-001: Phase 05 Zero-Shot SLM Benchmark Protocol, Validity Policies, and Selection Hierarchy
- **Date:** 2026-11-13
- **Phase:** Phase 05 (Zero-Shot SLM Benchmark and Selection)
- **Decision:** Formally lock the experimental protocol, taxonomy, validity gates, and selection rules for Phase 05:
  1. **Model Scope:** Exactly 10 instruction-tuned SLMs ($\le 4\text{B}$ parameters) across 5 distinct model families: Llama 3.2 (1B, 3B), Qwen 2.5 (0.5B, 1.5B, 3B), Gemma 2 (2B), SmolLM2 (135M, 360M, 1.7B), and Phi-3.5 (3.8B). Zero traditional ML, classical time-series, deep time-series, or foundation time-series models permitted.
  2. **Primary Benchmark Prompt & Representation:** Template A (cumulative 5-day log-return prediction from historical prices) is frozen *a priori* as the universal benchmark prompt. Prompt-and-input-representation sensitivity analysis is strictly quarantined to an independent development split and evaluated against the unified log-return target $r_{t \to t+5} = \log(P_{t+5} / P_t)$.
  3. **Screening Cohort (420 Samples) & Cross-Market Target Construction:**
     - Screening origins are temporally synchronized using common market trading sessions across India, South Africa, and USA ($k \in \{0, 9, 18, 27, 36, 45, 54, 63, 72, 81, 90, 99, 108, 117\}$; $\Delta k = 9$).
     - Ticker targets are constructed strictly along each ticker's own home-exchange trading session sequence (5th subsequent trading session on that exchange). Target calendar dates may vary across markets due to local holiday closures, but reflect exact 5-trading-day returns.
     - The cohort spans 30 stocks (1 per sector across all 10 canonical sectors per country) $\times$ 14 origin dates = 420 samples. The exact manifest `configs/screening_cohort_manifest.json` will be generated from this common-session logic prior to running Gate 5.4.
  4. **Validity Parsing & Two-Tier Thresholds:**
     - Strict validity requires exact compliance with `[FORECAST: <number>]` matched as a case-sensitive full string (`^\s*\[FORECAST:\s*([+-]?\d+(?:\.\d+)?)\s*\]\s*$`). Fallback parsing is tracked diagnostically but scored as invalid under primary benchmark metrics.
     - Native chat-template protocol: Every model must be invoked using its native `tokenizer.apply_chat_template` wrapping the frozen Template A semantic prompt text inside a `[{"role": "user", "content": ...}]` structure with `add_generation_prompt=True`. The benchmark runner requires `tokenizer.chat_template` to be present and halts with an explicit `NativeChatTemplateError` if missing, completely preventing silent raw-prompt degradation or ad-hoc custom string wrappers. The underlying Template A prompt text remains 100% frozen and byte-for-byte identical across all models.
     - Tier 1 (Screening Threshold, Gate 5.4): $\ge 90.0\%$ strict validity required on 420 samples.
     - Tier 2 (Backbone Eligibility Threshold, Gate 5.6): $\ge 95.0\%$ strict validity required on full validation data.
  5. **No-Winner, SFT Research Candidate, and Tie-Breaking Contingencies:**
     - *Forecasting Winner Definition:* A candidate is declared a true forecasting winner only if it achieves `valid_output_pct >= 95.0%` AND `RelRMSE_replaced < 1.0000` on Validation $H=5$ (outperforming the trivial Random Walk persistence benchmark).
     - *SFT Research Candidate Selection (When None Beats Persistence):* If eligible models exist (`valid_output_pct >= 95.0%`) but none beats Persistence (`RelRMSE_replaced >= 1.0000`), the top model is NOT designated a forecasting winner. Instead, it is designated strictly as an **SFT research candidate** for Phase 06 fine-tuning, accompanied by the explicit published finding that no zero-shot SLM outperformed the random walk baseline.
     - *No Eligible Backbone Outcome:* If no model satisfies $\ge 95.0\%$ strict validity on validation, the benchmark halts with an explicit *No Eligible Backbone Found* declaration. No model is selected automatically.
     - *Reproducible Throughput Measurement for Tie-Breaking:* If two contenders fall within a 1.0% relative error margin, ties are broken deterministically by (a) Directional Accuracy, (b) Strict Validity %, (c) Parameter Count (lower is better), and (d) Measured Generation Throughput. Throughput is strictly the final tie-breaker and cannot override error rankings outside the 1.0% margin. It must be evaluated under a standardized protocol: sequential execution on identical hardware, batch size = 1, greedy decoding (`temperature=0.0`, `max_new_tokens=32`), 5 discarded warm-up passes, exact same 50-sample slice and order (the first 50 samples of the 420 screening cohort sorted lexicographically by `(ticker, origin_date)`), MPS synchronization before and after timing, prompt prefill explicitly excluded from generation tokens/sec, and averaged over 3 repeated runs.
  6. **Horizon Hierarchy & Test Isolation:** Primary Horizon $H=5$ is the sole criterion for backbone selection. Secondary Horizon $H=1$ is evaluated for top contenders and reported separately without influencing selection. The locked test split (`2024-11-11` to `2025-05-30`) is evaluated once on the final selected winning backbone only.
  7. **Table Reporting Standard:** All benchmark tables must report Strict Validity %, Invalid Output %, Common-Valid-Subset metrics (MAE, RMSE, NRMSE, RelRMSE, MASE, DA, Bias), and Persistence-Replaced metrics.
- **Rationale:** Guarantees complete scientific rigor, zero test-set leakage, transparent handling of model hallucinations, and deterministic reproducibility.
- **Alternatives Considered & Rejected:**
  - *Option B (Select model based on whichever horizon performs best):* *Rejected:* Introduces post-hoc cherry-picking.
  - *Option C (Count conversational numeric extraction as valid):* *Rejected:* Masks structural instruction-following failures.
- **Timing:** *A Priori* (locked prior to model benchmarking).
- **Impacted Files / Components:** `research/MASTER_RESEARCH_PLAN.md`, `configs/benchmark_zero_shot.yaml`, `src/benchmark/`, `research/results/phase_05/`.
