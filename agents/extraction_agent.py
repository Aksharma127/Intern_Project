"""ExtractionAgent: handles loading/parsing of invoice JSON and basic OCR simulation."""
from typing import Dict, Any
from .base_agent import BaseAgent
import logging

logger = logging.getLogger(__name__)


class ExtractionAgent(BaseAgent):
    def __init__(self, name: str = "ExtractionAgent"):
        super().__init__(name)

    def process(self, source: Any) -> Dict[str, Any]:
        """Accept a pre-extracted dict or a path to a JSON file and normalize output.

        Returns a standard extracted dict with keys such as ``extraction_confidence`` and
        ``line_items`` that downstream agents expect.
        """
        data = None
        if isinstance(source, str):
            # assume file path
            import json
            with open(source, "r") as f:
                data = json.load(f)
            self.log(f"Loaded extracted invoice JSON from {source}")
        elif isinstance(source, dict):
            data = source
            self.log("Processing pre-extracted invoice dict")
        else:
            raise TypeError("Unsupported source type for ExtractionAgent")

        # Normalize small defaults
        if "extraction_confidence" not in data:
            data["extraction_confidence"] = 0.9
        if "document_quality" not in data:
            data["document_quality"] = "unknown"

        # Add basic reasoning note
        data.setdefault("agent_reasoning", [])
        data["agent_reasoning"].append(f"ExtractionAgent: base extraction confidence {data['extraction_confidence']:.2f}")

        return data
