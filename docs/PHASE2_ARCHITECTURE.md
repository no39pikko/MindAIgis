# Phase 2 アーキテクチャ設計書

## 1. 概要

Phase 2では、自然言語クエリ処理と事実ベースの要約生成機能を追加します。将来的なCMDB連携やEmail自動生成にも対応できる拡張可能なアーキテクチャを設計します。

### 主要機能

1. **自然言語クエリ処理**: 「先月web-prod-01でディスク容量のアラートが出たときどう対応した？」のような自然言語での検索
2. **事実ベース要約生成**: 過去のチケット情報のみを使用し、推測や一般的なアドバイスを含まない要約
3. **コメント（ジャーナル）のインデックス化**: チケットの説明だけでなく、すべてのコメントも検索対象に
4. **日付フィルタ**: 「先月」「昨日」などの相対日付と絶対日付の両方に対応
5. **外部データソース連携基盤**: CMDB、Emailテンプレートなどへの拡張可能な設計

### 設計原則

- **モジュール性**: 各機能を独立したサービスとして実装
- **拡張性**: プラグインアーキテクチャで新しいデータソースを容易に追加
- **LLM非依存**: OpenAI APIから将来的にローカルLLaMAへの移行を可能に
- **事実厳守**: LLMによる推測・幻覚を排除し、過去の記録のみを使用

---

## 2. システムアーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                         UI Layer                             │
│  ┌──────────────────┐    ┌───────────────────────────────┐ │
│  │ Streamlit UI v2  │    │   Future: Web Dashboard        │ │
│  │ (自然言語検索)    │    │   (React/Vue)                  │ │
│  └──────────────────┘    └───────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  /search/intelligent (新規)                           │  │
│  │  /search (既存)                                        │  │
│  │  /webhook/zabbix                                      │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Service Layer (新規)                       │
│  ┌─────────────────┐  ┌──────────────────┐                 │
│  │ LLM Service     │  │ Intelligent      │                 │
│  │ (抽象化層)       │  │ Search Service   │                 │
│  │ - OpenAI        │  │ - クエリ分析      │                 │
│  │ - LLaMA (将来)  │  │ - 事実ベース要約  │                 │
│  └─────────────────┘  └──────────────────┘                 │
│                                                              │
│  ┌─────────────────┐  ┌──────────────────┐                 │
│  │ Query Parser    │  │ Integration      │                 │
│  │ Service         │  │ Service          │                 │
│  │ - 自然言語解析   │  │ - プラグイン管理  │                 │
│  │ - 日付パース     │  │ - 外部データ統合  │                 │
│  └─────────────────┘  └──────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Existing Services (拡張)                        │
│  ┌─────────────────┐  ┌──────────────────┐                 │
│  │ Vector Service  │  │ Redmine Service  │                 │
│  │ (v2)            │  │ (v2)             │                 │
│  │ - コメント対応   │  │ - ジャーナル取得  │                 │
│  │ - 日付フィルタ   │  │ - 拡張メタデータ  │                 │
│  └─────────────────┘  └──────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Plugin Layer (新規)                         │
│  ┌─────────────────┐  ┌──────────────────┐                 │
│  │ CMDB Plugin     │  │ Email Template   │                 │
│  │ - サーバー情報   │  │ Plugin           │                 │
│  │ - 保守契約情報   │  │ - テンプレート取得│                 │
│  └─────────────────┘  └──────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Data Layer                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Qdrant   │  │ Redmine  │  │ CMDB     │  │ Email    │  │
│  │ (Vector) │  │ (Tickets)│  │ (将来)   │  │ DB(将来) │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 新規コンポーネント詳細設計

### 3.1 LLM Service (抽象化層)

**ファイル**: `app/services/llm_service.py`

**責務**:
- LLMプロバイダーの抽象化（OpenAI/LLaMA切り替え）
- クエリ分析
- 事実ベース要約生成

**インターフェース設計**:

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime

class BaseLLMProvider(ABC):
    """LLMプロバイダーの基底クラス"""

    @abstractmethod
    def analyze_query(self, query: str) -> Dict:
        """
        自然言語クエリを解析して構造化データに変換

        Returns:
            {
                "keywords": ["ディスク容量", "アラート"],
                "server_names": ["web-prod-01"],
                "date_range": {
                    "start": "2024-10-01",
                    "end": "2024-10-31"
                },
                "intent": "search_past_resolution"
            }
        """
        pass

    @abstractmethod
    def synthesize_facts(
        self,
        query: str,
        tickets: List[Dict],
        context: Optional[Dict] = None
    ) -> str:
        """
        過去のチケット情報から事実ベースの要約を生成

        Args:
            query: ユーザーの質問
            tickets: 検索結果のチケットリスト
            context: 追加コンテキスト（CMDB情報など）

        Returns:
            事実ベースの要約テキスト（Markdown形式）
        """
        pass

class OpenAIProvider(BaseLLMProvider):
    """OpenAI APIを使用した実装"""

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def analyze_query(self, query: str) -> Dict:
        # OpenAI Function Callingで構造化データ抽出
        # 日付パース、キーワード抽出、サーバー名抽出
        pass

    def synthesize_facts(self, query: str, tickets: List[Dict], context: Optional[Dict] = None) -> str:
        # 厳格なシステムプロンプトで事実のみを要約
        pass

class LLaMAProvider(BaseLLMProvider):
    """将来のローカルLLaMA実装用"""

    def __init__(self):
        # ローカルLLaMAエンドポイント設定
        self.endpoint = os.getenv("LLAMA_ENDPOINT", "http://localhost:8080")

    def analyze_query(self, query: str) -> Dict:
        # LLaMAでのクエリ分析実装
        pass

    def synthesize_facts(self, query: str, tickets: List[Dict], context: Optional[Dict] = None) -> str:
        # LLaMAでの要約生成実装
        pass

class LLMService:
    """LLMサービスのファサード"""

    def __init__(self):
        provider_type = os.getenv("LLM_PROVIDER", "openai")

        if provider_type == "openai":
            self.provider = OpenAIProvider()
        elif provider_type == "llama":
            self.provider = LLaMAProvider()
        else:
            raise ValueError(f"Unknown LLM provider: {provider_type}")

    def analyze_query(self, query: str) -> Dict:
        return self.provider.analyze_query(query)

    def synthesize_facts(self, query: str, tickets: List[Dict], context: Optional[Dict] = None) -> str:
        return self.provider.synthesize_facts(query, tickets, context)
```

**システムプロンプト（事実ベース要約）**:

```python
FACT_SYNTHESIS_PROMPT = """あなたは保守運用チケットの記録係です。

重要な制約:
1. 提供されたチケット情報のみを使用してください
2. 推測や一般的なアドバイスは絶対に含めないでください
3. すべての情報に出典（チケット番号）を明記してください
4. 過去形で記述してください（「〜すべき」ではなく「〜でした」）
5. チケットに記載がない情報は「記載なし」と明記してください

出力形式:
## 検索結果
[検索条件の要約]

## 過去の対応事例
### チケット#XXXXX (YYYY-MM-DD)
- **問題**: ...
- **対応**: ...
- **結果**: ...
- **対応時間**: ...

## 共通パターン
[複数チケットから見られる共通点。必ずチケット番号を引用]

## 注意点
[過去の対応で特筆すべき点。必ずチケット番号を引用]

提供されたチケット情報:
{tickets_json}

ユーザーの質問:
{query}
"""
```

### 3.2 Intelligent Search Service

**ファイル**: `app/services/intelligent_search.py`

**責務**:
- 自然言語クエリを受け取り、検索から要約までを統合
- クエリ分析 → ベクトル検索 → 詳細取得 → 事実要約の流れを制御

```python
from typing import Dict, List, Optional
from app.services.llm_service import LLMService
from app.services.vector_service import VectorService
from app.services.redmine_service import RedmineService
from app.services.integration_service import IntegrationService

class IntelligentSearchService:
    """自然言語クエリを処理する統合検索サービス"""

    def __init__(self):
        self.llm_service = LLMService()
        self.vector_service = VectorService()
        self.redmine_service = RedmineService()
        self.integration_service = IntegrationService()

    def search(
        self,
        query: str,
        limit: int = 10,
        include_context: bool = True
    ) -> Dict:
        """
        自然言語クエリで検索し、事実ベースの要約を返す

        Args:
            query: 自然言語クエリ
            limit: 最大取得件数
            include_context: 外部データ（CMDB等）を含めるか

        Returns:
            {
                "query_analysis": {...},  # パースされたクエリ
                "search_results": [...],  # 検索結果
                "summary": "...",         # 事実ベース要約
                "context": {...}          # 外部データ（オプション）
            }
        """

        # 1. クエリ分析
        query_analysis = self.llm_service.analyze_query(query)

        # 2. ベクトル検索（日付フィルタ付き）
        search_params = self._build_search_params(query_analysis, limit)
        similar_tickets = self.vector_service.search_similar_tickets_advanced(**search_params)

        # 3. Redmineから詳細情報を取得（コメント含む）
        enriched_tickets = []
        for ticket in similar_tickets:
            detail = self.redmine_service.get_ticket_details_with_comments(ticket["ticket_id"])
            if detail:
                enriched_tickets.append({
                    **ticket,
                    **detail
                })

        # 4. 外部コンテキストの取得（オプション）
        context = None
        if include_context:
            context = self._gather_context(query_analysis, enriched_tickets)

        # 5. 事実ベース要約生成
        summary = self.llm_service.synthesize_facts(
            query=query,
            tickets=enriched_tickets,
            context=context
        )

        return {
            "query_analysis": query_analysis,
            "search_results": enriched_tickets,
            "summary": summary,
            "context": context,
            "metadata": {
                "total_results": len(enriched_tickets),
                "date_range": query_analysis.get("date_range"),
                "keywords": query_analysis.get("keywords")
            }
        }

    def _build_search_params(self, query_analysis: Dict, limit: int) -> Dict:
        """クエリ分析結果から検索パラメータを構築"""
        params = {
            "alert_message": " ".join(query_analysis.get("keywords", [])),
            "limit": limit
        }

        if "date_range" in query_analysis:
            params["date_range"] = query_analysis["date_range"]

        if "server_names" in query_analysis:
            params["server_filter"] = query_analysis["server_names"]

        return params

    def _gather_context(self, query_analysis: Dict, tickets: List[Dict]) -> Dict:
        """外部データソースからコンテキスト情報を収集"""
        context = {}

        # サーバー名が特定されている場合、CMDB情報を取得（将来実装）
        if "server_names" in query_analysis:
            server_info = self.integration_service.get_server_info(
                query_analysis["server_names"]
            )
            context["servers"] = server_info

        return context
```

### 3.3 Integration Service（プラグイン管理）

**ファイル**: `app/services/integration_service.py`

**責務**:
- 外部データソース（CMDB、Email等）へのアクセスを統合管理
- プラグインの動的ロードと実行

```python
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
import importlib
import os

class BasePlugin(ABC):
    """プラグインの基底クラス"""

    @abstractmethod
    def get_name(self) -> str:
        """プラグイン名"""
        pass

    @abstractmethod
    def is_enabled(self) -> bool:
        """プラグインが有効かどうか"""
        pass

    @abstractmethod
    def fetch_data(self, **kwargs) -> Dict:
        """データ取得"""
        pass

class IntegrationService:
    """外部データソース統合サービス"""

    def __init__(self):
        self.plugins: Dict[str, BasePlugin] = {}
        self._load_plugins()

    def _load_plugins(self):
        """app/plugins/ 配下のプラグインを動的にロード"""
        plugin_dir = "app/plugins"

        if not os.path.exists(plugin_dir):
            os.makedirs(plugin_dir)
            return

        for filename in os.listdir(plugin_dir):
            if filename.endswith("_plugin.py") and not filename.startswith("__"):
                module_name = filename[:-3]
                try:
                    module = importlib.import_module(f"app.plugins.{module_name}")
                    plugin_class = getattr(module, "Plugin", None)

                    if plugin_class and issubclass(plugin_class, BasePlugin):
                        plugin = plugin_class()
                        if plugin.is_enabled():
                            self.plugins[plugin.get_name()] = plugin
                            print(f"Loaded plugin: {plugin.get_name()}")
                except Exception as e:
                    print(f"Failed to load plugin {module_name}: {e}")

    def get_server_info(self, server_names: List[str]) -> Dict:
        """CMDB連携でサーバー情報を取得"""
        if "cmdb" in self.plugins:
            return self.plugins["cmdb"].fetch_data(server_names=server_names)
        return {}

    def get_email_template(self, template_name: str, **kwargs) -> Optional[str]:
        """Emailテンプレートを取得"""
        if "email_template" in self.plugins:
            return self.plugins["email_template"].fetch_data(
                template_name=template_name,
                **kwargs
            )
        return None

    def list_available_plugins(self) -> List[str]:
        """利用可能なプラグイン一覧"""
        return list(self.plugins.keys())
```

### 3.4 プラグイン実装例

**ファイル**: `app/plugins/cmdb_plugin.py` (将来実装)

```python
from app.services.integration_service import BasePlugin
from typing import Dict, List
import os

class Plugin(BasePlugin):
    """CMDBプラグイン（将来実装）"""

    def get_name(self) -> str:
        return "cmdb"

    def is_enabled(self) -> bool:
        # 環境変数でCMDB連携の有効/無効を制御
        return os.getenv("CMDB_ENABLED", "false").lower() == "true"

    def fetch_data(self, **kwargs) -> Dict:
        """
        サーバー情報をCMDBから取得

        Args:
            server_names: サーバー名のリスト

        Returns:
            {
                "web-prod-01": {
                    "serial_number": "ABC123456",
                    "vendor": "Dell",
                    "maintenance_contract": "2025-12-31まで",
                    "support_email": "support@vendor.com"
                }
            }
        """
        server_names = kwargs.get("server_names", [])

        # TODO: 実際のCMDB APIを呼び出す
        # ここではダミーデータを返す
        result = {}
        for server_name in server_names:
            result[server_name] = {
                "serial_number": "N/A",
                "vendor": "N/A",
                "maintenance_contract": "N/A",
                "support_email": "N/A"
            }

        return result
```

**ファイル**: `app/plugins/email_template_plugin.py` (将来実装)

```python
from app.services.integration_service import BasePlugin
from typing import Dict, Optional
import os

class Plugin(BasePlugin):
    """Emailテンプレートプラグイン（将来実装）"""

    def get_name(self) -> str:
        return "email_template"

    def is_enabled(self) -> bool:
        return os.getenv("EMAIL_TEMPLATE_ENABLED", "false").lower() == "true"

    def fetch_data(self, **kwargs) -> Optional[str]:
        """
        Emailテンプレートを取得

        Args:
            template_name: テンプレート名（例: "vendor_escalation"）
            vendor: ベンダー名
            issue_description: 問題の説明

        Returns:
            テンプレート文字列（変数展開済み）
        """
        template_name = kwargs.get("template_name")

        # TODO: データベースやファイルからテンプレートを読み込む
        templates = {
            "vendor_escalation": """
件名: 障害エスカレーション - {server_name}

{vendor}サポート御中

以下の障害について、エスカレーションいたします。

【サーバー情報】
- サーバー名: {server_name}
- シリアル番号: {serial_number}
- 保守契約: {maintenance_contract}

【障害内容】
{issue_description}

【対応履歴】
{resolution_history}

ご確認のほど、よろしくお願いいたします。
"""
        }

        if template_name in templates:
            return templates[template_name].format(**kwargs)

        return None
```

---

## 4. 既存サービスの拡張

### 4.1 Vector Service v2

**ファイル**: `app/services/vector_service.py` (拡張)

**追加機能**:
1. コメント（ジャーナル）のインデックス化
2. 日付範囲フィルタ
3. サーバー名フィルタ

```python
# 追加メソッド

def index_ticket_with_comments(
    self,
    ticket_id: int,
    subject: str,
    description: str = "",
    resolution: str = "",
    comments: List[Dict] = None,
    metadata: dict = None
):
    """
    チケットをコメント付きでインデックス

    Args:
        ticket_id: チケットID
        subject: 件名
        description: 説明
        resolution: 解決策
        comments: コメントリスト [{"user": "...", "created_on": "...", "notes": "..."}]
        metadata: 追加メタデータ
    """
    # コメントを全文に含める
    comments_text = ""
    if comments:
        comments_text = "\n".join([
            f"コメント ({c.get('user', 'N/A')}, {c.get('created_on', 'N/A')}): {c.get('notes', '')}"
            for c in comments
        ])

    full_text = f"件名: {subject}\n説明: {description}\n解決策: {resolution}\n{comments_text}"

    # ベクトル化
    vector = self.embed_text(full_text)

    # ペイロード作成（拡張メタデータ）
    payload = {
        "ticket_id": ticket_id,
        "subject": subject,
        "description": description,
        "resolution": resolution,
        "comments": comments or [],
        "indexed_at": datetime.now().isoformat()
    }

    if metadata:
        payload.update(metadata)

    # Qdrantに保存
    self.qdrant.upsert(
        collection_name=self.collection_name,
        points=[PointStruct(
            id=ticket_id,
            vector=vector,
            payload=payload
        )]
    )

def search_similar_tickets_advanced(
    self,
    alert_message: str,
    limit: int = 5,
    score_threshold: float = 0.3,
    date_range: Optional[Dict] = None,
    server_filter: Optional[List[str]] = None
) -> List[dict]:
    """
    高度な類似チケット検索（日付・サーバー名フィルタ対応）

    Args:
        alert_message: 検索クエリ
        limit: 取得件数
        score_threshold: 類似度閾値
        date_range: {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}
        server_filter: サーバー名リスト

    Returns:
        類似チケットのリスト
    """
    query_vector = self.embed_text(alert_message)

    # フィルタ条件を構築
    filter_conditions = []

    if date_range:
        # 日付範囲フィルタ（created_onまたはclosed_onで絞り込み）
        from qdrant_client.models import Range, FieldCondition

        if "start" in date_range:
            filter_conditions.append(
                FieldCondition(
                    key="closed_on",
                    range=Range(
                        gte=date_range["start"]
                    )
                )
            )

        if "end" in date_range:
            filter_conditions.append(
                FieldCondition(
                    key="closed_on",
                    range=Range(
                        lte=date_range["end"]
                    )
                )
            )

    # サーバー名フィルタ（payloadに含まれるserver_names配列で検索）
    # TODO: server_names配列のインデックス化が必要

    # 検索実行
    search_params = {
        "collection_name": self.collection_name,
        "query_vector": query_vector,
        "limit": limit,
        "score_threshold": score_threshold,
        "with_payload": True
    }

    if filter_conditions:
        search_params["query_filter"] = Filter(must=filter_conditions)

    search_results = self.qdrant.search(**search_params)

    # 結果を整形
    results = []
    for hit in search_results:
        results.append({
            "ticket_id": hit.payload.get("ticket_id"),
            "similarity": hit.score,
            "subject": hit.payload.get("subject"),
            "description": hit.payload.get("description", ""),
            "resolution": hit.payload.get("resolution", ""),
            "comments": hit.payload.get("comments", []),
            "category": hit.payload.get("category"),
            "assigned_to": hit.payload.get("assigned_to"),
            "closed_on": hit.payload.get("closed_on"),
            "status": hit.payload.get("status")
        })

    return results
```

### 4.2 Redmine Service v2

**ファイル**: `app/services/redmine_service.py` (拡張)

**追加機能**:
1. ジャーナル（コメント）の完全な取得
2. サーバー名の抽出

```python
# 追加メソッド

def get_ticket_details_with_comments(self, ticket_id: int) -> Optional[dict]:
    """
    チケットの詳細情報をコメント付きで取得

    Returns:
        チケット情報（コメントリスト含む）
    """
    issue = self.get_ticket(ticket_id)
    if not issue:
        return None

    # すべてのジャーナル（コメント）を取得
    comments = []
    if hasattr(issue, 'journals') and issue.journals:
        for journal in issue.journals:
            if hasattr(journal, 'notes') and journal.notes:
                comments.append({
                    "user": getattr(journal.user, 'name', 'Unknown') if hasattr(journal, 'user') else 'Unknown',
                    "created_on": journal.created_on.isoformat() if hasattr(journal, 'created_on') else None,
                    "notes": journal.notes
                })

    # サーバー名を説明文から抽出（簡易実装）
    server_names = self._extract_server_names(
        issue.subject + " " + getattr(issue, 'description', '')
    )

    return {
        "ticket_id": issue.id,
        "subject": issue.subject,
        "description": getattr(issue, 'description', '') or '',
        "resolution": comments[-1]["notes"] if comments else "",  # 最後のコメントを解決策とする
        "comments": comments,
        "server_names": server_names,
        "category": getattr(issue.category, 'name', None) if hasattr(issue, 'category') else None,
        "assigned_to": getattr(issue.assigned_to, 'name', None) if hasattr(issue, 'assigned_to') else None,
        "status": issue.status.name if hasattr(issue, 'status') else None,
        "priority": issue.priority.name if hasattr(issue, 'priority') else None,
        "created_on": issue.created_on if hasattr(issue, 'created_on') else None,
        "updated_on": issue.updated_on if hasattr(issue, 'updated_on') else None,
        "closed_on": issue.closed_on if hasattr(issue, 'closed_on') else None,
        "tracker": issue.tracker.name if hasattr(issue, 'tracker') else None,
        "project": issue.project.name if hasattr(issue, 'project') else None,
    }

def _extract_server_names(self, text: str) -> List[str]:
    """
    テキストからサーバー名を抽出（簡易パターンマッチング）

    Args:
        text: 検索対象テキスト

    Returns:
        サーバー名のリスト
    """
    import re

    # サーバー名パターン（例: web-prod-01, db-server-02, など）
    # 環境に合わせてカスタマイズ必要
    patterns = [
        r'\b[a-z]+-[a-z]+-\d+\b',  # web-prod-01形式
        r'\b[a-z]+\d+\b',          # server01形式
    ]

    server_names = set()
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        server_names.update(matches)

    return list(server_names)
```

---

## 5. データモデル拡張

### 5.1 Qdrant Payload Schema v2

```python
{
    "ticket_id": 12345,
    "subject": "web-prod-01でディスク容量アラート",
    "description": "ディスク使用率が90%を超えました...",
    "resolution": "古いログファイルを削除して対応完了",
    "comments": [
        {
            "user": "山田太郎",
            "created_on": "2024-10-15T10:00:00",
            "notes": "/var/log配下のログを確認中"
        },
        {
            "user": "佐藤花子",
            "created_on": "2024-10-15T10:30:00",
            "notes": "30日以上前のログを削除しました"
        }
    ],
    "server_names": ["web-prod-01"],
    "category": "Infrastructure",
    "assigned_to": "山田太郎",
    "status": "Closed",
    "priority": "High",
    "created_on": "2024-10-15T03:20:00",
    "closed_on": "2024-10-15T10:45:00",
    "tracker": "Bug",
    "project": "Infrastructure",
    "indexed_at": "2024-11-08T12:00:00"
}
```

---

## 6. API設計

### 6.1 新規エンドポイント

#### POST /search/intelligent

自然言語クエリで検索し、事実ベースの要約を返す

**Request**:
```json
{
    "query": "先月web-prod-01でディスク容量のアラートが出たときどう対応した？",
    "limit": 10,
    "include_context": true
}
```

**Response**:
```json
{
    "query_analysis": {
        "keywords": ["ディスク容量", "アラート"],
        "server_names": ["web-prod-01"],
        "date_range": {
            "start": "2024-10-01",
            "end": "2024-10-31"
        },
        "intent": "search_past_resolution"
    },
    "search_results": [
        {
            "ticket_id": 12345,
            "similarity": 0.89,
            "subject": "web-prod-01でディスク容量アラート",
            "description": "...",
            "resolution": "...",
            "comments": [...],
            "server_names": ["web-prod-01"],
            "closed_on": "2024-10-15T10:45:00"
        }
    ],
    "summary": "## 検索結果\n先月（2024年10月）にweb-prod-01サーバーでディスク容量アラートが発生した事例が3件見つかりました...",
    "context": {
        "servers": {
            "web-prod-01": {
                "serial_number": "ABC123456",
                "vendor": "Dell",
                "maintenance_contract": "2025-12-31まで"
            }
        }
    },
    "metadata": {
        "total_results": 3,
        "date_range": {"start": "2024-10-01", "end": "2024-10-31"},
        "keywords": ["ディスク容量", "アラート"]
    }
}
```

---

## 7. 実装ロードマップ

### Phase 2.1: 基盤実装（2週間）

1. **LLM Service実装**
   - OpenAIProvider実装（クエリ分析、事実要約）
   - システムプロンプト設計
   - LLaMA用インターフェース定義

2. **Intelligent Search Service実装**
   - クエリ分析〜要約のワークフロー実装
   - エラーハンドリング

3. **Integration Service実装**
   - プラグインローダー実装
   - 基本的なプラグインインターフェース定義

### Phase 2.2: データ拡張（1週間）

1. **Vector Service v2**
   - コメントインデックス化
   - 日付フィルタ実装

2. **Redmine Service v2**
   - ジャーナル完全取得
   - サーバー名抽出ロジック

3. **データ再インデックス**
   - 既存データの移行スクリプト

### Phase 2.3: UI・テスト（1週間）

1. **Streamlit UI v2**
   - 自然言語検索インターフェース
   - 要約表示
   - チケット詳細表示（コメント含む）

2. **テストケース作成**
   - LLMモックを使った単体テスト
   - 統合テスト

3. **ドキュメント更新**

### Phase 2.4: プラグイン実装（将来）

1. **CMDBプラグイン**
   - 実際のCMDB APIに接続
   - サーバー情報取得

2. **Emailテンプレートプラグイン**
   - テンプレートDB設計
   - 変数展開エンジン

---

## 8. 環境変数

### 追加の環境変数

```.env
# LLM設定
LLM_PROVIDER=openai  # openai | llama
OPENAI_MODEL=gpt-4o-mini
LLAMA_ENDPOINT=http://localhost:8080  # 将来のLLaMAエンドポイント

# プラグイン設定
CMDB_ENABLED=false
CMDB_API_URL=
CMDB_API_KEY=

EMAIL_TEMPLATE_ENABLED=false
EMAIL_TEMPLATE_DB_PATH=

# 検索設定
DEFAULT_SEARCH_LIMIT=10
DEFAULT_SCORE_THRESHOLD=0.3
```

---

## 9. セキュリティ考慮事項

1. **LLM Injection対策**
   - ユーザー入力のサニタイズ
   - システムプロンプトの保護

2. **外部データアクセス制御**
   - プラグインごとの権限管理
   - API認証情報の安全な管理

3. **ログ管理**
   - 検索クエリのログ記録（個人情報に注意）
   - LLM APIコールのログ

---

## 10. パフォーマンス最適化

1. **キャッシング**
   - クエリ分析結果のキャッシュ
   - ベクトル検索結果のキャッシュ（短期間）

2. **非同期処理**
   - 外部データ取得の並列化
   - LLM API呼び出しのタイムアウト設定

3. **インデックス最適化**
   - Qdrantのインデックスパラメータチューニング
   - コメント数が多いチケットの扱い

---

## 11. まとめ

Phase 2では、自然言語クエリ処理と事実ベースの要約生成を実現します。

**重要なポイント**:
- **モジュール性**: 各機能を独立したサービスとして実装し、テスト・保守を容易に
- **拡張性**: プラグインアーキテクチャで将来的なCMDB連携やEmail自動生成に対応
- **LLM非依存**: OpenAI → LLaMAへの移行パスを確保
- **事実厳守**: LLMによる推測を排除し、過去の記録のみを使用する設計

この設計により、保守運用の現場で信頼できるAIアシスタントを実現します。
