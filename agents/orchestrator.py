"""Orchestrator: wires agents, computes layered confidences and final decisions"""
from typing import Dict, Any
from .agent_state import AgentState
from .matching import MatchingAgent
from .validation import ValidationAgent


class Orchestrator:
    def __init__(self, po_db):
        # support either a list of POs or a dict with key 'purchase_orders' (file load)
        if isinstance(po_db, dict) and "purchase_orders" in po_db:
            po_list = po_db["purchase_orders"]
        else:
            po_list = po_db
        self.state = AgentState()
        self.matching = MatchingAgent(po_list, self.state)
        self.validation = ValidationAgent(self.state)

    def compute_decision_confidence(self, extracted_conf: float, match_conf: float, discrepancy_conf: float, penalty_factor: float = 1.0) -> float:
        # Decision-level = min of layer confidences and apply penalty
        base = min(extracted_conf, match_conf, discrepancy_conf)
        return float(max(0.0, min(1.0, base * penalty_factor)))

    def process(self, extracted: Dict[str, Any]) -> Dict[str, Any]:
        self.state.start_timer()

        self.state.record_invocation("Orchestrator")

        # Field-level confidence: assume extraction provides an overall extraction_confidence
        extraction_conf = float(extracted.get("extraction_confidence", 0.9))

        matching_results = self.matching.match_invoice(extracted)
        match_conf = float(matching_results.get("po_match_confidence", 0.0))

        # Very simple discrepancy confidence: if no discrepancies -> 1.0 else (1 - max severity fraction)
        discrepancies = extracted.get("discrepancies", [])
        if not discrepancies:
            discrepancy_conf = 1.0
        else:
            # map severities: low=0.9, medium=0.6, high=0.2
            severity_scores = [
                0.9 if d.get("severity") == "low" else 0.6
                if d.get("severity") == "medium" else 0.2
                for d in discrepancies
            ]
            worst = min(1.0, max(severity_scores))
            discrepancy_conf = worst

        # Initial penalty factor based on whether any agents requested help
        penalty = 1.0
        for m in self.state.messages:
            if m.next_action:
                penalty *= 0.98  # small penalty per outgoing request

        decision_conf = self.compute_decision_confidence(extraction_conf, match_conf, discrepancy_conf, penalty)

        # Simple recommended action logic based on rules (soft, agentic reasoning)
        recommended_action = "flag_for_review"
        if decision_conf > 0.90 and (match_conf > 0.95) and not discrepancies:
            recommended_action = "auto_approve"
        elif any(d.get("severity") == "high" for d in discrepancies) or match_conf < 0.5:
            recommended_action = "escalate_to_human"

        processing_results = {
            "extraction_confidence": extraction_conf,
            "document_quality": extracted.get("document_quality", "unknown"),
            "extracted_data": extracted,
            "matching_results": matching_results,
            "discrepancies": discrepancies,
            "recommended_action": recommended_action,
            "decision_confidence": decision_conf,
            "agent_messages": [m.to_dict() for m in self.state.messages],
        }

        # Run final validation self-check
        validation = self.validation.validate(processing_results)
        penalty_factor = validation.get("penalty_factor", 1.0)
        # apply additional penalty
        if penalty_factor < 1.0:
            processing_results["decision_confidence"] = float(processing_results["decision_confidence"] * penalty_factor)
            # if validation suggested downgrade, apply it
            for m in validation.get("messages", []):
                if m.get("next_action") == "downgrade_to_flag":
                    processing_results["recommended_action"] = "flag_for_review"
                if m.get("next_action") == "escalate":
                    processing_results["recommended_action"] = "escalate_to_human"

        self.state.stop_timer()
        processing_results.update(self.state.to_dict())

        return processing_results


# Helper CLI run
if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 3:
        print("Usage: python agents/orchestrator.py <extracted_invoice.json> <purchase_orders.json>")
        sys.exit(1)

    extracted_file = sys.argv[1]
    po_db_file = sys.argv[2]
    with open(extracted_file, "r") as f:
        extracted = json.load(f)
    with open(po_db_file, "r") as f:
        po_db = json.load(f)

    orch = Orchestrator(po_db)
    result = orch.process(extracted)
    print(json.dumps(result, indent=2))
