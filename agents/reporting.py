"""Reporting utilities: generate a simple self-contained HTML report for processing results"""
import json
from pathlib import Path
import webbrowser
from datetime import datetime

BAR_COLORS = {
    "extraction_confidence": "#4CAF50",
    "po_match_confidence": "#2196F3",
    "discrepancy_confidence": "#FF9800",
    "decision_confidence": "#9C27B0",
}


def _safe_float(val):
    try:
        return float(val)
    except Exception:
        return 0.0


def generate_html_report(results: dict, title: str = "Test Report", output_path: str = None, open_in_browser: bool = True) -> str:
    """Create a simple HTML report summarizing processing results and confidence metrics.

    Returns the path to the generated file.
    """
    out_dir = Path(output_path) if output_path else Path("./reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename = out_dir / f"{title.replace(' ', '_')}_{timestamp}.html"

    # Compute confidence bars
    extraction_conf = _safe_float(results.get("extraction_confidence", 0.0))
    match_conf = _safe_float(results.get("matching_results", {}).get("po_match_confidence", 0.0))
    # approximate discrepancy confidence: if present compute as in orchestrator
    discrepancies = results.get("discrepancies", [])
    if not discrepancies:
        discrepancy_conf = 1.0
    else:
        worst = min([1.0, max([0.9 if d.get("severity") == "low" else 0.6 if d.get("severity") == "medium" else 0.2 for d in discrepancies])])
        discrepancy_conf = worst
    decision = _safe_float(results.get("decision_confidence", 0.0))

    # harness to display JSON nicely
    pretty_json = json.dumps(results, indent=2)

    html = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>
    body {{ font-family: Arial, sans-serif; padding: 20px; }}
    .metric {{ margin: 8px 0 }}
    .bar {{ height: 20px; background: #eee; border-radius: 4px; overflow: hidden; }}
    .bar-inner {{ height: 100%; text-align: right; padding-right: 6px; color: white; font-weight: bold }}
    pre.json {{ background: #f7f7f7; padding: 12px; border-radius: 6px; max-height: 480px; overflow: auto }}
    .section {{ margin-bottom: 18px }}
    .badge {{ background: #eee; padding: 4px 8px; border-radius: 4px; margin-right: 6px }}
    .messages {{ margin-top: 8px }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <p><em>Generated at {timestamp} (UTC)</em></p>

  <div class="section">
    <h2>Summary ✅</h2>
    <p><strong>Recommended action:</strong> <span class="badge">{results.get('recommended_action')}</span>
    <strong>Decision confidence:</strong> <span class="badge">{decision:.3f}</span></p>
  </div>

  <div class="section">
    <h2>Confidence metrics 🔧</h2>
    <div class="metric">Extraction confidence: {extraction_conf:.3f}
      <div class="bar"><div class="bar-inner" style="width: {extraction_conf*100}%; background:{BAR_COLORS['extraction_confidence']}">{extraction_conf:.2f}</div></div>
    </div>

    <div class="metric">PO match confidence: {match_conf:.3f}
      <div class="bar"><div class="bar-inner" style="width: {match_conf*100}%; background:{BAR_COLORS['po_match_confidence']}">{match_conf:.2f}</div></div>
    </div>

    <div class="metric">Discrepancy confidence: {discrepancy_conf:.3f}
      <div class="bar"><div class="bar-inner" style="width: {discrepancy_conf*100}%; background:{BAR_COLORS['discrepancy_confidence']}">{discrepancy_conf:.2f}</div></div>
    </div>

    <div class="metric">Decision confidence: {decision:.3f}
      <div class="bar"><div class="bar-inner" style="width: {decision*100}%; background:{BAR_COLORS['decision_confidence']}">{decision:.2f}</div></div>
    </div>
  </div>

  <div class="section">
    <h2>Agent messages 💬</h2>
    <div class="messages">
      {''.join('<div><strong>'+m.get('sender','')+'</strong>: '+m.get('content','')+' <em>('+str(m.get('next_action'))+')</em></div>' for m in results.get('agent_messages', []))}
      {('<div><em>No messages recorded.</em></div>' if not results.get('agent_messages') else '')}
    </div>
  </div>

  <div class="section">
    <h2>Raw processing results 📦</h2>
    <pre class="json">{pretty_json}</pre>
  </div>

</body>
</html>
"""

    filename.write_text(html, encoding="utf-8")

    if open_in_browser:
        webbrowser.open(filename.as_uri())

    return str(filename)
