"""Small CLI demonstrating the agentic flow: matching, validation and decisions."""
import json
import sys
import time
from pathlib import Path
from agents.orchestrator import Orchestrator
from agents.extraction_agent import ExtractionAgent
from core.ui import UI


class AgentLogger:
    """Helper to make the terminal look like an AI is thinking."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

    @staticmethod
    def print_phase(phase_name):
        print(f"\n{AgentLogger.HEADER}{AgentLogger.BOLD}=== {phase_name} ==={AgentLogger.ENDC}")
        time.sleep(0.5)

    @staticmethod
    def agent_think(agent_name, action):
        sys.stdout.write(f"{AgentLogger.CYAN}🤖 [{agent_name}]{AgentLogger.ENDC} {action}...")
        sys.stdout.flush()
        time.sleep(0.8)
        print(f" {AgentLogger.GREEN}Done.{AgentLogger.ENDC}")

    @staticmethod
    def log_decision(decision, confidence, reason):
        color = AgentLogger.GREEN if decision == "auto_approve" else AgentLogger.FAIL
        if decision == "flag_for_review":
            color = AgentLogger.WARNING

        print(f"\n{AgentLogger.BOLD}🎯 FINAL DECISION:{AgentLogger.ENDC} {color}{decision.upper()}{AgentLogger.ENDC}")
        print(f"   📊 Confidence: {confidence * 100:.1f}%")
        print(f"   📝 Reason: {reason}\n")


def _resolve_extracted_path(arg_path: str) -> str:
    """Resolve a PDF/json input to an available extracted JSON example if possible."""
    p = Path(arg_path)
    # If user passed a json path, use it directly
    if p.exists() and p.suffix.lower() == ".json":
        return str(p)

    # Otherwise try to find an extracted example matching the basename
    base = p.stem
    candidates = list((Path(__file__).parent / "extracted_examples").glob("**/*"))
    # also include `data/mock_extention` for example extracted inputs
    candidates += list((Path(__file__).resolve().parent / "data" / "mock_extention").glob("**/*"))
    # Exact match variant: base_extracted.json (search both locations)
    preferred = Path(__file__).parent / "extracted_examples" / f"{base}_extracted.json"
    if not preferred.exists():
        preferred = Path(__file__).resolve().parent / "data" / "mock_extention" / f"{base}_extracted.json"
    if preferred.exists():
        return str(preferred)

    # Tokenized fuzzy search (e.g., Invoice_4_Price_Trap -> tokens invoice, 4, price, trap)
    import re
    tokens = [t for t in re.split(r'[^a-zA-Z0-9]+', base.lower()) if t]
    for c in candidates:
        if not c.is_file():
            continue
        name = c.name.lower()
        # if any token matches across filename, treat as a candidate
        if any(tok in name for tok in tokens):
            return str(c)

    # Fallback: use the first available extracted example
    first = next((c for c in candidates if c.is_file()), None)
    if first:
        return str(first)

    # If nothing available, raise
    raise FileNotFoundError("No extracted examples available to simulate PDF extraction")


def main(input_path: str, po_db_path: str):
    # UI intro
    UI.banner()
    UI.section("Data Ingestion")
    UI.log("System", "Loading Purchase Order Database...", "THINKING")

    with open(po_db_path, "r") as f:
        po_db = json.load(f)

    UI.log("System", f"Loaded {len(po_db.get('purchase_orders', po_db))} Purchase Orders.", "SUCCESS")

    # Determine extracted data source (accept json or simulate pdf->extracted mapping)
    AgentLogger.print_phase("INITIALIZING AGENTS")
    AgentLogger.agent_think("ExtractionAgent", "Scanning document structure")

    extraction_agent = ExtractionAgent()
    resolved = _resolve_extracted_path(input_path)
    extracted = extraction_agent.process(resolved)

    UI.section("Matching Agent")
    # Indicate matching intent. If there's no PO reference, show fuzzy flow
    if not extracted.get("po_reference"):
        AgentLogger.agent_think("MatchingAgent", "PO Number missing. Executing Fuzzy Match")
    else:
        AgentLogger.agent_think("MatchingAgent", "Looking up PO reference")

    orch = Orchestrator(po_db)
    result = orch.process(extracted)

    # Show discrepancies visually (esp. price traps)
    UI.section("Discrepancy Review")
    for d in result.get("discrepancies", []) or []:
        if d.get("type") == "price_mismatch":
            UI.show_discrepancy(
                item=d.get("details", "Item"),
                inv_price=d.get("invoice_value", 0.0),
                po_price=d.get("po_value", 0.0),
            )
            UI.log(
                "Validator",
                f"Price variance {d.get('variance_percentage'):.1f}% -> {d.get('recommended_action')}",
                "WARNING",
            )

    # Final Decision
    reason_parts = []
    reason_parts.extend(extracted.get("agent_reasoning", []))
    mr = result.get("matching_results", {})
    reason_parts.extend(mr.get("match_reasoning", []) if mr else [])
    if result.get("discrepancies"):
        reason_parts.append(f"{len(result.get('discrepancies'))} discrepancy(ies) detected")

    reason = " ".join(reason_parts) if reason_parts else "No further details"

    AgentLogger.log_decision(
        decision=result.get("recommended_action", "flag_for_review"),
        confidence=result.get("decision_confidence", 0.0),
        reason=reason,
    )

    # Print JSON output for reproducibility
    print(json.dumps(result, indent=2))


if __name__ == "__main__":

    if len(sys.argv) < 3:
        print("Usage: python process_invoice.py <extracted_invoice.json> <purchase_orders.json>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
