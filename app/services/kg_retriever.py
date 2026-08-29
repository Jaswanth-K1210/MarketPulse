"""
Knowledge Graph Retriever — Two-stage retrieval over the financial KG.

FinKario two-stage retrieval:
  Stage 1: Given a query/ticker, find all related entity nodes in the KG
  Stage 2: For those entities, fetch recent events (news, filings, alerts)

This beats plain RAG because it traverses relationship edges before
fetching context, giving the LLM a structured view of the ecosystem.
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class KGRetriever:
    """
    Two-stage retrieval over the financial knowledge graph.
    """

    def __init__(self):
        self._builder = None

    def _get_builder(self):
        if self._builder is None:
            from app.services.kg_builder import kg_builder
            self._builder = kg_builder
            if not self._builder._loaded:
                self._builder.build()
        return self._builder

    def retrieve(self, ticker: str, depth: int = 2, max_entities: int = 10) -> Dict[str, Any]:
        """
        Two-stage retrieval for a ticker.

        Stage 1: Find related entities (traverse KG edges up to `depth` hops)
        Stage 2: Fetch recent context for each entity (alerts, news)

        Returns structured context for LLM consumption.
        """
        kg = self._get_builder()
        graph = kg.graph

        if not graph.has_node(ticker):
            return {
                "ticker": ticker,
                "stage1_entities": [],
                "stage2_context": {},
                "retrieval_summary": f"No KG data found for {ticker}",
            }

        # ── Stage 1: Entity traversal ────────────────────────────────────────
        entities = self._traverse(ticker, depth, max_entities)

        # ── Stage 2: Context fetching ────────────────────────────────────────
        context = {}
        for entity in entities:
            entity_id = entity["id"]
            entity_context = {"entity": entity}

            # Fetch recent alerts mentioning this entity
            try:
                from app.services.persistence import persistence_service
                alerts = persistence_service.get_alerts(limit=5)
                relevant_alerts = [
                    a for a in alerts
                    if entity_id.upper() in (a.get("headline", "") + a.get("full_reasoning", "")).upper()
                ]
                entity_context["recent_alerts"] = [
                    {"headline": a["headline"], "severity": a["severity"], "impact_pct": a["impact_pct"]}
                    for a in relevant_alerts[:3]
                ]
            except Exception:
                entity_context["recent_alerts"] = []

            # Fetch temporal memory
            try:
                from app.services.memory_agent import memory_agent
                trend = memory_agent.get_trend(entity_id)
                streak = memory_agent.get_streak(entity_id)
                entity_context["temporal"] = {
                    "trend": trend.get("trend", "unknown"),
                    "streak": streak,
                }
            except Exception:
                entity_context["temporal"] = {}

            context[entity_id] = entity_context

        # ── Build retrieval summary ──────────────────────────────────────────
        summary_lines = [f"=== KG RETRIEVAL: {ticker} ({len(entities)} entities) ==="]
        for entity in entities[:5]:
            edge = entity.get("edge_type", "related")
            weight = entity.get("weight", 0)
            summary_lines.append(
                f"  {entity['id']}: {edge} (strength: {weight:.2f})"
            )

        return {
            "ticker": ticker,
            "stage1_entities": entities,
            "stage2_context": context,
            "retrieval_summary": "\n".join(summary_lines),
        }

    def _traverse(self, start: str, depth: int, max_entities: int) -> List[Dict]:
        """BFS traversal from start node, collecting related entities."""
        import networkx as nx
        kg = self._get_builder()
        graph = kg.graph

        visited = set()
        entities = []
        queue = [(start, 0, "self")]

        while queue and len(entities) < max_entities:
            node_id, level, edge_type = queue.pop(0)

            if node_id in visited or level > depth:
                continue
            visited.add(node_id)

            if node_id != start:
                node_data = graph.nodes.get(node_id, {})
                entities.append({
                    "id": node_id,
                    "type": node_data.get("type", "unknown"),
                    "edge_type": edge_type,
                    "weight": 0,  # Will be set from edge data
                    "hop_distance": level,
                })

            # Get neighbors
            for _, neighbor, data in graph.out_edges(node_id, data=True):
                if neighbor not in visited:
                    weight = data.get("weight", 0)
                    queue.append((neighbor, level + 1, data.get("edge_type", "related")))

            # Also check incoming edges
            for neighbor, _, data in graph.in_edges(node_id, data=True):
                if neighbor not in visited:
                    weight = data.get("weight", 0)
                    queue.append((neighbor, level + 1, data.get("edge_type", "related")))

        # Update weights from graph
        for entity in entities:
            eid = entity["id"]
            if graph.has_edge(start, eid):
                entity["weight"] = graph[start][eid].get("weight", 0)
            elif graph.has_edge(eid, start):
                entity["weight"] = graph[eid][start].get("weight", 0)

        return entities

    def format_for_llm(self, retrieval_result: Dict) -> str:
        """Format retrieval results into a concise string for LLM consumption."""
        lines = [retrieval_result.get("retrieval_summary", "")]

        context = retrieval_result.get("stage2_context", {})
        for entity_id, ctx in list(context.items())[:5]:
            alerts = ctx.get("recent_alerts", [])
            temporal = ctx.get("temporal", {})

            if alerts or temporal:
                lines.append(f"\n--- {entity_id} ---")
                if temporal.get("trend") and temporal["trend"] != "insufficient_data":
                    lines.append(f"  Trend: {temporal['trend']}")
                    streak = temporal.get("streak", {})
                    if streak.get("count", 0) >= 2:
                        lines.append(f"  Streak: {streak['count']} {streak['direction']}")
                for alert in alerts[:2]:
                    lines.append(f"  Alert: {alert['headline'][:80]} ({alert['severity']}, {alert['impact_pct']:+.1f}%)")

        return "\n".join(lines)


# Singleton
kg_retriever = KGRetriever()
