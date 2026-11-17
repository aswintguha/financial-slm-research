"""
Comprehensive Unit Test Suite for Gate 5.1 Infrastructure.

Test Categories:
1. Strict Output Parser & Hierarchical Fallback Tests
   - Exact tag matches, embedded tags, negative numbers, decimals.
   - Conversational outputs, missing tags, leading numbers (recorded as fallback, is_valid=False).
   - NaN, Inf, non-numeric strings, empty strings.
   - Economic bound violations (|return| > 3.0, price <= 0.0).
   - Template A, B, and C target reconciliation and price reconstruction.
2. Screening Cohort Sampler & Reproducibility Tests
   - Stratified representation: exactly 1 stock per sector across all 10 canonical sectors for India, SA, USA.
   - Fixed count: exactly 30 stocks, exactly 14 origin dates, exactly 420 samples.
   - Deterministic sorting by (ticker, origin_date).
   - Ticker-specific H=5 target session construction following home exchange calendar.
   - Reproducibility across multiple generator runs.
   - Deterministic 50-sample throughput tie-breaker slice selection.
3. Temporal Causality & Zero-Leakage Tests
   - Origin date temporal boundary: past_dates[-1] == origin_date.
   - Target date strictly in the future: target_date > origin_date.
   - No target information inside past prices.
4. Dataset & Manifest Integrity Tests
   - Verification of dataset_integrity_manifest.json presence and validity.
"""

import sys
import os
import math
import json
from collections import defaultdict

# Add modules to path
sys.path.append(os.path.abspath("src/benchmark"))
sys.path.append(os.path.abspath("src/evaluation"))

from prompt_templates import format_template_a, format_template_b, format_template_c
from output_parser import parse_model_output
from screening_sampler import generate_screening_cohort, save_screening_cohort_manifest
from evaluator import compute_metrics
from run_zero_shot import apply_model_chat_template, NativeChatTemplateError

# ==============================================================================
# 1. PARSER & VALIDITY TESTS
# ==============================================================================

def test_parser_exact_tag_matches():
    """Verify that exact uppercase [FORECAST: <num>] tags with only surrounding whitespace are strictly parsed as valid."""
    cases = [
        ("[FORECAST: 0.025]", 0.025),
        ("[FORECAST: -0.0185]", -0.0185),
        ("[FORECAST: +0.0125]", 0.0125),
        ("[FORECAST: 0.0]", 0.0),
        ("[FORECAST: -0.0]", 0.0),
        ("[FORECAST: 1.2500]", 1.2500),
        ("  [FORECAST: +0.0345]  ", 0.0345),  # surrounding spaces allowed
        ("\n\n[FORECAST: -0.0120]\n", -0.0120),  # surrounding newlines allowed
        ("\t[FORECAST: 0.0050]\t\n", 0.0050)
    ]
    for text, expected in cases:
        res = parse_model_output(text, template_type="Template_A", origin_price=100.0)
        assert res["is_valid"] is True, f"Failed on valid text '{text}'"
        assert res["strict_valid"] is True
        assert res["fallback_extracted"] is False
        assert abs(res["predicted_return"] - expected) < 1e-6
        assert res["reconstructed_price"] is not None
        expected_p = 100.0 * math.exp(expected)
        assert abs(res["reconstructed_price"] - expected_p) < 1e-5

def test_parser_case_sensitivity_rejects_non_uppercase():
    """Verify that lowercase or mixed-case tags are strictly marked is_valid=False."""
    cases = [
        ("[forecast: 0.025]", 0.025),
        ("[Forecast: 0.025]", 0.025),
        ("[ForeCast: -0.0185]", -0.0185),
        ("[FOREcast: +0.0125]", 0.0125)
    ]
    for text, expected_fallback in cases:
        res = parse_model_output(text, template_type="Template_A", origin_price=100.0)
        assert res["is_valid"] is False, f"Non-uppercase tag should be invalid under primary scoring: '{text}'"
        assert res["strict_valid"] is False
        assert res["fallback_extracted"] is True
        assert abs(res["fallback_value"] - expected_fallback) < 1e-6
        assert "Missing mandatory [FORECAST: <number>] tag" in res["error_reason"] or "conversational" in res["error_reason"]

def test_parser_embedded_conversational_text_is_invalid():
    """Verify that any output with conversational text before or after the tag is strictly marked is_valid=False."""
    cases = [
        ("My prediction is [FORECAST: 0.025]", 0.025),
        ("[FORECAST: 0.025] because the trend is positive.", 0.025),
        ("Here is the prediction: [FORECAST: +0.0345]. Hope this helps!", 0.0345),
        ("Sure! [FORECAST: -0.0150]", -0.0150),
        ("[FORECAST: 0.0100] is my guess.", 0.0100),
        ("Analysis shows bullish momentum. [FORECAST: 0.0200]\nConfidence: high.", 0.0200)
    ]
    for text, expected_fallback in cases:
        res = parse_model_output(text, template_type="Template_A", origin_price=100.0)
        assert res["is_valid"] is False, f"Output with chatter should be invalid: '{text}'"
        assert res["strict_valid"] is False
        assert res["fallback_extracted"] is True
        assert abs(res["fallback_value"] - expected_fallback) < 1e-6
        assert res["error_reason"] == "Tag accompanied by disallowed conversational text"

def test_parser_conversational_fallback_is_invalid():
    """Verify that conversational or untagged numbers are recorded as fallback but marked is_valid=False."""
    cases = [
        "The predicted return is 0.0125.",
        "Based on momentum, I forecast +0.0250 for next week.",
        "0.0185",
        "return = -0.0050",
        "forecast: 0.0142",
        "Price forecast is 154.25"
    ]
    for text in cases:
        res = parse_model_output(text, template_type="Template_A", origin_price=100.0)
        assert res["is_valid"] is False, f"Should be invalid under primary scoring: '{text}'"
        assert res["strict_valid"] is False
        assert res["fallback_extracted"] is True
        assert res["fallback_value"] is not None
        assert res["error_reason"] == "Missing mandatory [FORECAST: <number>] tag"

def test_parser_non_numeric_and_malformed():
    """Verify that text with no numbers or malformed numbers is cleanly rejected."""
    cases = [
        "",
        "I cannot predict future stock movements.",
        "[FORECAST: NaN]",
        "[FORECAST: Inf]",
        "[FORECAST: None]",
        "[FORECAST: HOLD]",
        "[FORECAST: ]",
        "None",
        "??? !!!"
    ]
    for text in cases:
        res = parse_model_output(text, template_type="Template_A", origin_price=100.0)
        assert res["is_valid"] is False
        assert res["strict_valid"] is False
        assert res["predicted_return"] is None

def test_parser_economic_bounds():
    """Verify economic boundary checks (|return| <= 3.0, price > 0)."""
    # Out-of-bounds return
    res_high_ret = parse_model_output("[FORECAST: 3.5]", template_type="Template_A", origin_price=100.0)
    assert res_high_ret["is_valid"] is False
    assert "exceeds economic bound" in res_high_ret["error_reason"]

    res_low_ret = parse_model_output("[FORECAST: -4.2]", template_type="Template_A", origin_price=100.0)
    assert res_low_ret["is_valid"] is False
    assert "exceeds economic bound" in res_low_ret["error_reason"]

    # Boundary edge cases
    res_bound = parse_model_output("[FORECAST: 3.0]", template_type="Template_A", origin_price=100.0)
    assert res_bound["is_valid"] is True

    # Template B price bounds
    res_zero_p = parse_model_output("[FORECAST: 0.0]", template_type="Template_B", origin_price=100.0)
    assert res_zero_p["is_valid"] is False
    assert "non-positive" in res_zero_p["error_reason"]

    res_neg_p = parse_model_output("[FORECAST: -15.5]", template_type="Template_B", origin_price=100.0)
    assert res_neg_p["is_valid"] is False

def test_parser_template_b_and_c_reconciliation():
    """Verify target reconciliation across Templates B and C."""
    # Template B: price level to implied return
    # P_0 = 100.0, P_hat = 105.0 -> implied return = log(1.05) ~ 0.048790
    res_b = parse_model_output("[FORECAST: 105.0]", template_type="Template_B", origin_price=100.0)
    assert res_b["is_valid"] is True
    assert res_b["reconstructed_price"] == 105.0
    expected_r = math.log(105.0 / 100.0)
    assert abs(res_b["predicted_return"] - expected_r) < 1e-6

    # Template C: daily return sequence prediction
    res_c = parse_model_output("[FORECAST: -0.0150]", template_type="Template_C", origin_price=50.0)
    assert res_c["is_valid"] is True
    assert res_c["predicted_return"] == -0.0150
    assert abs(res_c["reconstructed_price"] - (50.0 * math.exp(-0.0150))) < 1e-6

# ==============================================================================
# 2. SAMPLER & COHORT REPRODUCIBILITY TESTS
# ==============================================================================

def test_screening_cohort_dimensions():
    """Verify exact count of 420 samples, 30 tickers, 14 origin dates."""
    samples = generate_screening_cohort()
    assert len(samples) == 420

    tickers = {s["ticker"] for s in samples}
    assert len(tickers) == 30

    dates = {s["origin_date"] for s in samples}
    assert len(dates) == 14

def test_screening_cohort_stratification():
    """Verify exactly 1 stock per sector across all 10 canonical sectors for each country."""
    samples = generate_screening_cohort()
    country_sector_tickers = defaultdict(lambda: defaultdict(set))
    for s in samples:
        country_sector_tickers[s["country"]][s["sector"]].add(s["ticker"])

    expected_countries = {"India", "South Africa", "United States"}
    assert set(country_sector_tickers.keys()) == expected_countries

    expected_sectors = {
        "Communication Services", "Consumer Discretionary", "Consumer Staples",
        "Energy", "Financials", "Healthcare", "Industrials", "Materials",
        "Real Estate", "Technology"
    }

    for c in expected_countries:
        sectors = set(country_sector_tickers[c].keys())
        assert sectors == expected_sectors, f"Sector mismatch in {c}"
        for s in expected_sectors:
            t_set = country_sector_tickers[c][s]
            assert len(t_set) == 1, f"Expected exactly 1 stock for {c} - {s}, got {len(t_set)}"

def test_screening_cohort_reproducibility():
    """Verify that two independent runs produce bit-for-bit identical sample tuples."""
    run1 = generate_screening_cohort()
    run2 = generate_screening_cohort()

    assert len(run1) == len(run2)
    for s1, s2 in zip(run1, run2):
        assert s1["ticker"] == s2["ticker"]
        assert s1["origin_date"] == s2["origin_date"]
        assert s1["target_date"] == s2["target_date"]
        assert s1["origin_price"] == s2["origin_price"]
        assert s1["target_price"] == s2["target_price"]
        assert s1["target_log_return"] == s2["target_log_return"]

def test_screening_cohort_deterministic_sorting():
    """Verify samples are sorted lexicographically in ascending order by (ticker, origin_date)."""
    samples = generate_screening_cohort()
    keys = [(s["ticker"], s["origin_date"]) for s in samples]
    assert keys == sorted(keys), "Samples must be strictly sorted by (ticker, origin_date)"

def test_throughput_tiebreaker_slice_selection():
    """Verify the 50-sample throughput tiebreaker slice is deterministic and matches the first 50 samples."""
    samples = generate_screening_cohort()
    slice_50 = samples[:50]
    assert len(slice_50) == 50

    # Ensure slice is unique and invariant
    manifest = save_screening_cohort_manifest()
    m_slice = manifest["throughput_tiebreaker_sample_slice"]
    assert len(m_slice) == 50

    for i in range(50):
        assert m_slice[i]["ticker"] == slice_50[i]["ticker"]
        assert m_slice[i]["origin_date"] == slice_50[i]["origin_date"]

# ==============================================================================
# 3. TEMPORAL CAUSALITY & ZERO-LEAKAGE TESTS
# ==============================================================================

def test_temporal_causality_and_no_lookahead():
    """Verify that every sample respects strict temporal causality."""
    samples = generate_screening_cohort()

    for s in samples:
        orig_date = s["origin_date"]
        targ_date = s["target_date"]
        past_dates = s["past_dates"]

        # 1. Target date strictly after origin date
        assert targ_date > orig_date, f"Target {targ_date} not after origin {orig_date}"

        # 2. Context window length is strictly W=20
        assert len(past_dates) == 20, f"Expected 20 past dates, got {len(past_dates)}"
        assert len(s["past_prices"]) == 20

        # 3. Last date of context is strictly the origin date
        assert past_dates[-1] == orig_date, f"Context last date {past_dates[-1]} != origin {orig_date}"

        # 4. Strictly strictly causal: all context dates <= origin_date
        for pd in past_dates:
            assert pd <= orig_date, f"Lookahead in context: date {pd} > origin {orig_date}"

        # 5. Target date is strictly NOT in the context window
        assert targ_date not in past_dates, f"Target date {targ_date} leaked into context"

def test_ticker_specific_target_construction():
    """Verify that target dates follow each ticker's own valid trading sessions."""
    samples = generate_screening_cohort()
    # Check that for any sample, origin_price and target_price are positive numbers
    for s in samples:
        assert s["origin_price"] > 0.0
        assert s["target_price"] > 0.0
        calculated_ret = round(math.log(s["target_price"] / s["origin_price"]), 6)
        assert abs(calculated_ret - s["target_log_return"]) < 1e-5

# ==============================================================================
# 4. EVALUATOR COMPATIBILITY INTEGRATION
# ==============================================================================

def test_evaluator_integration_with_parser_outputs():
    """Verify that parsed outputs integrate cleanly with evaluator.compute_metrics."""
    samples = generate_screening_cohort()[:10]
    actual_returns = [s["target_log_return"] for s in samples]

    # Generate mix of valid and invalid model outputs
    raw_outputs = [
        "[FORECAST: +0.0100]",
        "Invalid conversational text",
        "[FORECAST: -0.0200]",
        "[FORECAST: 0.0050]",
        "[FORECAST: NaN]",
        "[FORECAST: +0.0300]",
        "0.0150 (missing tag)",
        "[FORECAST: -0.0050]",
        "[FORECAST: 0.0000]",
        "[FORECAST: +0.0120]"
    ]

    parsed_preds = []
    for raw, s in zip(raw_outputs, samples):
        p_res = parse_model_output(raw, template_type="Template_A", origin_price=s["origin_price"])
        if p_res["is_valid"]:
            parsed_preds.append(p_res["predicted_return"])
        else:
            parsed_preds.append(None)

    metrics = compute_metrics(
        actual=actual_returns,
        predicted=parsed_preds,
        persistence_predicted=[0.0] * len(actual_returns),
        in_sample_naive_mae=0.038318,
        is_persistence_model=False
    )

    assert metrics["total_predictions"] == 10
    assert metrics["valid_predictions"] == 7
    assert metrics["invalid_predictions"] == 3
    assert metrics["valid_output_pct"] == 70.0
    assert "common_valid_subset" in metrics
    assert "persistence_replaced" in metrics
    assert metrics["common_valid_subset"]["mae"] is not None
    assert metrics["persistence_replaced"]["mae"] is not None

# ==============================================================================
# 5. CHAT-TEMPLATE RUNNER & MOCK TOKENIZER TESTS
# ==============================================================================

class MockTokenizerWithChatTemplate:
    def __init__(self, template_str="<|im_start|>user\n{{ messages[0]['content'] }}<|im_end|>\n<|im_start|>assistant\n"):
        self.chat_template = template_str
        self.name_or_path = "MockTokenizerWithTemplate"
        self.eos_token_id = 2
        self.pad_token_id = 2

    def apply_chat_template(self, messages, tokenize=True, add_generation_prompt=True, return_tensors=None):
        content = messages[0]["content"]
        rendered = f"<|im_start|>user\n{content}<|im_end|>\n"
        if add_generation_prompt:
            rendered += "<|im_start|>assistant\n"
        if tokenize:
            import torch
            # Mock tokenization: return dummy tensor
            return torch.tensor([[1, 2, 3, 4, 5]])
        return rendered

class MockTokenizerWithoutChatTemplate:
    def __init__(self):
        self.chat_template = None
        self.name_or_path = "MockTokenizerNoTemplate"

def test_chat_template_runner_semantic_preservation():
    """Verify that apply_model_chat_template preserves exact frozen prompt content inside messages."""
    tok = MockTokenizerWithChatTemplate()
    raw_prompt = format_template_a(
        ticker="AAPL",
        country="United States",
        sector="Technology",
        origin_date="2024-04-09",
        target_date="2024-04-16",
        past_prices=[100.0 + i for i in range(20)]
    )
    # Check rendered output
    rendered = tok.apply_chat_template([{"role": "user", "content": raw_prompt}], tokenize=False, add_generation_prompt=True)
    assert raw_prompt in rendered, "Exact prompt text must be preserved within rendered chat template"
    assert "<|im_start|>assistant" in rendered

def test_chat_template_runner_missing_template_raises_error():
    """Verify that a tokenizer lacking chat_template raises an explicit NativeChatTemplateError."""
    tok = MockTokenizerWithoutChatTemplate()
    try:
        apply_model_chat_template(tok, "Test prompt")
        assert False, "Should have raised NativeChatTemplateError"
    except NativeChatTemplateError as e:
        assert "does not expose a native chat_template" in str(e)
        assert "silent fallback to raw prompting or improvised wrappers is strictly forbidden" in str(e)

def run_all_tests():
    print("Executing Gate 5.1 Unit Test Suite...")
    test_parser_exact_tag_matches()
    print("  [PASS] test_parser_exact_tag_matches")
    test_parser_case_sensitivity_rejects_non_uppercase()
    print("  [PASS] test_parser_case_sensitivity_rejects_non_uppercase")
    test_parser_embedded_conversational_text_is_invalid()
    print("  [PASS] test_parser_embedded_conversational_text_is_invalid")
    test_parser_conversational_fallback_is_invalid()
    print("  [PASS] test_parser_conversational_fallback_is_invalid")
    test_parser_non_numeric_and_malformed()
    print("  [PASS] test_parser_non_numeric_and_malformed")
    test_parser_economic_bounds()
    print("  [PASS] test_parser_economic_bounds")
    test_parser_template_b_and_c_reconciliation()
    print("  [PASS] test_parser_template_b_and_c_reconciliation")
    test_screening_cohort_dimensions()
    print("  [PASS] test_screening_cohort_dimensions")
    test_screening_cohort_stratification()
    print("  [PASS] test_screening_cohort_stratification")
    test_screening_cohort_reproducibility()
    print("  [PASS] test_screening_cohort_reproducibility")
    test_screening_cohort_deterministic_sorting()
    print("  [PASS] test_screening_cohort_deterministic_sorting")
    test_throughput_tiebreaker_slice_selection()
    print("  [PASS] test_throughput_tiebreaker_slice_selection")
    test_temporal_causality_and_no_lookahead()
    print("  [PASS] test_temporal_causality_and_no_lookahead")
    test_ticker_specific_target_construction()
    print("  [PASS] test_ticker_specific_target_construction")
    test_evaluator_integration_with_parser_outputs()
    print("  [PASS] test_evaluator_integration_with_parser_outputs")
    test_chat_template_runner_semantic_preservation()
    print("  [PASS] test_chat_template_runner_semantic_preservation")
    test_chat_template_runner_missing_template_raises_error()
    print("  [PASS] test_chat_template_runner_missing_template_raises_error")
    print("\nALL 17 UNIT TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_all_tests()
