"""Validation Agent: final self-check that applies reconciliation rules as soft checks

Refactor: use constants from config, add structured discrepancies, and append agent reasoning.
"""
from typing import Dict, Any, List
from .agent_state import AgentState
from .messages import AgentMessage
from .base_agent import BaseAgent
import logging
from core.config import PRICE_FLAG_LOW_PERCENT, PRICE_FLAG_HIGH_PERCENT

logger = logging.getLogger(__name__)


class ValidationAgent(BaseAgent):
    def __init__(self, state: AgentState, name: str = "ValidationAgent"):
        super().__init__(name)
        self.state = state

    def _evaluate_price_variances(self, processing_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Produce price-related discrepancies following reconciliation rules."""
        discrepancies = []
        extracted = processing_results.get("extracted_data", {})
        matched_po_id = processing_results.get("matching_results", {}).get("matched_po")
        # find PO object if provided via matching results (exact or suggested/fuzzy)
        suggested_po = processing_results.get("matching_results", {}).get("suggested_po_obj")

        # If neither exact matched_po_id nor a suggested PO object exists, skip price checks
        if not matched_po_id and not suggested_po:
            return discrepancies

        # Use the suggested PO object when exact match id is not available
        po_obj = suggested_po
        
        if not po_obj:
            return discrepancies

        invoice_lines = extracted.get("line_items", [])
        po_lines = po_obj.get("line_items", [])

        # Attempt to match line items by description approximation
        from difflib import SequenceMatcher

        def sim(a: str, b: str) -> float:
            if not a or not b:
                return 0.0
            return SequenceMatcher(None, a.lower(), b.lower()).ratio()

        for idx, inv_li in enumerate(invoice_lines):
            # Find best matching po line
            best = None
            best_score = 0.0
            for po_li in po_lines:
                s = sim(inv_li.get("description", ""), po_li.get("description", ""))
                if s > best_score:
                    best_score = s
                    best = po_li
            if not best:
                continue

            inv_price = float(inv_li.get("unit_price", inv_li.get("line_total", 0.0)))
            po_price = float(best.get("unit_price", best.get("line_total", 0.0)))
            if po_price == 0:
                continue
            delta = inv_price - po_price
            perc = abs(delta) / po_price

            if perc > PRICE_FLAG_HIGH_PERCENT:
                severity = "high"
                recommended = "escalate_to_human"
            elif perc > PRICE_FLAG_LOW_PERCENT:
                severity = "medium"
                recommended = "flag_for_review"
            else:
                severity = "low"
                recommended = None

            if severity != "low":
                discrepancies.append({
                    "type": "price_mismatch",
                    "severity": severity,
                    "line_item_index": idx,
                    "field": "unit_price",
                    "invoice_value": inv_price,
                    "po_value": po_price,
                    "variance_percentage": perc * 100.0,
                    "details": f"Invoice unit price {inv_price} vs PO price {po_price} ({perc:.2%})",
                    "recommended_action": recommended,
                    "confidence": 0.9,
                })

        return discrepancies

    def validate(self, processing_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run checks and add discrepancy entries to processing_results. Returns messages and penalty factor.
        """
        self.state.record_invocation(self.name)
        messages = []
        penalty = 1.0

        # Ensure discrepancies list exists
        processing_results.setdefault("discrepancies", [])

        # Price checks - may add high/medium severity discrepancies
        price_discs = self._evaluate_price_variances(processing_results)
        if price_discs:
            processing_results["discrepancies"].extend(price_discs)
            # If any high severity add message and heavy penalty
            if any(d.get("severity") == "high" for d in price_discs):
                msg = AgentMessage(
                    sender=self.name,
                    content="High price variance detected; escalate",
                    confidence=0.2,
                    next_action="escalate",
                )
                self.state.add_message(msg)
                messages.append(msg)
                penalty *= 0.5
            else:
                msg = AgentMessage(
                    sender=self.name,
                    content="Price variances detected; flag for review",
                    confidence=0.6,
                    next_action="downgrade_to_flag",
                )
                self.state.add_message(msg)
                messages.append(msg)
                penalty *= 0.8

        # If no PO matched but fuzzy suggestions exist, add a discrepancy
        match = processing_results.get("matching_results", {})
        if not match.get("matched_po") and match.get("po_match_confidence", 0.0) >= 0.7:
            processing_results["discrepancies"].append({
                "type": "missing_po_reference",
                "severity": "medium",
                "field": "po_reference",
                "details": (
                    "Invoice does not contain a PO reference but a fuzzy match was found"
                ),
                "suggested_po": match.get("matched_po"),
                "match_confidence": match.get("po_match_confidence"),
                "recommended_action": "flag_for_review",
            })
            msg = AgentMessage(
                sender=self.name,
                content=(
                    "Missing PO reference but fuzzy match available; flagging"
                ),
                confidence=match.get("po_match_confidence", 0.0),
                next_action="downgrade_to_flag",
            )
            self.state.add_message(msg)
            messages.append(msg)
            penalty *= 0.9

        # Low match confidence overall
        if match.get("po_match_confidence", 1.0) < 0.5:
            msg = AgentMessage(
                sender=self.name,
                content="Very low PO match confidence; escalation recommended",
                confidence=match.get("po_match_confidence", 0.0),
                next_action="escalate",
            )
            self.state.add_message(msg)
            messages.append(msg)
            penalty *= 0.6

        # OVERRIDE: If a PO was inferred via fuzzy matching, never allow auto-approval.
        # Ensure we at least flag for review so a human confirms the inferred PO.
        if match.get("match_method") == "fuzzy_supplier_product":
            # Don't add downgrade if we've already escalated due to severe issues
            if not any(m.next_action == "escalate" for m in messages):
                msg = AgentMessage(
                    sender=self.name,
                    content=(
                        "PO was inferred by fuzzy matching; downgrade to flag for review to require human confirmation"
                    ),
                    confidence=match.get("po_match_confidence", 0.0),
                    next_action="downgrade_to_flag",
                )
                self.state.add_message(msg)
                messages.append(msg)

        return {"messages": [m.to_dict() for m in messages], "penalty_factor": penalty}

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Compatibility wrapper for BaseAgent.process - expects processing_results dict"""
        return self.validate(context)
