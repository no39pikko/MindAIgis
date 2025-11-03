from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ZabbixAlert(BaseModel):
    """Zabbixからのアラート情報"""
    trigger_name: str = Field(..., description="トリガー名")
    hostname: str = Field(..., description="ホスト名")
    severity: str = Field(..., description="重要度 (Disaster, High, Average, Warning, Information)")
    item_value: str = Field(..., description="アイテム値")
    event_id: int = Field(..., description="イベントID")
    trigger_id: Optional[int] = Field(None, description="トリガーID")
    event_time: Optional[datetime] = Field(None, description="イベント発生時刻")

    class Config:
        json_schema_extra = {
            "example": {
                "trigger_name": "disk usage over 90%",
                "hostname": "web-prod-01",
                "severity": "High",
                "item_value": "92%",
                "event_id": 12345,
                "trigger_id": 67890,
                "event_time": "2025-11-03T14:32:15"
            }
        }


class AlertSearchRequest(BaseModel):
    """類似検索リクエスト"""
    alert_text: str = Field(..., description="検索するアラートテキスト")
    limit: int = Field(5, ge=1, le=20, description="取得する類似チケット数")
