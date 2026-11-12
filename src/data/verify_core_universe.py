import csv, json
from collections import defaultdict

# 1. Load splits definition
with open('research/results/phase_03/leakage_audit_results.json') as f:
    d = json.load(f)

splits = d['split_specifications']['splits']
train_start, train_end = splits['train']['start_date'], splits['train']['end_date']
val_start, val_end = splits['validation']['start_date'], splits['validation']['end_date']
test_start, test_end = splits['test']['start_date'], splits['test']['end_date']

secondary_tickers = set(d['universe_partitions']['secondary_tickers'])

print(f"Train period: {train_start} to {train_end}")
print(f"Val period: {val_start} to {val_end}")
print(f"Test period: {test_start} to {test_end}")
print(f"Secondary tickers (excluded from core): {sorted(list(secondary_tickers))}")

# 2. Load global clean common data
records = []
with open('data/processed/global_equities_common.csv', 'r', encoding='utf-8') as f:
    r = csv.DictReader(f)
    for row in r:
        records.append(row)

by_ticker = defaultdict(list)
for r in records:
    by_ticker[r['ticker']].append(r)

core_tickers = sorted([t for t in by_ticker.keys() if t not in secondary_tickers])
print(f"Core tickers count: {len(core_tickers)}")

# Check observations per period for each core ticker
ticker_period_stats = {}
incomplete_tickers = []

for t in core_tickers:
    recs = by_ticker[t]
    train_obs = [r for r in recs if train_start <= r['date'] <= train_end]
    val_obs = [r for r in recs if val_start <= r['date'] <= val_end]
    test_obs = [r for r in recs if test_start <= r['date'] <= test_end]
    total_obs = len(recs)
    
    first_d = min(r['date'] for r in recs)
    last_d = max(r['date'] for r in recs)
    
    ticker_period_stats[t] = {
        'total': total_obs,
        'train': len(train_obs),
        'val': len(val_obs),
        'test': len(test_obs),
        'first_date': first_d,
        'last_date': last_d
    }
    
    # Incomplete criteria: if train < 450 (expected ~500) or val < 100 (expected ~140) or test < 100 (expected ~135)
    # or if missing start/end
    if len(train_obs) < 450 or len(val_obs) < 100 or len(test_obs) < 100:
        incomplete_tickers.append((t, ticker_period_stats[t]))

totals = [s['total'] for s in ticker_period_stats.values()]
train_counts = [s['train'] for s in ticker_period_stats.values()]
val_counts = [s['val'] for s in ticker_period_stats.values()]
test_counts = [s['test'] for s in ticker_period_stats.values()]

sorted_totals = sorted(totals)
med_total = sorted_totals[len(sorted_totals)//2]

print("\n--- CORE UNIVERSE (146 TICKERS) OBSERVATION STATS ---")
print(f"Total Observations per ticker:")
print(f"  Min: {min(totals)}")
print(f"  Max: {max(totals)}")
print(f"  Median: {med_total}")
print(f"Train Observations: min={min(train_counts)}, max={max(train_counts)}, median={sorted(train_counts)[len(train_counts)//2]}")
print(f"Val Observations: min={min(val_counts)}, max={max(val_counts)}, median={sorted(val_counts)[len(val_counts)//2]}")
print(f"Test Observations: min={min(test_counts)}, max={max(test_counts)}, median={sorted(test_counts)[len(test_counts)//2]}")

print(f"\nTickers flagged as incomplete required window: {len(incomplete_tickers)}")
for item in incomplete_tickers:
    print(" ", item)

# Let's inspect lowest total count ticker in core:
lowest_t = [t for t, s in ticker_period_stats.items() if s['total'] == min(totals)][0]
print(f"\nLowest count ticker in core: {lowest_t} -> {ticker_period_stats[lowest_t]}")
