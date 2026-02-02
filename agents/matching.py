"""Matching Agent: performs PO matching with fuzzy logic and overlap scoring

Refactored to subclass BaseAgent and include explicit fallback strategy when no PO number is present.
"""
from difflib import SequenceMatcher
from typing import Dict, Any, List
from .messages import AgentMessage
from .agent_state import AgentState
from .base_agent import BaseAgent
import logging

logger = logging.getLogger(__name__)


def similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


class MatchingAgent(BaseAgent):
    def __init__(self, po_db: List[Dict[str, Any]], state: AgentState, name: str = "MatchingAgent"):
        super().__init__(name)
        self.po_db = po_db
        self.state = state

    def find_po(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Find a PO by strategy:
        1) Direct PO reference on invoice
        2) Fuzzy matching by supplier + products (fallback)

        Returns dict with keys: po (dict or None), confidence (0-1), reasoning (list)
        """
        reasoning: List[str] = []

        # Strategy 1: Direct Match by PO number
        po_ref = invoice_data.get("po_reference") or invoice_data.get("po_number")
        if po_ref:
            reasoning.append(f"Found PO reference on invoice: {po_ref}")
            for po in self.po_db:
                if po.get("po_id") == po_ref or po.get("po_number") == po_ref:
                    reasoning.append("Exact PO ID match")
                    return {"po": po, "confidence": 0.98, "reasoning": reasoning}
            reasoning.append("PO reference present but not found in DB")

        # Strategy 2: Fuzzy match
        self.log("No PO number found or not in DB. Attempting fuzzy match by supplier and items...", "info")
        reasoning.append("No PO reference found; attempting fuzzy match by supplier+items")

        supplier = invoice_data.get("supplier", "")
        # Compute invoice total from line items when explicit total not provided
        def compute_total(items):
            t = 0.0
            for li in items:
                q = float(li.get("quantity", 1))
                up = li.get("unit_price", li.get("line_total", 0.0))
                t += q * float(up)
            return t

        invoice_items = [li.get("description", "") for li in invoice_data.get("line_items", [])]
        invoice_total = float(invoice_data.get("total_amount", compute_total(invoice_data.get("line_items", []))))

        # Helper to normalize supplier names (remove ltd/limited/co etc.)
        def normalize_supplier(s: str) -> str:
            if not s:
                return ""
            s = s.lower()
            for token in [" ltd", " limited", " co.", " co", ","]:
                s = s.replace(token, "")
            return s.strip()

        inv_supplier_norm = normalize_supplier(supplier)

        best_candidate = None
        best_score = 0.0
        best_details = {}

        for po in self.po_db:
            po_supplier = po.get("supplier", "")
            po_supplier_norm = normalize_supplier(po_supplier)

            # Start with 0 and add weighted signals - prioritize supplier match heavily
            score = 0.0

            # 1) Supplier name exact/substring match (heavy weight)
            if inv_supplier_norm and (inv_supplier_norm in po_supplier_norm or po_supplier_norm in inv_supplier_norm):
                score += 0.50

            # 2) Total amount proximity (medium weight)
            try:
                po_total = float(po.get("total", 0.0))
                # Small absolute tolerance for small totals or relative 1% tolerance
                tol = max(5.0, 0.01 * abs(po_total))
                if abs(invoice_total - po_total) <= tol:
                    score += 0.30
            except Exception:
                pass

            # 3) Product description similarity (small weight)
            po_items = [li.get("description", "") for li in po.get("line_items", [])]
            product_scores = []
            matched_count = 0
            unmatched_items_local = []
            for inv_item in invoice_items:
                best_item_score = 0.0
                for po_item in po_items:
                    s = similarity(inv_item, po_item)
                    if s > best_item_score:
                        best_item_score = s
                product_scores.append(best_item_score)
                if best_item_score >= 0.75:
                    matched_count += 1
                else:
                    unmatched_items_local.append(inv_item)

            overlap = matched_count / max(1, len(invoice_items))
            avg_product_score = (sum(product_scores) / len(product_scores)) if product_scores else 0.0

            # Add a small contribution from products and overlap
            score += 0.15 * avg_product_score
            # Slightly reward overlap but do not heavily penalize low overlap here
            score += 0.10 * overlap

            if score > best_score:
                best_score = score
                best_candidate = po
                best_details = {
                    "supplier_sim": similarity(supplier, po_supplier),
                    "avg_product_score": avg_product_score,
                    "overlap": overlap,
                    "unmatched_items": unmatched_items_local,
                }

        # Use a lower threshold for accepting a supplier-led fuzzy match
        if best_score < 0.40:
            reasoning.append(
                f"Best fuzzy candidate low confidence ({best_score:.2f}) - no reliable PO found"
            )
            msg = AgentMessage(
                sender=self.name,
                content=f"No confident PO match ({best_score:.2f})",
                confidence=best_score,
                next_action="request_validation",
            )
            self.state.add_message(msg)
            self.state.add_fallback("fuzzy_po_match")
        else:
            reasoning.append(
                f"Fuzzy match found candidate {best_candidate.get('po_number') if best_candidate else None}"
                f" with score {best_score:.2f}"
            )

        return {"po": best_candidate, "confidence": float(best_score), "reasoning": reasoning, "details": best_details}

    def match_invoice(self, extracted: Dict[str, Any]) -> Dict[str, Any]:
        """Main method kept for backwards compatibility with Orchestrator.
        Populates matching results with confidence, matched PO id, method, overlap and unmatched items.
        """
        self.state.record_invocation(self.name)

        find = self.find_po(extracted)
        po = find.get("po")
        confidence = float(find.get("confidence", 0.0))
        reasoning = find.get("reasoning", [])
        details = find.get("details", {})

        # Unmatched items: use details from fuzzy matcher if present
        if po and details:
            overlap = details.get("overlap", 0.0)
            unmatched_items = details.get("unmatched_items", [])
        else:
            overlap = 0.0
            unmatched_items = []

        # If fuzzy path chosen, populate match_method accordingly
        match_method = "exact_po_reference" if extracted.get("po_reference") else "fuzzy_supplier_product"

        # If very low confidence, ensure state records fallback
        if confidence < 0.75:
            self.state.add_fallback("fuzzy_po_match")
            msg = AgentMessage(sender=self.name, content="Low confidence match - requesting further validation", confidence=confidence, next_action="request_validation")
            self.state.add_message(msg)

        return {
            "po_match_confidence": confidence,
            "matched_po": po.get("po_number") if po else None,
            "suggested_po_obj": po,
            "match_method": match_method,
            "overlap": float(details.get("overlap", overlap)),
            "unmatched_items": unmatched_items,
            "match_reasoning": reasoning,
        }

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Compatibility wrapper for BaseAgent.process"""
        return self.match_invoice(context)
