import json
from agents.orchestrator import Orchestrator
from pathlib import Path

# Use repository data paths so tests run from any working directory
ROOT = Path(__file__).resolve().parent.parent


def load_po_db():
    with open(ROOT / "data" / "database" / "purchase_orders.json", "r") as f:
        data = json.load(f)
    return data.get("purchase_orders", data)


def test_overlap_penalty_and_message():
    # Arrange: load PO DB and invoice 5 (missing PO)
    po_db = load_po_db()
    extracted = json.loads(open(ROOT / "data" / "mock_extraction" / "invoice_5_extracted.json").read())

    orch = Orchestrator(po_db)

    # Act
    res = orch.process(extracted)

    # Assert: we should have overlap <= 1.0 for a fuzzy match and unmatched_items listed
    match = res["matching_results"]
    assert "overlap" in match
    assert match["overlap"] <= 1.0

    # Ensure we matched to the expected PO for Invoice 5 (supplier EuroChem Trading)
    assert match.get("matched_po") == "PO-2024-005"

    # Because the PO was inferred via fuzzy matching we should not auto-approve; expect a human flag
    assert res.get("recommended_action") == "flag_for_review"

    # If overlap < 0.75, the state should have a fallback recorded
    if match["overlap"] < 0.75:
        assert "fuzzy_po_match" in res["system_metrics"]["fallbacks_used"]

    # If po_match_confidence < 0.75, there should be an agent message requesting validation
    assert "po_match_confidence" in match
    if match["po_match_confidence"] < 0.75:
        assert any(m.get("next_action") == "request_validation" for m in res["agent_messages"]) 


def test_decision_confidence_math():
    orch = Orchestrator([])
    # scenario: extraction 0.92, match 0.7, discrepancy 0.6, penalty 0.98^2 -> expect min=0.6 then apply penalty
    dec = orch.compute_decision_confidence(0.92, 0.7, 0.6, penalty_factor=0.9604)
    assert abs(dec - (0.6 * 0.9604)) < 1e-6
