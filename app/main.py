import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.models.alert import ZabbixAlert, AlertSearchRequest, IntelligentSearchRequest
from app.models.ticket import SimilarTicket
from app.services.vector_service import VectorService
from app.services.redmine_service import RedmineService
from app.services.intelligent_search import IntelligentSearchService

load_dotenv()

# FastAPIアプリケーション初期化
app = FastAPI(
    title="MindAIgis API",
    description="保守運用特化型AIアシスタント - MVP版",
    version="0.1.0"
)

# CORS設定（Streamlitからのアクセスを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切に制限すること
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# サービスの初期化
vector_service = VectorService()
redmine_service = RedmineService()

# Phase 2: Intelligent Search Service (環境変数で制御)
intelligent_search_enabled = os.getenv("INTELLIGENT_SEARCH_ENABLED", "false").lower() == "true"
intelligent_search_service = None

if intelligent_search_enabled:
    try:
        intelligent_search_service = IntelligentSearchService()
        print("✓ Intelligent Search Service enabled")
    except Exception as e:
        print(f"✗ Failed to initialize Intelligent Search Service: {e}")
        print("  Continuing without intelligent search features...")
else:
    print("ℹ Intelligent Search Service disabled (set INTELLIGENT_SEARCH_ENABLED=true to enable)")


@app.get("/")
async def root():
    """ヘルスチェック"""
    return {
        "service": "MindAIgis API",
        "status": "running",
        "version": "0.1.0"
    }


@app.get("/health")
async def health_check():
    """詳細なヘルスチェック"""
    health_status = {
        "api": "healthy",
        "qdrant": "unknown",
        "redmine": "unknown"
    }

    # Qdrant接続チェック
    try:
        collection_info = vector_service.get_collection_info()
        health_status["qdrant"] = "healthy"
        health_status["qdrant_info"] = collection_info
    except Exception as e:
        health_status["qdrant"] = f"unhealthy: {str(e)}"

    # Redmine接続チェック
    try:
        if redmine_service.test_connection():
            health_status["redmine"] = "healthy"
        else:
            health_status["redmine"] = "unhealthy"
    except Exception as e:
        health_status["redmine"] = f"unhealthy: {str(e)}"

    return health_status


@app.post("/webhook/zabbix")
async def receive_zabbix_alert(alert: ZabbixAlert):
    """
    Zabbixからのアラート受信エンドポイント

    Args:
        alert: Zabbixアラート情報

    Returns:
        類似チケット検索結果
    """
    try:
        # アラート情報を整形
        alert_text = f"{alert.trigger_name} on {alert.hostname}: {alert.item_value}"

        # 類似チケット検索
        similar_tickets = vector_service.search_similar_tickets(
            alert_text,
            limit=5
        )

        # Redmineから詳細情報を取得して補完
        enriched_results = []
        for ticket in similar_tickets:
            detail = redmine_service.get_ticket_details(ticket["ticket_id"])
            if detail:
                # ベクトル検索結果とRedmine詳細をマージ
                enriched_results.append({
                    **ticket,
                    "category": detail.get("category"),
                    "priority": detail.get("priority"),
                    "tracker": detail.get("tracker"),
                    "project": detail.get("project")
                })
            else:
                enriched_results.append(ticket)

        return {
            "alert": alert.dict(),
            "similar_tickets": enriched_results,
            "count": len(enriched_results)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing alert: {str(e)}")


@app.post("/search", response_model=list[SimilarTicket])
async def search_similar_tickets(request: AlertSearchRequest):
    """
    類似チケット検索エンドポイント（UI用）

    Args:
        request: 検索リクエスト

    Returns:
        類似チケットのリスト
    """
    try:
        # ベクトル検索
        similar_tickets = vector_service.search_similar_tickets(
            request.alert_text,
            limit=request.limit
        )

        # Redmineから詳細情報を取得
        enriched_results = []
        for ticket in similar_tickets:
            detail = redmine_service.get_ticket_details(ticket["ticket_id"])
            if detail:
                enriched_results.append({
                    **ticket,
                    "category": detail.get("category"),
                    "priority": detail.get("priority"),
                    "tracker": detail.get("tracker"),
                    "project": detail.get("project")
                })
            else:
                enriched_results.append(ticket)

        return enriched_results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@app.post("/search/intelligent")
async def intelligent_search(request: IntelligentSearchRequest):
    """
    自然言語クエリ検索エンドポイント（Phase 2）

    自然言語でチケットを検索し、LLMによる事実ベースの要約を返す。

    Args:
        request: 自然言語検索リクエスト

    Returns:
        {
            "query_analysis": {...},  # パースされたクエリ
            "search_results": [...],  # 検索結果
            "summary": "...",         # 事実ベース要約
            "context": {...},         # 外部データ
            "metadata": {...}         # メタデータ
        }
    """
    if not intelligent_search_enabled or not intelligent_search_service:
        raise HTTPException(
            status_code=503,
            detail="Intelligent search is not enabled. Set INTELLIGENT_SEARCH_ENABLED=true and OPENAI_API_KEY in environment variables."
        )

    try:
        result = intelligent_search_service.search(
            query=request.query,
            limit=request.limit,
            include_context=request.include_context
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Intelligent search error: {str(e)}")


@app.post("/index/ticket/{ticket_id}")
async def index_ticket(ticket_id: int):
    """
    特定のチケットをインデックスに追加

    Args:
        ticket_id: インデックスするチケットID

    Returns:
        インデックス結果
    """
    try:
        # Redmineからチケット情報を取得
        detail = redmine_service.get_ticket_details(ticket_id)
        if not detail:
            raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")

        # ベクトルDBにインデックス
        vector_service.index_ticket(
            ticket_id=detail["ticket_id"],
            subject=detail["subject"],
            description=detail["description"],
            resolution=detail["resolution"],
            metadata={
                "category": detail.get("category"),
                "assigned_to": detail.get("assigned_to"),
                "status": detail.get("status"),
                "closed_on": detail.get("closed_on").isoformat() if detail.get("closed_on") else None
            }
        )

        return {
            "success": True,
            "ticket_id": ticket_id,
            "message": f"Ticket #{ticket_id} indexed successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing error: {str(e)}")


@app.get("/collection/info")
async def get_collection_info():
    """
    Qdrantコレクション情報を取得

    Returns:
        コレクションの統計情報
    """
    try:
        info = vector_service.get_collection_info()
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting collection info: {str(e)}")


@app.delete("/index/ticket/{ticket_id}")
async def delete_ticket_from_index(ticket_id: int):
    """
    インデックスからチケットを削除

    Args:
        ticket_id: 削除するチケットID

    Returns:
        削除結果
    """
    try:
        vector_service.delete_ticket(ticket_id)
        return {
            "success": True,
            "ticket_id": ticket_id,
            "message": f"Ticket #{ticket_id} deleted from index"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deletion error: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))

    uvicorn.run(app, host=host, port=port)
