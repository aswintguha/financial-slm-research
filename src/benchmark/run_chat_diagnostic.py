"""
Gate 5.2.1: SmolLM2-135M Chat-Template Diagnostic.

Execution Requirements:
- Checkpoint: Already downloaded HuggingFaceTB/SmolLM2-135M-Instruct
  (revision: 12fd25f77366fa6b3b4b768ec3050bf629380bac)
- Device: MPS (Apple Silicon Metal Performance Shaders)
- Precision: bfloat16
- Evaluation: Same 10 synthetic dummy samples from Gate 5.2 smoke test.
- Prompt text: Exact frozen Template A prompt text, wrapped via tokenizer.apply_chat_template.
- Format:
    messages = [{"role": "user", "content": prompt_text}]
    tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_tensors="pt")
- Saved separately to research/results/phase_05/smollm2_135m_chat_template_diagnostic_results.json
"""

import sys
import os
import time
import json
import math
import psutil
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

# Ensure benchmark modules are on path
sys.path.append(os.path.abspath("src/benchmark"))
from prompt_templates import format_template_a
from output_parser import parse_model_output

def run_chat_template_diagnostic():
    print("=== STARTING GATE 5.2.1: CHAT-TEMPLATE DIAGNOSTIC ===")

    model_id = "HuggingFaceTB/SmolLM2-135M-Instruct"
    expected_commit = "12fd25f77366fa6b3b4b768ec3050bf629380bac"

    # 1. Load Tokenizer & Model
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    assert tokenizer.chat_template is not None, "ERROR: Tokenizer does not expose a native chat template!"
    print("  Native Tokenizer Chat Template verified.")

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16,
        device_map=None
    ).to("mps")
    torch.mps.synchronize()

    commit_hash = getattr(model.config, "_commit_hash", "N/A")
    print(f"  Loaded model ID: {model_id} (commit: {commit_hash})")
    print(f"  Model dtype: {model.dtype}, device: {model.device}")
    assert model.dtype == torch.bfloat16, f"Expected torch.bfloat16, got {model.dtype}"
    assert model.device.type == "mps", f"Expected mps, got {model.device}"

    # 2. Exact same 10 synthetic dummy samples as Gate 5.2
    base_prices = [100.0, 50.0, 250.0, 15.0, 80.0, 120.0, 30.0, 450.0, 95.0, 180.0]
    dummy_samples = []
    for i in range(10):
        bp = base_prices[i]
        synthetic_past = [round(bp * (1.0 + 0.002 * (k - 10)), 2) for k in range(20)]
        prompt_text = format_template_a(
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
            "raw_prompt_text": prompt_text
        })

    # Sample rendered chat template for auditing
    sample_messages = [{"role": "user", "content": dummy_samples[0]["raw_prompt_text"]}]
    rendered_sample = tokenizer.apply_chat_template(sample_messages, tokenize=False, add_generation_prompt=True)
    print("\n[Rendered Chat Template Inspection (Sample 1)]: ")
    print(rendered_sample[:200] + " ... [TRUNCATED] ... " + rendered_sample[-60:])

    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id

    # 3. Execute Generation
    process = psutil.Process(os.getpid())
    generation_results = []
    total_generated_tokens = 0
    total_generation_time = 0.0

    print("\n[Executing Sequential Generation with Native Chat Template]")
    for idx, s in enumerate(dummy_samples):
        messages = [{"role": "user", "content": s["raw_prompt_text"]}]
        # Tokenize via native apply_chat_template
        encoded = tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt"
        ).to("mps")

        input_len = encoded.shape[1]

        torch.mps.synchronize()
        t0_gen = time.perf_counter()

        with torch.no_grad():
            gen_out = model.generate(
                input_ids=encoded,
                max_new_tokens=32,
                temperature=0.0,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id
            )
            torch.mps.synchronize()

        t_gen = time.perf_counter() - t0_gen

        # Extract newly generated tokens
        new_tokens = gen_out[0][input_len:]
        new_token_ids = new_tokens.tolist()
        num_new_tokens = len(new_token_ids)

        # Decode with and without special tokens
        gen_text_stripped = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        gen_text_raw = tokenizer.decode(new_tokens, skip_special_tokens=False)

        tokens_per_sec = (num_new_tokens / t_gen) if t_gen > 0 else 0.0
        total_generated_tokens += num_new_tokens
        total_generation_time += t_gen

        # Parse using frozen strict case-sensitive parser
        parse_res = parse_model_output(
            raw_text=gen_text_stripped,
            template_type="Template_A",
            origin_price=s["origin_price"]
        )

        ended_with_eos = (tokenizer.eos_token_id in new_token_ids)
        eos_pos = new_token_ids.index(tokenizer.eos_token_id) if ended_with_eos else -1

        generation_results.append({
            "sample_id": s["sample_id"],
            "input_tokens": input_len,
            "generated_tokens": num_new_tokens,
            "generation_time_sec": round(t_gen, 4),
            "tokens_per_sec": round(tokens_per_sec, 2),
            "token_ids": new_token_ids,
            "raw_output_with_special": gen_text_raw,
            "decoded_output_stripped": gen_text_stripped,
            "ended_with_eos": ended_with_eos,
            "eos_token_position": eos_pos,
            "is_valid": parse_res["is_valid"],
            "strict_valid": parse_res["strict_valid"],
            "fallback_extracted": parse_res["fallback_extracted"],
            "fallback_value": parse_res["fallback_value"],
            "predicted_return": parse_res["predicted_return"],
            "error_reason": parse_res["error_reason"]
        })

        print(f"  Sample {idx+1:02d}: {num_new_tokens} tokens in {t_gen:.4f}s ({tokens_per_sec:.1f} tok/s) | Valid: {parse_res['is_valid']} | Raw: {repr(gen_text_stripped[:45])}")

    mem_peak = process.memory_info().rss / (1024 * 1024)
    valid_count = sum(1 for r in generation_results if r["is_valid"])
    strict_valid_count = sum(1 for r in generation_results if r["strict_valid"])
    fallback_count = sum(1 for r in generation_results if r["fallback_extracted"])
    overall_tok_per_sec = (total_generated_tokens / total_generation_time) if total_generation_time > 0 else 0.0

    diagnostic_summary = {
        "gate": "Gate 5.2.1 SmolLM2-135M Chat-Template Diagnostic",
        "description": "Exploratory diagnostic comparing native tokenizer chat template against raw prompt continuation",
        "model_id": model_id,
        "commit_hash": commit_hash,
        "parameters": 134515008,
        "dtype": str(model.dtype),
        "device": str(model.device),
        "license": "Apache-2.0",
        "chat_template_rendered_sample_prefix": rendered_sample[:150],
        "performance": {
            "total_samples": len(dummy_samples),
            "total_generated_tokens": total_generated_tokens,
            "total_generation_time_sec": round(total_generation_time, 4),
            "mean_tokens_per_sec": round(overall_tok_per_sec, 2),
            "peak_rss_mb": round(mem_peak, 2)
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

    out_path = "research/results/phase_05/smollm2_135m_chat_template_diagnostic_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(diagnostic_summary, f, indent=2)

    print(f"\nSaved chat template diagnostic results to {out_path}")
    print(f"Summary: {valid_count}/10 Strictly Valid ({diagnostic_summary['validity']['valid_pct']}%) | Throughput: {overall_tok_per_sec:.2f} tok/s")
    print("=== GATE 5.2.1 DIAGNOSTIC COMPLETE ===")

if __name__ == "__main__":
    run_chat_template_diagnostic()

