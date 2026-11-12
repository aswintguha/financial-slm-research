import math
from evaluator import compute_metrics

def run_unit_tests():
    print("Running evaluator and target reconstruction unit tests...")
    
    # 1. Perfect forecast test
    actual = [0.01, -0.02, 0.015, -0.005]
    pred_perfect = [0.01, -0.02, 0.015, -0.005]
    m = compute_metrics(actual, pred_perfect, persistence_predicted=[0.0]*4)
    assert m['common_valid_subset']['mae'] == 0.0, "MAE should be 0 for perfect forecast"
    assert m['common_valid_subset']['rmse'] == 0.0, "RMSE should be 0 for perfect forecast"
    assert m['common_valid_subset']['directional_accuracy'] == 100.0, "DA should be 100% for perfect forecast"
    print("  [PASS] Perfect forecast test")

    # 2. Persistence baseline test (all 0.0 return)
    pers = [0.0, 0.0, 0.0, 0.0]
    m_pers = compute_metrics(actual, pers, persistence_predicted=pers)
    assert m_pers['common_valid_subset']['relative_rmse_vs_persistence'] == 1.0, "Rel RMSE of persistence to itself must be 1.0"
    print("  [PASS] Persistence relative RMSE test")

    # 3. Invalid prediction tracking & persistence-replacement test
    pred_with_invalid = [0.01, None, float('nan'), -0.005]
    m_inv = compute_metrics(actual, pred_with_invalid, persistence_predicted=[0.0]*4)
    assert m_inv['total_predictions'] == 4
    assert m_inv['valid_predictions'] == 2
    assert m_inv['invalid_predictions'] == 2
    assert m_inv['valid_output_pct'] == 50.0
    # On valid subset: actual [0.01, -0.005], pred [0.01, -0.005] -> MAE = 0.0
    assert m_inv['common_valid_subset']['mae'] == 0.0
    # On persistence-replaced: actual [0.01, -0.02, 0.015, -0.005], pred [0.01, 0.0, 0.0, -0.005]
    # errors = [0, 0.02, -0.015, 0], MAE = (0.02 + 0.015)/4 = 0.00875
    assert abs(m_inv['persistence_replaced']['mae'] - 0.00875) < 1e-6
    print("  [PASS] Invalid prediction and replacement test")

    # 4. Target construction & Price reconstruction test
    # P_origin = 100.0, P_future = 105.0
    # r = log(105 / 100)
    P_0 = 100.0
    P_H = 105.0
    r_target = math.log(P_H / P_0)
    # Price reconstruction: P_pred = P_0 * exp(r_pred)
    P_reconstructed = P_0 * math.exp(r_target)
    assert abs(P_reconstructed - P_H) < 1e-9, "Price reconstruction must exactly recover P_future"
    print("  [PASS] Target construction and price reconstruction mathematical identity test")

    print("All unit tests passed successfully!\n")

if __name__ == '__main__':
    run_unit_tests()
