"""
Execution script for Phase 05 Gate 5.4: 420-Sample Zero-Shot Screening Benchmark across all 10 candidate SLMs.
Idempotent: skips models whose full 420-sample results are already saved on disk.
"""

import sys
import os
import gc
import json
import time
import math
import hashlib
from typing import List, Dict, Any

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

sys.path.append(os.path.abspath("src/benchmark"))
from prompt_templates import format_template_a
from output_parser import parse_model_output
from run_zero_shot import apply_model_chat_template

MANIFEST_PATH = "configs/screening_cohort_manifest.json"
EXPECTED_MANIFEST_SHA256 = "7cafe701d2fd689d660da104e465e515ec271d12e94f22605e458de8eaadee9e"
OUTPUT_DIR = "research/results/phase_05"

CANDIDATE_MODELS = [
    {
        "family": "SmolLM2",
        "name": "SmolLM2 135M Instruct",
        "id": "HuggingFaceTB/SmolLM2-135M-Instruct",
        "revision": "12fd25f77366fa6b3b4b768ec3050bf629380bac",
        "license": "apache-2.0"
    },
    {
        "family": "SmolLM2",
        "name": "SmolLM2 360M Instruct",
        "id": "HuggingFaceTB/SmolLM2-360M-Instruct",
        "revision": "a10cc1512eabd3dde888204e902eca88bddb4951",
        "license": "apache-2.0"
    },
    {
        "family": "Qwen 2.5",
        "name": "Qwen 2.5 0.5B Instruct",
        "id": "Qwen/Qwen2.5-0.5B-Instruct",
        "revision": "7ae557604adf67be50417f59c2c2f167def9a775",
        "license": "apache-2.0"
    },
    {
        "family": "Llama 3.2",
        "name": "Llama 3.2 1B Instruct",
        "id": "meta-llama/Llama-3.2-1B-Instruct",
        "revision": "9213176726f574b556790deb65791e0c5aa438b6",
        "license": "llama3.2"
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
        "family": "Gemma 2",
        "name": "Gemma 2 2B IT",
        "id": "google/gemma-2-2b-it",
        "revision": "299a8560bedf22ed1c72a8a11e7dce4a7f9f51f8",
        "license": "gemma"
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
        "family": "Phi-3.5",
        "name": "Phi-3.5 mini Instruct",
        "id": "microsoft/Phi-3.5-mini-instruct",
        "revision": "2fe192450127e6a83f7441aef6e3ca586c338b77",
        "license": "mit"
    }
]

def verify_manifest() -> List[Dict[str, Any]]:
    with open(MANIFEST_PATH, "rb") as f:
        actual_sha = hashlib.sha256(f.read()).hexdigest()
    if actual_sha != EXPECTED_MANIFEST_SHA256:
        raise ValueError(f"Manifest SHA mismatch: expected {EXPECTED_MANIFEST_SHA256}, got {actual_sha}")
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    samples = data["samples"]
    if len(samples) != 420:
        raise ValueError(f"Expected 420 samples, got {len(samples)}")
    return samples

def run_screening_for_model(
    model_cfg: Dict[str, Any],
    samples: List[Dict[str, Any]],
    device: str = "mps"
) -> Dict[str, Any]:
    model_id = model_cfg["id"]
    revision = model_cfg["revision"]
    model_name = model_cfg["name"]
    safe_name = model_id.replace("/", "_")
    model_out_path = os.path.join(OUTPUT_DIR, f"gate_5_4_{safe_name}_screening_results.json")

    # If results already exist and are complete, load and return
    if os.path.exists(model_out_path):
        try:
            with open(model_out_path, "r", encoding="utf-8") as fp:
                existing = json.load(fp)
            if existing.get("summary", {}).get("samples_completed") == 420:
                print(f"[CACHED/SKIPPING] {model_name}: 420 samples already completed.")
                return existing
        except Exception:
            pass

    print(f"\n{'='*70}\n[START] {model_name} ({model_id})\n{'='*70}")

    # 1. Load Tokenizer & Model with retry logic
    t0_load = time.perf_counter()
    max_retries = 3
    loaded = False
    for attempt in range(max_retries):
        try:
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
            loaded = True
            break
        except Exception as e:
            print(f"[RETRY {attempt+1}/{max_retries}] Loading {model_id} failed: {e}")
            time.sleep(5)

    if not loaded:
        print(f"[ERROR] Permanently failed to load model {model_id}")
        return {
            "summary": {
                "model_name": model_name,
                "model_id": model_id,
                "revision": revision,
                "license": model_cfg["license"],
                "status": "LOAD_ERROR",
                "samples_attempted": len(samples),
                "samples_completed": 0,
                "strict_valid_count": 0,
                "strict_valid_pct": 0.0,
                "screening_threshold_90pct_pass": False
            },
            "results": []
        }

    t_load = time.perf_counter() - t0_load
    num_params = sum(p.numel() for p in model.parameters())
    print(f"Loaded {num_params:,} parameters in {t_load:.2f}s on {device} (bfloat16)")

    pad_token_id = tokenizer.pad_token_id or tokenizer.eos_token_id

    # 2. Iterate through all 420 samples sequentially
    results_list = []
    total_gen_time = 0.0
    total_gen_tokens = 0

    t0_infer = time.perf_counter()
    for idx, s in enumerate(samples):
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

        results_list.append({
            "sample_id": s["sample_id"],
            "ticker": s["ticker"],
            "origin_date": s["origin_date"],
            "target_date": s["target_date"],
            "origin_price": s["origin_price"],
            "target_price": s["target_price"],
            "target_log_return": s["target_log_return"],
            "raw_text": raw_text,
            "parsed": parsed,
            "gen_tokens": num_new_tokens,
            "gen_time_sec": t_sample_gen
        })

        if (idx + 1) % 70 == 0 or idx == len(samples) - 1:
            strict_so_far = sum(1 for r in results_list if r["parsed"]["is_valid"])
            pct_so_far = (strict_so_far / (idx + 1)) * 100.0
            print(f"  [{model_name}] Progress: {idx + 1}/420 | Strict Valid: {strict_so_far}/{idx + 1} ({pct_so_far:.1f}%)")

    total_infer_time = time.perf_counter() - t0_infer

    # 3. Compute Metrics
    n = len(samples)
    strict_valid_count = sum(1 for r in results_list if r["parsed"]["is_valid"])
    strict_valid_pct = (strict_valid_count / n) * 100.0
    invalid_count = n - strict_valid_count
    invalid_pct = (invalid_count / n) * 100.0
    fallback_count = sum(1 for r in results_list if (not r["parsed"]["is_valid"] and r["parsed"].get("fallback_extracted", False)))
    fallback_pct = (fallback_count / n) * 100.0
    econ_violations = sum(1 for r in results_list if not r["parsed"].get("passed_bounds", True))

    # Persistence Baseline (H=5)
    y_actual = [s["target_log_return"] for s in samples]
    pers_sq_errs = [y**2 for y in y_actual]
    pers_abs_errs = [abs(y) for y in y_actual]
    pers_rmse = math.sqrt(sum(pers_sq_errs) / n)
    pers_mae = sum(pers_abs_errs) / n

    # Persistence-Replaced Predictions
    y_rep = []
    for r in results_list:
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
    valid_actual = [s["target_log_return"] for s, r in zip(samples, results_list) if r["parsed"]["is_valid"]]
    valid_pred = [r["parsed"]["predicted_return"] for r in results_list if r["parsed"]["is_valid"]]
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

    mean_throughput = (total_gen_tokens / total_gen_time) if total_gen_time > 0 else 0.0
    screening_pass = (strict_valid_pct >= 90.0)

    # 4. Explicit Memory Cleanup
    del model
    del tokenizer
    gc.collect()
    if device == "mps":
        torch.mps.empty_cache()

    summary = {
        "model_name": model_name,
        "model_id": model_id,
        "revision": revision,
        "license": model_cfg["license"],
        "parameter_count": num_params,
        "status": "COMPLETED",
        "samples_attempted": n,
        "samples_completed": len(results_list),
        "strict_valid_count": strict_valid_count,
        "strict_valid_pct": round(strict_valid_pct, 2),
        "invalid_count": invalid_count,
        "invalid_pct": round(invalid_pct, 2),
        "fallback_extracted_count": fallback_count,
        "fallback_extracted_pct": round(fallback_pct, 2),
        "economic_bound_violations": econ_violations,
        "screening_threshold_90pct_pass": screening_pass,
        "timing": {
            "load_time_sec": round(t_load, 2),
            "total_inference_time_sec": round(total_infer_time, 2),
            "generation_only_time_sec": round(total_gen_time, 2),
            "total_generated_tokens": total_gen_tokens,
            "mean_tokens_per_sec": round(mean_throughput, 2)
        },
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
            "directional_accuracy_pct": round(val_da, 2) if val_da is not None else None
        }
    }

    out_payload = {
        "summary": summary,
        "results": results_list
    }
    with open(model_out_path, "w", encoding="utf-8") as f:
        json.dump(out_payload, f, indent=2)

    print(f"\n[FINISH] {model_name}: Strict Valid = {strict_valid_pct:.1f}% | Pass 90% = {screening_pass} | Replaced RelRMSE = {rel_rmse_rep:.6f}")
    return out_payload

def main():
    print("=" * 80)
    print("PHASE 05 - GATE 5.4: 420-SAMPLE ZERO-SHOT SLM SCREENING BENCHMARK")
    print("=" * 80)

    samples = verify_manifest()
    print(f"Verified Screening Cohort Manifest: exactly {len(samples)} samples. SHA-256 matches bit-for-bit.")

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Compute Device: {device} (bfloat16)")

    all_summaries = []
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for idx, model_cfg in enumerate(CANDIDATE_MODELS):
        print(f"\n>>> Model {idx+1}/{len(CANDIDATE_MODELS)}: {model_cfg['name']} <<<")
        run_res = run_screening_for_model(model_cfg, samples, device=device)
        all_summaries.append(run_res["summary"])

    consolidated_path = os.path.join(OUTPUT_DIR, "gate_5_4_screening_benchmark_report.json")
    consolidated_payload = {
        "benchmark": "Phase 05 Gate 5.4 Zero-Shot SLM Screening (420 Samples)",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "cohort_samples": len(samples),
        "screening_threshold_pct": 90.0,
        "device": device,
        "precision": "bfloat16",
        "models_count": len(CANDIDATE_MODELS),
        "models_summary": all_summaries
    }
    with open(consolidated_path, "w", encoding="utf-8") as f:
        json.dump(consolidated_payload, f, indent=2)

    print("\n" + "=" * 80)
    print(f"ALL 10 MODELS PROCESSED. Consolidated report saved to: {consolidated_path}")
    print("=" * 80)

if __name__ == "__main__":
    main()
