"""
Parser base com logging em tempo real via callbacks
"""
import re
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class LogEntry:
    timestamp: str
    stage: str
    action: str
    details: Dict[str, Any]
    severity: str = "INFO"


class ATSLogger:
    """Logger com callbacks para streaming em tempo real"""

    STAGES = {
        "INGEST": "📥 Ingestão",
        "PARSE": "🔍 Parsing",
        "EXTRACT": "🧬 Extração",
        "NORMALIZE": "🔄 Normalização",
        "MATCH": "🎯 Matching",
        "SCORE": "📊 Scoring",
        "FILTER": "🚧 Filtros",
        "DECISION": "✅ Decisão",
    }

    def __init__(self, candidate_name: str = "unknown"):
        self.candidate_name = candidate_name
        self.logs: List[LogEntry] = []
        self._callbacks: List[Callable] = []
        self._start_time = datetime.now()

    def add_callback(self, callback: Callable):
        self._callbacks.append(callback)

    def log(self, stage: str, action: str, details: Dict[str, Any], severity: str = "INFO"):
        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            stage=stage,
            action=action,
            details=details,
            severity=severity
        )
        self.logs.append(entry)
        # Notifica todos os callbacks em tempo real
        for cb in self._callbacks:
            try:
                cb(entry)
            except Exception:
                pass

    def to_dict(self) -> List[Dict]:
        return [{
            "timestamp": e.timestamp,
            "stage": e.stage,
            "stage_name": self.STAGES.get(e.stage, e.stage),
            "action": e.action,
            "details": e.details,
            "severity": e.severity,
        } for e in self.logs]
