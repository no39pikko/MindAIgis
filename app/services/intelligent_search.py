"""
Intelligent Search Service

自然言語クエリを受け取り、検索から要約までを統合的に処理するサービス。

処理フロー:
1. 自然言語クエリをLLMで解析
2. ベクトル検索（日付・サーバー名フィルタ付き）
3. Redmineから詳細情報とコメントを取得
4. 外部データソース（CMDB等）から追加情報を取得
5. LLMで事実ベースの要約を生成
"""

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

        print("Intelligent Search Service initialized")

    def search(
        self,
        query: str,
        limit: int = 10,
        include_context: bool = True
    ) -> Dict:
        """
        自然言語クエリで検索し、事実ベースの要約を返す

        Args:
            query: 自然言語クエリ（例: "先月web-prod-01でディスク容量のアラートが出たときどう対応した？"）
            limit: 最大取得件数
            include_context: 外部データ（CMDB等）を含めるか

        Returns:
            {
                "query_analysis": {...},  # パースされたクエリ
                "search_results": [...],  # 検索結果
                "summary": "...",         # 事実ベース要約
                "context": {...},         # 外部データ（オプション）
                "metadata": {...}         # メタデータ
            }
        """
        print(f"\n=== Intelligent Search ===")
        print(f"Query: {query}")

        # 1. クエリ分析
        print("\n[1/5] Analyzing query...")
        query_analysis = self.llm_service.analyze_query(query)
        print(f"  Keywords: {query_analysis.get('keywords')}")
        print(f"  Server names: {query_analysis.get('server_names')}")
        print(f"  Date range: {query_analysis.get('date_range')}")
        print(f"  Intent: {query_analysis.get('intent')}")

        # 2. ベクトル検索（日付フィルタ付き）
        print("\n[2/5] Searching similar tickets...")
        search_params = self._build_search_params(query_analysis, limit)
        similar_tickets = self._search_tickets(search_params)
        print(f"  Found {len(similar_tickets)} tickets")

        if not similar_tickets:
            return {
                "query_analysis": query_analysis,
                "search_results": [],
                "summary": "検索条件に一致する過去のチケットは見つかりませんでした。\n\n検索条件を変更するか、キーワードを調整してみてください。",
                "context": None,
                "metadata": {
                    "total_results": 0,
                    "date_range": query_analysis.get("date_range"),
                    "keywords": query_analysis.get("keywords")
                }
            }

        # 3. Redmineから詳細情報を取得（コメント含む）
        print("\n[3/5] Fetching ticket details from Redmine...")
        enriched_tickets = self._enrich_tickets(similar_tickets)
        print(f"  Enriched {len(enriched_tickets)} tickets")

        # 4. 外部コンテキストの取得（オプション）
        context = None
        if include_context:
            print("\n[4/5] Gathering external context...")
            context = self._gather_context(query_analysis, enriched_tickets)
            if context:
                print(f"  Context keys: {list(context.keys())}")
            else:
                print("  No external context available")

        # 5. 事実ベース要約生成
        print("\n[5/5] Generating fact-based summary...")
        summary = self.llm_service.synthesize_facts(
            query=query,
            tickets=enriched_tickets,
            context=context
        )
        print("  Summary generated")

        print("\n=== Search Complete ===\n")

        return {
            "query_analysis": query_analysis,
            "search_results": enriched_tickets,
            "summary": summary,
            "context": context,
            "metadata": {
                "total_results": len(enriched_tickets),
                "date_range": query_analysis.get("date_range"),
                "keywords": query_analysis.get("keywords"),
                "server_names": query_analysis.get("server_names")
            }
        }

    def _build_search_params(self, query_analysis: Dict, limit: int) -> Dict:
        """
        クエリ分析結果から検索パラメータを構築

        Args:
            query_analysis: LLMによるクエリ分析結果
            limit: 最大取得件数

        Returns:
            検索パラメータ
        """
        # キーワードを結合して検索クエリを作成
        keywords = query_analysis.get("keywords", [])
        alert_message = " ".join(keywords) if keywords else query_analysis.get("original_query", "")

        params = {
            "alert_message": alert_message,
            "limit": limit
        }

        # 日付範囲フィルタ
        if "date_range" in query_analysis and query_analysis["date_range"]:
            params["date_range"] = query_analysis["date_range"]

        # サーバー名フィルタ
        if "server_names" in query_analysis and query_analysis["server_names"]:
            params["server_filter"] = query_analysis["server_names"]

        return params

    def _search_tickets(self, search_params: Dict) -> List[Dict]:
        """
        ベクトル検索を実行

        Args:
            search_params: 検索パラメータ

        Returns:
            検索結果のチケットリスト
        """
        try:
            # 高度な検索メソッドがあればそれを使用、なければ通常の検索
            if hasattr(self.vector_service, 'search_similar_tickets_advanced'):
                return self.vector_service.search_similar_tickets_advanced(**search_params)
            else:
                # フォールバック: 通常の検索メソッド
                return self.vector_service.search_similar_tickets(
                    alert_message=search_params.get("alert_message", ""),
                    limit=search_params.get("limit", 10)
                )
        except Exception as e:
            print(f"Error searching tickets: {e}")
            return []

    def _enrich_tickets(self, tickets: List[Dict]) -> List[Dict]:
        """
        Redmineから詳細情報を取得してチケット情報を補完

        Args:
            tickets: ベクトル検索結果

        Returns:
            補完されたチケットリスト
        """
        enriched_tickets = []

        for ticket in tickets:
            ticket_id = ticket.get("ticket_id")

            try:
                # Redmineから詳細取得（コメント含む）
                if hasattr(self.redmine_service, 'get_ticket_details_with_comments'):
                    detail = self.redmine_service.get_ticket_details_with_comments(ticket_id)
                else:
                    # フォールバック: 通常の詳細取得
                    detail = self.redmine_service.get_ticket_details(ticket_id)

                if detail:
                    # ベクトル検索結果とRedmine詳細をマージ
                    enriched_ticket = {
                        **ticket,  # similarity スコア等を保持
                        **detail   # Redmineの詳細情報で上書き/追加
                    }
                    enriched_tickets.append(enriched_ticket)
                else:
                    # 詳細取得失敗時はベクトル検索結果のみ使用
                    enriched_tickets.append(ticket)

            except Exception as e:
                print(f"Error enriching ticket #{ticket_id}: {e}")
                enriched_tickets.append(ticket)

        return enriched_tickets

    def _gather_context(self, query_analysis: Dict, tickets: List[Dict]) -> Optional[Dict]:
        """
        外部データソースからコンテキスト情報を収集

        Args:
            query_analysis: クエリ分析結果
            tickets: チケットリスト

        Returns:
            コンテキスト情報
        """
        context = {}

        # サーバー名が特定されている場合、CMDB情報を取得
        server_names = query_analysis.get("server_names", [])

        # チケットからもサーバー名を抽出
        for ticket in tickets:
            if "server_names" in ticket:
                server_names.extend(ticket["server_names"])

        # 重複排除
        server_names = list(set(server_names))

        if server_names and self.integration_service.is_plugin_available("cmdb"):
            try:
                server_info = self.integration_service.get_server_info(server_names)
                if server_info:
                    context["servers"] = server_info
            except Exception as e:
                print(f"Error fetching CMDB data: {e}")

        # その他の外部データソース統合（将来実装）
        # - ネットワーク構成図
        # - 監視ダッシュボードリンク
        # など

        return context if context else None

    def search_basic(
        self,
        alert_message: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        基本的な検索（自然言語解析なし）

        既存のAPIとの互換性のため残す。
        新規開発では search() メソッドを使用すること。

        Args:
            alert_message: 検索クエリ
            limit: 最大取得件数

        Returns:
            検索結果のチケットリスト
        """
        # ベクトル検索
        similar_tickets = self.vector_service.search_similar_tickets(
            alert_message=alert_message,
            limit=limit
        )

        # Redmineから詳細取得
        enriched_tickets = self._enrich_tickets(similar_tickets)

        return enriched_tickets
