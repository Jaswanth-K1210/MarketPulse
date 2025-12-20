"""
Article Model
Represents a news article from various sources
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
import uuid


class Article(BaseModel):
    """News article model"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    url: str
    source: str
    published_at: datetime
    content: str
    companies_mentioned: List[str] = Field(default_factory=list)
    event_type: Optional[str] = None
    priority: Optional[int] = None
    relevance: Optional[str] = None
    processed_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "published_at": self.published_at.isoformat(),
            "content": self.content,
            "companies_mentioned": self.companies_mentioned,
            "event_type": self.event_type,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Article":
        """Create from dictionary"""
        if isinstance(data.get("published_at"), str):
            data["published_at"] = datetime.fromisoformat(data["published_at"])
        if data.get("processed_at") and isinstance(data["processed_at"], str):
            data["processed_at"] = datetime.fromisoformat(data["processed_at"])
        return cls(**data)
