"""Final smoke test for demo readiness: Invoice 5 happy path."""
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_cmd(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def test_invoice_5_demo_smoke():
    cmd = [sys.executable, str(PROJECT_ROOT / "process_invoice.py"), str(PROJECT_ROOT / "data" / "mock_extraction" / "invoice_5_extracted.json"), str(PROJECT_ROOT / "data" / "database" / "purchase_orders.json")]
    code, out = run_cmd(cmd)
    assert code == 0, f"process_invoice exited with code {code}\n{out}"
    assert "PO-2024-005" in out, f"Expected PO-2024-005 in output:\n{out}"
    assert "FLAG_FOR_REVIEW" in out, f"Expected FLAG_FOR_REVIEW in output:\n{out}"
    # Ensure there are no price mismatch lines
    assert "DISCREPANCY DETECTED" not in out and "price_mismatch" not in out.lower(), f"Unexpected discrepancy output:\n{out}"


if __name__ == "__main__":
    test_invoice_5_demo_smoke()
    print("Smoke test passed.")
