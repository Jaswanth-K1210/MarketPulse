"""
Audit Agent — Structured audit log for every pipeline run.

Orchestration paper insight: add a final node that logs every agent's output
with timestamps. This enables the "explain this signal" feature that
Bloomberg users love — click an alert, see the full reasoning trail.

Stores:
  - Per-node execution records (name, duration, input hash, output summary)
  - Tool calls made (which tools, latencies, success/fail)
  - LLM prompts used (truncated to 500 chars)
  - Final pipeline decision and confidence
"""
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AuditRecord:
    """Single node execution record."""

    def __init__(self, node_name: str):
        self.node_name = node_name
        self.started_at = time.time()
        self.completed_at: Optional[float] = None
        self.duration_ms: Optional[float] = None
        self.input_keys: List[str] = []
        self.output_keys: List[str] = []
        self.tools_called: List[Dict] = []
        self.llm_prompts: List[str] = []
        self.errors: List[str] = []
        self.metadata: Dict[str, Any] = {}

    def finish(self, output_keys: List[str] = None, errors: List[str] = None):
        self.completed_at = time.time()
        self.duration_ms = round((self.completed_at - self.started_at) * 1000, 1)
        if output_keys:
            self.output_keys = output_keys
        if errors:
            self.errors = errors

    def to_dict(self) -> dict:
        return {
            "node": self.node_name,
            "started_at": datetime.fromtimestamp(self.started_at, tz=timezone.utc).isoformat(),
            "duration_ms": self.duration_ms,
            "input_keys": self.input_keys,
            "output_keys": self.output_keys,
            "tools_called": self.tools_called,
            "llm_prompts": self.llm_prompts[:3],  # Cap at 3
            "errors": self.errors,
            "metadata": self.metadata,
        }


class AuditAgent:
    """
    Collects structured audit records for a single pipeline run.
    Persisted to SQLite agent_logs table after pipeline completion.
    """

    def __init__(self):
        self.records: List[AuditRecord] = []
        self.pipeline_started: Optional[float] = None
        self.pipeline_id: str = ""
        self.user_id: str = ""
        self.portfolio: List[str] = []

    def start_pipeline(self, user_id: str, portfolio: List[str]) -> str:
        """Initialize audit for a new pipeline run."""
        self.records = []
        self.pipeline_started = time.time()
        self.user_id = user_id
        self.portfolio = portfolio
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.pipeline_id = f"PIPE-{ts}-{abs(hash(str(portfolio))) % 10000:04}"
        return self.pipeline_id

    def start_node(self, node_name: str, input_state: dict = None) -> AuditRecord:
        """Begin auditing a node execution."""
        record = AuditRecord(node_name)
        if input_state:
            record.input_keys = list(input_state.keys())
        self.records.append(record)
        return record

    def log_tool_call(
        self,
        record: AuditRecord,
        tool_name: str,
        ticker: str = "",
        latency_ms: float = 0,
        success: bool = True,
        result_summary: str = "",
    ):
        """Log a quantitative tool call within a node."""
        record.tools_called.append({
            "tool": tool_name,
            "ticker": ticker,
            "latency_ms": round(latency_ms, 1),
            "success": success,
            "result_summary": result_summary[:200],
        })

    def log_llm_prompt(self, record: AuditRecord, prompt: str, tier: str = ""):
        """Log an LLM prompt used within a node."""
        record.llm_prompts.append({
            "tier": tier,
            "prompt_preview": prompt[:500],
            "length": len(prompt),
        })

    def finish_node(
        self,
        record: AuditRecord,
        output_keys: List[str] = None,
        errors: List[str] = None,
        metadata: Dict[str, Any] = None,
    ):
        """Finalize a node audit record."""
        record.finish(output_keys, errors)
        if metadata:
            record.metadata = metadata

    def build_audit_summary(self, final_state: dict) -> Dict[str, Any]:
        """
        Build the complete audit summary after pipeline completion.
        This is what gets stored and returned with the alert.
        """
        pipeline_duration = 0
        if self.pipeline_started:
            pipeline_duration = round((time.time() - self.pipeline_started) * 1000, 1)

        total_tool_calls = sum(len(r.tools_called) for r in self.records)
        total_llm_calls = sum(len(r.llm_prompts) for r in self.records)
        total_errors = sum(len(r.errors) for r in self.records)

        # Node-level breakdown
        node_breakdown = []
        for r in self.records:
            node_breakdown.append({
                "node": r.node_name,
                "duration_ms": r.duration_ms,
                "tools_called": len(r.tools_called),
                "llm_calls": len(r.llm_prompts),
                "errors": len(r.errors),
                "success": len(r.errors) == 0,
            })

        # Slowest nodes
        sorted_by_duration = sorted(
            [r for r in self.records if r.duration_ms],
            key=lambda r: r.duration_ms,
            reverse=True,
        )

        return {
            "pipeline_id": self.pipeline_id,
            "user_id": self.user_id,
            "portfolio": self.portfolio,
            "total_duration_ms": pipeline_duration,
            "nodes_executed": len(self.records),
            "total_tool_calls": total_tool_calls,
            "total_llm_calls": total_llm_calls,
            "total_errors": total_errors,
            "success": total_errors == 0,
            "node_breakdown": node_breakdown,
            "slowest_nodes": [
                {"node": r.node_name, "duration_ms": r.duration_ms}
                for r in sorted_by_duration[:3]
            ],
            "alert_id": final_state.get("alert_id", ""),
            "confidence_score": final_state.get("confidence_score", 0),
            "alpha_score": final_state.get("alpha_score_total", 0),
        }

    def persist(self) -> None:
        """Save audit records to SQLite agent_logs table."""
        try:
            from app.services.database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()

            for record in self.records:
                cursor.execute(
                    """INSERT INTO agent_logs (agent_name, task, result_summary, timestamp)
                       VALUES (?, ?, ?, ?)""",
                    (
                        record.node_name,
                        f"Pipeline {self.pipeline_id}",
                        json.dumps(record.to_dict()),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )

            conn.commit()
            conn.close()
            logger.info(f"AuditAgent: Persisted {len(self.records)} records for {self.pipeline_id}")
        except Exception as e:
            logger.warning(f"AuditAgent: Persist failed (non-fatal): {e}")


# Singleton per pipeline run (reset at start)
audit_agent = AuditAgent()
