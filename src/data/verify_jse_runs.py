import csv, math
from collections import defaultdict

jse_by_ticker = defaultdict(list)
with open('data/raw/JSE_data.csv', 'r') as f:
    reader = csv.reader(f)
    next(reader)
    for r in reader:
        jse_by_ticker[r[2].strip()].append({
            'date': r[1].strip(),
            'close': float(r[5].strip())
        })

for t in jse_by_ticker:
    jse_by_ticker[t].sort(key=lambda x: x['date'])

# For each ticker, let's find the median price to establish baseline scale
affected_observations = []

for t, recs in jse_by_ticker.items():
    prices = [r['close'] for r in recs]
    sorted_p = sorted(prices)
    median_p = sorted_p[len(sorted_p)//2]
    
    # Check each observation: is it approximately median / 100?
    # Specifically, if close * 100 is within 0.3x to 3.0x of local rolling context or median, while close is ~0.01x
    for i, r in enumerate(recs):
        curr_p = r['close']
        prev_p = recs[i-1]['close'] if i > 0 else recs[i+1]['close']
        next_p = recs[i+1]['close'] if i < len(recs)-1 else recs[i-1]['close']
        
        # Check if curr_p is depressed by factor ~100 relative to both neighbors or local context
        # Case 1: single day drop (prev_p and next_p are both ~100 * curr_p)
        ratio_prev = curr_p / prev_p if prev_p else 1.0
        ratio_next = next_p / curr_p if next_p else 1.0
        
        # Case 2: contiguous run of depressed days where all days in run are ~100x lower
        # Let's test if curr_p * 70 < median_p and (curr_p * 100) is close to surrounding valid prices
        # Or more strictly:
        is_unit_error = False
        rule_name = ""
        
        # Isolated single-day error
        if 0.007 <= ratio_prev <= 0.015 and 65.0 <= ratio_next <= 140.0:
            is_unit_error = True
            rule_name = "isolated_1day_zar_switch"
        # Run of 2 or more days: curr_p / prev_p ~ 0.01 and subsequent days flat, then jumps back ~100x
        elif 0.007 <= ratio_prev <= 0.015 and 0.7 <= ratio_next <= 1.4:
            # Check ahead until it jumps back
            k = i + 1
            while k < len(recs) and 0.7 <= (recs[k]['close'] / recs[k-1]['close']) <= 1.4:
                k += 1
            if k < len(recs) and 65.0 <= (recs[k]['close'] / recs[k-1]['close']) <= 140.0:
                is_unit_error = True
                rule_name = f"multi_day_zar_run_start (run len {k - i})"
        elif 0.7 <= ratio_prev <= 1.4 and 65.0 <= ratio_next <= 140.0:
            # Check backwards if it started with a ~0.01 drop
            k = i - 1
            while k >= 0 and 0.7 <= (recs[k+1]['close'] / recs[k]['close']) <= 1.4:
                k -= 1
            if k >= 0 and 0.007 <= (recs[k+1]['close'] / recs[k]['close']) <= 0.015:
                is_unit_error = True
                rule_name = f"multi_day_zar_run_end (from idx {k+1})"
        elif 0.7 <= ratio_prev <= 1.4 and 0.7 <= ratio_next <= 1.4:
            # Interior of a multi-day run
            # Check backwards
            k1 = i - 1
            while k1 >= 0 and 0.7 <= (recs[k1+1]['close'] / recs[k1]['close']) <= 1.4:
                k1 -= 1
            k2 = i + 1
            while k2 < len(recs) and 0.7 <= (recs[k2]['close'] / recs[k2-1]['close']) <= 1.4:
                k2 += 1
            if k1 >= 0 and 0.007 <= (recs[k1+1]['close'] / recs[k1]['close']) <= 0.015 and \
               k2 < len(recs) and 65.0 <= (recs[k2]['close'] / recs[k2-1]['close']) <= 140.0:
                is_unit_error = True
                rule_name = "multi_day_zar_run_interior"
                
        if is_unit_error:
            affected_observations.append({
                'ticker': t,
                'date': r['date'],
                'prev_date': recs[i-1]['date'] if i > 0 else None,
                'prev_close': prev_p,
                'close': curr_p,
                'next_date': recs[i+1]['date'] if i < len(recs)-1 else None,
                'next_close': next_p,
                'curr_prev_ratio': round(ratio_prev, 4),
                'next_curr_ratio': round(ratio_next, 4),
                'inferred_unit': 'ZAR',
                'proposed_corrected_value': round(curr_p * 100.0, 4),
                'rule': rule_name
            })

print(f"Total unit-switch observations identified: {len(affected_observations)}")
by_ticker_aff = defaultdict(list)
for o in affected_observations:
    by_ticker_aff[o['ticker']].append(o)
print(f"Affected tickers count: {len(by_ticker_aff)}")
for t, obs in by_ticker_aff.items():
    print(f"  {t}: {len(obs)} days (sample date: {obs[0]['date']}, close: {obs[0]['close']} -> {obs[0]['proposed_corrected_value']})")
