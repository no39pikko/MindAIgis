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


class IntelligentSearchRequest(BaseModel):
    """自然言語検索リクエスト（Phase 2）"""
    query: str = Field(..., description="自然言語クエリ（例: 先月web-prod-01でディスク容量のアラートが出たときどう対応した？）")
    limit: int = Field(10, ge=1, le=50, description="取得する類似チケット数")
    include_context: bool = Field(True, description="外部データ（CMDB等）を含めるか")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "先月web-prod-01でディスク容量のアラートが出たときどう対応した？",
                "limit": 10,
                "include_context": True
            }
        }


class ProcedureAssistRequest(BaseModel):
    """手順書作成補佐リクエスト（Phase 3）"""
    task: str = Field(..., description="作業内容（例: FW設定Aの手順書を作りたい）")
    context: Optional[str] = Field(None, description="追加コンテキスト（オプション）")

    class Config:
        json_schema_extra = {
            "example": {
                "task": "FW設定Aの手順書を作りたい",
                "context": "新規サーバーへの展開で、既存FWも並行稼働中"
            }
        }
