"""Agent messaging objects"""
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import json


@dataclass
class AgentMessage:
    sender: str
    content: str
    confidence: float
    next_action: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def __repr__(self) -> str:
        return (
            f"AgentMessage(sender={self.sender!r}, confidence={self.confidence:.2f}, "
            f"next_action={self.next_action!r})"
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict())
