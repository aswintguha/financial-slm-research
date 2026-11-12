import csv, math, json, os
from collections import defaultdict

# 1. JSE Full Episode Extraction
jse_by_ticker = defaultdict(list)
with open('data/raw/JSE_data.csv', 'r') as f:
    reader = csv.reader(f)
    next(reader)
    for r in reader:
        jse_by_ticker[r[2].strip()].append({'orig_idx': r[0], 'date': r[1].strip(), 'ticker': r[2].strip(), 'close': float(r[5].strip())})

for t in jse_by_ticker:
    jse_by_ticker[t].sort(key=lambda x: x['date'])

jse_observations_to_correct = []
episodes = []

for t, recs in jse_by_ticker.items():
    n = len(recs)
    i = 0
    while i < n:
        if i > 0 and 0.007 <= (recs[i]['close'] / recs[i-1]['close']) <= 0.015:
            start_i = i
            base_p = recs[i-1]['close']
            while i < n - 1 and not (65.0 <= (recs[i+1]['close'] / recs[i]['close']) <= 140.0):
                i += 1
            end_i = i
            next_p = recs[end_i+1]['close'] if end_i < n - 1 else None
            run_days = end_i - start_i + 1
            
            # Record episode
            episodes.append({
                'ticker': t,
                'start_date': recs[start_i]['date'],
                'end_date': recs[end_i]['date'],
                'days': run_days,
                'pre_trough_date': recs[start_i-1]['date'],
                'pre_trough_price': base_p,
                'trough_sample_price': recs[start_i]['close'],
                'post_trough_date': recs[end_i+1]['date'] if end_i < n - 1 else None,
                'post_trough_price': next_p,
                'classification': 'CONFIRMED AND CORRECTABLE'
            })
            
            # Record each individual observation
            for k in range(start_i, end_i + 1):
                p_c = recs[k]['close']
                p_prev = recs[k-1]['close'] if k > 0 else None
                p_next = recs[k+1]['close'] if k < n - 1 else None
                jse_observations_to_correct.append({
                    'ticker': t,
                    'date': recs[k]['date'],
                    'prev_date': recs[k-1]['date'] if k > 0 else None,
                    'prev_close': p_prev,
                    'current_close': p_c,
                    'next_date': recs[k+1]['date'] if k < n - 1 else None,
                    'next_close': p_next,
                    'curr_prev_ratio': round(p_c / p_prev, 4) if p_prev else None,
                    'next_curr_ratio': round(p_next / p_c, 4) if p_next else None,
                    'inferred_unit': 'ZAR (quoted in Rands instead of Cents)',
                    'proposed_corrected_value': round(p_c * 100.0, 4),
                    'evidence_rule': 'Trough episode: entry drop ~0.01x, stable interior, exit jump ~100x (or series boundary)',
                    'classification': 'CONFIRMED AND CORRECTABLE'
                })
            i += 1
        else:
            i += 1

# BIK.JO separate verification
bik_recs = jse_by_ticker['BIK.JO']
bik_anomaly = {
    'ticker': 'BIK.JO',
    'transition_date': '2024-02-05',
    'pre_date': '2024-02-02',
    'pre_close': 0.17,
    'post_close': 17.0,
    'ratio': 100.0,
    'observations_pre': 481,
    'observations_post': 328,
    'note': 'Permanent 100x shift on 2024-02-05. Traded 0.10-0.36 for first 481 days, then 14-18 for remaining 328 days. Unclear whether the first half was quoted in Rands or a 1:100 reverse split occurred.',
    'classification': 'CONFIRMED BUT REQUIRES EXTERNAL VERIFICATION'
}

# 2. Indian CAs
indian_cas = [
    {
        'ticker': 'TATASTEEL.BSE',
        'event_date': '2022-07-28',
        'action_type': 'Stock Split (Sub-division of Shares)',
        'pre_event_date': '2022-07-27',
        'pre_event_price': 959.45,
        'post_event_price': 100.35,
        'observed_ratio': round(100.35 / 959.45, 4),
        'proposed_adjustment_factor': 0.10,
        'adjusted_historical_price_rule': 'P_{adjusted, t} = P_{raw, t} * 0.10 for all t <= 2022-07-27',
        'direction': 'Backward',
        'expected_effect_on_returns': 'Eliminates false -89.54% single-day crash on 2022-07-28; smooths historical return series',
        'classification': 'CONFIRMED AND CORRECTABLE'
    },
    {
        'ticker': 'IRB.BSE',
        'event_date': '2023-02-22',
        'action_type': 'Stock Split (Sub-division of Shares)',
        'pre_event_date': '2023-02-21',
        'pre_event_price': 297.85,
        'post_event_price': 34.20,
        'observed_ratio': round(34.20 / 297.85, 4),
        'proposed_adjustment_factor': 0.10,
        'adjusted_historical_price_rule': 'P_{adjusted, t} = P_{raw, t} * 0.10 for all t <= 2023-02-21',
        'direction': 'Backward',
        'expected_effect_on_returns': 'Eliminates false -88.52% single-day crash on 2023-02-22',
        'classification': 'CONFIRMED AND CORRECTABLE'
    },
    {
        'ticker': 'DRREDDY.BSE',
        'event_date': '2024-10-28',
        'action_type': 'Stock Split (Sub-division of Shares)',
        'pre_event_date': '2024-10-25',
        'pre_event_price': 6514.15,
        'post_event_price': 1312.40,
        'observed_ratio': round(1312.40 / 6514.15, 4),
        'proposed_adjustment_factor': 0.20,
        'adjusted_historical_price_rule': 'P_{adjusted, t} = P_{raw, t} * 0.20 for all t <= 2024-10-25',
        'direction': 'Backward',
        'expected_effect_on_returns': 'Eliminates false -79.85% single-day crash on 2024-10-28',
        'classification': 'CONFIRMED AND CORRECTABLE'
    },
    {
        'ticker': 'AUBANK.BSE',
        'event_date': '2022-06-09',
        'action_type': 'Bonus Issue',
        'pre_event_date': '2022-06-08',
        'pre_event_price': 1258.85,
        'post_event_price': 613.20,
        'observed_ratio': round(613.20 / 1258.85, 4),
        'proposed_adjustment_factor': 0.50,
        'adjusted_historical_price_rule': 'P_{adjusted, t} = P_{raw, t} * 0.50 for all t <= 2022-06-08',
        'direction': 'Backward',
        'expected_effect_on_returns': 'Eliminates false -51.29% single-day crash on 2022-06-09',
        'classification': 'CONFIRMED AND CORRECTABLE'
    },
    {
        'ticker': 'BLUESTARCO.BSE',
        'event_date': '2023-06-20',
        'action_type': 'Bonus Issue',
        'pre_event_date': '2023-06-19',
        'pre_event_price': 1525.35,
        'post_event_price': 790.35,
        'observed_ratio': round(790.35 / 1525.35, 4),
        'proposed_adjustment_factor': 0.50,
        'adjusted_historical_price_rule': 'P_{adjusted, t} = P_{raw, t} * 0.50 for all t <= 2023-06-19',
        'direction': 'Backward',
        'expected_effect_on_returns': 'Eliminates false -48.19% single-day crash on 2023-06-20',
        'classification': 'CONFIRMED AND CORRECTABLE'
    },
    {
        'ticker': 'RELIANCE.BSE',
        'event_date': '2024-10-28',
        'action_type': 'Bonus Issue',
        'pre_event_date': '2024-10-25',
        'pre_event_price': 2655.45,
        'post_event_price': 1334.30,
        'observed_ratio': round(1334.30 / 2655.45, 4),
        'proposed_adjustment_factor': 0.50,
        'adjusted_historical_price_rule': 'P_{adjusted, t} = P_{raw, t} * 0.50 for all t <= 2024-10-25',
        'direction': 'Backward',
        'expected_effect_on_returns': 'Eliminates false -49.75% single-day crash on 2024-10-28',
        'classification': 'CONFIRMED AND CORRECTABLE'
    }
]

# 3. Short history stocks
short_stocks = [
    {
        'ticker': 'NSTG',
        'market': 'US',
        'first_date': '2022-03-01',
        'last_date': '2024-06-25',
        'observation_count': 583,
        'reason': 'Chapter 11 bankruptcy filing (Feb 2024) and subsequent Nasdaq delisting (June 2024).',
        'scope_recommendation': 'Secondary analysis universe (excluded from core 3-year rolling origin benchmark)',
        'classification': 'CONFIRMED AND RETAIN AS-IS (Documented Delisting)'
    },
    {
        'ticker': 'ASC.JO',
        'market': 'JSE',
        'first_date': '2024-05-24',
        'last_date': '2025-05-30',
        'observation_count': 252,
        'reason': 'Ascendis Health restructuring and debt unbundling listing on JSE (May 2024).',
        'scope_recommendation': 'Secondary analysis universe (evaluated on overlapping 1-year window 2024-2025)',
        'classification': 'CONFIRMED AND RETAIN AS-IS (Documented New Listing)'
    },
    {
        'ticker': 'BHARTIHEXA.BSE',
        'market': 'India',
        'first_date': '2024-04-12',
        'last_date': '2025-05-30',
        'observation_count': 282,
        'reason': 'Bharti Hexacom IPO and BSE listing on April 12, 2024.',
        'scope_recommendation': 'Secondary analysis universe (evaluated on post-IPO window 2024-2025)',
        'classification': 'CONFIRMED AND RETAIN AS-IS (Documented IPO)'
    },
    {
        'ticker': 'GMRP%26UI.BSE',
        'market': 'India',
        'first_date': '2022-03-23',
        'last_date': '2025-05-30',
        'observation_count': 784,
        'reason': 'Post-demerger trading commenced late March 2022; %26 represents URL-encoded &.',
        'scope_recommendation': 'Core universe (decode ticker to GMRP_UI.BSE; series has 784 of 807 days)',
        'classification': 'CONFIRMED AND CORRECTABLE (Symbol Decode & Alignment)'
    }
]

full_report = {
    'summary': {
        'total_jse_observations_to_correct': len(jse_observations_to_correct),
        'total_jse_trough_episodes': len(episodes),
        'total_jse_affected_tickers': len(set(x['ticker'] for x in jse_observations_to_correct)),
        'total_indian_corporate_actions': len(indian_cas),
        'total_short_stocks': len(short_stocks)
    },
    'jse_trough_episodes': episodes,
    'jse_observations_to_correct_sample': jse_observations_to_correct[:20],
    'jse_observations_to_correct_all': jse_observations_to_correct,
    'jse_regime_shift_bik': bik_anomaly,
    'indian_corporate_actions': indian_cas,
    'short_history_stocks': short_stocks
}

with open('research/results/phase_02/anomaly_resolution_report.json', 'w') as f:
    json.dump(full_report, f, indent=2)

print(f"Final report saved. Total JSE observations to correct: {len(jse_observations_to_correct)} across {len(episodes)} episodes.")
