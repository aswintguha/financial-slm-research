"""
Full Validation Zero-Shot Championship Evaluation Runner for Phase 05 Gate 5.6.

Protocol Constraints (DEC-P05-001):
- Cohort: Exact N=20,781 validation observations from research/results/phase_04/baseline_sample_predictions.csv
- Context: Past W=20 trading days closing prices formatted to 2 decimals
- Prompt: Frozen Template A (cumulative 5-day log return)
- Native Chat Template: apply_chat_template(messages, tokenize=True, add_generation_prompt=True)
- Decoding: Greedy (temperature=0.0, do_sample=False), max_new_tokens=32
- Hardware: Apple Silicon MPS, torch.bfloat16, sequential execution
- Output Parser: Strict regex r'^\s*\[FORECAST:\s*([+-]?\d+(?:\.\d+)?)\]\s*$'
- Eligibility Gate: >= 95.0% strict validity
- Forecasting Winner Rule: >= 95.0% validity AND RelRMSE_replaced < 1.0000
- Checkpointing: Incremental flush every 500 samples to disk (JSONL format) with resume support
"""

import sys
import os
import gc
import csv
import json
import time
import math
from collections import defaultdict
from typing import List, Dict, Any

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

sys.path.append(os.path.abspath("src/benchmark"))
from prompt_templates import format_template_a
from output_parser import parse_model_output
from run_zero_shot import apply_model_chat_template

BASELINE_PREDS_CSV = "research/results/phase_04/baseline_sample_predictions.csv"
COMMON_DATA_CSV = "data/processed/global_equities_common.csv"
OUTPUT_DIR = "research/results/phase_05"

QUALIFYING_MODELS = [
    {
        "family": "Qwen 2.5",
        "name": "Qwen 2.5 0.5B Instruct",
        "id": "Qwen/Qwen2.5-0.5B-Instruct",
        "revision": "7ae557604adf67be50417f59c2c2f167def9a775",
        "license": "apache-2.0"
    },
    {
        "family": "Qwen 2.5",
        "name": "Qwen 2.5 1.5B Instruct",
        "id": "Qwen/Qwen2.5-1.5B-Instruct",
        "revision": "989aa7980e4cf806f80c7fef2b1adb7bc71aa306",
        "license": "apache-2.0"
    },
    {
        "family": "SmolLM2",
        "name": "SmolLM2 1.7B Instruct",
        "id": "HuggingFaceTB/SmolLM2-1.7B-Instruct",
        "revision": "31b70e2e869a7173562077fd711b654946d38674",
        "license": "apache-2.0"
    },
    {
        "family": "Llama 3.2",
        "name": "Llama 3.2 3B Instruct",
        "id": "meta-llama/Llama-3.2-3B-Instruct",
        "revision": "0cb88a4f764b7a12671c53f0838cd831a0843b95",
        "license": "llama3.2"
    },
    {
        "family": "Qwen 2.5",
        "name": "Qwen 2.5 3B Instruct",
        "id": "Qwen/Qwen2.5-3B-Instruct",
        "revision": "aa8e72537993ba99e69dfaafa59ed015b17504d1",
        "license": "other"
    },
    {
        "family": "Gemma 2",
        "name": "Gemma 2 2B IT",
        "id": "google/gemma-2-2b-it",
        "revision": "299a8560bedf22ed1c72a8a11e7dce4a7f9f51f8",
        "license": "gemma"
    }
]

def load_validation_samples() -> List[Dict[str, Any]]:
    print("Loading Phase 04 validation baseline predictions...")
    with open(BASELINE_PREDS_CSV, "r", encoding="utf-8") as fp:
        val_rows = [r for r in csv.DictReader(fp) if r.get("split") == "val"]
    assert len(val_rows) == 20781, f"Expected 20,781 validation rows, got {len(val_rows)}"

    print("Indexing historical prices from global_equities_common.csv...")
    records_by_ticker = defaultdict(list)
    with open(COMMON_DATA_CSV, "r", encoding="utf-8") as fp:
        for row in csv.DictReader(fp):
            records_by_ticker[row["ticker"]].append({
                "date": row["date"],
                "close": float(row["close"])
            })

    for t, recs in records_by_ticker.items():
        recs.sort(key=lambda x: x["date"])

    validation_samples = []
    for idx, r in enumerate(val_rows):
        t = r["ticker"]
        d_orig = r["origin_date"]
        d_target = r["target_date"]
        p_orig = float(r["origin_price"])
        p_target = float(r["target_price"])
        r_actual = float(r["actual_target_log_return"])

        recs = records_by_ticker[t]
        date_to_idx = {rec["date"]: i for i, rec in enumerate(recs)}
        assert d_orig in date_to_idx, f"Date {d_orig} not found for ticker {t}"
        i_orig = date_to_idx[d_orig]
        assert i_orig >= 19, f"Insufficient history for {t} at {d_orig}"

        past_recs = recs[i_orig - 19 : i_orig + 1]
        past_prices = [rec["close"] for rec in past_recs]
        assert len(past_prices) == 20

        validation_samples.append({
            "sample_index": idx,
            "sample_id": f"VAL_{idx+1:05d}",
            "ticker": t,
            "sector": r["sector"],
            "country": r["country"],
            "origin_date": d_orig,
            "target_date": d_target,
            "origin_price": p_orig,
            "target_price": p_target,
            "actual_target_log_return": r_actual,
            "past_prices": past_prices
        })

    print(f"Constructed exactly {len(validation_samples):,} full validation samples with 20-day historical contexts.")
    return validation_samples

def evaluate_validation_results(
    samples: List[Dict[str, Any]],
    results: List[Dict[str, Any]],
    model_cfg: Dict[str, Any],
    timing_info: Dict[str, Any],
    num_params: int
) -> Dict[str, Any]:
    n = len(samples)
    assert len(results) == n

    strict_valid_count = sum(1 for r in results if r["parsed"]["is_valid"])
    strict_valid_pct = (strict_valid_count / n) * 100.0
    invalid_count = n - strict_valid_count
    invalid_pct = (invalid_count / n) * 100.0
    fallback_count = sum(1 for r in results if (not r["parsed"]["is_valid"] and r["parsed"].get("fallback_extracted", False)))
    fallback_pct = (fallback_count / n) * 100.0
    econ_violations = sum(1 for r in results if not r["parsed"].get("passed_bounds", True))

    y_actual = [s["actual_target_log_return"] for s in samples]

    # Persistence Baseline
    pers_sq_errs = [y**2 for y in y_actual]
    pers_abs_errs = [abs(y) for y in y_actual]
    pers_rmse = math.sqrt(sum(pers_sq_errs) / n)
    pers_mae = sum(pers_abs_errs) / n

    # Persistence-Replaced Predictions
    y_rep = []
    for r in results:
        if r["parsed"]["is_valid"]:
            y_rep.append(r["parsed"]["predicted_return"])
        else:
            y_rep.append(0.0)

    rep_sq_errs = [(y - y_hat)**2 for y, y_hat in zip(y_actual, y_rep)]
    rep_abs_errs = [abs(y - y_hat) for y, y_hat in zip(y_actual, y_rep)]
    rep_rmse = math.sqrt(sum(rep_sq_errs) / n)
    rep_mae = sum(rep_abs_errs) / n
    rel_rmse_rep = (rep_rmse / pers_rmse) if pers_rmse > 0 else 1.0

    # Common Valid Subset
    valid_actual = [s["actual_target_log_return"] for s, r in zip(samples, results) if r["parsed"]["is_valid"]]
    valid_pred = [r["parsed"]["predicted_return"] for r in results if r["parsed"]["is_valid"]]
    num_valid = len(valid_pred)

    if num_valid > 0:
        val_sq_errs = [(y - y_hat)**2 for y, y_hat in zip(valid_actual, valid_pred)]
        val_abs_errs = [abs(y - y_hat) for y, y_hat in zip(valid_actual, valid_pred)]
        val_rmse = math.sqrt(sum(val_sq_errs) / num_valid)
        val_mae = sum(val_abs_errs) / num_valid
        
        val_pers_rmse = math.sqrt(sum(y**2 for y in valid_actual) / num_valid)
        val_pers_mae = sum(abs(y) for y in valid_actual) / num_valid
        val_rel_rmse = (val_rmse / val_pers_rmse) if val_pers_rmse > 0 else 1.0

        da_eligible = sum(1 for y in valid_actual if y != 0.0)
        da_correct = sum(1 for y, y_hat in zip(valid_actual, valid_pred) if (y > 0 and y_hat > 0) or (y < 0 and y_hat < 0))
        val_da = (da_correct / da_eligible * 100.0) if da_eligible > 0 else None
    else:
        val_rmse = None
        val_mae = None
        val_pers_rmse = None
        val_pers_mae = None
        val_rel_rmse = None
        val_da = None
        da_eligible = 0
        da_correct = 0

    is_eligible = (strict_valid_pct >= 95.0)
    is_forecasting_winner = (is_eligible and rel_rmse_rep < 1.000000)

    return {
        "model_name": model_cfg["name"],
        "model_id": model_cfg["id"],
        "revision": model_cfg["revision"],
        "license": model_cfg["license"],
        "parameter_count": num_params,
        "status": "COMPLETED",
        "samples_attempted": n,
        "samples_completed": len(results),
        "strict_valid_count": strict_valid_count,
        "strict_valid_pct": round(strict_valid_pct, 4),
        "invalid_count": invalid_count,
        "invalid_pct": round(invalid_pct, 4),
        "fallback_extracted_count": fallback_count,
        "fallback_extracted_pct": round(fallback_pct, 4),
        "economic_bound_violations": econ_violations,
        "validation_eligibility_95pct_pass": is_eligible,
        "forecasting_winner_declared": is_forecasting_winner,
        "timing": timing_info,
        "persistence_baseline": {
            "rmse": round(pers_rmse, 6),
            "mae": round(pers_mae, 6)
        },
        "persistence_replaced": {
            "rmse": round(rep_rmse, 6),
            "mae": round(rep_mae, 6),
            "rel_rmse_vs_persistence": round(rel_rmse_rep, 6)
        },
        "common_valid_subset": {
            "valid_samples": num_valid,
            "rmse": round(val_rmse, 6) if val_rmse is not None else None,
            "mae": round(val_mae, 6) if val_mae is not None else None,
            "persistence_rmse": round(val_pers_rmse, 6) if val_pers_rmse is not None else None,
            "persistence_mae": round(val_pers_mae, 6) if val_pers_mae is not None else None,
            "rel_rmse_vs_persistence": round(val_rel_rmse, 6) if val_rel_rmse is not None else None,
            "directional_accuracy_pct": round(val_da, 2) if val_da is not None else None,
            "directional_accuracy_correct": da_correct,
            "directional_accuracy_eligible": da_eligible
        }
    }

def run_evaluation_for_model(
    model_cfg: Dict[str, Any],
    samples: List[Dict[str, Any]],
    device: str = "mps"
) -> Dict[str, Any]:
    model_id = model_cfg["id"]
    revision = model_cfg["revision"]
    model_name = model_cfg["name"]
    safe_name = model_id.replace("/", "_")
    
    summary_path = os.path.join(OUTPUT_DIR, f"gate_5_6_{safe_name}_validation_summary.json")
    checkpoint_jsonl = os.path.join(OUTPUT_DIR, f"gate_5_6_{safe_name}_validation_predictions.jsonl")

    # Check if model already completed
    if os.path.exists(summary_path):
        try:
            with open(summary_path, "r", encoding="utf-8") as fp:
                saved_summary = json.load(fp)
            if saved_summary.get("samples_completed") == len(samples):
                print(f"[CACHED/COMPLETED] {model_name} already completed full {len(samples):,} validation samples.")
                return saved_summary
        except Exception:
            pass

    print(f"\n{'='*80}\n[START] Full Validation Evaluation: {model_name} ({model_id})\n{'='*80}")

    # Resume capability: check existing predictions in checkpoint_jsonl
    completed_results = []
    completed_indices = set()
    if os.path.exists(checkpoint_jsonl):
        print(f"Found existing checkpoint file: {checkpoint_jsonl}. Reading completed samples...")
        with open(checkpoint_jsonl, "r", encoding="utf-8") as fp:
            for line in fp:
                if line.strip():
                    rec = json.loads(line)
                    completed_results.append(rec)
                    completed_indices.add(rec["sample_index"])
        print(f"Resuming from {len(completed_results):,} / {len(samples):,} previously evaluated samples.")

    if len(completed_results) == len(samples):
        print(f"All {len(samples):,} samples already in checkpoint JSONL. Recomputing final summary...")
        # Sort by sample_index
        completed_results.sort(key=lambda x: x["sample_index"])
        timing_dummy = {"note": "Loaded from checkpoint"}
        summary = evaluate_validation_results(samples, completed_results, model_cfg, timing_dummy, 0)
        with open(summary_path, "w", encoding="utf-8") as fp:
            json.dump(summary, fp, indent=2)
        return summary

    # 1. Load Tokenizer & Model
    t0_load = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(
        model_id,
        revision=revision,
        use_fast=True
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        revision=revision,
        torch_dtype=torch.bfloat16
    ).to(device)
    model.eval()

    t_load = time.perf_counter() - t0_load
    num_params = sum(p.numel() for p in model.parameters())
    print(f"Loaded {num_params:,} parameters in {t_load:.2f}s on {device} (bfloat16)")

    pad_token_id = tokenizer.pad_token_id or tokenizer.eos_token_id

    # Open checkpoint JSONL in append mode
    fp_ckpt = open(checkpoint_jsonl, "a", encoding="utf-8")

    total_gen_time = 0.0
    total_gen_tokens = 0
    t0_infer = time.perf_counter()

    for idx, s in enumerate(samples):
        if idx in completed_indices:
            continue

        prompt_text = format_template_a(
            ticker=s["ticker"],
            country=s["country"],
            sector=s["sector"],
            origin_date=s["origin_date"],
            target_date=s["target_date"],
            past_prices=s["past_prices"]
        )

        encoded = apply_model_chat_template(tokenizer, prompt_text, add_generation_prompt=True)
        encoded = encoded.to(device)
        input_len = encoded.shape[1]

        if device == "mps":
            torch.mps.synchronize()
        t_sample_start = time.perf_counter()

        with torch.no_grad():
            gen_out = model.generate(
                input_ids=encoded,
                max_new_tokens=32,
                temperature=0.0,
                do_sample=False,
                pad_token_id=pad_token_id
            )
            if device == "mps":
                torch.mps.synchronize()

        t_sample_gen = time.perf_counter() - t_sample_start
        new_tokens = gen_out[0][input_len:]
        num_new_tokens = len(new_tokens)
        total_gen_time += t_sample_gen
        total_gen_tokens += num_new_tokens

        raw_text = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        parsed = parse_model_output(
            raw_text=raw_text,
            template_type="Template_A",
            origin_price=s["origin_price"]
        )

        rec = {
            "sample_index": idx,
            "sample_id": s["sample_id"],
            "ticker": s["ticker"],
            "origin_date": s["origin_date"],
            "target_date": s["target_date"],
            "origin_price": s["origin_price"],
            "target_price": s["target_price"],
            "actual_target_log_return": s["actual_target_log_return"],
            "raw_text": raw_text,
            "parsed": parsed,
            "gen_tokens": num_new_tokens,
            "gen_time_sec": t_sample_gen
        }

        completed_results.append(rec)
        completed_indices.add(idx)

        # Write to checkpoint file immediately
        fp_ckpt.write(json.dumps(rec) + "\n")

        # Flush every 500 samples
        if (len(completed_results)) % 500 == 0:
            fp_ckpt.flush()
            val_so_far = sum(1 for r in completed_results if r["parsed"]["is_valid"])
            pct_so_far = (val_so_far / len(completed_results)) * 100.0
            elapsed = time.perf_counter() - t0_infer
            sec_per_item = elapsed / (len(completed_results) - (len(samples) - len(completed_results))) if elapsed > 0 else 0
            print(f"  [{model_name}] Progress: {len(completed_results):,}/{len(samples):,} ({len(completed_results)/len(samples)*100:.1f}%) | Strict Valid: {val_so_far:,} ({pct_so_far:.2f}%)")

    fp_ckpt.flush()
    fp_ckpt.close()
    total_infer_time = time.perf_counter() - t0_infer

    # Explicit Memory Cleanup
    del model
    del tokenizer
    gc.collect()
    if device == "mps":
        torch.mps.empty_cache()

    # Sort results
    completed_results.sort(key=lambda x: x["sample_index"])
    assert len(completed_results) == len(samples)

    timing_info = {
        "load_time_sec": round(t_load, 2),
        "total_inference_time_sec": round(total_infer_time, 2),
        "generation_only_time_sec": round(total_gen_time, 2),
        "total_generated_tokens": total_gen_tokens,
        "mean_tokens_per_sec": round((total_gen_tokens / total_gen_time), 2) if total_gen_time > 0 else 0.0
    }

    summary = evaluate_validation_results(samples, completed_results, model_cfg, timing_info, num_params)

    with open(summary_path, "w", encoding="utf-8") as fp:
        json.dump(summary, fp, indent=2)

    print(f"\n[FINISH] {model_name}: Strict Valid = {summary['strict_valid_pct']:.2f}% | Pass 95% = {summary['validation_eligibility_95pct_pass']} | Replaced RelRMSE = {summary['persistence_replaced']['rel_rmse_vs_persistence']:.6f}")
    return summary

def main():
    print("=" * 80)
    print("PHASE 05 - GATE 5.6: FULL VALIDATION CHAMPIONSHIP EVALUATION (N=20,781)")
    print("=" * 80)

    val_samples = load_validation_samples()
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Execution Compute Device: {device} (bfloat16)")

    all_summaries = []
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for idx, model_cfg in enumerate(QUALIFYING_MODELS):
        print(f"\n>>> Championship Model {idx+1}/{len(QUALIFYING_MODELS)}: {model_cfg['name']} <<<")
        summary = run_evaluation_for_model(model_cfg, val_samples, device=device)
        all_summaries.append(summary)

    # Compile Consolidated Championship Report
    championship_path = os.path.join(OUTPUT_DIR, "gate_5_6_championship_report.json")
    championship_payload = {
        "benchmark": "Phase 05 Gate 5.6 Full Validation Championship Evaluation",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "validation_samples_count": len(val_samples),
        "eligibility_threshold_pct": 95.0,
        "forecasting_winner_rule": "strict_valid_pct >= 95.0 AND persistence_replaced_RelRMSE < 1.000000",
        "device": device,
        "precision": "bfloat16",
        "models_evaluated_count": len(QUALIFYING_MODELS),
        "models_summary": all_summaries
    }

    with open(championship_path, "w", encoding="utf-8") as fp:
        json.dump(championship_payload, fp, indent=2)

    print("\n" + "=" * 80)
    print(f"CHAMPIONSHIP EVALUATION COMPLETED. Consolidated report saved to: {championship_path}")
    print("=" * 80)

if __name__ == "__main__":
    main()

