"""
手順書作成補佐サービス（Phase 3）

10年選手の先輩のように、手順書作成に必要な情報を提供する。
- マルチ視点での自動検索
- チケット関係性の把握
- ハマりポイント・注意事項の抽出
- 差分分析
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
            query: 作業内容（例: "FW設定Aの手順書を作りたい"）
            context: 追加コンテキスト（オプション）

        Returns:
            {
                "search_strategies": [...],  # 検索戦略
                "tickets_by_perspective": {...},  # 視点別チケット
                "important_tickets": [...],  # 重要度順チケット
                "cautions": [...],  # 注意事項
                "pitfalls": [...],  # ハマりポイント
                "references": [...],  # 参照すべき設定値等
                "updates": [...],  # 既存システムの更新
                "relationships": {...},  # チケット関係図
                "summary": "..."  # 先輩風まとめ
            }
        """
        print(f"\n=== 手順書作成補佐 ===")
        print(f"Query: {query}")

        # 1. 検索戦略を生成
        print("\n[1/7] 検索戦略を生成中...")
        strategies = self._generate_search_strategies(query, context)
        print(f"  生成された戦略: {len(strategies)}個")

        # 2. マルチ視点検索
        print("\n[2/7] マルチ視点検索を実行中...")
        tickets_by_perspective = self._multi_perspective_search(strategies)
        total_tickets = sum(len(tickets) for tickets in tickets_by_perspective.values())
        print(f"  取得チケット数: {total_tickets}件")

        # 3. チケット関係性分析
        print("\n[3/7] チケット関係性を分析中...")
        all_ticket_ids = self._extract_all_ticket_ids(tickets_by_perspective)
        relationships = self._analyze_relationships(all_ticket_ids)
        print(f"  関連チケット: {len(relationships.get('related', []))}件")

        # 4. コメント重要度分析
        print("\n[4/7] コメントを分析中...")
        analyzed_tickets = self._analyze_comments(tickets_by_perspective)

        # 5. 差分検出
        print("\n[5/7] 差分を検出中...")
        updates = self._detect_updates(analyzed_tickets)
        print(f"  検出された更新: {len(updates)}件")

        # 6. 重要度順ソート
        print("\n[6/7] 重要度を評価中...")
        important_tickets = self._rank_by_importance(analyzed_tickets, query)

        # 7. 先輩風まとめ生成
        print("\n[7/7] まとめを生成中...")
        summary = self._generate_senior_summary(
            query=query,
            strategies=strategies,
            important_tickets=important_tickets,
            relationships=relationships,
            updates=updates
        )

        print("\n=== 補佐完了 ===\n")

        return {
            "search_strategies": strategies,
            "tickets_by_perspective": tickets_by_perspective,
            "important_tickets": important_tickets,
            "cautions": [t for t in analyzed_tickets if t.get("has_cautions")],
            "pitfalls": [t for t in analyzed_tickets if t.get("has_pitfalls")],
            "references": [t for t in analyzed_tickets if t.get("has_config_values")],
            "updates": updates,
            "relationships": relationships,
            "summary": summary
        }

    def _generate_search_strategies(self, query: str, context: Optional[str] = None) -> List[Dict]:
        """
        LLMを使って検索戦略を生成

        Returns:
            [
                {
                    "perspective": "直近の同じ作業",
                    "query": "FW設定A",
                    "filters": {"status": ["open", "in_progress", "closed"]},
                    "limit": 10,
                    "priority": "high"
                },
                ...
            ]
        """
        prompt = f"""あなたは10年のキャリアを持つ運用保守のベテランです。
以下の作業について、Redmineチケットを検索する戦略を考えてください。

【作業内容】
{query}

【検索すべき視点】
1. 直近の同じ作業（最優先、多めに）
2. 完了した同じ作業の事例（マスターチケット）
3. 既存システムの設定情報（並行稼働中）
4. 関連するトラブル事例
5. 関連システム・関連設定

各視点について、以下を考えてください：
- 検索キーワード
- 期待されるチケット数
- 重要度（high/medium/low）

JSON形式で出力してください：
```json
[
  {{
    "perspective": "視点名",
    "search_query": "検索クエリ",
    "expected_count": 件数,
    "priority": "high/medium/low",
    "reason": "なぜこの視点が重要か"
  }}
]
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

            # strategies キーが存在する場合はそれを使用、なければ全体を使用
            if "strategies" in result:
                return result["strategies"]
            else:
                return result if isinstance(result, list) else []

        except Exception as e:
            print(f"  検索戦略生成エラー: {e}")
            # フォールバック: デフォルト戦略
            return [
                {
                    "perspective": "直近の同じ作業",
                    "search_query": query,
                    "expected_count": 10,
                    "priority": "high",
                    "reason": "最新の作業手順を確認"
                },
                {
                    "perspective": "完了事例",
                    "search_query": f"{query} クローズ",
                    "expected_count": 3,
                    "priority": "medium",
                    "reason": "完了した手順を参考"
                }
            ]

    def _multi_perspective_search(self, strategies: List[Dict]) -> Dict[str, List[Dict]]:
        """
        複数の視点で検索を実行

        Returns:
            {
                "直近の同じ作業": [...],
                "完了事例": [...],
                ...
            }
        """
        results = {}

        for strategy in strategies:
            perspective = strategy.get("perspective", "その他")
            search_query = strategy.get("search_query", "")
            expected_count = strategy.get("expected_count", 5)
            priority = strategy.get("priority", "medium")

            # 優先度に応じて件数を調整
            if priority == "high":
                limit = max(expected_count, 10)
            elif priority == "medium":
                limit = min(expected_count, 5)
            else:
                limit = min(expected_count, 2)

            try:
                # ベクトル検索
                tickets = self.vector_service.search_similar_tickets(
                    alert_message=search_query,
                    limit=limit
                )

                # Redmineから詳細取得
                enriched = []
                for ticket in tickets:
                    detail = self.redmine_service.get_ticket_details_with_comments(
                        ticket.get("ticket_id")
                    )
                    if detail:
                        enriched.append({
                            **ticket,
                            **detail
                        })

                results[perspective] = enriched
                print(f"  {perspective}: {len(enriched)}件")

            except Exception as e:
                print(f"  {perspective}の検索エラー: {e}")
                results[perspective] = []

        return results

    def _extract_all_ticket_ids(self, tickets_by_perspective: Dict[str, List[Dict]]) -> Set[int]:
        """すべてのチケットIDを抽出"""
        ticket_ids = set()
        for tickets in tickets_by_perspective.values():
            for ticket in tickets:
                ticket_ids.add(ticket.get("ticket_id"))
        return ticket_ids

    def _analyze_relationships(self, ticket_ids: Set[int]) -> Dict:
        """
        チケット間の関係性を分析

        Returns:
            {
                "related": [...],  # 関連チケット
                "parent_child": {...},  # 親子関係
                "references": {...}  # コメント内参照
            }
        """
        relationships = {
            "related": [],
            "parent_child": {},
            "references": {}
        }

        for ticket_id in ticket_ids:
            try:
                # Redmineから詳細取得（関連情報含む）
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
                        # #1234 のようなパターンを抽出
                        matches = re.findall(r'#(\d+)', notes)
                        refs.update([int(m) for m in matches])

                    if refs:
                        relationships["references"][ticket_id] = list(refs)

            except Exception as e:
                print(f"  チケット#{ticket_id}の関係性分析エラー: {e}")

        return relationships

    def _analyze_comments(self, tickets_by_perspective: Dict[str, List[Dict]]) -> List[Dict]:
        """
        LLMでコメントを分析し、重要情報を抽出

        Returns:
            各チケットに以下を追加:
            - important_comments: 重要なコメント
            - has_cautions: 注意事項あり
            - has_pitfalls: ハマりポイントあり
            - has_config_values: 設定値あり
        """
        all_tickets = []
        for tickets in tickets_by_perspective.values():
            all_tickets.extend(tickets)

        analyzed = []

        for ticket in all_tickets:
            ticket_id = ticket.get("ticket_id")
            comments = ticket.get("comments", [])

            if not comments:
                analyzed.append(ticket)
                continue

            # LLMでコメント分析
            try:
                analysis = self._analyze_comments_with_llm(ticket_id, comments)

                ticket_analyzed = {
                    **ticket,
                    "important_comments": analysis.get("important_comments", []),
                    "has_cautions": analysis.get("has_cautions", False),
                    "has_pitfalls": analysis.get("has_pitfalls", False),
                    "has_config_values": analysis.get("has_config_values", False),
                    "caution_summary": analysis.get("caution_summary", ""),
                    "pitfall_summary": analysis.get("pitfall_summary", ""),
                }

                analyzed.append(ticket_analyzed)

            except Exception as e:
                print(f"  チケット#{ticket_id}のコメント分析エラー: {e}")
                analyzed.append(ticket)

        return analyzed

    def _analyze_comments_with_llm(self, ticket_id: int, comments: List[Dict]) -> Dict:
        """LLMでコメントを分析"""
        comments_text = "\n\n".join([
            f"[{c.get('user')} - {c.get('created_on')}]\n{c.get('notes')}"
            for c in comments
        ])

        prompt = f"""以下はチケット#{ticket_id}のコメントです。
運用手順書を作成する際に重要な情報を抽出してください。

【コメント】
{comments_text[:3000]}  # 長すぎる場合は切る

【抽出すべき情報】
1. 注意事項: 必ず気をつけるべきこと
2. ハマりポイント: 実際に失敗した事例や回避方法
3. 設定値: 具体的な設定内容（これは参照のみ提示）

JSON形式で出力:
```json
{{
  "has_cautions": true/false,
  "caution_summary": "注意事項の要約",
  "has_pitfalls": true/false,
  "pitfall_summary": "ハマりポイントの要約",
  "has_config_values": true/false,
  "important_comments": [
    {{
      "index": コメント番号,
      "user": "ユーザー名",
      "type": "caution/pitfall/config",
      "summary": "要約"
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
            return json.loads(response.choices[0].message.content)

        except Exception as e:
            print(f"  LLM分析エラー: {e}")
            return {
                "has_cautions": False,
                "has_pitfalls": False,
                "has_config_values": False,
                "important_comments": []
            }

    def _detect_updates(self, tickets: List[Dict]) -> List[Dict]:
        """
        既存システムの更新を検出

        スレッドから「更新」「変更」「パッチ」などを検出
        """
        updates = []

        for ticket in tickets:
            comments = ticket.get("comments", [])
            ticket_id = ticket.get("ticket_id")

            for idx, comment in enumerate(comments):
                notes = comment.get("notes", "")

                # 更新関連のキーワード
                update_keywords = ["更新", "変更", "パッチ", "修正", "適用", "反映"]

                if any(kw in notes for kw in update_keywords):
                    updates.append({
                        "ticket_id": ticket_id,
                        "comment_index": idx,
                        "user": comment.get("user"),
                        "created_on": comment.get("created_on"),
                        "content": notes[:200],
                        "requires_reflection": True  # 新規設定への反映が必要
                    })

        return updates

    def _rank_by_importance(self, tickets: List[Dict], query: str) -> List[Dict]:
        """
        LLMでチケットの重要度を評価してソート

        Returns:
            重要度順にソートされたチケットリスト
        """
        if not tickets:
            return []

        # チケット情報をLLMに渡す形式に変換
        tickets_info = []
        for ticket in tickets[:20]:  # 最大20件まで
            tickets_info.append({
                "ticket_id": ticket.get("ticket_id"),
                "subject": ticket.get("subject"),
                "status": ticket.get("status"),
                "closed_on": ticket.get("closed_on"),
                "has_cautions": ticket.get("has_cautions", False),
                "has_pitfalls": ticket.get("has_pitfalls", False),
                "similarity": ticket.get("similarity", 0)
            })

        prompt = f"""以下のチケットを、手順書作成の重要度順に並び替えてください。

【作業内容】
{query}

【チケット一覧】
{tickets_info}

【評価基準】
1. 完了した同じ作業（最重要）
2. ハマりポイント・注意事項あり
3. 類似度が高い
4. 最近の事例

チケットIDを重要度順に並べてJSON形式で出力:
```json
{{
  "ranked_ticket_ids": [ticket_id1, ticket_id2, ...]
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
            ranked_ids = result.get("ranked_ticket_ids", [])

            # IDの順序でチケットをソート
            ticket_map = {t.get("ticket_id"): t for t in tickets}
            ranked = []
            for ticket_id in ranked_ids:
                if ticket_id in ticket_map:
                    ranked.append(ticket_map[ticket_id])

            # ランクに入らなかったチケットも末尾に追加
            ranked_ids_set = set(ranked_ids)
            for ticket in tickets:
                if ticket.get("ticket_id") not in ranked_ids_set:
                    ranked.append(ticket)

            return ranked

        except Exception as e:
            print(f"  重要度評価エラー: {e}")
            # フォールバック: 類似度順
            return sorted(tickets, key=lambda t: t.get("similarity", 0), reverse=True)

    def _generate_senior_summary(
        self,
        query: str,
        strategies: List[Dict],
        important_tickets: List[Dict],
        relationships: Dict,
        updates: List[Dict]
    ) -> str:
        """
        10年選手の先輩風にまとめを生成
        """
        # 上位5件のチケット情報
        top_tickets = important_tickets[:5]

        tickets_summary = []
        for ticket in top_tickets:
            summary = f"チケット#{ticket.get('ticket_id')}: {ticket.get('subject')}"
            if ticket.get("has_cautions"):
                summary += " [注意事項あり]"
            if ticket.get("has_pitfalls"):
                summary += " [ハマりポイントあり]"
            tickets_summary.append(summary)

        prompt = f"""あなたは10年のキャリアを持つ運用保守のベテラン先輩です。
後輩が以下の作業の手順書を作ろうとしています。

【作業内容】
{query}

【検索した視点】
{[s.get('perspective') for s in strategies]}

【見つかった重要なチケット】
{chr(10).join(tickets_summary)}

【既存システムの更新】
{len(updates)}件の更新が検出されました

【チケット間の関連】
- 関連チケット: {len(relationships.get('related', []))}件
- 参照チケット: {len(relationships.get('references', {}))}件

先輩として、以下のような口調でアドバイスをしてください：
- 「まずチケット#XXXXを見とけ。ここに全体の流れが書いてある」
- 「チケット#YYYYのコメント3は必ず読め。ハマるぞ」
- 「既存システムの設定は#ZZZZを参照な」
- 「最近#AAAAで更新があったから、そっちも反映しておけよ」

簡潔に、実践的に、先輩らしく。
"""

        try:
            response = self.llm_service.provider.client.chat.completions.create(
                model=self.llm_service.provider.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,  # 少し高めで先輩らしい口調
                max_tokens=1000
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"  まとめ生成エラー: {e}")
            return "手順書作成に必要なチケットを検索しました。重要なチケットから確認してください。"
