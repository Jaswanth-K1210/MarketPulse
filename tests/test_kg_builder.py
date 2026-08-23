"""Tests for kg_builder.py — Dynamic knowledge graph builder."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import json
import tempfile
import networkx as nx
from unittest.mock import patch
from app.services.kg_builder import KnowledgeGraphBuilder


@pytest.fixture
def builder():
    """KGBuilder with mocked persistence to avoid polluting real data."""
    b = KnowledgeGraphBuilder()
    # Override persistence path to a temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        b._persist_path = os.path.join(tmpdir, "test_kg.json")
        # Patch the module-level KG_PERSIST_PATH
        with patch("app.services.kg_builder.KG_PERSIST_PATH", os.path.join(tmpdir, "test_kg.json")):
            yield b


class TestBuild:
    def test_build_returns_networkx_graph(self, builder):
        result = builder.build()
        assert isinstance(result, nx.DiGraph)

    def test_build_populates_nodes(self, builder):
        builder.build()
        assert builder.graph.number_of_nodes() > 0

    def test_build_creates_edges(self, builder):
        builder.build()
        assert builder.graph.number_of_edges() > 0

    def test_build_force_rebuild(self, builder):
        builder.build()
        node_count_1 = builder.graph.number_of_nodes()
        builder.build(force_rebuild=True)
        assert builder.graph.number_of_nodes() > 0

    def test_build_loads_from_cache(self, builder):
        builder.build()
        assert builder._loaded is True
        # Second call should use cached
        builder.build()
        assert builder._loaded is True


class TestGetEntityContext:
    def test_unknown_entity(self, builder):
        builder.build()
        ctx = builder.get_entity_context("ZZZZ")
        assert ctx["ticker"] == "ZZZZ"
        assert ctx["found"] is False

    def test_known_entity_has_neighbors(self, builder):
        builder.build()
        # Find any node that exists
        nodes = list(builder.graph.nodes())
        if nodes:
            ticker = nodes[0]
            ctx = builder.get_entity_context(ticker)
            assert ctx["found"] is True
            assert "neighbors" in ctx
            assert "degree" in ctx
            assert "attributes" in ctx

    def test_entity_context_sorted_by_weight(self, builder):
        builder.build()
        nodes = list(builder.graph.nodes())
        if nodes:
            ticker = nodes[0]
            ctx = builder.get_entity_context(ticker)
            weights = [n["weight"] for n in ctx["neighbors"]]
            assert weights == sorted(weights, reverse=True)


class TestAddEventEdge:
    def test_add_event_edge(self, builder):
        builder.build()
        nodes_before = builder.graph.number_of_nodes()
        builder.add_event_edge("AAPL", "SEC_FILING", "10-K annual report filed", 0.8)
        assert builder.graph.number_of_nodes() > nodes_before
        # Verify the event node exists
        event_nodes = [n for n in builder.graph.nodes() if n.startswith("EVENT-")]
        assert len(event_nodes) > 0


class TestAddEdge:
    def test_add_edge_creates_nodes(self, builder):
        builder.build()
        builder._add_edge("TICK1", "TICK2", "competitor", 0.9, source="test")
        assert builder.graph.has_node("TICK1")
        assert builder.graph.has_node("TICK2")
        assert builder.graph.has_edge("TICK1", "TICK2")

    def test_add_edge_updates_weight_if_higher(self, builder):
        builder.build()
        builder._add_edge("A", "B", "competitor", 0.5, source="test")
        builder._add_edge("A", "B", "supplier", 0.9, source="test")
        assert builder.graph["A"]["B"]["weight"] == 0.9
        assert builder.graph["A"]["B"]["edge_type"] == "supplier"

    def test_add_edge_keeps_existing_if_higher(self, builder):
        builder.build()
        builder._add_edge("A", "B", "competitor", 0.9, source="test")
        builder._add_edge("A", "B", "supplier", 0.3, source="test")
        assert builder.graph["A"]["B"]["weight"] == 0.9


class TestPersistence:
    def test_persist_creates_file(self, builder):
        builder.build()
        with patch("app.services.kg_builder.KG_PERSIST_PATH", builder._persist_path):
            builder.persist()
        assert os.path.exists(builder._persist_path)

    def test_persist_loads_back(self, builder):
        builder.build()
        with patch("app.services.kg_builder.KG_PERSIST_PATH", builder._persist_path):
            builder.persist()
        # Create new builder and load
        builder2 = KnowledgeGraphBuilder()
        with patch("app.services.kg_builder.KG_PERSIST_PATH", builder._persist_path):
            with open(builder._persist_path) as f:
                data = json.load(f)
            builder2.graph = nx.node_link_graph(data)
            builder2._loaded = True
        assert builder2.graph.number_of_nodes() > 0
