# Preflight Audit & Execution Plan: Phase 05 Gate 5.5 / 5.6 Full-Validation Evaluation

**Preflight Execution Date:** 2026-11-15T18:25:00Z  
**Branch:** `phase-05-zero-shot`  
**Purpose:** Comprehensive preflight verification for the full validation split evaluation ($N=20,781$) across the six Gate 5.4 qualifying models.  
**Strict Policy Constraint:** Read-only audit only. No inference executed, no model fine-tuning, no git commits.

---

## 1. Qualifying Candidate Models & Local Checkpoint Availability

All six models that passed the Gate 5.4 Screening Threshold ($\ge 90.0\%$ strict validity) are fully downloaded, verified, and cached locally in `~/.cache/huggingface/hub/`.

| # | Model Name | Hugging Face Repo ID | Resolved Commit SHA | Parameter Count | License | Screening Validity (%) | Local Cache Status |
| :---: | :--- | :--- | :---: | :---: | :--- | :---: | :---: |
| 1 | **Qwen 2.5 0.5B Instruct** | `Qwen/Qwen2.5-0.5B-Instruct` | `7ae557604adf67be50417f59c2c2f167def9a775` | 494,032,768 | Apache-2.0 | 100.0% | **Cached locally** |
| 2 | **Qwen 2.5 1.5B Instruct** | `Qwen/Qwen2.5-1.5B-Instruct` | `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` | 1,543,714,304 | Apache-2.0 | 100.0% | **Cached locally** |
| 3 | **SmolLM2 1.7B Instruct** | `HuggingFaceTB/SmolLM2-1.7B-Instruct` | `31b70e2e869a7173562077fd711b654946d38674` | 1,711,376,384 | Apache-2.0 | 100.0% | **Cached locally** |
| 4 | **Gemma 2 2B IT** | `google/gemma-2-2b-it` | `299a8560bedf22ed1c72a8a11e7dce4a7f9f51f8` | 2,614,341,888 | Gemma Terms | 100.0% | **Cached locally** |
| 5 | **Qwen 2.5 3B Instruct** | `Qwen/Qwen2.5-3B-Instruct` | `aa8e72537993ba99e69dfaafa59ed015b17504d1` | 3,085,938,688 | Qwen Research | 100.0% | **Cached locally** |
| 6 | **Llama 3.2 3B Instruct** | `meta-llama/Llama-3.2-3B-Instruct` | `0cb88a4f764b7a12671c53f0838cd831a0843b95` | 3,212,749,824 | Llama 3.2 | 99.8% | **Cached locally** |

*Disqualified Models from Gate 5.4:*
- `SmolLM2-135M-Instruct` (0.0% valid)
- `Llama-3.2-1B-Instruct` (0.0% valid)
- `SmolLM2-360M-Instruct` (1.2% valid)
- `Phi-3.5-mini-instruct` (16.4% valid)

---

## 2. Full Validation Cohort Integrity & Baseline Verification

- **Validation Split Definition (DEC-P03-001):**
  `2024-04-09` to `2024-10-31` (~7 months, following Purge Gap 1).
- **Cohort Size:** Exactly **$N = 20,781$** samples across all 150 tickers (146 Core Universe + 4 Secondary Universe).
- **Sample Invariance Check:**
  - Audited against `research/results/phase_04/baseline_sample_predictions.csv` (20,781 validation rows).
  - Every sample specifies: `ticker`, `sector`, `country`, `origin_date`, `target_date`, `origin_price`, `target_price`, and `actual_target_log_return`.
- **Frozen Persistence Baseline (Random Walk $H=5$):**
  - Validation Persistence RMSE: **`0.093042`**
  - Validation Persistence MAE: **`0.037751`**
  - Verified mathematically: $\sqrt{\frac{1}{20781} \sum_{i=1}^{20781} y_i^2} \equiv \mathbf{0.093042}$. Matches `research/results/phase_04/baseline_metrics.json` bit-for-bit.

---

## 3. Data Caveat Trace: Sample `SCREEN_189` and `EEL.JO` in Validation

- **Forensic Audit Finding:**
  The $100\times$ quote redenomination error for `EEL.JO` (0.12 to 12.0) identified in Gate 5.4 occurred on `2024-07-10`.
- **Validation Split Overlap:**
  Because the validation period runs through October 2024, exactly 5 rolling-origin samples for `EEL.JO` span the `2024-07-10` boundary where origin close is `0.12` and target close is `12.0` ($r = 4.60517$).
- **Protocol Treatment Consistency:**
  - In Phase 04, the baseline evaluator scored these observations as part of the full validation partition, producing the frozen validation persistence benchmark $\text{RMSE} = 0.093042$.
  - Per DEC-P05-001, **zero samples will be altered, removed, or winsorized**. The candidate SLMs will be evaluated on the exact, identical 20,781 validation samples scored in Phase 04.

---

## 4. Frozen Protocol Rules & Thresholds

1. **Prompt Template:**
   Frozen primary **Template A** only (`past_prices` formatted to 2 decimals, soliciting 5-day cumulative log return).
2. **Native Chat Template:**
   Direct token-ID generation via `tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True)`.
3. **Deterministic Decoding:**
   Greedy decoding (`do_sample=False`, `temperature=None`), `max_new_tokens=32`, `torch.bfloat16` on Apple Silicon MPS, `batch_size=1`.
4. **Strict Output Parser:**
   Case-sensitive regex: `r'^\s*\[FORECAST:\s*([+-]?\d+(?:\.\d+)?)\]\s*$'`.
5. **Tier 2 Eligibility Gate (Gate 5.6):**
   A candidate model must achieve **$\ge 95.0\%$ strict validity** across all 20,781 validation samples. Models falling below 95.0% are disqualified from selection.
6. **Winning Backbone Declaration Rule:**
   - **Forecasting Winner:** A candidate must achieve `valid_pct >= 95.0%` AND `RelRMSE_replaced < 1.0000` (beating Persistence RMSE $0.093042$).
   - **SFT Research Candidate:** If eligible models exist ($\ge 95.0\%$ valid) but none beats Persistence ($\text{RelRMSE}_{\text{replaced}} \ge 1.0000$), the top model is classified strictly as an **SFT research candidate** for Phase 06 fine-tuning, with the explicit published finding that no zero-shot SLM beat random walk.
   - **No Eligible Backbone Found:** If no model satisfies $\ge 95.0\%$ strict validity, the protocol halts with a formal *No Eligible Backbone Found* declaration.

---

## 5. Resource Requirements & Sequential Execution Plan

### 5.1 Measured Hardware Throughput & Runtime Estimates
Based on Gate 5.4 timing on the Apple Silicon M5 MPS backend:

| Model Name | Param Count | Measured Speed (tok/s) | Sec / Sample | Est. Runtime for 20,781 Samples | Priority Order |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Qwen 2.5 0.5B Instruct** | 0.49B | 36.6 | 0.356s | **~2.1 hours** | Batch 1 (Fast) |
| **Qwen 2.5 1.5B Instruct** | 1.54B | 19.2 | 0.666s | **~3.8 hours** | Batch 1 (Fast) |
| **SmolLM2 1.7B Instruct** | 1.71B | 18.3 | 0.767s | **~4.4 hours** | Batch 1 (Fast) |
| **Llama 3.2 3B Instruct** | 3.21B | 12.4 | 0.890s | **~5.1 hours** | Batch 2 (Medium) |
| **Qwen 2.5 3B Instruct** | 3.09B | 9.8 | 1.300s | **~7.5 hours** | Batch 2 (Medium) |
| **Gemma 2 2B IT** | 2.61B | 4.8 | 3.058s | **~17.7 hours** | Batch 3 (Long-running) |
| **Total Cumulative Compute** | — | — | — | **~40.6 hours** | Sequential Execution |

### 5.2 Memory Management & Fault-Tolerance Strategy
- **Sequential Execution:** Exactly one model loaded in RAM/MPS memory at a time.
- **Explicit Garbage Collection:**
  ```python
  del model
  del tokenizer
  gc.collect()
  torch.mps.empty_cache()
```
- **Incremental Checkpointing:** The runner will save predictions in batches of 500 samples to disk (e.g. `gate_5_6_checkpoint_<model>.jsonl`). If an interrupted session or OS thermal pause occurs, it resumes exactly from the last completed sample index without re-running completed samples.

---

## 6. Output Artifact & Reproducibility Plan

Upon execution, the following files will be generated under `research/results/phase_05/`:
1. `gate_5_6_full_validation_predictions_<model>.jsonl` (Per-sample generations, token counts, timings, and parsed outputs).
2. `gate_5_6_validation_summary_<model>.json` (Summary metrics, strict validity %, fallback %, persistence-replaced RMSE/MAE/RelRMSE, common-valid metrics, DA).
3. `gate_5_6_championship_report.json` (Consolidated 6-model championship ranking and backbone decision).
4. `selected_backbone.json` (Locked winning backbone metadata or SFT research candidate selection record).

---

## 7. Preflight Status & Recommendation

- **Integrity Status:** **READY (100% Verified).**
- **Blockers:** **None.** All models cached, all tokens verified, validation dataset verified against Phase 04 ground truth.
- **Strict Stop Condition Acknowledged:** Execution is paused. Inference will NOT begin without your explicit authorization.

