import csv
from collections import defaultdict

jse_by_ticker = defaultdict(list)
with open('data/raw/JSE_data.csv', 'r') as f:
    reader = csv.reader(f)
    next(reader)
    for r in reader:
        jse_by_ticker[r[2].strip()].append({'date': r[1].strip(), 'close': float(r[5].strip())})

for t in jse_by_ticker:
    jse_by_ticker[t].sort(key=lambda x: x['date'])

# For each ticker, let's find all episodes where price dropped by ~100x and later jumped back ~100x
episodes = []
for t, recs in jse_by_ticker.items():
    n = len(recs)
    i = 0
    while i < n:
        if i > 0 and 0.007 <= (recs[i]['close'] / recs[i-1]['close']) <= 0.015:
            # start of a trough
            drop_date = recs[i]['date']
            prev_p = recs[i-1]['close']
            start_i = i
            # walk until jump back ~100x
            while i < n - 1 and not (65.0 <= (recs[i+1]['close'] / recs[i]['close']) <= 140.0):
                i += 1
            # i is now the last day of the trough (or end of data)
            end_i = i
            jump_date = recs[i+1]['date'] if i < n - 1 else None
            next_p = recs[i+1]['close'] if i < n - 1 else None
            run_days = end_i - start_i + 1
            episodes.append({
                'ticker': t,
                'start_date': drop_date,
                'end_date': recs[end_i]['date'],
                'run_days': run_days,
                'prev_close': prev_p,
                'sample_trough_close': recs[start_i]['close'],
                'next_close': next_p,
                'sample_ratio_prev': round(recs[start_i]['close'] / prev_p, 4),
                'sample_ratio_next': round(next_p / recs[end_i]['close'], 4) if next_p else None
            })
            i += 1
        else:
            i += 1

print(f"Total trough episodes: {len(episodes)}")
total_days = sum(e['run_days'] for e in episodes)
print(f"Total days across all trough episodes: {total_days}")
for e in episodes:
    print(f"{e['ticker']}: {e['start_date']} to {e['end_date']} ({e['run_days']} days), prev={e['prev_close']} -> trough={e['sample_trough_close']} -> next={e['next_close']}")
