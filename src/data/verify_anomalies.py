import csv, math, json, os, zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict

# 1. Load JSE Data
jse_by_ticker = defaultdict(list)
with open('data/raw/JSE_data.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    header = next(reader)
    for r in reader:
        jse_by_ticker[r[2].strip()].append({
            'orig_idx': r[0],
            'date': r[1].strip(),
            'ticker': r[2].strip(),
            'close': float(r[5].strip())
        })

# Sort each ticker series
for t in jse_by_ticker:
    jse_by_ticker[t].sort(key=lambda x: x['date'])

# 2. Detailed analysis of JSE unit toggling
# We look for patterns where price is in ZAR (divided by 100) vs ZAC (cents)
# Usually normal price is around P0. When dropped by factor of 100, price is ~ P0 / 100.
# Let's inspect every case where ratio is ~0.01 or ~100
jse_unit_anomalies = []

for t, recs in jse_by_ticker.items():
    n = len(recs)
    for i in range(n):
        curr_p = recs[i]['close']
        prev_p = recs[i-1]['close'] if i > 0 else None
        next_p = recs[i+1]['close'] if i < n - 1 else None
        
        ratio_prev = (curr_p / prev_p) if prev_p else None
        ratio_next = (next_p / curr_p) if next_p else None
        
        # Check single-day glitch: curr dropped ~100x from prev, and next jumped ~100x from curr
        # Or multi-day glitch where a contiguous run of days is ~100x lower than outer context
        is_glitch = False
        rule = None
        inferred_unit = 'ZAC'
        corrected_p = curr_p
        
        if ratio_prev is not None and ratio_next is not None:
            if 0.007 <= ratio_prev <= 0.015 and 65.0 <= ratio_next <= 140.0:
                is_glitch = True
                rule = "single_day_rand_quote_isolated"
                inferred_unit = "ZAR (quoted in Rands instead of Cents)"
                corrected_p = round(curr_p * 100.0, 4)
            # What if multi-day glitch?
        
        # Let's record all instances where either ratio is near 0.01 or 100 to catch everything
        if (ratio_prev is not None and (0.007 <= ratio_prev <= 0.015 or 65.0 <= ratio_prev <= 140.0)) or \
           (ratio_next is not None and (0.007 <= ratio_next <= 0.015 or 65.0 <= ratio_next <= 140.0)):
            jse_unit_anomalies.append({
                'ticker': t,
                'idx': i,
                'date': recs[i]['date'],
                'prev_date': recs[i-1]['date'] if i > 0 else None,
                'prev_close': prev_p,
                'close': curr_p,
                'next_date': recs[i+1]['date'] if i < n - 1 else None,
                'next_close': next_p,
                'curr_prev_ratio': round(ratio_prev, 4) if ratio_prev else None,
                'next_curr_ratio': round(ratio_next, 4) if ratio_next else None,
            })

print(f"Total potential JSE boundary rows examined: {len(jse_unit_anomalies)}")
