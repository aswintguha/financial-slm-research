import csv, math, json, os, sys
from collections import defaultdict
from typing import List, Dict, Any

# Add evaluation module to path
sys.path.append(os.path.abspath('src/evaluation'))
from evaluator import compute_metrics

print("Executing Phase 04: Statistical Baselines Execution & Evaluation...")

# 1. Load Split Definition & Universe Partitions
with open('research/results/phase_03/leakage_audit_results.json') as f:
    phase03_data = json.load(f)

splits = phase03_data['split_specifications']['splits']
train_start = splits['train']['start_date']
train_end = splits['train']['end_date']
val_start = splits['validation']['start_date']
val_end = splits['validation']['end_date']
test_start = splits['test']['start_date']
test_end = splits['test']['end_date']

secondary_tickers = set(phase03_data['universe_partitions']['secondary_tickers'])

# 2. Load Processed Global Common Data
records = []
with open('data/processed/global_equities_common.csv', 'r', encoding='utf-8') as f:
    r = csv.DictReader(f)
    for row in r:
        records.append({
            'date': row['date'],
            'ticker': row['ticker'],
            'sector': row['sector'],
            'country': row['country'],
            'close': float(row['close'])
        })

by_ticker = defaultdict(list)
for r in records:
    by_ticker[r['ticker']].append(r)

# Predefined Core Universe (146 stocks) vs Secondary (4 stocks)
core_tickers = sorted([t for t in by_ticker.keys() if t not in secondary_tickers])
print(f"Loaded {len(records)} records across {len(by_ticker)} tickers.")
print(f"Core Full-History Universe: {len(core_tickers)} tickers.")
print(f"Secondary Universe: {len(secondary_tickers)} tickers.")

# 3. Horizon and Window Setup
H_primary = 5
H_secondary = 1
W_context = 20

# 4. Generate Target Samples per Ticker
def build_samples_for_horizon(H: int):
    samples = []
    for t in core_tickers:
        recs = sorted(by_ticker[t], key=lambda x: x['date'])
        n = len(recs)
        for i in range(W_context - 1, n - H):
            d_origin = recs[i]['date']
            d_target = recs[i + H]['date']
            p_origin = recs[i]['close']
            p_target = recs[i + H]['close']
            target_log_ret = math.log(p_target / p_origin)
            
            # Determine split partition
            split_label = None
            if d_origin <= train_end:
                if d_target < val_start:
                    split_label = 'train'
            elif val_start <= d_origin <= val_end:
                if d_target < test_start:
                    split_label = 'val'
            elif test_start <= d_origin <= test_end:
                split_label = 'test'
                
            if split_label is not None:
                past_closes = [recs[k]['close'] for k in range(i - W_context + 1, i + 1)]
                past_daily_returns = [
                    math.log(past_closes[k] / past_closes[k - 1])
                    for k in range(1, len(past_closes))
                ]
                samples.append({
                    'ticker': t,
                    'sector': recs[i]['sector'],
                    'country': recs[i]['country'],
                    'origin_date': d_origin,
                    'target_date': d_target,
                    'origin_price': p_origin,
                    'target_price': p_target,
                    'target_log_return': target_log_ret,
                    'split': split_label,
                    'past_closes': past_closes,
                    'past_daily_returns': past_daily_returns
                })
    return samples

samples_H5 = build_samples_for_horizon(H=5)
samples_H1 = build_samples_for_horizon(H=1)

# 5. Baseline Prediction Functions
def predict_persistence(sample, H):
    return 0.0

def predict_historical_mean(sample, H):
    daily_rets = sample['past_daily_returns']
    mean_daily = sum(daily_rets) / len(daily_rets)
    return mean_daily * H

def predict_moving_average_5(sample, H):
    ma_rets = sample['past_daily_returns'][-5:]
    mean_ma = sum(ma_rets) / len(ma_rets)
    return mean_ma * H

def predict_drift(sample, H):
    p_start = sample['past_closes'][0]
    p_end = sample['past_closes'][-1]
    w_len = len(sample['past_closes'])
    drift_rate = math.log(p_end / p_start) / (w_len - 1)
    return drift_rate * H

# Precalculate strictly past-only in-sample training naive MAE for MASE scaling:
# Training samples only! Zero validation or test data is used.
train_samples_h5 = [s for s in samples_H5 if s['split'] == 'train']
train_actual_h5 = [s['target_log_return'] for s in train_samples_h5]
in_sample_naive_mae_h5 = sum(abs(y) for y in train_actual_h5) / len(train_actual_h5)

train_samples_h1 = [s for s in samples_H1 if s['split'] == 'train']
train_actual_h1 = [s['target_log_return'] for s in train_samples_h1]
in_sample_naive_mae_h1 = sum(abs(y) for y in train_actual_h1) / len(train_actual_h1)

print(f"Precalculated In-Sample Training Naive MAE (Denominator for MASE):")
print(f"  H=5 Training Naive MAE: {in_sample_naive_mae_h5:.6f}")
print(f"  H=1 Training Naive MAE: {in_sample_naive_mae_h1:.6f}")

baselines = {
    'Persistence': predict_persistence,
    'Historical_Mean': predict_historical_mean,
    'Moving_Average_5': predict_moving_average_5,
    'Drift': predict_drift
}

results_summary = {
    'mase_specification': {
        'denominator_description': 'Mean Absolute Error of the in-sample naive forecast (Persistence r_hat=0) computed strictly on training data',
        'training_naive_mae_h5': round(in_sample_naive_mae_h5, 6),
        'training_naive_mae_h1': round(in_sample_naive_mae_h1, 6),
        'leakage_protection': 'Denominator strictly computed on training split (2022-03-01 to 2024-03-29); zero validation/test visibility'
    }
}

for H_val, s_data, h_name, naive_mae in [(5, samples_H5, 'H5_Primary', in_sample_naive_mae_h5), (1, samples_H1, 'H1_Secondary', naive_mae := in_sample_naive_mae_h1)]:
    results_summary[h_name] = {}
    
    for split_name in ['train', 'val', 'test']:
        split_samples = [s for s in s_data if s['split'] == split_name]
        actual_returns = [s['target_log_return'] for s in split_samples]
        pers_preds = [predict_persistence(s, H_val) for s in split_samples]
        
        results_summary[h_name][split_name] = {}
        
        for b_name, b_fn in baselines.items():
            preds = [b_fn(s, H_val) for s in split_samples]
            is_pers = (b_name == 'Persistence')
            metrics = compute_metrics(
                actual=actual_returns,
                predicted=preds,
                persistence_predicted=pers_preds,
                in_sample_naive_mae=naive_mae,
                is_persistence_model=is_pers
            )
            results_summary[h_name][split_name][b_name] = metrics
            
            c_m = metrics['common_valid_subset']
            da_str = c_m['directional_accuracy_label']
            print(f"[{h_name}][{split_name.upper()}][{b_name:18}] RMSE: {c_m['rmse']:.6f} | MAE: {c_m['mae']:.6f} | RelRMSE: {c_m['relative_rmse_vs_persistence']:.4f} | MASE: {c_m['mase']} | DA: {da_str}")

# Save machine readable outputs
os.makedirs('research/results/phase_04', exist_ok=True)
with open('research/results/phase_04/baseline_metrics.json', 'w') as f:
    json.dump(results_summary, f, indent=2)

print("\nUpdated research/results/phase_04/baseline_metrics.json successfully.")
