"""
Deterministic Screening Cohort Sampler for Phase 05.

Protocol Rules Enforced:
1. Stratified 30-Stock Universe:
   - Exactly 1 stock per sector across all 10 canonical sectors for India (BSE), South Africa (JSE), and USA.
   - Selected from the 146 Core Full-History Universe using a fixed random seed (seed=42).
2. Common-Session Synchronized Origin Dates:
   - Synchronized across 133 common trading sessions (k in [0, 132]).
   - 14 origin dates sampled using uniform step Delta_k = 9 (indices 0, 9, 18, 27, 36, 45, 54, 63, 72, 81, 90, 99, 108, 117).
   - Leaving later sessions (k in [118, 132]) as a boundary buffer.
3. Ticker-Specific H=5 Target Construction:
   - Target calendar dates and prices follow each ticker's own exchange calendar sequence: the 5th subsequent valid trading session on that exchange.
4. Deterministic Sample Order:
   - Sorted lexicographically in ascending order by (ticker, origin_date).
5. Fixed 420 Samples: 30 stocks x 14 origin dates = exactly 420 samples.
"""

import csv
import json
import os
import random
from collections import defaultdict
from typing import List, Dict, Any, Tuple

RANDOM_SEED = 42
NUM_ORIGIN_DATES = 14
COMMON_SESSION_STEP = 9
HORIZON_H = 5
CONTEXT_W = 20

def generate_screening_cohort(
    data_path: str = "data/processed/global_equities_common.csv",
    secondary_tickers: Tuple[str, ...] = ("ASC.JO", "BHARTIHEXA.BSE", "BIK.JO", "NSTG")
) -> List[Dict[str, Any]]:
    """
    Builds the 420-sample stratified screening cohort.
    """
    sec_set = set(secondary_tickers)

    # 1. Load Data and Index by Ticker
    records_by_ticker = defaultdict(list)
    tickers_by_country_sector = defaultdict(lambda: defaultdict(list))

    with open(data_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            t = row["ticker"]
            if t in sec_set:
                continue
            rec = {
                "date": row["date"],
                "ticker": t,
                "sector": row["sector"],
                "country": row["country"],
                "close": float(row["close"])
            }
            records_by_ticker[t].append(rec)

    for t, recs in records_by_ticker.items():
        recs.sort(key=lambda x: x["date"])
        c = recs[0]["country"]
        s = recs[0]["sector"]
        if t not in tickers_by_country_sector[c][s]:
            tickers_by_country_sector[c][s].append(t)

    # 2. Select 30 Stratified Stocks (seed=42)
    rng = random.Random(RANDOM_SEED)
    selected_tickers = []
    selected_info = {}

    for c in sorted(tickers_by_country_sector.keys()):
        for s in sorted(tickers_by_country_sector[c].keys()):
            avail = sorted(tickers_by_country_sector[c][s])
            chosen = rng.choice(avail)
            selected_tickers.append(chosen)
            selected_info[chosen] = {"country": c, "sector": s}

    selected_tickers.sort()
    assert len(selected_tickers) == 30, f"Expected 30 tickers, got {len(selected_tickers)}"

    # 3. Determine Common Trading-Session Dates across Validation Split (2024-04-09 to 2024-10-31)
    # Validation boundary
    val_start = "2024-04-09"
    val_end = "2024-10-31"

    dates_by_country = defaultdict(set)
    for t in selected_tickers:
        c = selected_info[t]["country"]
        for r in records_by_ticker[t]:
            d = r["date"]
            if val_start <= d <= val_end:
                dates_by_country[c].add(d)

    countries = list(dates_by_country.keys())
    common_dates = sorted(list(dates_by_country[countries[0]] & dates_by_country[countries[1]] & dates_by_country[countries[2]]))
    assert len(common_dates) == 133, f"Expected 133 common sessions, got {len(common_dates)}"

    # Sample 14 origin dates with step=9
    sampled_origin_dates = [common_dates[i * COMMON_SESSION_STEP] for i in range(NUM_ORIGIN_DATES)]
    assert len(sampled_origin_dates) == 14

    # 4. Build Samples with Ticker-Specific H=5 Target Construction
    samples = []
    for t in selected_tickers:
        recs = records_by_ticker[t]
        date_to_idx = {r["date"]: i for i, r in enumerate(recs)}

        for d_orig in sampled_origin_dates:
            assert d_orig in date_to_idx, f"Origin date {d_orig} not found for ticker {t}"
            i_orig = date_to_idx[d_orig]

            # Context lookback check
            assert i_orig >= CONTEXT_W - 1, f"Insufficient context for {t} at {d_orig}"
            past_records = recs[i_orig - CONTEXT_W + 1 : i_orig + 1]
            past_prices = [r["close"] for r in past_records]
            past_dates = [r["date"] for r in past_records]

            # Past daily returns inside context
            past_daily_returns = [
                past_prices[k] / past_prices[k - 1] - 1.0  # percentage / relative return
                for k in range(1, len(past_prices))
            ]

            # Ticker-specific H=5 target session: 5th subsequent trading session on ticker's own exchange
            i_target = i_orig + HORIZON_H
            assert i_target < len(recs), f"Target index out of bounds for {t} at {d_orig}"

            d_target = recs[i_target]["date"]
            p_orig = recs[i_orig]["close"]
            p_target = recs[i_target]["close"]
            import math
            realized_log_ret = math.log(p_target / p_orig)

            samples.append({
                "ticker": t,
                "country": selected_info[t]["country"],
                "sector": selected_info[t]["sector"],
                "origin_date": d_orig,
                "target_date": d_target,
                "origin_price": p_orig,
                "target_price": p_target,
                "target_log_return": round(realized_log_ret, 6),
                "past_prices": past_prices,
                "past_dates": past_dates,
                "past_daily_returns": [round(r, 6) for r in past_daily_returns]
            })

    # Sort strictly by (ticker, origin_date)
    samples.sort(key=lambda s: (s["ticker"], s["origin_date"]))
    assert len(samples) == 420, f"Expected 420 samples, got {len(samples)}"
    return samples

def save_screening_cohort_manifest(
    output_path: str = "configs/screening_cohort_manifest.json"
) -> Dict[str, Any]:
    """
    Generates and saves the screening cohort manifest.
    """
    samples = generate_screening_cohort()
    manifest = {
        "manifest_metadata": {
            "name": "Phase 05 Stratified Screening Cohort (420 Samples)",
            "protocol_phase": "Phase 05 (Zero-Shot SLM Benchmark)",
            "random_seed": RANDOM_SEED,
            "tickers_count": 30,
            "origin_dates_count": NUM_ORIGIN_DATES,
            "total_samples": len(samples),
            "common_session_step": COMMON_SESSION_STEP,
            "horizon_H": HORIZON_H,
            "context_W": CONTEXT_W,
            "target_construction_rule": "Ticker-specific: 5th subsequent valid trading session on home exchange"
        },
        "selected_tickers": sorted(list({s["ticker"] for s in samples})),
        "sampled_origin_dates": sorted(list({s["origin_date"] for s in samples})),
        "throughput_tiebreaker_sample_slice": [
            {"sample_index": i, "ticker": s["ticker"], "origin_date": s["origin_date"]}
            for i, s in enumerate(samples[:50])
        ],
        "samples": [
            {
                "sample_id": f"SCREEN_{i+1:03d}",
                "ticker": s["ticker"],
                "country": s["country"],
                "sector": s["sector"],
                "origin_date": s["origin_date"],
                "target_date": s["target_date"],
                "origin_price": s["origin_price"],
                "target_price": s["target_price"],
                "target_log_return": s["target_log_return"],
                "past_dates": s["past_dates"],
                "past_prices": s["past_prices"]
            }
            for i, s in enumerate(samples)
        ]
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return manifest

if __name__ == "__main__":
    m = save_screening_cohort_manifest()
    print(f"Generated manifest: {len(m['samples'])} samples across {len(m['selected_tickers'])} tickers.")

