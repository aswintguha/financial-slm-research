# Phase 05 Research Handoff & Replication Guide

**Project:** Empirical SLM Financial Time-Series Forecasting Benchmark  
**Phase:** Phase 05 — Zero-Shot SLM Benchmark & Backbone Selection  
**Branch:** `phase-05-zero-shot`  
**Date:** 2026-11-17  
**Status:** Completed & Validated (Ready for Phase 06 SFT scoping)  

---

## 1. Executive Summary & Research State

This document provides complete instructions for researchers to replicate, verify, and extend Phase 05 results directly from the `phase-05-zero-shot` branch.

In Phase 05, we conducted a rigorous, zero-shot financial forecasting benchmark across 10 small language models ($\le 4\text{B}$ parameters) on international equity market data (India, South Africa, and the United States). All benchmarking conformed to the locked protocol (**DEC-P05-001**) and the updated [research/MASTER_RESEARCH_PLAN.md](file:///Users/aryakpal/financial-slm-research/research/MASTER_RESEARCH_PLAN.md).

### Completed Research Gates
1. **Gate 5.0 (Data & Hardware Integrity):** Raw and processed dataset SHA256 verification against Phase 03/04 baselines. Stage A MPS bfloat16 hardware validation.
2. **Gate 5.1 (Prompt & Strict Parser Protocol):** Standardized Template A prompt, strict regex parser (`[FORECAST: <value>]`), and native chat-template enforcement.
3. **Gate 5.2 (Sampling & Smoke Test):** Deterministic greedy decoding verification on `SmolLM2-135M-Instruct` (zero variance across repeated runs).
4. **Gate 5.3 (Sensitivity Analysis E02):** Evaluated 3 prompt templates $\times$ 2 numerical representations across 60 samples (360 total generations). Template A (Direct Horizon Log-Return) established as the most stable formulation.
5. **Gate 5.4 (Screening Benchmark):** Evaluated all 10 candidate models on the stratified 420-sample cohort ($4,200$ inferences). 6 models met the Tier 1 screening eligibility ($\ge 90.0\%$ strict validity). 4 models failed (135M, 360M, Llama 1B, Phi-3.5 mini).
6. **Gate 5.4 Independent Audit & Investigation:** Traced quotation-scale redenomination ($100\times$ jump) in South African ticker `EEL.JO` (`SCREEN_189`). Verified persistence baseline RMSE ($0.232462$) and corrected undefined division-by-zero RelRMSE metrics.
7. **Gate 5.5/5.6 Preflight:** Checkpoint, disk, and configuration readiness verified for the full validation cohort ($N=20,781$).
8. **Gate 5.6 (Full Validation Championship Benchmark):** Evaluated all 6 qualifying models across all $N=20,781$ validation samples ($124,686$ total inferences).
9. **Gate 5.6 Statistical Robustness Audit:** Comprehensive paired-error, block-bootstrap, market-level, and sensitivity analysis of candidate winner `SmolLM2-1.7B-Instruct`.

> [!IMPORTANT]
> **Strict Authorization Scope Boundaries:**
> - Phase 06 Supervised Fine-Tuning (SFT) has **NOT** been authorized or initiated.
> - The locked test set (`2024-11-11` to `2025-05-30`) remains completely untouched and has **NOT** been accessed.

---

## 2. Final Benchmark Results

### 2.1 Gate 5.4 Screening Benchmark ($N=420$)

| Rank | Model Name | Parameters | Strict Validity | Valid RelRMSE | Persistence-Replaced RelRMSE | Status |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| 1 | `Qwen/Qwen2.5-0.5B-Instruct` | 0.49B | **100.0%** | 0.999676 | **0.999676** | Qualified for Gate 5.6 |
| 2 | `Qwen/Qwen2.5-1.5B-Instruct` | 1.54B | **100.0%** | 0.999719 | **0.999719** | Qualified for Gate 5.6 |
| 3 | `HuggingFaceTB/SmolLM2-1.7B-Instruct` | 1.71B | **100.0%** | 1.000004 | **1.000004** | Qualified for Gate 5.6 |
| 4 | `meta-llama/Llama-3.2-3B-Instruct` | 3.21B | **98.81%** | 1.001691 | **1.001691** | Qualified for Gate 5.6 |
| 5 | `Qwen/Qwen2.5-3B-Instruct` | 3.09B | **99.76%** | 1.002237 | **1.002237** | Qualified for Gate 5.6 |
| 6 | `google/gemma-2-2b-it` | 2.61B | **100.0%** | 1.005167 | **1.005167** | Qualified for Gate 5.6 |
| 7 | `microsoft/Phi-3.5-mini-instruct` | 3.82B | 16.43% | 0.994539 | 1.002826 | Disqualified (<90% validity) |
| 8 | `HuggingFaceTB/SmolLM2-360M-Instruct` | 0.36B | 1.19% | N/A* | 1.000000 | Disqualified (<90% validity) |
| 9 | `meta-llama/Llama-3.2-1B-Instruct` | 1.23B | 0.00% | N/A | 1.000000 | Disqualified (<90% validity) |
| 10 | `HuggingFaceTB/SmolLM2-135M-Instruct` | 0.13B | 0.00% | N/A | 1.000000 | Disqualified (<90% validity) |

*\*Note: Valid RelRMSE for SmolLM2 360M is mathematically undefined (N/A) because all 5 valid predictions coincided with zero realized returns.*

### 2.2 Gate 5.6 Full Validation Championship ($N=20,781$)

*Ground Truth Persistence Baseline ($H=5$):* $\text{RMSE} = 0.093042, \text{MAE} = 0.037751$.

| Rank | Model Candidate | Strict Validity | Valid RelRMSE | Replaced RelRMSE | Replaced RMSE | Replaced MAE | DA (%) | Protocol Status |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **1** | **`HuggingFaceTB/SmolLM2-1.7B-Instruct`** | **100.0%** | **0.999311** | **0.999311** | **0.092978** | 0.038015 | 49.03% | **Forecasting Winner** |
| 2 | `google/gemma-2-2b-it` | 100.0% | 1.002416 | 1.002416 | 0.093267 | 0.038545 | 53.37% | Eligible Contender |
| 3 | `Qwen/Qwen2.5-0.5B-Instruct` | 100.0% | 1.003054 | 1.003054 | 0.093326 | 0.038301 | 46.33% | Eligible Contender |
| 4 | `meta-llama/Llama-3.2-3B-Instruct` | 99.47% | 1.005678 | 1.005648 | 0.093567 | 0.039299 | 53.08% | Eligible Contender |
| 5 | `Qwen/Qwen2.5-1.5B-Instruct` | 100.0% | 1.013122 | 1.013122 | 0.094263 | 0.040143 | 46.30% | Eligible Contender |
| 6 | `Qwen/Qwen2.5-3B-Instruct` | 99.99% | 1.025272 | 1.025265 | 0.095393 | 0.042093 | 46.23% | Eligible Contender |

---

## 3. Critical Scientific Caveats & Robustness Findings

While `SmolLM2-1.7B-Instruct` formally satisfies the frozen winner rule (`valid_pct >= 95%` and `RelRMSE_replaced < 1.0000`), the comprehensive statistical robustness audit ([research/results/phase_05/gate_5_6_robustness_audit.md](file:///Users/aryakpal/financial-slm-research/research/results/phase_05/gate_5_6_robustness_audit.md)) reveals critical nuances that the research partner must understand:

1. **Statistical Insignificance:**
   - A 2,000-iteration ticker-clustered and time-blocked bootstrap ($L=5$ trading days) yields a 95% CI for RelRMSE of **$[0.998501, 1.001935]$** ($p = 0.3650$). The nominal 0.069% RMSE advantage is statistically indistinguishable from zero.
2. **Majority Persistence Dominance:**
   - In paired error analysis, **Persistence wins on 51.81% of samples** (10,766 vs. 9,565 for SmolLM2). Both median squared-error difference ($+1.794 \times 10^{-7}$) and median absolute-error difference ($+1.000 \times 10^{-4}$) favor Persistence.
3. **EEL.JO Data-Quality Distortion:**
   - South African ticker `EEL.JO` experienced a quotation-scale transition from cents to rands (a $100\times$ jump yielding $r \approx 4.60517$).
   - Across all 20,781 observations, SmolLM2's total squared-error reduction is $-0.247903$. The 5 quotation-jump samples alone contribute **$-0.351366$** purely due to quadratic scaling.
   - When those 5 observations are excluded diagnostically ($N=20,776$), SmolLM2's RelRMSE rises to **1.000700** (underperforming Persistence).
4. **Proposed Research Backbone Rationale:**
   - `SmolLM2-1.7B-Instruct` is recommended as the research backbone for Phase 06 SFT based on **100.0% instruction and format compliance, high inference throughput, and compact size**, rather than any claim of pre-existing zero-shot predictive alpha.

---

## 4. Exact Model Revisions

All models evaluated in Gate 5.6 were fetched from Hugging Face Hub using the following resolved commit SHAs:

| Model Roster Name | Hugging Face Repository ID | Resolved Commit SHA |
| :--- | :--- | :--- |
| **SmolLM2 1.7B Instruct** | `HuggingFaceTB/SmolLM2-1.7B-Instruct` | `31b70e2e869a7173562077fd711b654946d38674` |
| **Qwen 2.5 0.5B Instruct** | `Qwen/Qwen2.5-0.5B-Instruct` | `7ae557604adf67be50417f59c2c2f167def9a775` |
| **Qwen 2.5 1.5B Instruct** | `Qwen/Qwen2.5-1.5B-Instruct` | `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` |
| **Qwen 2.5 3B Instruct** | `Qwen/Qwen2.5-3B-Instruct` | `aa8e72537993ba99e69dfaafa59ed015b17504d1` |
| **Gemma 2 2B IT** | `google/gemma-2-2b-it` | `299a8560bedf22ed1c72a8a11e7dce4a7f9f51f8` |
| **Llama 3.2 3B Instruct** | `meta-llama/Llama-3.2-3B-Instruct` | `0cb88a4f764b7a12671c53f0838cd831a0843b95` |

---

## 5. Dataset Requirements & Verification

Per project policy, raw and processed tabular datasets in `data/` are not tracked in Git to maintain repository efficiency. Replicating the benchmark requires placing the datasets in the directory structure below and verifying their SHA256 hashes against `configs/dataset_integrity_manifest.json`:

```
data/
├── raw/
│   ├── Indian-Final-Data-3month.xlsx  (SHA256: 423c3d3590fead9a009741a7cd1850b5a53ee98152dbb4a44da5744dad120f0c)
│   ├── JSE_data.csv                   (SHA256: 069ae3994735b6eece45b2deaab63e6b660731bc6c28b803239ee9ec37cca9ff)
│   └── US_data.csv                    (SHA256: 942dee898f6caeb20d6b8ec41e81118e38509813d2712e15ef370d64d1a5e999)
└── processed/
    ├── global_equities_common.csv     (SHA256: ac57727f389c6bcdd641b172b8689aaceb127ab8a94c47fc0e29b4ea17605526)
    ├── india_equities_clean.csv       (SHA256: f85801e84b7d8bf04cccc80b594f538380ae88b4a3e698f51d1f142ddf8a58b9)
    ├── jse_equities_clean.csv         (SHA256: 05d7e861923c24a89ec8d6fac2cac4e46ac2c199eee68a833e3a19f7a4f73e88)
    └── us_equities_clean.csv          (SHA256: e9713b1efbf3e928e71f3d5015a6309d1774c520bc7bdbb5b9fec410dfcd37b9)
```

Verification command:
```bash
shasum -a 256 data/raw/* data/processed/*
```

---

## 6. Environment & Hardware Setup

- **Python Version:** `Python 3.12.x` (Recommended: `3.12.16`)
- **PyTorch & Accelerators:** `torch==2.5.1`, `transformers==4.46.2`, `accelerate==1.1.1`
- **Execution Target:** Apple Silicon (`mps`) or Linux (`cuda`). All benchmark runs were executed on Apple Silicon MPS using `bfloat16`.
- **Reproducibility Controls:**
  - Greedy decoding (`temperature=0.0`, `do_sample=False`, `top_p=1.0`).
  - Batch size: `1`.
  - Max generated tokens: `32`.
  - Format constraint: Template A with `[FORECAST: <number>]`.

Setup environment:
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # Or install torch, transformers, accelerate, pyyaml, tqdm
```

---

## 7. How to Reproduce Benchmark Results

### 7.1 Verify Prompts and Output Parser
```bash
.venv/bin/python src/benchmark/test_prompt_and_parser.py
```

### 7.2 Run Gate 5.4 Screening Benchmark (420 samples)
```bash
.venv/bin/python src/benchmark/run_gate_5_4_screening.py
```
Outputs are written to `research/results/phase_05/gate_5_4_*`.

### 7.3 Run Gate 5.6 Full Validation Evaluation (20,781 samples)
```bash
.venv/bin/python src/benchmark/run_gate_5_6_validation.py
```
This script evaluates each model sequentially with incremental checkpointing every 500 samples.

---

## 8. Next Steps & Scope Boundaries

### Immediate Next Steps for Research Partner:
1. Review [research/results/phase_05/gate_5_6_robustness_audit.md](file:///Users/aryakpal/financial-slm-research/research/results/phase_05/gate_5_6_robustness_audit.md) and [research/RESEARCH_DECISIONS.md](file:///Users/aryakpal/financial-slm-research/research/RESEARCH_DECISIONS.md) (Decision **DEC-P05-001**).
2. Formulate the Phase 06 Supervised Fine-Tuning (SFT) preflight protocol for `SmolLM2-1.7B-Instruct` (LoRA/QLoRA vs. Full Fine-Tuning, learning rate, target modules, context formatting).
3. Obtain explicit stakeholder authorization before launching any training or touching the test split.
