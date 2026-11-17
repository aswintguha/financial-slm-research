"""
Reproducibility script for Gate 5.0 Stage A Hardware & MPS / bfloat16 Tensor-Level Verification.
Executed on Apple Silicon (macOS Darwin arm64) using PyTorch 2.5.1 under Python 3.12.16.

Numerical Tolerances Documented:
- IEEE bfloat16 utilizes 1 sign bit, 8 exponent bits, and 7 mantissa bits (~1e-2 to 1e-3 relative resolution).
- For a 512-dimensional inner product of standard normal variables, accumulated variance yields
  expected absolute discrepancies bounded by max_abs_err < 1.0 and mean relative error rel_err < 0.05.
- Observed empirically: Max Absolute Error = 0.394081, Mean Relative Error = 0.018595 (1.86%).
"""

import torch

def verify_hardware_stage_a():
    print("=== STAGE A HARDWARE & MPS / BFLOAT16 VERIFICATION ===")
    print("PyTorch Version:", torch.__version__)
    print("MPS Built:", torch.backends.mps.is_built())
    print("MPS Available:", torch.backends.mps.is_available())
    assert torch.backends.mps.is_available(), "ERROR: MPS is not available on this Apple Silicon system."

    device = torch.device("mps")

    # 1. Tensor Allocation and Synchronization
    print("\n[Test 1: Tensor Allocation and Synchronization]")
    x_bf16 = torch.ones((1024, 1024), dtype=torch.bfloat16, device=device)
    y_bf16 = torch.randn((1024, 1024), dtype=torch.bfloat16, device=device)
    torch.mps.synchronize()
    print("  Allocated x and y (1024x1024 bfloat16 on mps).")
    print("  torch.mps.synchronize() call succeeded.")

    # 2. bfloat16 Matrix Multiplication (GEMM)
    print("\n[Test 2: bfloat16 GEMM (Matrix Multiplication)]")
    z_bf16 = torch.matmul(x_bf16, y_bf16)
    torch.mps.synchronize()
    print("  torch.matmul in bfloat16 on MPS completed.")

    # 3. Finite Values & NaN/Inf Verification
    print("\n[Test 3: Finite Values & NaN/Inf Verification]")
    has_nan = torch.isnan(z_bf16).any().item()
    has_inf = torch.isinf(z_bf16).any().item()
    print("  Contains NaN:", has_nan)
    print("  Contains Inf:", has_inf)
    assert not has_nan, "ERROR: bfloat16 calculation produced NaN values!"
    assert not has_inf, "ERROR: bfloat16 calculation produced Inf values!"
    print("  All elements are finite.")

    # 4. Numerical Parity with CPU float32 Reference
    print("\n[Test 4: Numerical Parity with CPU float32 Reference]")
    torch.manual_seed(42)
    a_cpu_f32 = torch.randn((512, 512), dtype=torch.float32)
    b_cpu_f32 = torch.randn((512, 512), dtype=torch.float32)
    ref_cpu_f32 = torch.matmul(a_cpu_f32, b_cpu_f32)

    a_mps_bf16 = a_cpu_f32.to(device=device, dtype=torch.bfloat16)
    b_mps_bf16 = b_cpu_f32.to(device=device, dtype=torch.bfloat16)
    res_mps_bf16 = torch.matmul(a_mps_bf16, b_mps_bf16)
    torch.mps.synchronize()

    res_mps_to_cpu = res_mps_bf16.to(dtype=torch.float32, device="cpu")

    abs_diff = torch.abs(ref_cpu_f32 - res_mps_to_cpu)
    max_abs_err = abs_diff.max().item()
    mean_abs_err = abs_diff.mean().item()
    rel_err = (abs_diff / (torch.abs(ref_cpu_f32) + 1e-7)).mean().item()

    print(f"  Max Absolute Difference:  {max_abs_err:.6f} (tolerance threshold: < 1.0)")
    print(f"  Mean Absolute Difference: {mean_abs_err:.6f}")
    print(f"  Mean Relative Difference: {rel_err:.6f} (tolerance threshold: < 0.05)")

    assert max_abs_err < 1.0, f"ERROR: Discrepancy too large ({max_abs_err})"
    assert rel_err < 0.05, f"ERROR: Relative error too large ({rel_err})"
    print("  Numerical parity within expected bfloat16 representation bounds.")

    # 5. Non-linear Activation Operations
    print("\n[Test 5: Non-linear Operations (GELU, Softmax)]")
    acts = torch.nn.functional.gelu(res_mps_bf16[:10, :10])
    probs = torch.nn.functional.softmax(res_mps_bf16[:10, :10], dim=-1)
    torch.mps.synchronize()
    print("  GELU and Softmax operations completed successfully.")
    assert not torch.isnan(acts).any().item()
    assert not torch.isnan(probs).any().item()

    print("\n=== ALL STAGE A HARDWARE & BFLOAT16 TESTS PASSED ===")

if __name__ == "__main__":
    verify_hardware_stage_a()

