import csv, math
from collections import defaultdict

jse_by_ticker = defaultdict(list)
with open('data/raw/JSE_data.csv', 'r') as f:
    reader = csv.reader(f)
    next(reader)
    for r in reader:
        jse_by_ticker[r[2].strip()].append({'date': r[1].strip(), 'close': float(r[5].strip())})

for t in jse_by_ticker:
    jse_by_ticker[t].sort(key=lambda x: x['date'])

# Classification of tickers:
# Type 1: High-value tickers where normal price is in thousands of cents (e.g. 1000 - 25000), 
#         and occasionally 1 or a few days drop to ~10 - 250 (e.g. VOD.JO, SBK.JO, TRE.JO, DTC.JO, FGL.JO, CKS.JO).
# Type 2: Mid-value tickers with clear multi-day / periodic switches (e.g. AON.JO, RTN.JO, TLM.JO, ADW.JO, PPR.JO, HUG.JO, MCZ.JO, TMT.JO, EEL.JO).
# Type 3: Low-penny tickers where prices are below 1 Rand (e.g. AHL.JO where price is 0.15 Rands vs 15 Cents).

print("--- Analysis of Tickers with 100x Jumps ---")
for t in ['SBK.JO', 'VOD.JO', 'TRE.JO', 'DTC.JO', 'FGL.JO', 'CKS.JO', 'AON.JO', 'RTN.JO', 'TLM.JO', 'ADW.JO', 'PPR.JO', 'HUG.JO', 'MCZ.JO', 'TMT.JO', 'EEL.JO', 'AYO.JO', 'AHL.JO', 'BIK.JO']:
    recs = jse_by_ticker[t]
    prices = [r['close'] for r in recs]
    print(f"{t}: min={min(prices):.4f}, max={max(prices):.4f}, median={sorted(prices)[len(prices)//2]:.4f}")
