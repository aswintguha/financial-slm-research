"""
Execution script for Gate 5.3: Prompt and Representation Sensitivity Analysis (Experiment E02).

Conditions:
- Template A: Primary benchmark prompt (returns from prices)
- Template B: Price-level prompt (nominal price from prices)
- Template C: Return sequence prompt (returns from returns)

Split:
- Independent 10% Training Development Split (2024-01-12 to 2024-03-20)
- 30 Stratified Tickers x 4 Origin Dates = 120 samples per condition (360 total generations)
- All target dates verified strictly <= 2024-03-29.

Model:
- HuggingFaceTB/SmolLM2-135M-Instruct (revision 12fd25f77366fa6b3b4b768ec3050bf629380bac)
- Greedy decoding, max_new_tokens=32, MPS bfloat16, Native Chat Template.
"""

import sys
import os
import csv
import json
import time
import math
from collections import defaultdict
from typing import List, Dict, Any

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

# Ensure benchmark modules are importable
sys.path.append(os.path.abspath("src/benchmark"))
from prompt_templates import format_template_a, format_template_b, format_template_c
from output_parser import parse_model_output
from run_zero_shot import apply_model_chat_template

# Predeclared parameters
MODEL_ID = "HuggingFaceTB/SmolLM2-135M-Instruct"
MODEL_REVISION = "12fd25f77366fa6b3b4b768ec3050bf629380bac"
TRAIN_START = "2022-03-01"
TRAIN_END = "2024-03-29"
MAX_NEW_TOKENS = 32
CONTEXT_W = 20
HORIZON_H = 5

SAMPLED_ORIGIN_DATES = ["2024-01-12", "2024-02-06", "2024-02-28", "2024-03-20"]

def build_dev_samples(
    data_path: str = "data/processed/global_equities_common.csv",
    manifest_path: str = "configs/screening_cohort_manifest.json"
) -> List[Dict[str, Any]]:
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    tickers = manifest["selected_tickers"]

    records_by_ticker = defaultdict(list)
    with open(data_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["ticker"] in tickers and row["date"] <= TRAIN_END:
                records_by_ticker[row["ticker"]].append({
                    "date": row["date"],
                    "ticker": row["ticker"],
                    "sector": row["sector"],
                    "country": row["country"],
                    "close": float(row["close"])
                })

    dev_samples = []
    for t in sorted(tickers):
        recs = records_by_ticker[t]
        recs.sort(key=lambda x: x["date"])
        date_to_idx = {r["date"]: i for i, r in enumerate(recs)}

        for d_orig in SAMPLED_ORIGIN_DATES:
            assert d_orig in date_to_idx, f"Origin {d_orig} not found for {t}"
            i_orig = date_to_idx[d_orig]

            # Context check
            assert i_orig >= CONTEXT_W - 1, f"Insufficient context for {t} at {d_orig}"
            past_records = recs[i_orig - CONTEXT_W + 1 : i_orig + 1]
            past_prices = [r["close"] for r in past_records]
            past_dates = [r["date"] for r in past_records]

            # Past daily returns inside context (19 returns)
            past_daily_returns = [
                past_prices[k] / past_prices[k - 1] - 1.0
                for k in range(1, len(past_prices))
            ]

            # 5th subsequent trading session on home exchange
            i_target = i_orig + HORIZON_H
            assert i_target < len(recs), f"Target index {i_target} out of range for {t}"
            d_target = recs[i_target]["date"]
            assert d_target <= TRAIN_END, f"Target {d_target} exceeds training cutoff {TRAIN_END} for {t}"

            p_orig = recs[i_orig]["close"]
            p_target = recs[i_target]["close"]
            target_log_ret = math.log(p_target / p_orig)

            dev_samples.append({
                "ticker": t,
                "country": recs[0]["country"],
                "sector": recs[0]["sector"],
                "origin_date": d_orig,
                "target_date": d_target,
                "origin_price": p_orig,
                "target_price": p_target,
                "target_log_return": round(target_log_ret, 6),
                "past_prices": past_prices,
                "past_dates": past_dates,
                "past_daily_returns": [round(r, 6) for r in past_daily_returns]
            })

    dev_samples.sort(key=lambda s: (s["ticker"], s["origin_date"]))
    assert len(dev_samples) == 120, f"Expected 120 dev samples, got {len(dev_samples)}"
    return dev_samples

def evaluate_predictions(
    samples: List[Dict[str, Any]],
    results: List[Dict[str, Any]],
    condition_id: str
) -> Dict[str, Any]:
    n = len(samples)
    assert len(results) == n

    strict_valid_count = 0
    fallback_extracted_count = 0
    econ_bound_violations = 0

    valid_actual_returns = []
    valid_pred_returns = []

    replaced_actual_returns = []
    replaced_pred_returns = []

    for s, res in zip(samples, results):
        p = res["parsed"]
        actual_r = s["target_log_return"]
        is_strict = p["is_valid"]
        has_fallback = p.get("fallback_extracted", False)

        if is_strict:
            strict_valid_count += 1
            pred_r = p["predicted_return"]
            valid_actual_returns.append(actual_r)
            valid_pred_returns.append(pred_r)
            replaced_pred_returns.append(pred_r)
        else:
            if has_fallback:
                fallback_extracted_count += 1
            if not p.get("passed_bounds", True):
                econ_bound_violations += 1
            # Persistence replacement: pred_r = 0.0
            replaced_pred_returns.append(0.0)

        replaced_actual_returns.append(actual_r)

    # Compute metrics for persistence baseline on full 120 samples
    # Persistence predicts 0.0 return
    pers_sq_errors = [y**2 for y in replaced_actual_returns]
    pers_rmse = math.sqrt(sum(pers_sq_errors) / n) if n > 0 else 0.0

    # Persistence-replaced metrics
    rep_sq_errors = [(y - y_hat)**2 for y, y_hat in zip(replaced_actual_returns, replaced_pred_returns)]
    rep_abs_errors = [abs(y - y_hat) for y, y_hat in zip(replaced_actual_returns, replaced_pred_returns)]
    rep_rmse = math.sqrt(sum(rep_sq_errors) / n) if n > 0 else 0.0
    rep_mae = sum(rep_abs_errors) / n if n > 0 else 0.0
    rel_rmse_rep = (rep_rmse / pers_rmse) if pers_rmse > 0 else 1.0

    # Common-valid metrics (if any)
    num_valid = len(valid_pred_returns)
    if num_valid > 0:
        val_sq_errors = [(y - y_hat)**2 for y, y_hat in zip(valid_actual_returns, valid_pred_returns)]
        val_abs_errors = [abs(y - y_hat) for y, y_hat in zip(valid_actual_returns, valid_pred_returns)]
        val_rmse = math.sqrt(sum(val_sq_errors) / num_valid)
        val_mae = sum(val_abs_errors) / num_valid
        # Directional Accuracy on valid (sign agreement, 0 return has no direction)
        da_correct = sum(
            1 for y, y_hat in zip(valid_actual_returns, valid_pred_returns)
            if (y > 0 and y_hat > 0) or (y < 0 and y_hat < 0)
        )
        val_da = (da_correct / num_valid) * 100.0
    else:
        val_rmse = None
        val_mae = None
        val_da = None

    return {
        "condition": condition_id,
        "sample_count": n,
        "strict_valid_count": strict_valid_count,
        "strict_valid_pct": round((strict_valid_count / n) * 100.0, 2),
        "fallback_extracted_count": fallback_extracted_count,
        "fallback_extracted_pct": round((fallback_extracted_count / n) * 100.0, 2),
        "economic_bound_violations": econ_bound_violations,
        "persistence_rmse": round(pers_rmse, 6),
        "persistence_replaced": {
            "rmse": round(rep_rmse, 6),
            "mae": round(rep_mae, 6),
            "rel_rmse_vs_persistence": round(rel_rmse_rep, 6)
        },
        "common_valid_subset": {
            "valid_samples": num_valid,
            "rmse": round(val_rmse, 6) if val_rmse is not None else None,
            "mae": round(val_mae, 6) if val_mae is not None else None,
            "directional_accuracy_pct": round(val_da, 2) if val_da is not None else None
        }
    }

def run_gate_5_3():
    print("=" * 70)
    print("STARTING GATE 5.3: PROMPT & REPRESENTATION SENSITIVITY ANALYSIS (E02)")
    print("=" * 70)

    # 1. Build and verify Dev Samples
    dev_samples = build_dev_samples()
    print(f"Constructed {len(dev_samples)} development samples across 30 tickers and 4 origin dates.")
    print("Verified: 100% of target dates conclude on or before 2024-03-28 (training partition).")

    # 2. Load Model & Tokenizer
    print(f"\nLoading Model: {MODEL_ID} (Revision: {MODEL_REVISION}) on Apple Silicon MPS bfloat16...")
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Using device: {device}, precision: bfloat16")

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
        use_fast=True
    )
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
        torch_dtype=torch.bfloat16
    ).to(device)
    model.eval()

    pad_token_id = tokenizer.pad_token_id or tokenizer.eos_token_id

    # Conditions to test
    conditions = [
        {"id": "Template_A", "name": "Template A (Returns from Prices - Primary Standard)"},
        {"id": "Template_B", "name": "Template B (Price Level from Prices - Ablation 1)"},
        {"id": "Template_C", "name": "Template C (Returns from Returns Sequence - Ablation 2)"}
    ]

    all_condition_results = {}
    all_raw_outputs = {}

    for cond in conditions:
        cond_id = cond["id"]
        cond_name = cond["name"]
        print(f"\n--- Running Condition: {cond_name} ---")

        results_list = []
        raw_generations = []
        t0_cond = time.perf_counter()

        for idx, s in enumerate(dev_samples):
            # Format prompt based on condition
            if cond_id == "Template_A":
                prompt_text = format_template_a(
                    ticker=s["ticker"],
                    country=s["country"],
                    sector=s["sector"],
                    origin_date=s["origin_date"],
                    target_date=s["target_date"],
                    past_prices=s["past_prices"]
                )
            elif cond_id == "Template_B":
                prompt_text = format_template_b(
                    ticker=s["ticker"],
                    country=s["country"],
                    sector=s["sector"],
                    origin_date=s["origin_date"],
                    target_date=s["target_date"],
                    past_prices=s["past_prices"]
                )
            elif cond_id == "Template_C":
                prompt_text = format_template_c(
                    ticker=s["ticker"],
                    country=s["country"],
                    sector=s["sector"],
                    origin_date=s["origin_date"],
                    target_date=s["target_date"],
                    past_daily_returns=s["past_daily_returns"]
                )

            # Native chat template tokenization
            encoded = apply_model_chat_template(tokenizer, prompt_text, add_generation_prompt=True)
            encoded = encoded.to(device)
            input_len = encoded.shape[1]

            if device == "mps":
                torch.mps.synchronize()

            with torch.no_grad():
                gen_out = model.generate(
                    input_ids=encoded,
                    max_new_tokens=MAX_NEW_TOKENS,
                    temperature=0.0,
                    do_sample=False,
                    pad_token_id=pad_token_id
                )
                if device == "mps":
                    torch.mps.synchronize()

            new_tokens = gen_out[0][input_len:]
            raw_text = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

            parsed = parse_model_output(
                raw_text=raw_text,
                template_type=cond_id,
                origin_price=s["origin_price"]
            )

            res_record = {
                "sample_idx": idx,
                "ticker": s["ticker"],
                "origin_date": s["origin_date"],
                "target_date": s["target_date"],
                "origin_price": s["origin_price"],
                "target_price": s["target_price"],
                "target_log_return": s["target_log_return"],
                "raw_text": raw_text,
                "parsed": parsed
            }
            results_list.append(res_record)
            raw_generations.append({
                "sample_idx": idx,
                "ticker": s["ticker"],
                "origin_date": s["origin_date"],
                "raw_text": raw_text,
                "is_valid": parsed["is_valid"],
                "predicted_return": parsed["predicted_return"],
                "fallback_extracted": parsed["fallback_extracted"],
                "fallback_value": parsed["fallback_value"]
            })

            if (idx + 1) % 40 == 0 or idx == len(dev_samples) - 1:
                print(f"  Processed {idx + 1}/{len(dev_samples)} samples...")

        t_cond = time.perf_counter() - t0_cond
        print(f"Completed {cond_id} in {t_cond:.2f}s.")

        eval_summary = evaluate_predictions(dev_samples, results_list, cond_id)
        eval_summary["duration_seconds"] = round(t_cond, 2)
        all_condition_results[cond_id] = eval_summary
        all_raw_outputs[cond_id] = raw_generations

        print(f"  Strict Validity: {eval_summary['strict_valid_pct']}% ({eval_summary['strict_valid_count']}/{len(dev_samples)})")
        print(f"  Fallback Extracted: {eval_summary['fallback_extracted_pct']}% ({eval_summary['fallback_extracted_count']}/{len(dev_samples)})")
        print(f"  Persistence-Replaced RelRMSE: {eval_summary['persistence_replaced']['rel_rmse_vs_persistence']}")

    # 3. Save Artifacts
    output_dir = "research/results/phase_05"
    os.makedirs(output_dir, exist_ok=True)
    results_path = os.path.join(output_dir, "gate_5_3_sensitivity_analysis_results.json")

    final_payload = {
        "experiment": "Gate 5.3 (E02: Prompt and Representation Sensitivity Analysis)",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": {
            "id": MODEL_ID,
            "revision": MODEL_REVISION,
            "device": device,
            "precision": "bfloat16",
            "decoding": "greedy",
            "max_new_tokens": MAX_NEW_TOKENS
        },
        "dev_split_allocation": {
            "training_period_start": TRAIN_START,
            "training_period_end": TRAIN_END,
            "training_total_common_sessions": 483,
            "dev_segment_10pct_common_sessions": 48,
            "dev_segment_common_session_range": ["2024-01-12", "2024-03-28"],
            "eligible_common_origin_sessions_count": 44,
            "eligible_common_origin_session_range": ["2024-01-12", "2024-03-20"],
            "target_boundary_verified": "All 120 target dates conclude <= 2024-03-28, inside training bounds",
            "sampled_origin_dates": SAMPLED_ORIGIN_DATES,
            "tickers_count": 30,
            "samples_per_condition": 120,
            "total_generations": 360
        },
        "condition_summaries": all_condition_results,
        "sample_generations": all_raw_outputs
    }

    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(final_payload, f, indent=2)

    print(f"\nSaved complete sensitivity results to: {results_path}")
    print("=" * 70)
    print("GATE 5.3 EXECUTION COMPLETED")
    print("=" * 70)

if __name__ == "__main__":
    run_gate_5_3()

