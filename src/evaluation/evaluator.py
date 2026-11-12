import math
from typing import List, Dict, Any, Optional

def compute_metrics(
    actual: List[float], 
    predicted: List[Optional[float]], 
    actual_origin_prices: Optional[List[float]] = None,
    persistence_predicted: Optional[List[float]] = None,
    in_sample_naive_mae: Optional[float] = None,
    is_persistence_model: bool = False
) -> Dict[str, Any]:
    """
    Unified multi-metric evaluator for financial time-series forecasting.
    Handles invalid/missing predictions transparently without silent imputation.
    Produces both common-valid-subset and persistence-replaced metrics.
    
    Persistence Directional Accuracy:
    - If is_persistence_model=True, directional_accuracy is set to None (N/A)
      because a constant zero-return forecast offers no directional prediction.
      Raw zero-hit rate is retained under 'zero_return_hit_rate'.
    """
    total = len(actual)
    if total == 0:
        return {'total': 0, 'valid': 0, 'invalid': 0, 'valid_pct': 0.0}
    
    # 1. Track validity
    valid_mask = [
        (p is not None and not math.isnan(p) and not math.isinf(p))
        for p in predicted
    ]
    valid_count = sum(valid_mask)
    invalid_count = total - valid_count
    valid_pct = round((valid_count / total) * 100.0, 4)
    
    # Helper for point metrics
    def calculate_core(y_true: List[float], y_pred: List[float]) -> Dict[str, Any]:
        n = len(y_true)
        if n == 0:
            return {
                'mae': float('nan'),
                'rmse': float('nan'),
                'nrmse': float('nan'),
                'mase': float('nan'),
                'directional_accuracy': None,
                'directional_accuracy_label': "N/A — zero-return forecast has no directional prediction" if is_persistence_model else None,
                'bias': float('nan')
            }
        errors = [p - y for p, y in zip(y_pred, y_true)]
        abs_errors = [abs(e) for e in errors]
        sq_errors = [e**2 for e in errors]
        
        mae = sum(abs_errors) / n
        rmse = math.sqrt(sum(sq_errors) / n)
        
        # NRMSE (normalized by range)
        y_range = max(y_true) - min(y_true)
        nrmse = (rmse / y_range) if y_range > 1e-12 else float('nan')
        
        # MASE (scaled by training-period in-sample naive MAE)
        mase = (mae / in_sample_naive_mae) if (in_sample_naive_mae is not None and in_sample_naive_mae > 1e-12) else float('nan')
        
        # Directional accuracy
        # For Persistence (which predicts constant 0.0), sign matching is undefined/non-directional.
        # We report DA as None (N/A) and record raw zero_return_hit_rate separately.
        correct_dir = 0
        for y, p in zip(y_true, y_pred):
            sign_y = 1 if y > 0 else (-1 if y < 0 else 0)
            sign_p = 1 if p > 0 else (-1 if p < 0 else 0)
            if sign_y == sign_p:
                correct_dir += 1
        raw_hit_rate = round((correct_dir / n) * 100.0, 4)
        
        if is_persistence_model:
            da_val = None
            da_label = "N/A — zero-return forecast has no directional prediction"
        else:
            da_val = raw_hit_rate
            da_label = f"{raw_hit_rate}%"
            
        # Bias (mean error = mean(pred - actual))
        bias = sum(errors) / n
        
        return {
            'mae': round(mae, 6),
            'rmse': round(rmse, 6),
            'nrmse': round(nrmse, 6),
            'mase': round(mase, 4) if not math.isnan(mase) else None,
            'directional_accuracy': da_val,
            'directional_accuracy_label': da_label,
            'raw_zero_return_hit_rate': raw_hit_rate if is_persistence_model else None,
            'bias': round(bias, 6)
        }

    # 2. Common Valid Subset Metrics
    valid_y_true = [y for y, m in zip(actual, valid_mask) if m]
    valid_y_pred = [p for p, m in zip(predicted, valid_mask) if m]
    common_metrics = calculate_core(valid_y_true, valid_y_pred)
    
    # 3. Persistence-Replaced Metrics
    replaced_y_pred = []
    for i in range(total):
        if valid_mask[i]:
            replaced_y_pred.append(predicted[i])
        else:
            default_p = persistence_predicted[i] if persistence_predicted is not None else 0.0
            replaced_y_pred.append(default_p)
            
    replaced_metrics = calculate_core(actual, replaced_y_pred)
    
    # Relative RMSE vs persistence
    rel_rmse_common = float('nan')
    rel_rmse_replaced = float('nan')
    if persistence_predicted is not None and len(persistence_predicted) == total:
        pers_valid = [p for p, m in zip(persistence_predicted, valid_mask) if m]
        pers_core_valid = calculate_core(valid_y_true, pers_valid)
        if pers_core_valid['rmse'] > 1e-12:
            rel_rmse_common = round(common_metrics['rmse'] / pers_core_valid['rmse'], 6)
            
        pers_core_all = calculate_core(actual, persistence_predicted)
        if pers_core_all['rmse'] > 1e-12:
            rel_rmse_replaced = round(replaced_metrics['rmse'] / pers_core_all['rmse'], 6)

    return {
        'total_predictions': total,
        'valid_predictions': valid_count,
        'invalid_predictions': invalid_count,
        'valid_output_pct': valid_pct,
        'common_valid_subset': {
            **common_metrics,
            'relative_rmse_vs_persistence': rel_rmse_common
        },
        'persistence_replaced': {
            **replaced_metrics,
            'relative_rmse_vs_persistence': rel_rmse_replaced
        },
        'efficiency': {
            'inference_time_sec': None,
            'memory_usage_mb': None
        }
    }
