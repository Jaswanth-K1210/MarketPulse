"""
Knowledge Graph Builder — Dynamic construction from multiple sources.

FinKario insight: standard RAG over financial documents fails because markets
move faster than knowledge bases update. Their event-enhanced knowledge graph
auto-updates from research reports. Two-stage graph-based retrieval beats
plain RAG by ~18% on stock trend prediction.

This module builds and maintains a lightweight knowledge graph from:
  1. Existing gnn_service.py hardcoded edges (seed)
  2. SEC 10-K/8-K relationship extraction (sec_parser.py)
  3. yfinance sector/industry metadata
  4. Pipeline-discovered relationships (from persistence)

Stored as NetworkX graph + JSON persistence file.
"""
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

logger = logging.getLogger(__name__)

KG_PERSIST_PATH = str(
    Path(__file__).parent.parent.parent / "data" / "knowledge_graph.json"
)


class KnowledgeGraphBuilder:
    """
    Builds and maintains a financial knowledge graph.
    Entities: companies (tickers), sectors, events
    Edges: supplier, customer, competitor, sector_member, event_affected
    """

    def __init__(self):
        self.graph = nx.DiGraph()
        self._loaded = False

    def build(self, force_rebuild: bool = False) -> nx.DiGraph:
        """
        Build the full knowledge graph from all sources.
        Returns the NetworkX graph.
        """
        if self._loaded and not force_rebuild:
            return self.graph

        # 1. Load from disk if available
        if not force_rebuild and os.path.exists(KG_PERSIST_PATH):
            try:
                with open(KG_PERSIST_PATH) as f:
                    data = json.load(f)
                self.graph = nx.node_link_graph(data)
                self._loaded = True
                logger.info(f"KG loaded from disk: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
                return self.graph
            except Exception as e:
                logger.warning(f"KG load failed: {e}, rebuilding from scratch")

        # 2. Seed from gnn_service.py edges
        self._seed_from_gnn()

        # 3. Add SEC 10-K relationships
        self._seed_from_sec()

        # 4. Add yfinance sector/industry
        self._seed_from_yfinance()

        # 5. Add DB-cached relationships
        self._seed_from_db()

        self._loaded = True
        self.persist()
        logger.info(
            f"KG built: {self.graph.number_of_nodes()} nodes, "
            f"{self.graph.number_of_edges()} edges"
        )
        return self.graph

    def _seed_from_gnn(self) -> None:
        """Import the 35+ hardcoded edges from gnn_service."""
        try:
            from app.services.gnn_service import _EDGES
            for src, tgt, weight in _EDGES:
                edge_type = "competitor" if weight < 0 else "supplier"
                self._add_edge(src, tgt, edge_type, abs(weight), source="gnn_static")
            logger.info(f"KG: Seeded {len(_EDGES)} edges from gnn_service")
        except Exception as e:
            logger.warning(f"KG: gnn_service seed failed: {e}")

    def _seed_from_sec(self) -> None:
        """Extract relationships from SEC 10-K filings for tracked companies."""
        try:
            from app.services.sec_parser import sec_parser
            from app.config import TRACKED_COMPANIES
            tickers = [t for t in TRACKED_COMPANIES if isinstance(t, str)][:10]

            for ticker in tickers:
                try:
                    rels = sec_parser.extract_relationships(ticker)
                    if rels:
                        for rel in rels:
                            target = rel.get("related_company", "")
                            if target and target != ticker:
                                self._add_edge(
                                    ticker, target,
                                    rel.get("type", "related"),
                                    rel.get("confidence", 0.7),
                                    source="sec_edgar",
                                )
                        logger.info(f"KG: SEC extracted {len(rels)} relationships for {ticker}")
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"KG: SEC seed failed: {e}")

    def _seed_from_yfinance(self) -> None:
        """Add sector/industry relationships from yfinance."""
        try:
            import yfinance as yf
            from app.config import TRACKED_COMPANIES
            tickers = [t for t in TRACKED_COMPANIES if isinstance(t, str)][:15]

            sector_members: Dict[str, List[str]] = {}
            for ticker in tickers:
                try:
                    stock = yf.Ticker(ticker)
                    info = stock.info
                    sector = info.get("sector", "")
                    industry = info.get("industry", "")
                    if sector:
                        self._add_node(ticker, "company", sector=sector, industry=industry)
                        sector_members.setdefault(sector, []).append(ticker)
                except Exception:
                    continue

            # Connect companies in same sector
            for sector, members in sector_members.items():
                self._add_node(sector, "sector")
                for member in members:
                    self._add_edge(member, sector, "sector_member", 0.8, source="yfinance")
                # Also add weak competitor edges between same-sector companies
                for i in range(len(members)):
                    for j in range(i + 1, len(members)):
                        self._add_edge(
                            members[i], members[j],
                            "sector_peer", 0.3,
                            source="yfinance",
                        )

            logger.info(f"KG: yfinance added {len(sector_members)} sectors")
        except Exception as e:
            logger.warning(f"KG: yfinance seed failed: {e}")

    def _seed_from_db(self) -> None:
        """Import discovered relationships from SQLite."""
        try:
            from app.services.persistence import persistence_service
            rels = persistence_service.get_all_relationships(limit=500)
            for rel in rels:
                src = rel.get("source_ticker", "")
                tgt = rel.get("target_ticker", "")
                if src and tgt:
                    self._add_edge(
                        src, tgt,
                        rel.get("relationship_type", "related"),
                        rel.get("confidence", 0.7),
                        source="discovered",
                    )
            logger.info(f"KG: DB seeded {len(rels)} relationships")
        except Exception as e:
            logger.warning(f"KG: DB seed failed: {e}")

    def _add_node(self, node_id: str, node_type: str, **attrs) -> None:
        if not self.graph.has_node(node_id):
            self.graph.add_node(node_id, type=node_type, **attrs)

    def _add_edge(
        self, src: str, tgt: str, edge_type: str, weight: float, source: str = ""
    ) -> None:
        self._add_node(src, "company")
        self._add_node(tgt, "company")
        if self.graph.has_edge(src, tgt):
            # Update weight if new weight is higher confidence
            existing = self.graph[src][tgt].get("weight", 0)
            if weight > existing:
                self.graph[src][tgt]["weight"] = weight
                self.graph[src][tgt]["edge_type"] = edge_type
                self.graph[src][tgt]["source"] = source
        else:
            self.graph.add_edge(
                src, tgt,
                edge_type=edge_type,
                weight=weight,
                source=source,
                added_at=datetime.now(timezone.utc).isoformat(),
            )

    def add_event_edge(
        self, ticker: str, event_type: str, description: str, severity: float
    ) -> None:
        """Add an event node and connect it to a ticker."""
        event_id = f"EVENT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}-{ticker}"
        self._add_node(event_id, "event", event_type=event_type, description=description[:200])
        self._add_edge(ticker, event_id, "event_affected", severity, source="pipeline")

    def persist(self) -> None:
        """Save graph to JSON."""
        try:
            os.makedirs(os.path.dirname(KG_PERSIST_PATH), exist_ok=True)
            data = nx.node_link_data(self.graph)
            with open(KG_PERSIST_PATH, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"KG persist failed: {e}")

    def get_entity_context(self, ticker: str) -> Dict[str, Any]:
        """Get all known context about a ticker from the KG."""
        if not self._loaded:
            self.build()

        if not self.graph.has_node(ticker):
            return {"ticker": ticker, "found": False}

        neighbors = []
        for _, tgt, data in self.graph.out_edges(ticker, data=True):
            node_data = self.graph.nodes.get(tgt, {})
            neighbors.append({
                "target": tgt,
                "edge_type": data.get("edge_type", "related"),
                "weight": data.get("weight", 0),
                "node_type": node_data.get("type", "unknown"),
            })

        return {
            "ticker": ticker,
            "found": True,
            "attributes": dict(self.graph.nodes.get(ticker, {})),
            "neighbors": sorted(neighbors, key=lambda x: x["weight"], reverse=True),
            "degree": self.graph.degree(ticker),
        }


# Singleton
kg_builder = KnowledgeGraphBuilder()
