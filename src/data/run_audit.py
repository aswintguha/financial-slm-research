import csv, math, os, json, zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict, Counter
from datetime import datetime, timedelta

def load_all_data():
    # 1. Load US Data
    us_records = []
    with open('data/raw/US_data.csv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        for r in reader:
            us_records.append({
                'market': 'US',
                'orig_idx': r[0],
                'date': r[1].strip(),
                'ticker': r[2].strip(),
                'sector': r[3].strip(),
                'country': r[4].strip(),
                'close': float(r[5].strip()) if r[5].strip() else None
            })

    # 2. Load JSE Data
    jse_records = []
    with open('data/raw/JSE_data.csv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        for r in reader:
            jse_records.append({
                'market': 'JSE',
                'orig_idx': r[0],
                'date': r[1].strip(),
                'ticker': r[2].strip(),
                'sector': r[3].strip(),
                'country': r[4].strip(),
                'close': float(r[5].strip()) if r[5].strip() else None
            })

    # 3. Load Indian Data
    india_records = []
    with zipfile.ZipFile('data/raw/Indian-Final-Data-3month.xlsx') as z:
        with z.open('xl/worksheets/sheet1.xml') as f:
            rows = []
            for event, elem in ET.iterparse(f):
                if elem.tag.endswith('row'):
                    row_data = {}
                    for c in elem:
                        if c.tag.endswith('c'):
                            cell_ref = c.attrib.get('r', '')
                            col_letter = ''.join([ch for ch in cell_ref if ch.isalpha()])
                            val = ''
                            t_tag = c.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')
                            v_tag = c.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
                            if t_tag is not None and t_tag.text:
                                val = t_tag.text
                            elif v_tag is not None and v_tag.text:
                                val = v_tag.text
                            row_data[col_letter] = val
                    rows.append(row_data)
                    elem.clear()

    header_row = rows[0]
    for r in rows[1:]:
        india_records.append({
            'market': 'India',
            'date': r.get('A', '').strip(),
            'sector': r.get('B', '').strip(),
            'ticker': r.get('C', '').strip(),
            'cap_size': r.get('D', '').strip(),
            'country': r.get('E', '').strip(),
            'open': float(r.get('F', '').strip()) if r.get('F', '').strip() else None,
            'high': float(r.get('G', '').strip()) if r.get('G', '').strip() else None,
            'low': float(r.get('H', '').strip()) if r.get('H', '').strip() else None,
            'close': float(r.get('I', '').strip()) if r.get('I', '').strip() else None,
            'volume': float(r.get('J', '').strip()) if r.get('J', '').strip() else None,
        })
    return {'US': us_records, 'JSE': jse_records, 'India': india_records}

datasets = load_all_data()

report = {}

for mname, records in datasets.items():
    print(f"\n==================== AUDITING {mname} ====================")
    m_rep = {}
    m_rep['record_count'] = len(records)
    
    # 1. Duplicates check
    ticker_date_pairs = [(r['ticker'], r['date']) for r in records]
    pair_counts = Counter(ticker_date_pairs)
    dups = {f"{k[0]}|{k[1]}": c for k, c in pair_counts.items() if c > 1}
    m_rep['duplicate_ticker_date_count'] = len(dups)
    m_rep['duplicate_ticker_date_samples'] = list(dups.items())[:10]
    print(f"Duplicate (ticker, date) records: {len(dups)}")
    
    # Group by ticker
    by_ticker = defaultdict(list)
    for r in records:
        by_ticker[r['ticker']].append(r)
        
    m_rep['unique_tickers'] = len(by_ticker)
    print(f"Unique tickers: {len(by_ticker)}")
    
    # Check date ordering, duplicate dates per ticker, observation counts
    ticker_stats = {}
    all_dates_set = set()
    chronology_violations = []
    
    for t, t_recs in by_ticker.items():
        dates = [r['date'] for r in t_recs]
        all_dates_set.update(dates)
        sorted_dates = sorted(dates)
        if dates != sorted_dates:
            chronology_violations.append(t)
            
        t_counts = Counter(dates)
        t_dups = [d for d, c in t_counts.items() if c > 1]
        
        ticker_stats[t] = {
            'count': len(t_recs),
            'unique_dates': len(set(dates)),
            'duplicate_dates_count': len(t_dups),
            'first_date': min(dates) if dates else None,
            'last_date': max(dates) if dates else None,
            'sector': t_recs[0]['sector'],
            'country': t_recs[0]['country']
        }
        
    m_rep['chronology_violations'] = chronology_violations
    print(f"Tickers with non-chronological order: {len(chronology_violations)}")
    
    obs_counts = [s['count'] for s in ticker_stats.values()]
    m_rep['min_obs_per_ticker'] = min(obs_counts)
    m_rep['max_obs_per_ticker'] = max(obs_counts)
    m_rep['obs_count_distribution'] = dict(Counter(obs_counts))
    print(f"Obs per ticker min={min(obs_counts)}, max={max(obs_counts)}, dist={dict(Counter(obs_counts))}")
    
    # Global calendar for market
    market_calendar = sorted(list(all_dates_set))
    m_rep['market_calendar_days'] = len(market_calendar)
    m_rep['market_start_date'] = market_calendar[0]
    m_rep['market_end_date'] = market_calendar[-1]
    print(f"Market calendar trading days: {len(market_calendar)} ({market_calendar[0]} to {market_calendar[-1]})")
    
    # Check trading-day gaps per ticker against the market calendar
    cal_date_to_idx = {d: i for i, d in enumerate(market_calendar)}
    ticker_missing_calendar_days = {}
    ticker_max_internal_gap = {}
    
    for t, t_recs in by_ticker.items():
        t_dates_set = set(r['date'] for r in t_recs)
        missing_market_days = [d for d in market_calendar if d not in t_dates_set]
        # Only consider missing days between the ticker's first and last date
        t_min_d = ticker_stats[t]['first_date']
        t_max_d = ticker_stats[t]['last_date']
        internal_missing = [d for d in missing_market_days if t_min_d <= d <= t_max_d]
        ticker_missing_calendar_days[t] = len(internal_missing)
        
        # Check max day gap between consecutive observations (calendar days)
        s_dates = sorted(list(t_dates_set))
        max_cal_gap = 0
        for i in range(len(s_dates) - 1):
            d1 = datetime.strptime(s_dates[i], '%Y-%m-%d')
            d2 = datetime.strptime(s_dates[i+1], '%Y-%m-%d')
            gap_days = (d2 - d1).days
            if gap_days > max_cal_gap:
                max_cal_gap = gap_days
        ticker_max_internal_gap[t] = max_cal_gap

    m_rep['ticker_internal_missing_market_days'] = ticker_missing_calendar_days
    m_rep['tickers_with_missing_internal_market_days'] = {t: c for t, c in ticker_missing_calendar_days.items() if c > 0}
    print(f"Tickers with missing internal trading days: {len(m_rep['tickers_with_missing_internal_market_days'])}")
    if m_rep['tickers_with_missing_internal_market_days']:
        print("Samples:", list(m_rep['tickers_with_missing_internal_market_days'].items())[:5])
        
    # Price validity: non-positive, NaN, Infinite
    invalid_prices = []
    extreme_returns = []
    large_jumps = [] # > 30% absolute daily change
    
    for t, t_recs in by_ticker.items():
        # Sort chronologically
        s_recs = sorted(t_recs, key=lambda x: x['date'])
        for idx, r in enumerate(s_recs):
            c = r.get('close')
            if c is None or math.isnan(c) or math.isinf(c) or c <= 0:
                invalid_prices.append((t, r['date'], c))
            if idx > 0:
                prev_c = s_recs[idx-1].get('close')
                if prev_c and c and prev_c > 0 and c > 0:
                    ret = (c - prev_c) / prev_c
                    log_ret = math.log(c / prev_c)
                    if abs(log_ret) > 0.5: # ~65% change or extreme
                        extreme_returns.append({
                            'ticker': t,
                            'date': r['date'],
                            'prev_date': s_recs[idx-1]['date'],
                            'prev_close': prev_c,
                            'close': c,
                            'pct_change': round(ret * 100, 2),
                            'log_ret': round(log_ret, 4)
                        })
                    if abs(ret) >= 0.30: # 30% jump
                        large_jumps.append({
                            'ticker': t,
                            'date': r['date'],
                            'prev_date': s_recs[idx-1]['date'],
                            'prev_close': prev_c,
                            'close': c,
                            'pct_change': round(ret * 100, 2)
                        })

    m_rep['invalid_prices_count'] = len(invalid_prices)
    m_rep['invalid_prices_samples'] = invalid_prices[:5]
    print(f"Invalid prices (<=0, NaN, Inf): {len(invalid_prices)}")
    
    m_rep['extreme_returns_count'] = len(extreme_returns)
    m_rep['extreme_returns'] = extreme_returns
    print(f"Extreme daily returns (|log_ret| > 0.5): {len(extreme_returns)}")
    if extreme_returns:
        print("Extreme returns samples:", extreme_returns[:5])
        
    m_rep['large_jumps_30pct_count'] = len(large_jumps)
    m_rep['large_jumps_30pct'] = large_jumps
    print(f"Large daily jumps (|pct_change| >= 30%): {len(large_jumps)}")

    # Ticker -> Sector and Ticker -> Country consistency
    ticker_sector_map = defaultdict(set)
    ticker_country_map = defaultdict(set)
    for r in records:
        ticker_sector_map[r['ticker']].add(r['sector'])
        ticker_country_map[r['ticker']].add(r['country'])
        
    multi_sectors = {t: list(s) for t, s in ticker_sector_map.items() if len(s) > 1}
    multi_countries = {t: list(c) for t, c in ticker_country_map.items() if len(c) > 1}
    m_rep['ticker_multi_sector_inconsistencies'] = multi_sectors
    m_rep['ticker_multi_country_inconsistencies'] = multi_countries
    print(f"Tickers with multiple sectors: {len(multi_sectors)}")
    print(f"Tickers with multiple countries: {len(multi_countries)}")
    
    # Sector distribution
    sector_dist = Counter([s['sector'] for s in ticker_stats.values()])
    m_rep['sector_distribution'] = dict(sector_dist)
    print(f"Sector distribution (tickers per sector): {dict(sector_dist)}")

    # Specific Indian checks
    if mname == 'India':
        ohlc_violations = []
        volume_violations = []
        cap_size_map = defaultdict(set)
        
        for r in records:
            o, h, l, c, v = r['open'], r['high'], r['low'], r['close'], r['volume']
            t, d = r['ticker'], r['date']
            cap_size_map[t].add(r['cap_size'])
            
            # OHLC consistency: low <= open/close <= high
            # Using small epsilon for floating point
            eps = 1e-5
            if not (l - eps <= o <= h + eps and l - eps <= c <= h + eps and l <= h + eps):
                ohlc_violations.append({
                    'ticker': t, 'date': d, 'open': o, 'high': h, 'low': l, 'close': c
                })
            # Volume validity
            if v is None or math.isnan(v) or v < 0:
                volume_violations.append({'ticker': t, 'date': d, 'volume': v})
            elif v == 0:
                pass # 0 volume might happen on illiquid days, note it
                
        zero_volume_count = sum(1 for r in records if r['volume'] == 0)
        multi_caps = {t: list(cs) for t, cs in cap_size_map.items() if len(cs) > 1}
        
        m_rep['indian_ohlc_violations_count'] = len(ohlc_violations)
        m_rep['indian_ohlc_violations_samples'] = ohlc_violations[:5]
        m_rep['indian_invalid_volume_count'] = len(volume_violations)
        m_rep['indian_zero_volume_count'] = zero_volume_count
        m_rep['indian_multi_cap_size_inconsistencies'] = multi_caps
        m_rep['indian_cap_size_distribution'] = dict(Counter([list(cs)[0] for cs in cap_size_map.values()]))
        
        print(f"Indian OHLC violations (low <= open/close <= high): {len(ohlc_violations)}")
        if ohlc_violations:
            print("OHLC violation samples:", ohlc_violations[:5])
        print(f"Indian negative/NaN volume: {len(volume_violations)}, zero volume: {zero_volume_count}")
        print(f"Indian tickers with multiple Cap Sizes: {len(multi_caps)}")
        print(f"Indian Cap Size distribution per ticker: {m_rep['indian_cap_size_distribution']}")
        
    m_rep['ticker_details'] = ticker_stats
    report[mname] = m_rep

# Cross-market checks
print("\n==================== CROSS-MARKET AUDIT ====================")
us_tickers = set(report['US']['ticker_details'].keys())
jse_tickers = set(report['JSE']['ticker_details'].keys())
india_tickers = set(report['India']['ticker_details'].keys())

cross_overlap = {
    'US_and_JSE': list(us_tickers.intersection(jse_tickers)),
    'US_and_India': list(us_tickers.intersection(india_tickers)),
    'JSE_and_India': list(jse_tickers.intersection(india_tickers)),
}
print("Tickers appearing in multiple markets:", cross_overlap)

# Cleaned ticker stems check (e.g. without .JO or .BSE)
us_stems = us_tickers
jse_stems = {t.replace('.JO', '') for t in jse_tickers}
india_stems = {t.replace('.BSE', '') for t in india_tickers}

stem_overlap = {
    'US_and_JSE_stems': list(us_stems.intersection(jse_stems)),
    'US_and_India_stems': list(us_stems.intersection(india_stems)),
    'JSE_and_India_stems': list(jse_stems.intersection(india_stems)),
}
print("Stem overlaps (symbol names without exchange suffix):", stem_overlap)

cross_market_rep = {
    'ticker_overlap': cross_overlap,
    'stem_overlap': stem_overlap,
    'market_comparisons': {
        'US': {'tickers': len(us_tickers), 'records': len(datasets['US']), 'days': report['US']['market_calendar_days']},
        'JSE': {'tickers': len(jse_tickers), 'records': len(datasets['JSE']), 'days': report['JSE']['market_calendar_days']},
        'India': {'tickers': len(india_tickers), 'records': len(datasets['India']), 'days': report['India']['market_calendar_days']}
    }
}
report['cross_market'] = cross_market_rep

os.makedirs('research/results/phase_02', exist_ok=True)
with open('research/results/phase_02/data_audit_results.json', 'w') as f:
    json.dump(report, f, indent=2)

print("\nAudit complete! Output saved to research/results/phase_02/data_audit_results.json")
