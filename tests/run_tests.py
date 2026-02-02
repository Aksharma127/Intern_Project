"""Lightweight test runner to avoid requiring pytest in the environment."""
import importlib.util
import sys
from pathlib import Path

# Ensure project root is on sys.path so imports like `agents.*` work when running from `tests/`
ROOT = str(Path(__file__).resolve().parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Import tests/test_confidence.py as a module without pytest
spec = importlib.util.spec_from_file_location("test_confidence", str(Path(__file__).parent / "test_confidence.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)



def run_all(report: bool = False, report_dir: str = None):
    from agents.orchestrator import Orchestrator
    from pathlib import Path
    import json
    from agents import reporting

    # Test 1: overlap/penalty scenario
    print("Running test: test_overlap_penalty_and_message...")
    # reproduce the test scenario inputs (use repository data paths)
    ROOT = Path(__file__).resolve().parent.parent
    po_db = json.load(open(ROOT / "data" / "database" / "purchase_orders.json", "r"))
    extracted = json.loads(open(ROOT / "data" / "mock_extraction" / "invoice_5_extracted.json").read())

    orch = Orchestrator(po_db)
    # generate a processing result to visualize
    res = orch.process(extracted)

    # run the test assertions
    mod.test_overlap_penalty_and_message()
    print("OK")

    if report:
        print("Generating HTML report for test_overlap_penalty_and_message...")
        reporting.generate_html_report(res, title="test_overlap_penalty_and_message", output_path=report_dir)

    # Test 2: decision confidence math
    print("Running test: test_decision_confidence_math...")
    mod.test_decision_confidence_math()
    print("OK")

    if report:
        # produce a synthetic report for the decision confidence math test
        orch2 = Orchestrator([])
        dec = orch2.compute_decision_confidence(0.92, 0.7, 0.6, penalty_factor=0.9604)
        dec_report = {
            "extraction_confidence": 0.92,
            "matching_results": {"po_match_confidence": 0.7},
            "discrepancies": [],
            "decision_confidence": dec,
            "recommended_action": "flag_for_review",
            "agent_messages": [],
        }
        print("Generating HTML report for test_decision_confidence_math...")
        reporting.generate_html_report(dec_report, title="test_decision_confidence_math", output_path=report_dir)

    print("All tests passed.")


if __name__ == "__main__":
    # add optional CLI flag --report and --report-dir
    import sys
    args = sys.argv[1:]
    report = "--report" in args
    report_dir = None
    for a in args:
        if a.startswith("--report-dir="):
            report_dir = a.split("=", 1)[1]

    run_all(report=report, report_dir=report_dir)
