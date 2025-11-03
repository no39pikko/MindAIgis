from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SimilarTicket(BaseModel):
    """類似チケット情報"""
    ticket_id: int = Field(..., description="チケットID")
    similarity: float = Field(..., ge=0.0, le=1.0, description="類似度スコア (0-1)")
    subject: str = Field(..., description="チケット件名")
    description: Optional[str] = Field(None, description="チケット説明")
    resolution: Optional[str] = Field(None, description="解決策・対応内容")
    category: Optional[str] = Field(None, description="カテゴリ")
    assigned_to: Optional[str] = Field(None, description="担当者")
    closed_on: Optional[datetime] = Field(None, description="完了日時")
    status: Optional[str] = Field(None, description="ステータス")

    class Config:
        json_schema_extra = {
            "example": {
                "ticket_id": 12345,
                "similarity": 0.95,
                "subject": "disk usage over 90% on web-prod-01",
                "description": "ディスク使用率が90%を超過しました",
                "resolution": "ログローテーション設定を修正",
                "category": "Infrastructure",
                "assigned_to": "admin",
                "closed_on": "2025-10-15T10:30:00",
                "status": "Closed"
            }
        }


class RedmineTicketIndex(BaseModel):
    """Redmineチケットインデックス情報"""
    ticket_id: int
    subject: str
    description: str
    resolution: str
    indexed_at: datetime
