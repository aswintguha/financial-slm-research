# Financial Time-Series Forecasting with Small Language Models (SLMs)
## Improved Research Plan — Phase by Phase

**Status:** DRAFT for discussion. Nothing here is final until you approve it.
**Source of truth:** your original research plan document. All research questions (RQ1–RQ6), hypotheses (H1–H6), experiment IDs (E00–E20), and terminology are preserved.
**Current stage:** Phase 1 (Data inspection). Nothing after it has started.

---

## How to read this document

Every item is tagged so you can see exactly what is original and what is new:

| Tag | Meaning |
|---|---|
| **[ORIGINAL]** | Taken directly from your plan, unchanged. |
| **[CLARIFY]** | The plan was silent or ambiguous. I am proposing a precise definition. |
| **[PROPOSED CHANGE]** | I want to add or modify something. It includes the *why*, the *research benefit*, and the *effect on reproducibility / publication validity*. **I will not apply any of these until you approve them.** |
| **[DECISION NEEDED]** | A choice only you can make (often after seeing the data). |

---

## Master Roadmap

| Phase | Name | Experiments | Gate (must pass before moving on) |
|---|---|---|---|
| 0 | Protocol freeze | — | Decisions below are written down and approved |
| 1 | Data inspection | E00 | Every raw file is understood and documented |
| 2 | Data audit and cleaning | E00, E01 | Audit report complete, no unexplained anomalies |
| 3 | Temporal splits and leakage audit | E01 | Automated leakage tests pass |
| 4 | Naive/statistical baselines and evaluation framework | E03 (E04, E05 removed from scope) | Evaluator is tested and baselines reproduce |
| 5 | Zero-shot SLM benchmark and selection | E02, E06 (E05 removed from scope) | Backbone selected on validation and frozen |
| 6 | Supervised fine-tuning and representation ablation | E07–E10 | Best representation chosen on validation |
| 7 | Regime-aware SFT | E11 | Ablation complete |
| 8 | Generalization studies | E12–E14, E15, E16 | Done |
| 9 | Statistical evaluation | E17, E18 | Done |
| 10 | Economic evaluation | E19, E20 | Done |
| 11 | Error analysis, figures, paper | — | Done |

**Rule of thumb:** a phase is not finished until its gate is passed. Later phases never reach back and change earlier decisions based on test results.

---

## Phase 0 — Protocol Freeze

**Goal:** write down every decision that could later be accused of being "tuned on the test set" *before* seeing any model results.

### Items
1. **[ORIGINAL]** Scope: 3 markets (India, USA, South Africa), about 50 stocks each, about 10 sectors. Primary task: closing-price/return forecasting from OHLCV only, with no news, sentiment, or macro data.
1a. **[SCOPE DECISION — set by you]** **Language-model-only study.** No time-series foundation models (Chronos, TimesFM, etc.) are used anywhere in the project. Experiment **E05 (TSFM baselines) is removed**.
1b. **[SCOPE DECISION — set by you]** **SLM-centric study: no ML/DL forecasting models.** ARIMA, XGBoost, LSTM, GRU, and PatchTST/iTransformer are removed. Experiment **E04 (deep baselines) is removed**, and E03 shrinks to simple naive/statistical reference baselines (persistence, historical mean, moving average). Experiment IDs are not renumbered, so E04 and E05 stay as gaps to keep the numbering consistent with your original document. The paper must state this scope explicitly and list the absence of ML/DL and TSFM comparisons as a limitation, because reviewers may still ask why a language model was used instead of established forecasting models.
2. **[DECISION NEEDED]** Final scope depends on what your three files actually contain. The plan assumes about 150 stocks. We will confirm this in Phase 1.
3. **[ORIGINAL]** SLM inclusion criteria (open-weight, language model rather than a time-series model, about 4B parameters or fewer, instruction-capable, runnable on your hardware, stable checkpoint, released before the benchmark cutoff date).
4. **[CLARIFY]** Define "SLM" explicitly in the paper (parameter ceiling and why).
5. **[CLARIFY] Metric definitions.** The original gives `NRMSE = RMSE / σ(y)` without saying which σ. Proposal: σ is the standard deviation of the target series **computed on the training period only** (per market or per stock, to be decided), never on the evaluation window.
6. **[CLARIFY] One evaluation scale for everything.** The zero-shot benchmark forecasts prices, but SFT's primary target is log returns. Proposal: every model's output is converted to **both** (a) a 7-step log-return forecast and (b) a reconstructed price forecast, and all metrics are reported on both. This makes zero-shot and SFT directly comparable.
7. **[PROPOSED CHANGE] Add a baseline-relative metric as co-primary.**
   - *What:* add relative RMSE versus persistence (`RMSE_model / RMSE_persistence`) and/or MASE, alongside NRMSE.
   - *Why:* NRMSE alone does not say whether the model beats the naive forecast, which is your central H6 question.
   - *Benefit:* a value below 1 reads directly as "beats persistence".
   - *Reproducibility/validity:* improves validity and does not harm reproducibility.
8. **[CLARIFY]** Fix random seeds, decoding settings (greedy, temperature 0), the numeric format in prompts (fixed decimal places), and the output-parsing rules.
9. **[PROPOSED CHANGE] Handling invalid model outputs.**
   - *What:* decide the policy now. Report "Valid %" (as your plan requires). For the headline comparison, evaluate all models on the **common subset where every model produced a valid output**. Also report a version where invalid outputs are replaced by persistence, clearly labelled.
   - *Why:* without a fixed rule, models that fail often can look artificially good or bad.
   - *Validity:* prevents a silent, hard-to-defend bias.

**Deliverable:** `configs/protocol_v1.yaml` and a short `PROTOCOL.md`, frozen with a git tag.

---

## Phase 1 — Data Inspection (YOU ARE HERE)

**Goal:** understand the three raw files. **Do not modify them.** Experiment ID: E00 (first half).

### What we find out (read-only)
- File type, size, number of rows and columns, column names and data types
- For `Indian-Final-Data-3month.xlsx`: how many sheets, and what "3month" means (frequency? duration? aggregation?)
- Date column: format, earliest and latest date, frequency (daily or not)
- How stocks are identified (ticker column, one column per stock, or one file per stock)
- Whether OHLCV is present, and whether prices look adjusted or unadjusted
- Rough count of stocks per market
- Date ranges and calendars per market

### Outputs
- `data/metadata/` dataset cards (one per file) describing structure, assumptions, and open questions
- An inspection log in `logs/`

### Gate
We can answer, for each file: *what is one row, what is the date frequency, how many stocks, which period, which columns?*

### [PROPOSED CHANGE] Raw-data protection
- *What:* record a checksum (SHA-256) of each raw file now, and make `data/raw/` read-only.
- *Why:* proves later that raw data was never altered.
- *Benefit:* strengthens reproducibility and satisfies your "keep raw data untouched" rule in a verifiable way.

---

## Phase 2 — Data Audit and Cleaning

**Goal:** a documented, reproducible path from raw files to a clean dataset. Experiments E00 and E01 (quality part).

### [ORIGINAL] Checks to run
- Missing dates, prices, and volume
- Duplicate `(ticker, date)` records
- Zero or negative prices, impossible jumps, repeated prices
- Splits and corporate actions
- Consistency of `ticker → company → country → market → sector`
- Trading calendars differ by market, so **align by actual date, never by row number**

### [PROPOSED CHANGE] Adjusted prices and corporate actions
- *What:* decide explicitly whether to use split/dividend-adjusted closes. Log which stocks have suspected unadjusted splits.
- *Why:* an unadjusted split looks like a 50% crash and would corrupt returns.
- *Benefit:* clean returns. Choice is documented for reviewers.
- *Validity:* required for credible results.

### [PROPOSED CHANGE] Missing-data policy
- *What:* no forward-filling across long gaps and no interpolation that uses future values. Short gaps may be handled with a documented causal rule only. Windows containing unresolved gaps are dropped, not repaired.
- *Why:* interpolation silently uses future information.
- *Validity:* directly prevents leakage.

### Outputs
- `data/processed/` (cleaned files, versioned, with a manifest listing every transformation)
- Data audit report (counts, issues found, actions taken)
- Dataset table (market, stocks, sectors, period, observations, missing %)

### Gate
Every removed or altered record is logged and justified. Raw files are unchanged (checksums match).

---

## Phase 3 — Temporal Splits and Leakage Audit

**Goal:** guarantee "at time t, the model sees only information available at or before t". Experiment E01.

### [ORIGINAL]
- No `train_test_split()` and no random splitting
- Chronological train / validation / test
- Preferred: rolling-origin (expanding-window) evaluation
- Window construction from history only. Overlapping windows never cross split boundaries.

### [PROPOSED CHANGE] Purge/embargo gap between splits
- *What:* leave a gap of at least the forecast horizon H (and ideally context length for any rolling statistic) between the last training target and the first validation/test input.
- *Frozen Decision:* The project formally adopts **Primary Horizon $H = 5$ trading days (one trading week)** and **Secondary Horizon $H = 1$ trading day**. The primary 5-day horizon represents one complete trading week, replacing any earlier 7-day calendar specification.
- *Why:* a window starting just before the boundary has targets that overlap the next split. This is subtle leakage even with chronological splits.
- *Benefit:* removes boundary contamination.
- *Validity:* standard practice in financial ML, and reviewers will check.

### [PROPOSED CHANGE] Pretraining-data contamination check
- *What:* record each candidate SLM's reported pretraining cutoff date and position the test period after those cutoffs.
- *Scientific Standard:* The test period occurs after the reported training cutoff dates of the candidate SLM checkpoints, reducing the risk of direct temporal memorization of the evaluation period. However, complete pretraining-data non-contamination cannot be independently guaranteed.
- *Why:* if a model saw historical stock prices during pretraining, zero-shot results can be inflated by memorization.
- *Benefit:* protects the empirical validity of the zero-shot SLM comparison while maintaining defensible claims.

### [PROPOSED CHANGE] Rolling-origin compute budget
- *What:* use rolling-origin for the cheap models (baselines, zero-shot). For SFT, which is expensive, use one primary chronological split and run rolling-origin only for the final selected configuration if budget allows.
- *Why:* repeating fine-tuning across every fold may be unaffordable on modest hardware.
- *Validity:* keeps the evaluation honest and feasible. It must be stated clearly in the paper.

### [CLARIFY] Normalization and regime rules
- All normalization statistics (mean, standard deviation) are computed **inside the context window only**.
- Regime thresholds (volatility and trend) are computed from **training-period data only** (or from an expanding window that never looks ahead).

### Automated leakage tests (to be implemented as code later)
1. No input timestamp is later than the forecast origin.
2. No window's targets overlap another split's inputs or targets.
3. Train max date < validation min date < test min date (with the gap).
4. Normalization/regime statistics are reproducible from past data only.

### Outputs
- Split definition file (dates per fold), leakage test suite and its report

### Gate
All leakage tests pass.

---

## Phase 4 — Baselines and Evaluation Framework

**Goal:** build and test the scoring machinery on cheap reference models before any SLM touches it. Experiment E03 (E04 removed).

### Baselines (scope narrowed by your decision)
Persistence (random walk), historical mean, moving average. These are simple financial forecasting rules, not ML/DL models. They answer the question: *does the SLM provide forecasting information beyond a trivial rule?*

**Removed from scope:** ARIMA, XGBoost, LSTM, GRU, PatchTST, iTransformer, and all time-series foundation models.

**[DECISION NEEDED]** ARIMA is a classical *statistical* model rather than ML/DL. I have removed it as you asked, but if you want a slightly stronger statistical reference, keeping it is cheap. Tell me if you want it back.

### [PROPOSED CHANGE] Build the evaluator first and test it
- *What:* implement one evaluation script (MAE, RMSE, NRMSE, relative RMSE, directional accuracy, bias, valid %) and unit-test it on persistence with known answers.
- *Why:* the same script scores everything, which is your "identical conditions" rule.
- *Benefit:* eliminates a classic source of inconsistent comparisons.

### [PROPOSED CHANGE] Fixed, pre-declared baseline settings
- *What:* fix the moving-average window length(s) and historical-mean lookback on the validation set (or in Phase 0) with a small, documented choice, then freeze them.
- *Why:* the few tunable settings in these baselines should not be chosen after seeing test results.
- *Validity:* strengthens the claim if the SLM wins, and the honesty of the result if it does not.

### Outputs
- Baseline results table, evaluator, `predictions.csv` and `metrics.json` per run

### Gate
Persistence results are reproduced exactly on re-run, and the evaluator tests pass.

---

## Phase 5 — Zero-Shot SLM Benchmark and Backbone Selection

**Goal:** answer RQ1, test H6, and select one backbone. Experiments E02 (prompt & representation sensitivity), E06 (zero-shot SLM benchmark). (E05 removed from scope).

### [ORIGINAL & FROZEN PROTOCOL]
- Exactly 10 open-weight instruction-tuned SLMs ($\le 4\text{B}$ parameters) across 5 model families (Llama 3.2, Qwen 2.5, Gemma 2, SmolLM2, Phi-3.5) evaluated under identical conditions.
- Strict scope: Zero traditional ML, zero classical time series (ARIMA), zero deep time series (LSTM/PatchTST), zero time-series foundation models (Chronos/TimesFM).
- Backbone selection performed on **validation split only**, then frozen. The locked test split is evaluated exactly once on the single selected winning backbone.
- Target formulation: Primary Horizon $H=5$ trading days cumulative log return is the sole backbone selection criterion. Secondary Horizon $H=1$ is evaluated for top contenders and reported separately without influencing selection.
- **Cross-Market Target Construction Policy:**
  - Screening forecast origins are temporally synchronized using common trading-session dates across all three markets.
  - For each individual stock, the $H=5$ target is constructed strictly along that stock's own exchange trading-session sequence: the 5th subsequent valid trading session on that exchange.
  - As a result of exchange-specific holiday calendars, target calendar dates may differ across markets for the same origin date (e.g. Ram Navami or Workers' Day). The protocol strictly records each ticker's actual origin date, target date, origin price, target price, and realized cumulative log return, and never artificially forces different international markets to share identical target calendar dates.
  - This identical ticker-specific target construction logic is applied uniformly across screening, full validation, and test evaluation.

### [VALIDITY CRITERIA & OUTPUT PARSING RULES]
- **Strict Compliance:** Exact `[FORECAST: <number>]` tag match is the primary validity criterion (`strict_valid`). Conversational / leading floats are recorded as diagnostic fallback parsing but treated as `is_valid = False` under primary benchmark scoring.
- **Two-Tier Validity Thresholds:**
  - Initial Screening Threshold (Gate 5.4, 420-sample cohort): $\ge 90.0\%$ strict validity required to qualify for championship validation.
  - Final Backbone Eligibility Threshold (Gate 5.6, full 20,781-sample validation split): $\ge 95.0\%$ strict validity required to be eligible as winning backbone.
- **Dual Metric Reporting:** Both *Common-Valid-Subset* metrics and *Persistence-Replaced* metrics are published in all benchmark tables. Persistence-replaced Relative RMSE vs. Persistence is the primary ranking metric.

### [NO-WINNER, SFT CANDIDATE SELECTION & TIE-BREAKING RULES]
- **Distinction Between Forecasting Winner vs. SFT Research Candidate:**
  - *Forecasting Winner:* A model must achieve `valid_output_pct >= 95.0%` AND `RelRMSE_replaced < 1.0000` on Validation $H=5$ (outperforming the trivial Random Walk Persistence benchmark).
  - *SFT Research Candidate (Underpersistence Outcome):* If eligible models exist (`valid_output_pct >= 95.0%`) but *none* beats Persistence (`RelRMSE_replaced >= 1.0000`), the top model is NOT designated a forecasting winner. Instead, it is classified strictly as an **SFT research candidate**, with the explicit scientific finding reported that no zero-shot SLM beat the random walk baseline.
  - *No Eligible Backbone Found:* If no candidate achieves $\ge 95.0\%$ strict validity on full validation data, the protocol formally declares an explicit *No Eligible Backbone Found* outcome, documents the systemic formatting breakdown across candidate architectures, and halts prior to fine-tuning. A model is never selected automatically if it fails the 95.0% validity gate.
- **Reproducible Inference-Throughput Protocol for Tie-Breaking:**
  If two top contenders have validation `RelRMSE_replaced` within a 1.0% relative margin, ties are broken using predeclared secondary criteria, where inference throughput is measured under strict standardization:
  1. *Hardware & Execution Isolation:* Evaluated sequentially on the exact same hardware, clearing MPS cache and performing OS garbage collection between models.
  2. *Standardized Generation Settings:* Batch size = 1, greedy decoding (`temperature=0.0`, `do_sample=False`), `max_new_tokens=32`, bfloat16 precision.
  3. *Fixed Warm-Up Procedure:* Exactly 5 warm-up inferences executed and discarded before timing begins.
  4. *Fixed Evaluation Slice & Ordering:* An identical predeclared 50-sample slice and exact sample order is evaluated for every candidate. The 50 samples are deterministically selected from the 420-sample screening cohort using a fixed rule: the first 50 samples sorted by `(ticker, origin_date)` in ascending lexicographical order. This sample selection is frozen *a priori* before model benchmarking and is strictly invariant across models.
  5. *Generation-Only Metric Definition:* Throughput (tokens/sec) is defined strictly as total generated output tokens divided by generation-only wall-clock time; prompt prefill time is explicitly excluded from the generation throughput metric.
  6. *Device Synchronization & Multi-Run Averaging:* Synchronize MPS (`torch.mps.synchronize()`) immediately before and after each timed interval. The timed 50-sample measurement is repeated three times ($K=3$ runs), reporting the mean throughput and run-to-run variability.
  7. *Strict Tie-Breaker Precedence:* Throughput is strictly the final tie-breaker; it can never override the primary $H=5$ Persistence-Replaced RelRMSE ranking outside the predeclared 1.0% relative tie margin.
  8. *Deterministic Tie-Breaking Hierarchy:*
     1. Primary tie-breaker: Higher Directional Accuracy (%) on the common valid subset.
     2. Secondary tie-breaker: Higher Strict Validity Percentage (`valid_output_pct`).
     3. Tertiary tie-breaker: Lower Parameter Count (favoring parameter efficiency for Phase 06 SFT).
     4. Quaternary tie-breaker: Higher measured generation throughput (mean tokens/sec across 3 runs).

### [SCREENING COHORT PROTOCOL]
- Fixed 420-sample stratified cohort: 30 stocks (1 per sector across all 10 canonical sectors in India, South Africa, and USA) $\times$ 14 evenly spaced validation trading sessions across the first 118 common sessions (`step=9` across common index $k \in \{0, 9, 18, 27, 36, 45, 54, 63, 72, 81, 90, 99, 108, 117\}$), leaving later sessions for boundary margin. All dates in documentation and the generated cohort manifest are required to derive deterministically from this identical common trading-session index logic.

### Outputs
- Benchmark table (`valid_pct`, `invalid_pct`, common-valid-subset metrics, persistence-replaced metrics, params, throughput, memory).
- A frozen "selected backbone" record in `research/results/phase_05/selected_backbone.json` and `research/RESEARCH_DECISIONS.md`.

### Gate
Backbone selected and permanently recorded. Never swapped or altered in later phases.

---

## Phase 6 — Supervised Fine-Tuning and Representation Ablation

**Goal:** answer RQ2 and RQ3. Experiments E07–E10.

### [ORIGINAL]
- Only the selected backbone is fine-tuned, using LoRA/QLoRA as the primary method
- Training windows built from history, never randomly split across train and test
- Primary target: future log returns (r₁…r₇). Secondary: direction derived from predicted returns.
- Four representations: raw prices, normalized prices, returns, normalized prices + returns
- Report trainable vs total parameters. Hyperparameters chosen on validation with a small search.

### [PROPOSED CHANGE] Multiple seeds
- *What:* train each final configuration with 3 random seeds and report mean and spread.
- *Why:* a single fine-tuning run can look better or worse by chance.
- *Benefit:* more trustworthy comparisons between representations.
- *Reproducibility:* improves it, at 3× training cost for the final configurations only (not for the hyperparameter search).

### [PROPOSED CHANGE] Order of experiments
- *What:* run the zero-shot reference (E06) and the four representation runs under the same hyperparameter budget.
- *Why:* otherwise one representation gets more tuning effort than another.
- *Validity:* keeps the ablation fair.

### Outputs
- Fine-tuned adapters, `config.json`, `predictions.csv`, `metrics.json` per experiment
- Representation ablation table

### Gate
Best representation selected using **validation** results only.

---

## Phase 7 — Regime-Aware SFT

**Goal:** answer RQ4. Experiment E11.

### [ORIGINAL]
- Trend regime (bullish, neutral, bearish) and volatility regime (low, medium, high), computed from past data only
- Regime labels added to the structured prompt
- Compared against the best non-regime model

### [CLARIFY] Regime definition
Fix the lookback length `k`, the slope definition, and the thresholds (for example, training-period quantiles) in Phase 0 or here before any model result is seen.

### [PROPOSED CHANGE] Control for the label itself
- *What:* add a control run where regime labels are shuffled or randomized, keeping everything else the same.
- *Why:* tells you whether the gain comes from real regime information or just from a longer/more structured prompt.
- *Benefit:* a stronger causal claim about regime conditioning.
- *Validity:* optional but highly recommended for a publishable ablation.

### Gate
Ablation complete. Name the method only if results support it (do not use "RA-FinSLM" in advance).

---

## Phase 8 — Generalization Studies

**Goal:** answer RQ5. Experiments E12–E16.

### [ORIGINAL]
- **Cross-stock:** hold out about 20% of stocks entirely
- **Cross-market:** leave-one-market-out (train on two markets, test on the third)
- **Cross-sector:** hold out one sector at a time (optional)
- **Horizon study:** 1, 3, 5, 7, 14, 30 days
- **Context study:** 23, 43, 83, 126, 252 days

### [PROPOSED CHANGE] Calendar alignment for cross-market tests
- *What:* when training on one market and testing on another, make sure the training and test periods respect the same chronological protocol, so no market's "future" leaks into another market's past.
- *Why:* markets move together in time (global shocks). Training on 2024 US data and testing on a 2023 Indian period would use the future.
- *Validity:* essential for a temporal-leakage-free cross-market claim.

### [DECISION NEEDED]
Which of cross-sector, horizon, and context studies are core vs. secondary, given time and compute. The original plan itself warns against letting the paper grow too large.

---

## Phase 9 — Statistical Evaluation

**Goal:** answer the first half of RQ6. Experiments E17, E18.

### [ORIGINAL]
- Diebold-Mariano tests (SFT vs persistence, historical mean, moving average, zero-shot SLM, and between SLM variants)
- Block bootstrap or stock/time-clustered bootstrap confidence intervals
- Effect size (percentage improvement)
- Bias analysis

### [PROPOSED CHANGE] Multiple-comparison control
- *What:* with many model pairs, correct p-values (for example, Holm) or use a Model Confidence Set.
- *Why:* many tests raise the chance of false "significant" results.
- *Validity:* a standard reviewer expectation.

### [CLARIFY] DM test for multi-step, overlapping forecasts
Use a HAC (autocorrelation-robust) variance estimator with a small-sample correction (Harvey-Leybourne-Newbold), as the original plan cautions about overlapping horizons.

### [CLARIFY] Aggregation across stocks
Decide whether tests are run per stock, per market, or on a pooled panel. State clearly how cross-sectional dependence is handled.

---

## Phase 10 — Economic Evaluation

**Goal:** answer the second half of RQ6. Experiments E19, E20.

### [ORIGINAL]
- Simple threshold rule: buy, sell, or hold based on predicted return
- Metrics: cumulative and annualized return, Sharpe ratio, maximum drawdown, turnover, win rate
- Transaction costs: 0, 10, 25, 50 bps
- No claims such as "we beat the market"

### [PROPOSED CHANGE] Threshold selection
- *What:* choose the trading threshold on validation data only, then apply it unchanged to test.
- *Why:* tuning the threshold on test results is a hidden form of leakage.
- *Validity:* keeps the economic result out-of-sample.

### [CLARIFY]
Specify execution timing (for example, signal at close of day t, trade at close or open of day t+1) so no look-ahead sneaks into the simulation.

---

## Phase 11 — Error Analysis, Figures, and Paper

### [ORIGINAL] Breakdowns
By country, sector, trend regime, volatility regime, and horizon.

### [ORIGINAL] Figures
Architecture, 10-SLM benchmark, zero-shot to SFT improvement, representation ablation, regime improvement, cross-market transfer, horizon performance, bias/error distribution, economic performance after costs.

### [PROPOSED CHANGE] Final-test discipline
- *What:* the test set is evaluated once per frozen model configuration, with a log of when and why each test evaluation happened.
- *Why:* repeated test peeking is the most common hidden flaw in finance-ML papers.
- *Validity:* directly supports the claim that results are genuinely out-of-sample.

### [ORIGINAL] Novelty claims
Do **not** claim "first to fine-tune an SLM for stock forecasting". Position the contribution as the combined, controlled experimental framework. Verify every related-work citation before submission.

---

## Cross-Cutting Practices (apply in every phase)

| Practice | Status |
|---|---|
| Experiment naming `EXP001_…` with `config.json`, `predictions.csv`, `metrics.json`, logs | [ORIGINAL] |
| Record model, version, params, dataset version, split dates, context, horizon, hyperparameters, seed, representation, market, sector, regime | [ORIGINAL] |
| Git commits and tags per phase; no files named `final2.py` | [ORIGINAL] |
| Pinned `requirements.txt` plus recorded library versions and hardware | [PROPOSED CHANGE]: needed for exact reproducibility |
| Data licensing and redistribution check for the three datasets | [PROPOSED CHANGE]: required before sharing code or data with the paper |
| Do **not** add news, sentiment, macro data, RAG, agents, RL/PPO, GNNs, or 50 models | [ORIGINAL] |

---

## Summary of Proposed Changes (all awaiting your approval)

| # | Phase | Proposed change | Main benefit |
|---|---|---|---|
| 1 | 0 | Co-primary relative-to-persistence metric | Directly tests H6 |
| 2 | 0 | Fixed invalid-output policy | Prevents hidden bias |
| 3 | 1 | Raw-file checksums and read-only raw folder | Proves raw data untouched |
| 4 | 2 | Explicit adjusted-price and missing-data rules | Clean, leakage-free returns |
| 5 | 3 | Purge/embargo gap between splits | Removes boundary leakage |
| 6 | 3 | Pretraining-cutoff contamination check | Protects zero-shot validity |
| 7 | 3 | Rolling-origin only where compute allows | Feasible and honest |
| 8 | 4 | Evaluator built and tested first, frozen baseline settings | Fair comparisons |
| 9 | 5 | Small prompt-robustness check and selection with uncertainty | More reliable ranking |
| 10 | 6 | 3 seeds for final configs, equal tuning budget per representation | Trustworthy ablation |
| 11 | 7 | Shuffled-regime control | Stronger causal claim |
| 12 | 8 | Calendar alignment in cross-market tests | No cross-market future leakage |
| 13 | 9 | Multiple-comparison correction | Fewer false positives |
| 14 | 10 | Validation-only threshold and explicit trade timing | Out-of-sample economics |
| 15 | 11 | Logged, single-use test evaluation | Publication credibility |

**None of these alter your research questions, hypotheses, or overall experimental structure.** They tighten definitions and close leakage and fairness gaps.

---

## Open Decisions for You

1. Confirm or adjust the scope (about 150 stocks) after Phase 1 inspection.
2. Approve or reject each proposed change above (you can answer by number).
3. Which of the secondary experiments (cross-sector, context study) are in scope for the first paper.
4. Compute budget: what GPU/hardware and time do you have? This affects model list, QLoRA vs LoRA, and rolling-origin scope.

**Next step when you are ready:** Phase 1, a read-only look at the three raw files.