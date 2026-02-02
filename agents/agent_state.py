"""Shared state across agents and lightweight metrics tracking"""
from typing import List, Dict, Any
from .messages import AgentMessage
import time


class AgentState:
    def __init__(self):
        self.messages: List[AgentMessage] = []
        self.metrics: Dict[str, Any] = {
            "agents_invoked": 0,
            "fallbacks_used": [],
            "processing_time_ms": 0,
        }
        self._start_time = None

    def start_timer(self):
        self._start_time = time.time()

    def stop_timer(self):
        if self._start_time is None:
            return
        elapsed = (time.time() - self._start_time) * 1000
        self.metrics["processing_time_ms"] = int(elapsed)

    def record_invocation(self, agent_name: str):
        self.metrics["agents_invoked"] += 1

    def add_fallback(self, name: str):
        if name not in self.metrics["fallbacks_used"]:
            self.metrics["fallbacks_used"].append(name)

    def add_message(self, msg: AgentMessage):
        self.messages.append(msg)

    def to_dict(self):
        return {"messages": [m.to_dict() for m in self.messages], "system_metrics": self.metrics}
