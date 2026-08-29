"""Tests for kg_retriever.py — Two-stage knowledge graph retrieval."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import tempfile
import networkx as nx
from unittest.mock import patch, MagicMock
from app.services.kg_retriever import KGRetriever
from app.services.kg_builder import KnowledgeGraphBuilder


@pytest.fixture
def retriever():
    """KGRetriever backed by a manually-built test graph."""
    builder = KnowledgeGraphBuilder()
    # Manually construct a small graph
    builder.graph = nx.DiGraph()
    builder.graph.add_node("AAPL", type="company", sector="Technology")
    builder.graph.add_node("MSFT", type="company", sector="Technology")
    builder.graph.add_node("Technology", type="sector")
    builder.graph.add_edge("AAPL", "MSFT", edge_type="sector_peer", weight=0.3, source="test")
    builder.graph.add_edge("AAPL", "Technology", edge_type="sector_member", weight=0.8, source="test")
    builder.graph.add_edge("MSFT", "Technology", edge_type="sector_member", weight=0.8, source="test")
    builder._loaded = True

    r = KGRetriever()
    r._builder = builder
    return r


class TestRetrieve:
    def test_retrieve_returns_dict(self, retriever):
        result = retriever.retrieve("AAPL")
        assert isinstance(result, dict)
        assert "ticker" in result
        assert "stage1_entities" in result
        assert "stage2_context" in result
        assert "retrieval_summary" in result

    def test_retrieve_known_ticker(self, retriever):
        result = retriever.retrieve("AAPL")
        assert result["ticker"] == "AAPL"
        assert len(result["stage1_entities"]) > 0
        # Should find MSFT and Technology
        entity_ids = [e["id"] for e in result["stage1_entities"]]
        assert "MSFT" in entity_ids or "Technology" in entity_ids

    def test_retrieve_unknown_ticker(self, retriever):
        result = retriever.retrieve("ZZZZ")
        assert result["ticker"] == "ZZZZ"
        assert result["stage1_entities"] == []
        assert result["stage2_context"] == {}

    def test_retrieve_summary_is_string(self, retriever):
        result = retriever.retrieve("AAPL")
        assert isinstance(result["retrieval_summary"], str)
        assert "AAPL" in result["retrieval_summary"]

    def test_retrieve_depth_limit(self, retriever):
        result = retriever.retrieve("AAPL", depth=1)
        entities = result["stage1_entities"]
        for e in entities:
            assert e["hop_distance"] <= 1

    def test_retrieve_max_entities(self, retriever):
        result = retriever.retrieve("AAPL", max_entities=1)
        assert len(result["stage1_entities"]) <= 1


class TestTraverse:
    def test_traverse_returns_list(self, retriever):
        entities = retriever._traverse("AAPL", depth=2, max_entities=10)
        assert isinstance(entities, list)

    def test_traverse_finds_neighbors(self, retriever):
        entities = retriever._traverse("AAPL", depth=2, max_entities=10)
        ids = [e["id"] for e in entities]
        assert "MSFT" in ids

    def test_traverse_includes_hop_distance(self, retriever):
        entities = retriever._traverse("AAPL", depth=2, max_entities=10)
        for e in entities:
            assert "hop_distance" in e
            assert e["hop_distance"] >= 1


class TestFormatForLLM:
    def test_format_returns_string(self, retriever):
        result = retriever.retrieve("AAPL")
        formatted = retriever.format_for_llm(result)
        assert isinstance(formatted, str)
        assert "AAPL" in formatted

    def test_format_unknown_ticker(self, retriever):
        result = retriever.retrieve("ZZZZ")
        formatted = retriever.format_for_llm(result)
        assert isinstance(formatted, str)
