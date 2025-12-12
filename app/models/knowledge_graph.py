"""
Knowledge Graph Model
Represents supply chain impact visualization
"""

from datetime import datetime
from typing import List, Dict
from pydantic import BaseModel, Field
import uuid


class GraphNode(BaseModel):
    """A node in the knowledge graph"""
    id: str
    type: str  # "event", "company", "impact"
    label: str
    metadata: Dict = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """An edge in the knowledge graph"""
    from_node: str  # Node ID
    to_node: str    # Node ID
    type: str       # "triggers", "affects", "impacts"
    confidence: float = 1.0
    metadata: Dict = Field(default_factory=dict)


class KnowledgeGraph(BaseModel):
    """Knowledge graph for supply chain visualization"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    alert_id: str
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def add_node(self, node_id: str, node_type: str, label: str, metadata: Dict = None):
        """Add a node to the graph"""
        node = GraphNode(
            id=node_id,
            type=node_type,
            label=label,
            metadata=metadata or {}
        )
        self.nodes.append(node)
        return node

    def add_edge(self, from_id: str, to_id: str, edge_type: str, confidence: float = 1.0, metadata: Dict = None):
        """Add an edge to the graph"""
        edge = GraphEdge(
            from_node=from_id,
            to_node=to_id,
            type=edge_type,
            confidence=confidence,
            metadata=metadata or {}
        )
        self.edges.append(edge)
        return edge

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "alert_id": self.alert_id,
            "nodes": [n.dict() for n in self.nodes],
            "edges": [e.dict() for e in self.edges],
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeGraph":
        """Create from dictionary"""
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])

        # Convert node dicts to GraphNode objects
        if data.get("nodes"):
            data["nodes"] = [GraphNode(**n) if isinstance(n, dict) else n for n in data["nodes"]]

        # Convert edge dicts to GraphEdge objects
        if data.get("edges"):
            data["edges"] = [GraphEdge(**e) if isinstance(e, dict) else e for e in data["edges"]]

        return cls(**data)
