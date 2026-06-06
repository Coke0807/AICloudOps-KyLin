import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class AuditLogEntry:
    trace_id: str
    timestamp: str
    step: str
    step_order: int
    data: Dict[str, Any]


@dataclass
class ReasoningTrace:
    trace_id: str
    start_time: str
    end_time: Optional[str]
    user_prompt: str
    steps: List[AuditLogEntry]
    final_result: Optional[Dict[str, Any]]


class AuditLogger:
    _instance = None
    _logs_dir: Path

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._logs_dir = Path("logs")
        self._logs_dir.mkdir(exist_ok=True)
        self._active_traces: Dict[str, ReasoningTrace] = {}
        self._initialized = True

    def start_trace(self, user_prompt: str) -> str:
        trace_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"
        
        trace = ReasoningTrace(
            trace_id=trace_id,
            start_time=now,
            end_time=None,
            user_prompt=user_prompt,
            steps=[],
            final_result=None,
        )
        
        self._active_traces[trace_id] = trace
        self._log_step(trace_id, "INIT", 0, {"user_prompt": user_prompt, "timestamp": now})
        return trace_id

    def _log_step(self, trace_id: str, step_name: str, order: int, data: Dict[str, Any]):
        if trace_id not in self._active_traces:
            return
        
        entry = AuditLogEntry(
            trace_id=trace_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            step=step_name,
            step_order=order,
            data=data,
        )
        
        self._active_traces[trace_id].steps.append(entry)

    def log_environment_sensing(self, trace_id: str, snapshot: Dict[str, Any]):
        self._log_step(trace_id, "ENVIRONMENT_SENSE", 1, {"snapshot": snapshot})

    def log_intent_analysis(self, trace_id: str, analysis: Dict[str, Any]):
        self._log_step(trace_id, "INTENT_ANALYSIS", 2, {"analysis": analysis})

    def log_safety_validation(self, trace_id: str, validation_result: Dict[str, Any]):
        self._log_step(trace_id, "SAFETY_VALIDATION", 3, {"validation": validation_result})

    def log_tool_execution(self, trace_id: str, tool_name: str, params: Dict[str, Any], result: Any):
        self._log_step(trace_id, "TOOL_EXECUTION", 4, {
            "tool": tool_name,
            "params": params,
            "result": result,
        })

    def log_final_decision(self, trace_id: str, decision: Dict[str, Any]):
        self._log_step(trace_id, "FINAL_DECISION", 5, {"decision": decision})

    def end_trace(self, trace_id: str, final_result: Dict[str, Any]) -> ReasoningTrace:
        if trace_id not in self._active_traces:
            raise ValueError(f"Trace {trace_id} not found")
        
        trace = self._active_traces[trace_id]
        trace.end_time = datetime.utcnow().isoformat() + "Z"
        trace.final_result = final_result
        
        self._save_trace(trace)
        del self._active_traces[trace_id]
        
        return trace

    def _save_trace(self, trace: ReasoningTrace):
        trace_file = self._logs_dir / f"trace_{trace.trace_id}.json"
        with open(trace_file, "w", encoding="utf-8") as f:
            json.dump(asdict(trace), f, ensure_ascii=False, indent=2)

    def get_trace(self, trace_id: str) -> Optional[ReasoningTrace]:
        trace_file = self._logs_dir / f"trace_{trace_id}.json"
        if trace_file.exists():
            with open(trace_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return ReasoningTrace(**data)
        return None

    def list_traces(self, limit: int = 50) -> List[Dict[str, Any]]:
        trace_files = sorted(self._logs_dir.glob("trace_*.json"), reverse=True)[:limit]
        traces = []
        for f in trace_files:
            with open(f, "r", encoding="utf-8") as tf:
                traces.append(json.load(tf))
        return traces
