"""
手順書作成補佐サービス（Phase 3）

Redmineチケットの具体的な内容を深く分析し、
手順書作成に必要な情報を柔軟かつインテリジェントに提供する。
"""

import re
from typing import Dict, List, Optional, Set
from app.services.llm_service import LLMService
from app.services.vector_service import VectorService
from app.services.redmine_service import RedmineService


class ProcedureAssistantService:
    """手順書作成補佐サービス"""

    def __init__(self):
        self.llm_service = LLMService()
        self.vector_service = VectorService()
        self.redmine_service = RedmineService()
        print("Procedure Assistant Service initialized")

    def assist(self, query: str, context: Optional[str] = None) -> Dict:
        """
        手順書作成を補佐

        Args:
            query: 作業内容
            context: 追加コンテキスト（オプション）

        Returns:
            分析結果と具体的な推奨事項
        """
        print(f"\n=== 手順書作成補佐 ===")
        print(f"Query: {query}")

        # 1. 検索戦略を生成
        print("\n[1/5] 検索戦略を生成中...")
        strategies = self._generate_search_strategies(query, context)
        print(f"  生成された戦略: {len(strategies)}個")

        # 2. マルチ視点検索
        print("\n[2/5] マルチ視点検索を実行中...")
        all_tickets = self._multi_perspective_search(strategies)
        print(f"  取得チケット数: {len(all_tickets)}件")

        # 3. チケット関係性分析
        print("\n[3/5] チケット関係性を分析中...")
        if all_tickets:
            ticket_ids = {t.get("ticket_id") for t in all_tickets}
            relationships = self._analyze_relationships(ticket_ids)
            print(f"  関連チケット: {len(relationships.get('related', []))}件")
        else:
            relationships = {"related": [], "parent_child": {}, "references": {}}

        # 4. 深い分析（LLMによる具体的な内容把握）
        print("\n[4/5] チケット内容を深く分析中...")
        analyzed_tickets = self._deep_analyze_tickets(all_tickets, query, context)

        # 5. インテリジェントな推奨を生成
        print("\n[5/5] 推奨事項を生成中...")
        recommendations = self._generate_intelligent_recommendations(
            query=query,
            context=context,
            tickets=analyzed_tickets,
            strategies=strategies,
            relationships=relationships
        )

        print("\n=== 補佐完了 ===\n")

        return {
            "query": query,
            "context": context,
            "search_strategies": strategies,
            "tickets_found": len(all_tickets),
            "analyzed_tickets": analyzed_tickets,
            "relationships": relationships,
            "recommendations": recommendations
        }

    def _generate_search_strategies(self, query: str, context: Optional[str] = None) -> List[Dict]:
        """
        タスクに基づいて複数の検索戦略を生成
        """
        context_str = f"\n\n追加コンテキスト: {context}" if context else ""

        prompt = f"""以下の作業について、Redmineチケットを検索する戦略を考えてください。

【作業内容】
{query}{context_str}

複数の視点から検索することで、漏れなく関連情報を収集したい。以下の視点を考慮してください：

1. 直近の同じ作業・類似作業（最も重要）
2. 完了した過去の事例
3. 関連するトラブルや失敗事例
4. 既存システムの設定情報
5. 関連する別の作業

各検索戦略について以下を出力してください：
- perspective: 検索視点の名前
- search_query: 検索に使うクエリ
- limit: 期待する件数
- priority: high/medium/low

JSON配列形式で出力してください。
```json
{{
  "strategies": [
    {{
      "perspective": "視点名",
      "search_query": "検索クエリ",
      "limit": 10,
      "priority": "high"
    }}
  ]
}}
```
"""

        try:
            response = self.llm_service.provider.client.chat.completions.create(
                model=self.llm_service.provider.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            import json
            result = json.loads(response.choices[0].message.content)

            strategies = result.get("strategies", [])
            if not strategies:
                # フォールバック
                strategies = [
                    {
                        "perspective": "類似作業",
                        "search_query": query,
                        "limit": 10,
                        "priority": "high"
                    }
                ]

            return strategies

        except Exception as e:
            print(f"  検索戦略生成エラー: {e}")
            return [
                {
                    "perspective": "類似作業",
                    "search_query": query,
                    "limit": 10,
                    "priority": "high"
                }
            ]

    def _multi_perspective_search(self, strategies: List[Dict]) -> List[Dict]:
        """
        複数の視点で検索を実行し、重複を除いて統合
        """
        seen_ticket_ids = set()
        all_tickets = []

        for strategy in strategies:
            search_query = strategy.get("search_query", "")
            limit = strategy.get("limit", 5)
            perspective = strategy.get("perspective", "")

            try:
                # ベクトル検索
                tickets = self.vector_service.search_similar_tickets(
                    alert_message=search_query,
                    limit=limit
                )

                # Redmineから詳細取得
                for ticket in tickets:
                    ticket_id = ticket.get("ticket_id")

                    # 重複スキップ
                    if ticket_id in seen_ticket_ids:
                        continue

                    seen_ticket_ids.add(ticket_id)

                    detail = self.redmine_service.get_ticket_details_with_comments(ticket_id)
                    if detail:
                        all_tickets.append({
                            **ticket,
                            **detail,
                            "found_by_perspective": perspective
                        })

                print(f"  {perspective}: {len(tickets)}件")

            except Exception as e:
                print(f"  {perspective}の検索エラー: {e}")

        return all_tickets

    def _analyze_relationships(self, ticket_ids: Set[int]) -> Dict:
        """
        チケット間の関係性を分析
        """
        relationships = {
            "related": [],
            "parent_child": {},
            "references": {}
        }

        for ticket_id in ticket_ids:
            try:
                issue = self.redmine_service.get_ticket(ticket_id)
                if not issue:
                    continue

                # 関連チケット
                if hasattr(issue, 'relations'):
                    for relation in issue.relations:
                        related_id = relation.issue_to_id if relation.issue_to_id != ticket_id else relation.issue_id
                        relationships["related"].append({
                            "from": ticket_id,
                            "to": related_id,
                            "type": relation.relation_type
                        })

                # 親子関係
                if hasattr(issue, 'parent'):
                    relationships["parent_child"][ticket_id] = {
                        "parent": issue.parent.id
                    }

                # コメント内の参照（#XXXX）
                detail = self.redmine_service.get_ticket_details_with_comments(ticket_id)
                if detail and detail.get("comments"):
                    refs = set()
                    for comment in detail["comments"]:
                        notes = comment.get("notes", "")
                        matches = re.findall(r'#(\d+)', notes)
                        refs.update([int(m) for m in matches])

                    if refs:
                        relationships["references"][ticket_id] = list(refs)

            except Exception as e:
                print(f"  チケット#{ticket_id}の関係性分析エラー: {e}")

        return relationships

    def _deep_analyze_tickets(self, tickets: List[Dict], query: str, context: Optional[str]) -> List[Dict]:
        """
        LLMで各チケットを深く分析
        - 具体的な作業内容の把握
        - 注意すべき点の抽出
        - トラブルや失敗の記録
        - 設定値や手順の参照
        """
        analyzed = []

        for ticket in tickets:
            ticket_id = ticket.get("ticket_id")
            subject = ticket.get("subject", "")
            description = ticket.get("description", "")
            comments = ticket.get("comments", [])
            status = ticket.get("status", "")

            # チケット全体を要約
            summary = self._summarize_ticket_content(
                ticket_id, subject, description, comments, query
            )

            # 重要度評価
            importance = self._evaluate_ticket_importance(
                ticket_id, subject, description, comments, query, context
            )

            analyzed.append({
                **ticket,
                "ai_summary": summary.get("summary", ""),
                "key_points": summary.get("key_points", []),
                "cautions": summary.get("cautions", []),
                "references": summary.get("references", []),
                "importance_score": importance.get("score", 0),
                "importance_reason": importance.get("reason", "")
            })

        # 重要度順にソート
        analyzed.sort(key=lambda t: t.get("importance_score", 0), reverse=True)

        return analyzed

    def _summarize_ticket_content(
        self,
        ticket_id: int,
        subject: str,
        description: str,
        comments: List[Dict],
        query: str
    ) -> Dict:
        """
        チケットの内容を要約し、重要なポイントを抽出
        """
        # コメントをテキスト化（最大3000文字）
        comments_text = ""
        if comments:
            comments_parts = []
            for idx, c in enumerate(comments[:10], 1):  # 最大10コメント
                user = c.get("user", "不明")
                notes = c.get("notes", "")
                if notes:
                    comments_parts.append(f"コメント{idx} ({user}): {notes[:300]}")
            comments_text = "\n\n".join(comments_parts)

        full_text = f"{description}\n\n{comments_text}"[:3000]

        prompt = f"""以下のRedmineチケットを分析してください。

【作業目的】
{query}

【チケット#{ticket_id}: {subject}】
{full_text}

このチケットについて、以下を抽出してください：

1. summary: このチケットで行われた作業の具体的な要約（2-3文）
2. key_points: 手順書作成に役立つ具体的なポイント（配列）
3. cautions: 注意すべき点や失敗事例（配列）
4. references: 参照すべき設定値や既存システム情報（配列）

チケットの具体的な内容を引用しながら、実用的な情報を抽出してください。
該当する情報がない場合は空配列を返してください。

JSON形式で出力:
```json
{{
  "summary": "チケットの要約",
  "key_points": ["ポイント1", "ポイント2"],
  "cautions": ["注意点1"],
  "references": ["参照情報1"]
}}
```
"""

        try:
            response = self.llm_service.provider.client.chat.completions.create(
                model=self.llm_service.provider.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            import json
            return json.loads(response.choices[0].message.content)

        except Exception as e:
            print(f"  チケット#{ticket_id}の要約エラー: {e}")
            return {
                "summary": subject,
                "key_points": [],
                "cautions": [],
                "references": []
            }

    def _evaluate_ticket_importance(
        self,
        ticket_id: int,
        subject: str,
        description: str,
        comments: List[Dict],
        query: str,
        context: Optional[str]
    ) -> Dict:
        """
        チケットの重要度を0-100で評価
        """
        context_str = f"\n\n追加コンテキスト: {context}" if context else ""

        prompt = f"""以下のチケットが、指定された作業にとってどれだけ重要かを0-100で評価してください。

【作業目的】
{query}{context_str}

【チケット#{ticket_id}: {subject}】
{description[:500]}

評価基準:
- 90-100: 必須。このチケットなしでは手順書が作れない
- 70-89: 重要。作業の理解に大きく役立つ
- 50-69: 参考になる。関連性がある
- 30-49: 間接的に関連
- 0-29: ほとんど関連性がない

JSON形式で出力:
```json
{{
  "score": 85,
  "reason": "評価理由を1-2文で"
}}
```
"""

        try:
            response = self.llm_service.provider.client.chat.completions.create(
                model=self.llm_service.provider.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"}
            )

            import json
            return json.loads(response.choices[0].message.content)

        except Exception as e:
            print(f"  チケット#{ticket_id}の重要度評価エラー: {e}")
            return {"score": 50, "reason": "評価できませんでした"}

    def _generate_intelligent_recommendations(
        self,
        query: str,
        context: Optional[str],
        tickets: List[Dict],
        strategies: List[Dict],
        relationships: Dict
    ) -> str:
        """
        全体を俯瞰して、インテリジェントな推奨を生成
        チケットの具体的な内容を引用しながら、柔軟かつ自然な文章で説明
        """
        if not tickets:
            return self._generate_no_results_recommendation(query, context)

        # 上位5件の詳細情報を準備
        top_tickets_info = []
        for ticket in tickets[:5]:
            info = f"""
チケット#{ticket.get('ticket_id')}: {ticket.get('subject')}
重要度: {ticket.get('importance_score')}/100
理由: {ticket.get('importance_reason')}
要約: {ticket.get('ai_summary')}
主なポイント: {', '.join(ticket.get('key_points', [])[:3])}
注意点: {', '.join(ticket.get('cautions', [])[:2]) if ticket.get('cautions') else 'なし'}
"""
            top_tickets_info.append(info.strip())

        tickets_summary = "\n\n".join(top_tickets_info)

        context_str = f"\n\n追加コンテキスト: {context}" if context else ""

        prompt = f"""あなたは運用保守のエキスパートAIアシスタントです。
以下の作業について手順書を作成しようとしているユーザーに、具体的で実用的なアドバイスを提供してください。

【作業内容】
{query}{context_str}

【実行した検索】
{len(strategies)}つの視点から検索し、{len(tickets)}件のチケットを見つけました。

【重要なチケット（上位5件）】
{tickets_summary}

【チケット間の関係】
- 関連チケット: {len(relationships.get('related', []))}件
- 参照されているチケット: {len(relationships.get('references', {}))}件

以下の形式で、自然な文章でアドバイスを生成してください：

1. 全体状況の説明（見つかったチケットから何が分かるか）
2. 最も重要なチケットとその具体的な内容
3. 注意すべき点やトラブル事例（チケットの具体的な内容を引用）
4. 参照すべき情報（設定値、既存システムなど）
5. 検索結果が少ない場合の代替アプローチ

要求:
- テンプレート的な文章ではなく、チケットの具体的な内容を踏まえた自然な説明
- 「チケット#XXXでは、〇〇という問題が発生し、△△という対処をしています」のように具体的に
- 箇条書きだけでなく、文章で流れるように説明
- ユーザーが次に何をすべきか明確に
- 専門的すぎず、分かりやすく

800-1200文字程度で。
"""

        try:
            response = self.llm_service.provider.client.chat.completions.create(
                model=self.llm_service.provider.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=2000
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"  推奨生成エラー: {e}")
            return self._generate_fallback_recommendation(tickets)

    def _generate_no_results_recommendation(self, query: str, context: Optional[str]) -> str:
        """
        検索結果がない場合の柔軟な推奨
        """
        context_str = f"\n\n追加コンテキスト: {context}" if context else ""

        prompt = f"""以下の作業について、Redmineで類似チケットを検索しましたが、該当するチケットが見つかりませんでした。

【作業内容】
{query}{context_str}

このような場合に、ユーザーに提供すべきアドバイスを生成してください：

1. なぜ該当チケットが見つからなかったか（新規作業、検索語の問題など）
2. 代替アプローチ（より広範な検索、類似作業の検索、担当者への確認など）
3. 手順書作成に向けた次のステップ

自然な文章で、400-600文字程度。
"""

        try:
            response = self.llm_service.provider.client.chat.completions.create(
                model=self.llm_service.provider.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=1000
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"  推奨生成エラー: {e}")
            return f"""
検索の結果、「{query}」に直接該当するチケットは見つかりませんでした。

これは新規の作業である可能性が高いです。以下のアプローチを試してください：

1. より広範な検索語で類似作業を探す
2. 関連するシステムやコンポーネントのチケットを確認
3. 過去の担当者や詳しい方に確認する
4. 既存のシステム構成を参照する

手順書を作成する際は、今回の作業を詳細に記録し、将来の参考資料として残すことをお勧めします。
"""

    def _generate_fallback_recommendation(self, tickets: List[Dict]) -> str:
        """
        LLM生成失敗時のフォールバック
        """
        if not tickets:
            return "該当するチケットが見つかりませんでした。検索条件を広げるか、関連する作業を探してみてください。"

        top_3 = tickets[:3]
        lines = ["検索の結果、以下のチケットが見つかりました：\n"]

        for idx, ticket in enumerate(top_3, 1):
            lines.append(f"{idx}. チケット#{ticket.get('ticket_id')}: {ticket.get('subject')}")
            if ticket.get('ai_summary'):
                lines.append(f"   {ticket.get('ai_summary')}")
            lines.append("")

        lines.append("これらのチケットを確認して、手順書作成の参考にしてください。")

        return "\n".join(lines)
