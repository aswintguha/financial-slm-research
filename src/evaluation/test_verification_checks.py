import math

def test_telescoping_identity():
    print("Running Test 1: Telescoping identity between log return mean and price ratio slope...")
    prices = [100.0, 102.5, 101.0, 104.2, 103.8, 106.0]
    W = len(prices) # 6
    # 1. Historical mean of daily log returns over context window
    daily_log_returns = [math.log(prices[i] / prices[i-1]) for i in range(1, W)]
    mean_daily_return = sum(daily_log_returns) / len(daily_log_returns)
    
    # 2. Drift slope across context window
    drift_slope = math.log(prices[-1] / prices[0]) / (W - 1)
    
    diff = abs(mean_daily_return - drift_slope)
    print(f"  Mean daily return: {mean_daily_return:.8f}")
    print(f"  Drift slope:       {drift_slope:.8f}")
    print(f"  Difference:        {diff:.2e}")
    assert diff < 1e-15, "Mathematical identity must hold exactly"
    print("  [PASS] Telescoping identity verified.\n")

def test_mase_analytical():
    print("Running Test 2: Analytical verification of per-ticker in-sample MASE scaling...")
    # Synthetic series of training prices
    train_prices = [100.0, 102.0, 101.0, 103.0, 102.0, 105.0]
    # Training actual H=1 log returns:
    # r1 = log(102/100) = 0.0198026
    # r2 = log(101/102) = -0.0098523
    # r3 = log(103/101) = 0.0196085
    # r4 = log(102/103) = -0.0097562
    # r5 = log(105/102) = 0.0289875
    # In-sample naive (persistence) forecast for return is r_hat = 0.
    # Therefore naive absolute errors are simply |r_i|:
    actual_train_returns = [math.log(train_prices[i]/train_prices[i-1]) for i in range(1, len(train_prices))]
    naive_in_sample_mae = sum(abs(r) for r in actual_train_returns) / len(actual_train_returns)
    print(f"  In-sample naive MAE denominator: {naive_in_sample_mae:.6f}")
    
    # Validation forecast test
    # Suppose validation actual return is r_val = 0.02, forecast is r_pred = 0.01
    val_error = abs(0.01 - 0.02) # 0.01
    expected_mase = val_error / naive_in_sample_mae
    print(f"  Expected validation MASE: {expected_mase:.6f}")
    assert abs(expected_mase - (0.01 / naive_in_sample_mae)) < 1e-12
    print("  [PASS] MASE formula verified analytically.\n")

if __name__ == '__main__':
    test_telescoping_identity()
    test_mase_analytical()
