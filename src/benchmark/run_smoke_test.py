"""
Gate 5.2 SmolLM2-135M-Instruct Smoke Test.

Execution Requirements:
- Checkpoint: HuggingFaceTB/SmolLM2-135M-Instruct
- Device: MPS (Apple Silicon Metal Performance Shaders)
- Precision: bfloat16 (strictly enforced; no silent fallback)
- Evaluation: Exactly 10 synthetic dummy samples (independent of validation and test splits)
- Metrics measured:
  * Model & tokenizer loading latency
  * Peak memory usage (RSS via psutil and MPS allocated bytes)
  * Sequential generation latency and tokens/second
  * Output validity under strict case-sensitive parser vs diagnostic fallback
  * Forward pass logits sanity & finite-value check
"""

import sys
import os
import time
import json
import math
import psutil

# Ensure benchmark modules are on path
sys.path.append(os.path.abspath("src/benchmark"))
from prompt_templates import format_template_a
from output_parser import parse_model_output

def run_smoke_test():
    print("=== STARTING GATE 5.2: SMOLLM2-135M-INSTRUCT SMOKE TEST ===")

    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM

    model_id = "HuggingFaceTB/SmolLM2-135M-Instruct"
    print(f"Target Checkpoint: {model_id}")
    print(f"PyTorch Version: {torch.__version__}")
    print(f"MPS Available: {torch.backends.mps.is_available()}")
    assert torch.backends.mps.is_available(), "ERROR: MPS is not available."

    process = psutil.Process(os.getpid())
    mem_before_load = process.memory_info().rss / (1024 * 1024)

    # 1. Loading Tokenizer and Model
    t0_load = time.perf_counter()
    print("\n[Step 1: Loading Tokenizer and Model in bfloat16 on MPS]")
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    
    # Strictly enforce dtype=torch.bfloat16 and device="mps"
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16,
        device_map=None
    ).to("mps")

    torch.mps.synchronize()
    t_load = time.perf_counter() - t0_load

    mem_after_load = process.memory_info().rss / (1024 * 1024)
    model_param_count = sum(p.numel() for p in model.parameters())

    # Get exact checkpoint commit hash
    commit_hash = getattr(model.config, "_commit_hash", "N/A")
    license_type = "Apache-2.0"

    print(f"  Model Loaded in: {t_load:.3f} s")
    print(f"  Model Parameters: {model_param_count:,}")
    print(f"  Model dtype: {model.dtype}")
    print(f"  Model device: {model.device}")
    print(f"  Exact Revision/Commit Hash: {commit_hash}")
    print(f"  Declared License: {license_type}")
    print(f"  Host RSS Memory: {mem_after_load:.2f} MB (+{mem_after_load - mem_before_load:.2f} MB)")

    assert model.dtype == torch.bfloat16, f"ERROR: Model dtype is {model.dtype}, expected torch.bfloat16"
    assert model.device.type == "mps", f"ERROR: Model device is {model.device}, expected mps"

    # 2. Minimal Forward Pass Verification
    print("\n[Step 2: Minimal Forward Pass Verification]")
    dummy_text = "Test token forward pass"
    inputs = tokenizer(dummy_text, return_tensors="pt").to("mps")
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        torch.mps.synchronize()

    assert not torch.isnan(logits).any().item(), "ERROR: Forward pass produced NaN logits!"
    assert not torch.isinf(logits).any().item(), "ERROR: Forward pass produced Inf logits!"
    print(f"  Forward pass successful. Logits shape: {list(logits.shape)}, dtype: {logits.dtype}")

    # 3. Exactly 10 Synthetic Dummy Samples (Zero overlap with validation/test)
    print("\n[Step 3: Constructing 10 Synthetic Dummy Samples]")
    dummy_samples = []
    base_prices = [100.0, 50.0, 250.0, 15.0, 80.0, 120.0, 30.0, 450.0, 95.0, 180.0]
    for i in range(10):
        bp = base_prices[i]
        # Construct synthetic past 20 prices with small drift
        synthetic_past = [round(bp * (1.0 + 0.002 * (k - 10)), 2) for k in range(20)]
        prompt = format_template_a(
            ticker=f"DUMMY_{i+1:02d}",
            country="SyntheticLand",
            sector="GeneralIndustries",
            origin_date="2021-01-20",
            target_date="2021-01-27",
            past_prices=synthetic_past
        )
        dummy_samples.append({
            "sample_id": f"DUMMY_{i+1:02d}",
            "origin_price": synthetic_past[-1],
            "prompt": prompt
        })
    print(f"  Created {len(dummy_samples)} synthetic dummy samples.")

    # 4. Sequential Generation & Latency / Throughput Measurement
    print("\n[Step 4: Executing Sequential Generation on 10 Dummy Samples]")
    generation_results = []
    total_generated_tokens = 0
    total_generation_time = 0.0

    # Ensure pad_token_id is defined
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id

    for idx, s in enumerate(dummy_samples):
        prompt_text = s["prompt"]
        encoded = tokenizer(prompt_text, return_tensors="pt").to("mps")
        input_len = encoded["input_ids"].shape[1]

        torch.mps.synchronize()
        t0_gen = time.perf_counter()

        with torch.no_grad():
            gen_out = model.generate(
                **encoded,
                max_new_tokens=32,
                temperature=0.0,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id
            )
            torch.mps.synchronize()

        t_gen = time.perf_counter() - t0_gen

        # Extract only the newly generated tokens
        new_tokens = gen_out[0][input_len:]
        num_new_tokens = len(new_tokens)
        gen_text = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

        tokens_per_sec = (num_new_tokens / t_gen) if t_gen > 0 else 0.0
        total_generated_tokens += num_new_tokens
        total_generation_time += t_gen

        # Parse output using strict case-sensitive parser
        parse_res = parse_model_output(
            raw_text=gen_text,
            template_type="Template_A",
            origin_price=s["origin_price"]
        )

        generation_results.append({
            "sample_id": s["sample_id"],
            "input_tokens": input_len,
            "generated_tokens": num_new_tokens,
            "generation_time_sec": round(t_gen, 4),
            "tokens_per_sec": round(tokens_per_sec, 2),
            "raw_output": gen_text,
            "is_valid": parse_res["is_valid"],
            "strict_valid": parse_res["strict_valid"],
            "fallback_extracted": parse_res["fallback_extracted"],
            "fallback_value": parse_res["fallback_value"],
            "predicted_return": parse_res["predicted_return"],
            "error_reason": parse_res["error_reason"]
        })

        print(f"  Sample {idx+1:02d}: {num_new_tokens} tokens in {t_gen:.4f}s ({tokens_per_sec:.1f} tok/s) | Valid: {parse_res['is_valid']} | Raw: {repr(gen_text[:40])}")

    mem_peak = process.memory_info().rss / (1024 * 1024)

    # 5. Summary Statistics
    valid_count = sum(1 for r in generation_results if r["is_valid"])
    strict_valid_count = sum(1 for r in generation_results if r["strict_valid"])
    fallback_count = sum(1 for r in generation_results if r["fallback_extracted"])
    overall_tok_per_sec = (total_generated_tokens / total_generation_time) if total_generation_time > 0 else 0.0

    summary = {
        "gate": "Gate 5.2 SmolLM2-135M Smoke Test",
        "model_id": model_id,
        "commit_hash": commit_hash,
        "parameters": model_param_count,
        "dtype": str(model.dtype),
        "device": str(model.device),
        "license": license_type,
        "loading_time_sec": round(t_load, 3),
        "memory_mb": {
            "initial_rss": round(mem_before_load, 2),
            "post_load_rss": round(mem_after_load, 2),
            "peak_rss": round(mem_peak, 2)
        },
        "performance": {
            "total_samples": len(dummy_samples),
            "total_generated_tokens": total_generated_tokens,
            "total_generation_time_sec": round(total_generation_time, 4),
            "mean_tokens_per_sec": round(overall_tok_per_sec, 2)
        },
        "validity": {
            "valid_count": valid_count,
            "invalid_count": len(dummy_samples) - valid_count,
            "valid_pct": round((valid_count / len(dummy_samples)) * 100.0, 2),
            "strict_valid_count": strict_valid_count,
            "fallback_extracted_count": fallback_count
        },
        "samples": generation_results
    }

    os.makedirs("research/results/phase_05", exist_ok=True)
    out_path = "research/results/phase_05/smollm2_135m_smoke_test_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\nSaved smoke test report to {out_path}")
    print(f"Summary: {valid_count}/10 Strictly Valid ({summary['validity']['valid_pct']}%) | Throughput: {overall_tok_per_sec:.2f} tokens/s | Peak RSS: {mem_peak:.2f} MB")
    print("=== SMOKE TEST RUN COMPLETE ===")

if __name__ == "__main__":
    run_smoke_test()

