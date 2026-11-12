# Phase 04: Statistical Baselines and Evaluation Framework

## Objective
Build, unit-test, and lock the unified financial forecasting evaluation framework for all subsequent Small Language Model (SLM) benchmarking. Implement the four strictly permitted simple statistical and naive reference baselines (**Persistence / Random Walk**, **Historical Mean**, **Moving Average**, and **Drift**) on the predefined 146-stock core full-history universe across both frozen forecasting horizons ($H=5$ primary, $H=1$ secondary). Verify target construction and price reconstruction mathematically, evaluate baseline performance across chronological splits without peeking at the locked test set, and establish benchmark performance anchors.

---

## Strict Scope Boundaries (Enforced)
Per the master research protocol and explicit user instructions, this research is strictly focused on Small Language Models.
The following models are **permanently excluded**:
- Recurrent neural networks (LSTM, GRU)
- Gradient boosting decision trees (XGBoost, LightGBM)
- Classical autoregressive time-series models (ARIMA, SARIMAX)
- Specialized time-series Transformers (PatchTST, iTransformer)
- Time-series foundation models (Chronos, TimesFM)

---

## Tasks & Methodology

### 1. Mathematical Target Formalization
- **Primary Target (5-Trading-Day Ahead Log Return):**
  $$r_{t \to t+5} = \log\left(\frac{P_{t+5}}{P_t}\right)$$
- **Secondary Target (1-Trading-Day Ahead Log Return):**
  $$r_{t \to t+1} = \log\left(\frac{P_{t+1}}{P_t}\right)$$
- **Price Forecast Reconstruction:**
  $$\hat{P}_{t+H} = P_t \times \exp(\hat{r}_{t \to t+H})$$

### 2. Implement Simple Reference Baselines
- **Baseline 1 — Persistence / Random Walk:**
  $$\hat{r}_{\text{pers}, t \to t+H} = 0.0 \quad \implies \quad \hat{P}_{t+H} = P_t$$
  *Directional Accuracy Policy:* Because Persistence predicts a constant zero return, it makes no directional prediction (neither Up nor Down). Its Directional Accuracy is formally reported as **`N/A — zero-return forecast has no directional prediction`**. The raw zero-return match rate is tracked separately.
- **Baseline 2 — Historical Mean:**
  Calculated strictly from the backward rolling context window ($W=20$ trading days, past 19 daily returns):
  $$\bar{r}_{\text{daily}, t} = \frac{1}{W-1}\sum_{k=1}^{W-1} \log\left(\frac{P_{t-W+1+k}}{P_{t-W+k}}\right), \quad \hat{r}_{\text{mean}, t \to t+H} = H \times \bar{r}_{\text{daily}, t}$$
- **Baseline 3 — Moving Average (MA-5):**
  Calculated strictly from the most recent 5 daily returns inside the context window:
  $$\bar{r}_{\text{MA5}, t} = \frac{1}{5}\sum_{k=0}^{4} \log\left(\frac{P_{t-k}}{P_{t-k-1}}\right), \quad \hat{r}_{\text{MA5}, t \to t+H} = H \times \bar{r}_{\text{MA5}, t}$$
- **Baseline 4 — Drift:**
  Standard linear drift across the 20-day context window:
  $$\text{drift rate} = \frac{\log(P_t / P_{t-W+1})}{W - 1}, \quad \hat{r}_{\text{drift}, t \to t+H} = H \times \text{drift rate}$$

### 3. Verification of Historical Mean vs. Drift Exact Equality
As demonstrated analytically in `src/evaluation/test_verification_checks.py`, the exact equality between Historical Mean and Drift across point metrics (RMSE, MAE, MASE, Bias) is a **mathematical identity** arising from telescoping sums of log returns over the context window:
$$\sum_{k=1}^{W-1} \log\left(\frac{P_{t-W+1+k}}{P_{t-W+k}}\right) = \log\left(\prod_{k=1}^{W-1} \frac{P_{t-W+1+k}}{P_{t-W+k}}\right) = \log\left(\frac{P_t}{P_{t-W+1}}\right)$$
Dividing both expressions by $(W - 1)$ yields identical daily rates:
$$\bar{r}_{\text{daily}, t} \equiv \text{drift rate}_t \quad \implies \quad \hat{r}_{\text{mean}, t \to t+H} \equiv \hat{r}_{\text{drift}, t \to t+H}$$
Both models produce identical point forecasts by definition under this rolling window structure. Directional accuracy displays a minute difference (48.15% vs 48.04%) due strictly to floating-point rounding precision at the sign zero boundary ($10^{-16}$).

### 4. Rigorous MASE (Mean Absolute Scaled Error) Specification
To guarantee zero lookahead leakage into the MASE scaling denominator:
- **Numerator:** Mean Absolute Error (MAE) of the model's out-of-sample forecast on the split being evaluated:
  $$\text{MAE} = \frac{1}{N}\sum_{i=1}^N |y_i - \hat{y}_i|$$
- **Denominator:** Mean Absolute Error of the in-sample naive persistence forecast ($r=0$) computed **strictly on the training split** (`2022-03-01` to `2024-03-29`, $N=72,844$ samples):
  $$\text{In-Sample Naive MAE} = \frac{1}{N_{\text{train}}}\sum_{i=1}^{N_{\text{train}}} |y_{\text{train}, i}|$$
  - For $H=5$: Denominator = **0.038318**
  - For $H=1$: Denominator = **0.016040**
- **Leakage Protection:** The denominator is completely fixed and frozen on training data. Zero validation or test data is used.
- **Aggregation:** Pooled panel evaluation across the 146 core full-history tickers.

---

## Results

### A. Unit-Test Suite Verification
```text
Running evaluator and target reconstruction unit tests...
  [PASS] Perfect forecast test (MAE=0.0, RMSE=0.0, DA=100.0%)
  [PASS] Persistence relative RMSE test (RelRMSE = 1.0000)
  [PASS] Invalid prediction and replacement test (Valid %=50.0%, replacement MAE matches manual derivation)
  [PASS] Target construction and price reconstruction mathematical identity test (|P_reconstructed - P_future| < 1e-9)
All unit tests passed successfully!

Running analytical verification checks...
  [PASS] Telescoping identity between log return mean and price ratio slope (|diff| < 1e-15)
  [PASS] Analytical verification of in-sample MASE scaling denominator
```

---

### B. Baseline Evaluation Results — Validation Split (`2024-04-09` to `2024-10-31`, N = 20,781)

The validation split serves as our pre-declared model comparison benchmark:

| Horizon | Baseline Model | RMSE | MAE | Relative RMSE vs. Persistence | MASE | Directional Accuracy (%) | Bias | Valid Output % |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **H = 5** (Primary) | **Persistence (Random Walk)** | **0.093042** | **0.037751** | **1.0000** | **0.9852** | **N/A** (zero-return forecast) | -0.005136 | 100.0% |
| $H = 5$ | **Historical Mean (W=20)** | 0.105228 | 0.045683 | 1.1310 | 1.1922 | **48.15%** | +0.001144 | 100.0% |
| $H = 5$ | **Drift (W=20)** | 0.105228 | 0.045683 | 1.1310 | 1.1922 | 48.04% | +0.001144 | 100.0% |
| $H = 5$ | **Moving Average (MA-5)** | 0.133933 | 0.058190 | 1.4395 | 1.5186 | 47.74% | -0.000032 | 100.0% |
| **H = 1** (Secondary) | **Persistence (Random Walk)** | **0.043409** | **0.015667** | **1.0000** | **0.9767** | **N/A** (zero-return forecast) | -0.000877 | 100.0% |
| $H = 1$ | **Historical Mean (W=20)** | 0.044588 | 0.016836 | 1.0272 | 1.0496 | 46.94% | +0.000379 | 100.0% |
| $H = 1$ | **Drift (W=20)** | 0.044588 | 0.016836 | 1.0272 | 1.0496 | 47.18% | +0.000379 | 100.0% |
| $H = 1$ | **Moving Average (MA-5)** | 0.047725 | 0.018429 | 1.0994 | 1.1489 | **49.42%** | +0.000143 | 100.0% |

*Persistence raw zero-return hit rate (market sessions where return was exactly 0.0) was 4.88% for H=5 and 8.86% for H=1.*

---

### C. Locked Baseline Reference Results — Test Split (`2024-11-11` to `2025-05-30`, N = 19,130 for H=5; 19,714 for H=1)

*This out-of-sample test evaluation is recorded strictly as an unpeeking empirical anchor. No baseline parameters were selected or adjusted based on these scores.*

| Horizon | Baseline Model | RMSE | MAE | Relative RMSE vs. Persistence | MASE | Directional Accuracy (%) | Bias |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **H = 5** | **Persistence** | **0.088999** | **0.043154** | **1.0000** | **1.1262** | **N/A** (zero-return forecast) | +0.002729 |
| $H = 5$ | **Historical Mean** | 0.101753 | 0.052582 | 1.1433 | 1.3723 | 46.17% | -0.000910 |
| $H = 5$ | **Drift** | 0.101753 | 0.052582 | 1.1433 | 1.3723 | 46.42% | -0.000910 |
| $H = 5$ | **Moving Average (MA-5)** | 0.132908 | 0.067248 | 1.4934 | 1.7550 | **48.49%** | -0.000298 |
| **H = 1** | **Persistence** | **0.041838** | **0.017350** | **1.0000** | **1.0816** | **N/A** (zero-return forecast) | +0.000567 |
| $H = 1$ | **Historical Mean** | 0.043105 | 0.018763 | 1.0303 | 1.1697 | 45.70% | -0.000111 |
| $H = 1$ | **Drift** | 0.043105 | 0.018763 | 1.0303 | 1.1697 | 46.33% | -0.000111 |
| $H = 1$ | **Moving Average (MA-5)** | 0.046386 | 0.020706 | 1.1087 | 1.2909 | **48.39%** | -0.000039 |

---

## Baseline Comparison & Analysis

1. **Validation Champion:**
   - **Persistence (Random Walk)** is conclusively the strongest baseline on point accuracy across validation and test splits:
     - On Validation ($H=5$): $\text{RMSE} = 0.093042$, $\text{MAE} = 0.037751$, $\text{MASE} = 0.9852$.
     - Historical Mean and Drift incur a **13.1% penalty** in RMSE ($\text{RelRMSE} = 1.1310$).
     - Moving Average (MA-5) incurs a **44.0% penalty** in RMSE ($\text{RelRMSE} = 1.4395$).
2. **Directional Accuracy Performance:**
   - Persistence makes no directional call, reported as `N/A`.
   - Historical Mean and Drift achieve $\approx 48.1\%$ directional accuracy on validation, while Moving Average achieves $47.7\%–49.4\%$.
   - None of the simple statistical baselines exceed $50\%$ directional accuracy, demonstrating that simple linear or rolling momentum rules do not provide predictive edge over a coin flip.

---

## Interpretation — SIMPLE ENGLISH

### B. Easy Explanation
Think of Phase 04 as testing how well four simple, "common-sense" rules perform before we bring in any AI models:

1. **The Four Rules Tested:**
   - **Persistence (The "No Change" Guess):** Guess that next week's stock price will be identical to today's price (zero return). Because it predicts zero change, it doesn't take a stand on whether the stock will go Up or Down, so its directional accuracy is correctly marked as **N/A**.
   - **Historical Mean (The "Monthly Average" Guess):** Average the past month's daily moves and project that forward for 5 days.
   - **Moving Average (The "Recent Trend" Guess):** Look only at the last 5 days of momentum and assume that trend continues.
   - **Drift (The "Straight Line" Guess):** Draw a line from the price 20 days ago to today's price, and extend the slope forward.
2. **Why Historical Mean and Drift Produce the Exact Same Point Forecasts:**
   - In math, when you take the average of daily percentage changes over a 20-day window, all the intermediate days cancel each other out in what mathematicians call a "telescoping sum." The average daily move is mathematically identical to drawing a straight line from day 1 to day 20. That is why both rules produce the exact same error numbers.
   - We verified this with a synthetic test and proved that it is a mathematical identity, not a bug.
3. **Who Won?**
   - **Persistence (assuming no change) won easily on prediction accuracy.**
   - Rules that tried to chase short-term momentum had 13% to 44% higher error because stock prices bounce around with random noise.
4. **Directional Accuracy (Up vs. Down):**
   - The momentum rules only guessed whether a stock would go Up or Down correctly about **48% of the time** — worse than flipping a fair coin!
5. **Why This Matters for our AI Research:**
   - We now have the exact targets that our Small Language Models must beat:
     - Can the SLM beat the "No Change" rule ($\text{RMSE} < 0.093$ on validation)?
     - Can the SLM predict whether the stock will go Up or Down better than a 50% coin flip?

---

## Files Created / Updated
- `src/evaluation/evaluator.py` (Updated with Persistence DA `N/A` handling and MASE scaling)
- `src/evaluation/test_evaluator.py` (Unit tests)
- `src/evaluation/test_verification_checks.py` (Analytical verification of identity and MASE)
- `src/benchmark/run_baselines.py` (Baseline execution pipeline)
- `research/results/phase_04/baseline_config.json`
- `research/results/phase_04/baseline_metrics.json`
- `research/results/phase_04/baseline_sample_predictions.csv`
- `research/phases/phase_04_baselines.md`
- `research/RESEARCH_DECISIONS.md` (DEC-P04-001 updated)
- `research/PHASE_LOG.md`

---

## Reproducibility
- **Command:** `python3 src/benchmark/run_baselines.py`
- **Analytical Check Command:** `python3 src/evaluation/test_verification_checks.py`
- **Determinism:** 100% deterministic across all 112,755 rolling window samples.

---

## Gate Status
**PASS**
- Persistence Directional Accuracy correctly handled as N/A.
- Historical Mean vs Drift equivalence mathematically proven and verified.
- MASE denominator verified strictly on training data with zero leakage.
- Unit tests and analytical checks passed 100%.

---

## Next Step
Await user review. Upon authorization, proceed to **Phase 05: Zero-Shot SLM Benchmark and Backbone Selection**.
