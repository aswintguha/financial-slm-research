# Gate 5.6 Statistical Robustness Audit: SmolLM2 1.7B vs. Persistence Baseline

**Date:** 2026-11-17  
**Author:** Antigravity (Google DeepMind)  
**Investigation Scope:** Read-Only Statistical Robustness Audit of Phase 05 Gate 5.6 Full Validation Championship ($N=20,781$)  
**Focal Comparison:** `HuggingFaceTB/SmolLM2-1.7B-Instruct` vs. `Persistence Baseline` ($H=5$ log-return)  
**Status:** Completed & Validated  

---

## 1. Executive Summary & Audit Verification Checklist

In accordance with user authorization and governance mandates, this read-only audit examines the statistical robustness, distributional properties, market/ticker-level decomposition, and sample-level sensitivity of the Gate 5.6 zero-shot championship result.

Under the frozen selection protocol (**DEC-P05-001**), `SmolLM2-1.7B-Instruct` met the literal winner criteria by achieving **100.0% strict format validity** ($\ge 95.0\%$) and a persistence-replaced **RelRMSE of 0.999311** ($< 1.0000$). However, this in-depth audit reveals that the nominal 0.069% RMSE advantage is **not statistically significant**, does not hold uniformly across markets, and is entirely an artifact of a small cluster of extreme source-data quotation-scale jumps in South African ticker `EEL.JO`.

### Audit Checklist
- [x] **Paired Error Analysis:** Exact paired differences in squared error (SE) and absolute error (AE) computed for all 20,781 validation observations.
- [x] **Distributional Dominance:** Majority of validation observations ($51.81\%$) strictly favor the Persistence baseline; median paired difference favors Persistence.
- [x] **Market Breakdown:** SmolLM2 underperforms Persistence in the United States ($\text{RelRMSE} = 1.000533$). India is essentially flat ($\text{RelRMSE} = 0.999828$). The marginal overall advantage stems entirely from South Africa ($\text{RelRMSE} = 0.999094$).
- [x] **Statistical Uncertainty (Panel Block Bootstrap):** 2,000 iterations of a ticker-clustered, time-blocked ($L=5$ trading days) bootstrap yield a 95% confidence interval for RelRMSE of $[0.998501, 1.001935]$ ($p = 0.3650$). The advantage over persistence is statistically indistinguishable from zero.
- [x] **EEL.JO Quotation Scale Sensitivity:** Across all 20,781 observations, SmolLM2 reduces total squared error by $-0.247903$. The 5 known `EEL.JO` quotation-scale jump observations alone contribute $-0.351366$. When those 5 observations are excluded diagnostically ($N=20,776$), SmolLM2's RelRMSE rises to **1.000700** (underperforming Persistence).
- [x] **Directional Accuracy:** 49.03% on eligible non-zero returns ($9,675 / 19,733$), which is below random chance (50.0%).
- [x] **Integrity Preserved:** Official full-cohort metrics ($N=20,781$) remain intact. No datasets, predictions, manifests, or Phase 03/04 artifacts were modified.

---

## 2. Full Paired Error Analysis ($N=20,781$)

To evaluate whether the model provides a genuine systematic reduction in forecast error, we analyze the per-observation paired differences between SmolLM2 1.7B ($y_{s,i}$) and Persistence ($y_{p,i} = 0.0$) against realized 5-day log-returns ($y_{i}$):
$$\Delta \text{SE}_i = (y_i - y_{s,i})^2 - (y_i - y_{p,i})^2$$
$$\Delta \text{AE}_i = |y_i - y_{s,i}| - |y_i - y_{p,i}|$$
*Note: A negative difference indicates that SmolLM2 has a smaller error (favors SmolLM2).*

### 2.1 Global Cohort Metrics & Paired Statistics

| Metric | Persistence Baseline | SmolLM2 1.7B Instruct | Paired Difference (Smol - Pers) | Interpretation |
| :--- | :--- | :--- | :--- | :--- |
| **Cohort Size ($N$)** | 20,781 | 20,781 | — | Full validation cohort |
| **Strict Validity** | 100.0% | 100.0% | 0.0% | Exact JSON format compliance |
| **RMSE** | **0.093042** | **0.092978** | **-0.000064** (-0.069%) | Nominal edge for SmolLM2 |
| **MAE** | **0.037751** | **0.038015** | **+0.000264** (+0.70%) | **Favors Persistence** |
| **RelRMSE** | 1.000000 | **0.999311** | -0.000689 | Protocol Winner threshold (<1.0) |
| **Total Sum of Squared Error** | 179.896959 | 179.649056 | -0.247903 | Aggregate squared error gap |
| **Mean Paired $\Delta \text{SE}$** | — | — | $-1.1929 \times 10^{-5}$ | Mean pulled negative by outliers |
| **Median Paired $\Delta \text{SE}$** | — | — | **$+1.7940 \times 10^{-7}$** | **Favors Persistence** |
| **Mean Paired $\Delta \text{AE}$** | — | — | $+2.6352 \times 10^{-4}$ | Favors Persistence |
| **Median Paired $\Delta \text{AE}$** | — | — | **$+1.0000 \times 10^{-4}$** | **Favors Persistence** |

### 2.2 Observation Win / Loss / Tie Distribution

Across the 20,781 validation samples:
- **Persistence Wins:** **10,766 observations (51.81%)**
- **SmolLM2 Wins:** **9,565 observations (46.03%)**
- **Exact Ties:** **450 observations (2.17%)** (where $y_i = 0.0$ and SmolLM2 predicted $0.0$)

> [!IMPORTANT]
> On more than **51.8%** of validation instances, Persistence produces a more accurate forecast than SmolLM2 1.7B. Both the median squared error difference and median absolute error difference are strictly positive, demonstrating that SmolLM2's aggregate RMSE edge is driven by high-leverage tail events rather than typical forecasting skill.

---

## 3. Geographic and Asset-Level Breakdown

### 3.1 Market Breakdown

| Market / Country | Samples ($N$) | Persistence RMSE | SmolLM2 RMSE | RelRMSE | Persistence MAE | SmolLM2 MAE | SmolLM2 Wins | Persistence Wins | Ties |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **India (`.BSE`)** | 6,861 | 0.050004 | 0.049996 | **0.999828** | 0.035274 | 0.035365 | 3,375 (49.19%) | 3,486 (50.81%) | 0 |
| **South Africa (`.JO`)** | 6,864 | 0.145043 | 0.144911 | **0.999094** | 0.042833 | 0.043513 | 2,699 (39.32%) | 3,715 (54.12%) | 450 |
| **United States** | 7,056 | 0.050983 | 0.051011 | **1.000533** | 0.035217 | 0.035243 | 3,491 (49.48%) | 3,565 (50.52%) | 0 |

**Observations from Market Breakdown:**
1. **United States:** Zero-shot SmolLM2 underperforms Persistence on both RMSE ($\text{RelRMSE} = 1.000533$) and MAE. In 50.52% of US trading windows, Persistence is superior.
2. **India:** Essentially flat parity ($\text{RelRMSE} = 0.999828$, an RMSE difference of only 8 parts per million), with Persistence winning 50.81% of observations and showing lower MAE.
3. **South Africa:** Shows the lowest RelRMSE (0.999094), yet has the **worst win-rate for SmolLM2** (only 39.32% wins vs. 54.12% for Persistence). The aggregate RMSE reduction in South Africa is overwhelmingly dominated by a single ticker (`EEL.JO`).

### 3.2 Ticker-Level Decomposition (146 Tickers)

Across all 146 unique tickers in the validation set:
- **Tickers favoring SmolLM2 (Net $\Delta \text{SE} < 0$):** **73 tickers (50.0%)**
- **Tickers favoring Persistence (Net $\Delta \text{SE} > 0$):** **73 tickers (50.0%)**

The distribution of ticker advantage is perfectly split 50/50. However, the magnitude of squared-error reduction is heavily concentrated in a single ticker:

| Ticker | Market | $N$ | Persistence RMSE | SmolLM2 RMSE | RelRMSE | Total $\Delta \text{SE}$ | W / L / T |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **EEL.JO** | South Africa | 143 | **0.8653** | **0.8640** | **0.998482** | **-0.324949** | 11 / 90 / 42 |
| `MTNL.BSE` | India | 140 | 0.1300 | 0.1296 | 0.996354 | -0.017234 | 76 / 64 / 0 |
| `TSLA` | US | 144 | 0.0934 | 0.0928 | 0.993896 | -0.015286 | 69 / 75 / 0 |
| `OBEROIRLTY.BSE` | India | 140 | 0.0510 | 0.0501 | 0.981307 | -0.013489 | 79 / 61 / 0 |
| `PPR.JO` | South Africa | 143 | 0.0395 | 0.0383 | 0.970238 | -0.013053 | 42 / 100 / 1 |

Notice that `EEL.JO` alone accounts for **$-0.324949$** in squared error difference—exceeding the net global advantage of SmolLM2 across the entire 20,781-sample benchmark ($-0.247903$).

---

## 4. EEL.JO Quotation Scale Sensitivity Analysis

In Gate 5.4, an independent investigation confirmed that South African ticker `EEL.JO` experienced a quotation-scale transition from cents to rands (a $100\times$ shift, yielding realized 5-day log-returns of $r = \ln(100) \approx +4.60517$). Five validation samples span this quotation jump:

### 4.1 The Five Quotation Jump Samples

| Sample ID | Origin Date | Target Date | Realized $r_{H=5}$ | SmolLM2 Pred | Pers Squared Error | SmolLM2 Squared Error | $\Delta \text{SE}$ (Smol - Pers) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `VAL_06479` | 2024-07-03 | 2024-07-10 | +4.60517 | +0.01250 | 21.20759 | 21.09262 | -0.114973 |
| `VAL_06480` | 2024-07-04 | 2024-07-11 | +4.60517 | +0.00010 | 21.20759 | 21.20667 | -0.000921 |
| `VAL_06481` | 2024-07-05 | 2024-07-12 | +4.60517 | +0.01250 | 21.20759 | 21.09262 | -0.114973 |
| `VAL_06482` | 2024-07-08 | 2024-07-15 | +4.60517 | +0.00060 | 21.20759 | 21.20206 | -0.005526 |
| `VAL_06483` | 2024-07-09 | 2024-07-16 | +4.60517 | +0.01250 | 21.20759 | 21.09262 | -0.114973 |
| **Sum** | — | — | — | — | **106.03795** | **105.68658** | **-0.351366** |

Because SmolLM2 happened to output slightly positive numbers (+0.01250 and +0.00060) on an extreme outlier where the true return was +4.60517, $(4.60517 - 0.0125)^2 = 21.0926$ vs. $4.60517^2 = 21.2076$, generating a large squared-error reduction purely due to quadratic scaling on a non-market data anomaly.

### 4.2 Sensitivity Cohort Comparisons

To test sensitivity without altering the official result, metrics were recomputed under two diagnostic exclusion subsets:

| Cohort | Samples ($N$) | Persistence RMSE | SmolLM2 RMSE | Persistence MAE | SmolLM2 MAE | Diagnostic RelRMSE | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Official Cohort (Full)** | **20,781** | **0.093042** | **0.092978** | **0.037751** | **0.038015** | **0.999311** | **Primary Official Result** |
| **Excluding 5 Quotation Jumps** | 20,776 | 0.059624 | 0.059666 | 0.036652 | 0.036918 | **1.000700** | Diagnostic Sensitivity |
| **Excluding All `EEL.JO`** | 20,638 | 0.059399 | 0.059430 | 0.036692 | 0.036920 | **1.000529** | Diagnostic Sensitivity |

> [!CAUTION]
> When the five known quotation-jump observations are excluded, SmolLM2's RelRMSE increases from **0.999311** to **1.000700**, reversing the advantage and demonstrating net underperformance relative to Persistence. On the remaining 20,776 observations, Persistence has both lower RMSE and lower MAE.

---

## 5. Statistical Uncertainty & Panel Block Bootstrap

### 5.1 Resampling Design
Financial panel validation data exhibits two forms of statistical dependence:
1. **Cross-Sectional Clustering:** Repeated observations across 146 individual tickers.
2. **Serial Autocorrelation:** Overlapping 5-day forecast horizons ($H=5$).

To account for both dependencies without making unrealistic i.i.d. assumptions:
- **Resampling Unit:** Tickers are resampled with replacement ($N_{\text{clusters}} = 146$).
- **Time Blocking:** Within each sampled ticker, the chronological series is partitioned into contiguous blocks of $L=5$ trading days (matching the forecast horizon length). Blocks are resampled with replacement to preserve short-term serial correlation.
- **Iterations:** $B = 2,000$ bootstrap replications.

### 5.2 Bootstrap Estimation Results

| Parameter | Observed Sample Statistic | Bootstrap Mean | Bootstrap Std Err | 95% Bootstrap CI | Empirical $p$-value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **RMSE Difference ($\Delta \text{RMSE}$)** | -0.000064 | -0.000040 | 0.000089 | **[-0.000209, +0.000114]** | $p = 0.3650$ ($H_0: \Delta \ge 0$) |
| **RelRMSE (Full $N=20,781$)** | 0.999311 | 0.999777 | 0.000882 | **[0.998501, 1.001935]** | $p = 0.3650$ ($H_0: \text{Rel} \ge 1$) |
| **MAE Difference ($\Delta \text{MAE}$)** | +0.000264 | +0.000271 | 0.000079 | **[+0.000119, +0.000429]** | $p < 0.0001$ ($H_0: \Delta \le 0$) |
| **RelRMSE (Excl. 5 Jumps, $N=20,776$)** | 1.000700 | 1.000685 | 0.000923 | **[0.998858, 1.002467]** | $p = 0.7815$ ($H_0: \text{Rel} \ge 1$) |

**Statistical Findings:**
- The 95% confidence interval for RelRMSE on the full cohort **spans 1.0000** ($[0.998501, 1.001935]$).
- The one-sided empirical p-value testing whether SmolLM2 significantly outperforms persistence is **0.3650**, far above conventional significance thresholds ($\alpha = 0.05$).
- Conversely, SmolLM2's MAE degradation ($+0.000264$) is highly statistically significant ($p < 0.0001$), with the entire 95% CI strictly positive.

---

## 6. Error Distribution & Quantile Profile

### 6.1 Quantiles of Absolute and Squared Error

| Quantile | Persistence Absolute Error | SmolLM2 Absolute Error | $\Delta \text{AE}$ (Smol - Pers) | Persistence Squared Error | SmolLM2 Squared Error | $\Delta \text{SE}$ (Smol - Pers) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **p25** | 0.009924 | 0.010797 | +0.000873 | $9.8486 \times 10^{-5}$ | $1.1658 \times 10^{-4}$ | $+1.8089 \times 10^{-5}$ |
| **p50 (Median)** | 0.024372 | 0.024533 | **+0.000161** | $5.9399 \times 10^{-4}$ | $6.0187 \times 10^{-4}$ | **$+7.8737 \times 10^{-6}$** |
| **p75** | 0.047006 | 0.047163 | +0.000157 | $2.2096 \times 10^{-3}$ | $2.2243 \times 10^{-3}$ | $+1.4785 \times 10^{-5}$ |
| **p90** | 0.080294 | 0.080522 | +0.000228 | $6.4471 \times 10^{-3}$ | $6.4838 \times 10^{-3}$ | $+3.6666 \times 10^{-5}$ |
| **p95** | 0.110810 | 0.111130 | +0.000320 | $1.2279 \times 10^{-2}$ | $1.2350 \times 10^{-2}$ | $+7.1021 \times 10^{-5}$ |
| **p99** | 0.223148 | 0.224344 | +0.001196 | $4.9795 \times 10^{-2}$ | $5.0330 \times 10^{-2}$ | $+5.3529 \times 10^{-4}$ |

At every evaluated quantile (p25, p50, p75, p90, p95, p99), SmolLM2 has **strictly larger absolute and squared errors** than Persistence. 

### 6.2 Directional Accuracy Audit

- **Total Samples:** 20,781
- **Realized Zero Returns ($r = 0.0$):** 1,048 samples (directionally undefined)
- **Eligible Non-Zero Denominator:** **19,733 samples**
- **SmolLM2 Correct Directional Predictions:** 9,675 samples
- **Directional Accuracy:** **49.03%**

SmolLM2 1.7B's directional accuracy on non-zero returns is slightly below 50.0%, confirming the absence of directional edge in zero-shot forecasts.

---

## 7. Synthesis and Formal Interpretation

To ensure scientific rigor, we explicitly distinguish between protocol adherence, statistical inference, and economic value:

1. **Protocol Decision (DEC-P05-001):**
   - The frozen selection rule states: *Eligibility requires strict validity $\ge 95\%$, and forecasting winner requires persistence-replaced $\text{RelRMSE} < 1.0000$ on the official validation cohort.*
   - `SmolLM2-1.7B-Instruct` achieved 100.0% strict validity and official RelRMSE of 0.999311.
   - **Formally, under the locked decision rule, SmolLM2 1.7B is the Gate 5.6 protocol winner.** The frozen rule is respected and not retroactively altered.

2. **Statistical Evidence:**
   - There is **no statistical evidence** that SmolLM2 1.7B has genuine forecasting superiority over the persistence baseline.
   - The paired t-test / panel block bootstrap 95% confidence interval spans 1.0000 ($p = 0.3650$).
   - Over 51.8% of observations favor Persistence. Median error differences favor Persistence. All error quantiles favor Persistence.
   - The 0.069% RMSE advantage is entirely eliminated when removing five known non-market quotation-jump samples in `EEL.JO`.

3. **Economic and Practical Forecasting Reality:**
   - Zero-shot LLMs/SLMs prompted with raw numerical price series exhibit near-zero forecasting capability out of the box, predicting values close to zero with slight noise that degrades MAE.
   - The model should not be considered an effective zero-shot financial forecaster in production without substantial domain adaptation.

4. **Recommendation for Phase 06 (Supervised Fine-Tuning):**
   - `SmolLM2-1.7B-Instruct` remains an excellent architectural backbone for fine-tuning due to:
     - 100.0% strict format compliance (zero formatting failure out of 20,781 samples).
     - Fast inference throughput and memory efficiency.
     - Strong prompt adherence and clean instruction-following.
   - The justification for advancing SmolLM2 1.7B to SFT should be framed as **instruction adherence and format stability**, rather than proven zero-shot predictive alpha.

---

## 8. Artifact and Dataset Invariance

- **Phase 03/04 Artifacts:** Fully verified, unedited, and unchanged.
- **Validation Dataset:** All 20,781 observations, sample IDs, and prices preserved in official records.
- **Git State:** Clean on branch `phase-05-zero-shot`.

