"""Tests for audit_agent.py — Structured pipeline audit log."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import json
from datetime import datetime, timezone
from app.services.audit_agent import AuditAgent, AuditRecord


class TestAuditRecord:
    def test_create_record(self):
        r = AuditRecord(node_name="alpha_scorer")
        assert r.node_name == "alpha_scorer"
        assert r.started_at is not None
        assert r.completed_at is None
        assert r.errors == []

    def test_finish(self):
        r = AuditRecord(node_name="test")
        r.finish(output_keys=["alpha_score", "alpha_signal"], errors=["timeout"])
        assert r.completed_at is not None
        assert r.duration_ms is not None
        assert r.duration_ms >= 0
        assert r.output_keys == ["alpha_score", "alpha_signal"]
        assert r.errors == ["timeout"]

    def test_finish_no_args(self):
        r = AuditRecord(node_name="test")
        r.finish()
        assert r.completed_at is not None
        assert r.errors == []

    def test_to_dict(self):
        r = AuditRecord(node_name="test")
        r.finish()
        d = r.to_dict()
        assert d["node"] == "test"
        assert "duration_ms" in d
        assert "started_at" in d
        assert "errors" in d

    def test_to_dict_truncates_llm_prompts(self):
        r = AuditRecord(node_name="test")
        r.llm_prompts = [{"tier": "t1", "prompt_preview": "x" * 600, "length": 600}] * 5
        d = r.to_dict()
        assert len(d["llm_prompts"]) <= 3


class TestAuditAgent:
    @pytest.fixture
    def agent(self):
        return AuditAgent()

    def test_start_pipeline(self, agent):
        pid = agent.start_pipeline(user_id="user1", portfolio=["AAPL", "MSFT"])
        assert pid.startswith("PIPE-")
        assert agent.pipeline_id == pid
        assert agent.user_id == "user1"
        assert agent.portfolio == ["AAPL", "MSFT"]

    def test_start_node(self, agent):
        agent.start_pipeline("u1", ["AAPL"])
        record = agent.start_node("alpha_scorer")
        assert isinstance(record, AuditRecord)
        assert record.node_name == "alpha_scorer"
        assert len(agent.records) == 1

    def test_start_node_with_input_state(self, agent):
        agent.start_pipeline("u1", ["AAPL"])
        record = agent.start_node("alpha_scorer", input_state={"key1": "val1", "key2": "val2"})
        assert set(record.input_keys) == {"key1", "key2"}

    def test_finish_node(self, agent):
        agent.start_pipeline("u1", ["AAPL"])
        record = agent.start_node("alpha_scorer")
        agent.finish_node(record, output_keys=["alpha_score"])
        assert record.completed_at is not None
        assert record.output_keys == ["alpha_score"]

    def test_finish_node_with_errors(self, agent):
        agent.start_pipeline("u1", ["AAPL"])
        record = agent.start_node("test")
        agent.finish_node(record, errors=["Connection timeout"])
        assert record.errors == ["Connection timeout"]

    def test_log_tool_call(self, agent):
        agent.start_pipeline("u1", ["AAPL"])
        record = agent.start_node("quant_tools")
        agent.log_tool_call(record, "technical", ticker="AAPL", latency_ms=150.3, success=True)
        assert len(record.tools_called) == 1
        assert record.tools_called[0]["tool"] == "technical"
        assert record.tools_called[0]["latency_ms"] == 150.3

    def test_log_llm_prompt(self, agent):
        agent.start_pipeline("u1", ["AAPL"])
        record = agent.start_node("alpha_scorer")
        agent.log_llm_prompt(record, "Synthesize the following data...", tier="groq")
        assert len(record.llm_prompts) == 1
        assert record.llm_prompts[0]["tier"] == "groq"

    def test_build_audit_summary(self, agent):
        agent.start_pipeline("u1", ["AAPL"])
        r1 = agent.start_node("alpha_scorer")
        agent.finish_node(r1, output_keys=["alpha_score"])
        r2 = agent.start_node("convergence_detector")
        agent.finish_node(r2, errors=["timeout"])

        summary = agent.build_audit_summary({"alert_id": "ALT-001", "confidence_score": 0.85})
        assert summary["pipeline_id"].startswith("PIPE-")
        assert summary["nodes_executed"] == 2
        assert summary["total_errors"] == 1
        assert summary["success"] is False
        assert summary["alert_id"] == "ALT-001"
        assert summary["confidence_score"] == 0.85

    def test_build_audit_summary_empty(self, agent):
        agent.start_pipeline("u1", [])
        summary = agent.build_audit_summary({})
        assert summary["nodes_executed"] == 0
        assert summary["total_tool_calls"] == 0
        assert summary["success"] is True

    def test_full_pipeline_audit(self, agent):
        agent.start_pipeline("u1", ["AAPL", "MSFT"])
        nodes = ["news_monitor", "classifier", "quant_tools", "alpha_scorer",
                 "convergence_detector", "matcher_fast", "impact_calculator",
                 "confidence_validator", "alert_generator", "memory_store",
                 "kg_retrieval", "quality_eval", "audit_final"]
        for node in nodes:
            r = agent.start_node(node)
            agent.finish_node(r, output_keys=[f"{node}_out"])

        summary = agent.build_audit_summary({"alert_id": "ALT-002"})
        assert summary["nodes_executed"] == 13
        assert summary["success"] is True

    def test_persist_does_not_crash(self, agent):
        agent.start_pipeline("u1", ["AAPL"])
        r = agent.start_node("test")
        agent.finish_node(r)
        # persist catches exceptions internally
        agent.persist()
