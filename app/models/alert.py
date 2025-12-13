"""
Alert Model
Represents a portfolio impact alert or opportunity
"""

from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
import uuid


class AffectedHolding(BaseModel):
    """A single affected holding in the portfolio"""
    company: str
    ticker: str
    quantity: int
    impact_percent: float
    impact_dollar: float
    current_price: Optional[float] = None


class Alert(BaseModel):
    """Portfolio impact alert or opportunity model"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str  # "portfolio_impact" or "opportunity"
    severity: str  # "high", "medium", "low"
    trigger_article_id: str

    # For portfolio impact alerts
    affected_holdings: List[AffectedHolding] = Field(default_factory=list)

    # For opportunity alerts
    target_company: Optional[str] = None
    target_ticker: Optional[str] = None

    # Common fields
    impact_percent: float
    impact_dollar: float
    recommendation: str  # "HOLD", "SELL", "BUY", "MONITOR"
    confidence: float  # 0.0 to 1.0
    chain: Dict = Field(default_factory=dict)  # Impact chain levels
    sources: List[str] = Field(default_factory=list)  # Article URLs
    explanation: str
    created_at: datetime = Field(default_factory=datetime.now)
    tags: Optional[List[str]] = Field(default=None)  # Optional tags for demo/categorization

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        result = {
            "id": self.id,
            "type": self.type,
            "severity": self.severity,
            "trigger_article_id": self.trigger_article_id,
            "affected_holdings": [h.dict() for h in self.affected_holdings],
            "target_company": self.target_company,
            "target_ticker": self.target_ticker,
            "impact_percent": self.impact_percent,
            "impact_dollar": self.impact_dollar,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "chain": self.chain,
            "sources": self.sources,
            "explanation": self.explanation,
            "created_at": self.created_at.isoformat()
        }
        # Add tags if they exist (for demo alerts)
        if hasattr(self, 'tags'):
            result["tags"] = self.tags
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "Alert":
        """Create from dictionary"""
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])

        # Convert affected_holdings dicts to AffectedHolding objects
        if data.get("affected_holdings"):
            data["affected_holdings"] = [
                AffectedHolding(**h) if isinstance(h, dict) else h
                for h in data["affected_holdings"]
            ]

        return cls(**data)
