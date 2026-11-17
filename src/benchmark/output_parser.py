"""
Hierarchical Output Parser for Phase 05 Zero-Shot Benchmarking.

Policies Enforced:
1. Strict Primary Validity (`strict_valid`):
   - Pattern: r'\\[FORECAST:\\s*([+-]?\\d+(?:\\.\\d+)?)\\]'
   - Output must contain the exact tag.
   - Non-compliant outputs are strictly marked `is_valid = False`.

2. Diagnostic Fallback Parsing (`fallback_extracted`):
   - Extracts leading floats or conversational numeric values.
   - Preserves `fallback_value` for diagnostics and failure-mode analysis,
     but ALWAYS assigns `is_valid = False` under primary benchmark scoring.

3. Economic Sanity Bounds:
   - For log returns: |predicted return| <= 3.0 (returns exceeding 3.0 represent >2000% moves).
   - For nominal prices: predicted price > 0.0.
   - Out-of-bounds predictions are marked `is_valid = False`.

4. Target Reconciliation:
   - Template A: Directly parses return r_hat. Price reconstructed via P_0 * exp(r_hat).
   - Template B: Directly parses price P_hat. Implied return computed via log(P_hat / P_0).
   - Template C: Directly parses percentage/log return r_hat.
"""

import re
import math
from typing import Dict, Any, Optional

# Full-string matching with only explicitly permitted surrounding whitespace:
# Disallows any conversational text before or after the tag.
# Case-sensitive: Requires exact uppercase [FORECAST: <number>] tag.
STRICT_FULL_STRING_REGEX = re.compile(r'^\s*\[FORECAST:\s*([+-]?\d+(?:\.\d+)?)\]\s*$')

# Diagnostic tag match anywhere in text (used to detect embedded tags accompanied by conversational chatter, case-insensitive for diagnostic tracking)
DIAGNOSTIC_EMBEDDED_TAG_REGEX = re.compile(r'\[FORECAST:\s*([+-]?\d+(?:\.\d+)?)\]', re.IGNORECASE)

FALLBACK_KEY_VALUE_REGEX = re.compile(r'(?:forecast|prediction|price|return)"?\s*[:=]\s*"?([+-]?\d+(?:\.\d+)?)', re.IGNORECASE)
FALLBACK_LEADING_FLOAT_REGEX = re.compile(r'^\s*([+-]?\d+(?:\.\d+)?)')
FALLBACK_ANY_FLOAT_REGEX = re.compile(r'([+-]?\d+(?:\.\d+)?)')

MAX_ABS_LOG_RETURN = 3.0  # Boundary check: cumulative log return magnitude <= 3.0 (e.g. ~2000% jump)

def parse_model_output(
    raw_text: str,
    template_type: str = "Template_A",
    origin_price: Optional[float] = None
) -> Dict[str, Any]:
    """
    Parses raw LLM generation string into structured numerical prediction.
    """
    result = {
        "raw_text": raw_text,
        "template_type": template_type,
        "is_valid": False,
        "strict_valid": False,
        "fallback_extracted": False,
        "predicted_return": None,
        "reconstructed_price": None,
        "raw_parsed_value": None,
        "fallback_value": None,
        "error_reason": None
    }

    if not raw_text or not isinstance(raw_text, str):
        result["error_reason"] = "Empty or non-string generation"
        return result

    # 1. Primary Strict Full-String Parsing
    # Requires exact full-string match with only optional surrounding whitespace.
    strict_match = STRICT_FULL_STRING_REGEX.match(raw_text)
    if strict_match:
        val_str = strict_match.group(1)
        try:
            num_val = float(val_str)
            if not math.isnan(num_val) and not math.isinf(num_val):
                result["raw_parsed_value"] = num_val
                result["strict_valid"] = True
            else:
                result["error_reason"] = "Tag value is NaN or Inf"
                return result
        except ValueError:
            result["error_reason"] = f"Failed to cast tag value '{val_str}' to float"
            return result
    else:
        # 2. Diagnostic Fallback Parsing (Only if strict full-string match fails)
        # Check if the text contained an embedded tag accompanied by conversational chatter
        embedded_match = DIAGNOSTIC_EMBEDDED_TAG_REGEX.search(raw_text)
        if embedded_match:
            try:
                emb_val = float(embedded_match.group(1))
                if not math.isnan(emb_val) and not math.isinf(emb_val):
                    result["fallback_value"] = emb_val
                    result["fallback_extracted"] = True
            except ValueError:
                pass
            result["error_reason"] = "Tag accompanied by disallowed conversational text"
            return result

        fb_match = (
            FALLBACK_KEY_VALUE_REGEX.search(raw_text) or
            FALLBACK_LEADING_FLOAT_REGEX.search(raw_text) or
            FALLBACK_ANY_FLOAT_REGEX.search(raw_text)
        )
        if fb_match:
            try:
                fb_val = float(fb_match.group(1))
                if not math.isnan(fb_val) and not math.isinf(fb_val):
                    result["fallback_value"] = fb_val
                    result["fallback_extracted"] = True
            except ValueError:
                pass
        result["error_reason"] = "Missing mandatory [FORECAST: <number>] tag"
        # Strict policy: Fallback is strictly invalid under primary benchmark
        return result

    # 3. Target Reconciliation & Economic Sanity Bounds
    num_val = result["raw_parsed_value"]

    if template_type in ("Template_A", "Template_C"):
        # num_val represents log return
        if abs(num_val) > MAX_ABS_LOG_RETURN:
            result["is_valid"] = False
            result["error_reason"] = f"Return magnitude {num_val} exceeds economic bound (+/- {MAX_ABS_LOG_RETURN})"
            return result
        
        result["predicted_return"] = num_val
        result["is_valid"] = True

        if origin_price is not None and origin_price > 0.0:
            result["reconstructed_price"] = origin_price * math.exp(num_val)

    elif template_type == "Template_B":
        # num_val represents nominal price level
        if num_val <= 0.0:
            result["is_valid"] = False
            result["error_reason"] = f"Predicted price {num_val} is non-positive"
            return result

        result["reconstructed_price"] = num_val
        if origin_price is not None and origin_price > 0.0:
            implied_ret = math.log(num_val / origin_price)
            if abs(implied_ret) > MAX_ABS_LOG_RETURN:
                result["is_valid"] = False
                result["error_reason"] = f"Implied return {implied_ret:.4f} exceeds economic bound (+/- {MAX_ABS_LOG_RETURN})"
                return result
            result["predicted_return"] = implied_ret
            result["is_valid"] = True
        else:
            result["is_valid"] = True
    else:
        result["error_reason"] = f"Unknown template type '{template_type}'"
        result["is_valid"] = False

    return result

