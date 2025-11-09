"""
手順書作成補佐サービス（Phase 3）

Consensus風の反復的検索・分析アプローチ:
1. 作業内容そのもので検索
2. 結果を読んで理解
3. さらに調べるべきことを特定
4. 追加検索を実行
5. 全体を統合
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

        Consensus風の反復的アプローチ:
        1. 作業内容を抽出して初回検索
        2. 結果を分析
        3. 追加で調べるべきことを特定
        4. 追加検索を実行
        5. 全体を統合

        Args:
            query: 作業内容
            context: 追加コンテキスト（オプション）

        Returns:
            分析結果と具体的な推奨事項
        """
        print(f"\n=== 手順書作成補佐（反復的検索） ===")
        print(f"Query: {query}")

        # [Step 1] 作業内容を抽出
        print("\n[1/5] 作業内容を抽出中...")
        task_keywords = self._extract_task_keywords(query, context)
        print(f"  抽出キーワード: {task_keywords}")

        # [Step 2] 初回検索（作業内容そのもの）
        print("\n[2/5] 初回検索中...")
        initial_tickets = self._search_tickets(task_keywords, limit=10)
        print(f"  初回検索結果: {len(initial_tickets)}件")

        # 0件の場合はフォールバック
        if len(initial_tickets) == 0:
            print("  → フォールバック検索（threshold=0）...")
            initial_tickets = self._search_tickets(task_keywords, limit=10, score_threshold=0.0)
            print(f"  フォールバック結果: {len(initial_tickets)}件")

        # [Step 3] 初回結果を分析して、追加で調べるべきことを特定
        print("\n[3/5] 初回結果を分析し、追加調査項目を特定中...")
        additional_queries = self._identify_additional_searches(
            query, context, initial_tickets, task_keywords
        )
        print(f"  追加調査項目: {len(additional_queries)}個")
        for aq in additional_queries:
            print(f"    - {aq}")

        # [Step 4] 追加検索を実行
        print("\n[4/5] 追加検索を実行中...")
        all_tickets = initial_tickets.copy()
        seen_ids = {t.get("ticket_id") for t in initial_tickets}

        for add_query in additional_queries[:3]:  # 最大3つまで
            print(f"  検索: {add_query}")
            additional_tickets = self._search_tickets(add_query, limit=5, score_threshold=0.2)

            # 重複を除いて追加
            for ticket in additional_tickets:
                tid = ticket.get("ticket_id")
                if tid not in seen_ids:
                    all_tickets.append(ticket)
                    seen_ids.add(tid)

            print(f"    → {len(additional_tickets)}件（重複除外後 合計{len(all_tickets)}件）")

        # 関係性分析
        relationships = {"related": [], "parent_child": {}, "references": {}}
        if all_tickets:
            print(f"\n  チケット関係性を分析中...")
            ticket_ids = {t.get("ticket_id") for t in all_tickets}
            relationships = self._analyze_relationships(ticket_ids)

        # [Step 5] 全体を深く分析して統合
        print("\n[5/5] 全体を分析・統合中...")
        analyzed_tickets = self._deep_analyze_tickets(all_tickets, query, context)

        # 総合的な推奨を生成
        recommendations = self._generate_recommendations(
            query=query,
            context=context,
            tickets=analyzed_tickets,
            relationships=relationships,
            task_keywords=task_keywords,
            search_process={
                "initial_query": task_keywords,
                "initial_count": len(initial_tickets),
                "additional_queries": additional_queries,
                "total_count": len(all_tickets)
            }
        )

        print("\n=== 補佐完了 ===\n")

        return {
            "query": query,
            "context": context,
            "task_keywords": task_keywords,
            "tickets_found": len(all_tickets),
            "analyzed_tickets": analyzed_tickets,
            "relationships": relationships,
            "search_process": {
                "initial_query": task_keywords,
                "initial_count": len(initial_tickets),
                "additional_queries": additional_queries,
                "total_count": len(all_tickets)
            },
            "recommendations": recommendations
        }

    def _extract_task_keywords(self, query: str, context: Optional[str] = None) -> str:
        """
        ユーザーのクエリから作業内容のキーワードを抽出
        「DNS設定変更の手順書を作りたい」→「DNS設定変更」
        """
        context_str = f"\n\n追加コンテキスト: {context}" if context else ""

        prompt = f"""以下のユーザーの要求から、作業内容のキーワードだけを抽出してください。

【ユーザーの要求】
{query}{context_str}

抽出するのは:
- 作業内容そのもの（例: DNS設定変更、FW設定A、サーバー移行）
- 「手順書」「作成」「作りたい」などは除外
- 簡潔に、検索に使えるキーワードのみ

JSON形式で出力:
```json
{{
  "keywords": "作業内容のキーワード"
}}
```

例:
- 入力: "DNS設定変更の手順書を作成したい"
  出力: {{"keywords": "DNS設定変更"}}
- 入力: "FW設定Aの手順書を作りたい"
  出力: {{"keywords": "FW設定A"}}
- 入力: "Webサーバーのログ解析方法"
  出力: {{"keywords": "Webサーバー ログ解析"}}
"""

        try:
            response = self.llm_service.provider.client.chat.completions.create(
                model=self.llm_service.provider.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"}
            )

            import json
            result = json.loads(response.choices[0].message.content)
            return result.get("keywords", query)

        except Exception as e:
            print(f"  キーワード抽出エラー: {e}")
            # フォールバック: 「手順書」「作成」などを除外
            fallback = query.replace("手順書", "").replace("作成", "").replace("作りたい", "").replace("を", "").replace("の", "").strip()
            return fallback

    def _identify_additional_searches(
        self,
        query: str,
        context: Optional[str],
        initial_tickets: List[Dict],
        task_keywords: str
    ) -> List[str]:
        """
        初回検索結果を分析して、追加で調べるべきことを特定
        Consensusのように、結果を読んで次に何を調べるべきか考える
        """
        if not initial_tickets:
            # 初回検索が0件の場合は、広範な検索を試みる
            return [
                task_keywords + " 設定",
                task_keywords + " トラブル",
                task_keywords + " 変更"
            ]

        # 初回検索結果の概要を作成
        tickets_summary = []
        for ticket in initial_tickets[:5]:
            tickets_summary.append(f"#{ticket.get('ticket_id')}: {ticket.get('subject')}")

        summary_text = "\n".join(tickets_summary)
        context_str = f"\n\n追加コンテキスト: {context}" if context else ""

        prompt = f"""以下の作業について手順書を作成するために、初回検索で以下のチケットが見つかりました。

【作業内容】
{query}{context_str}

【初回検索キーワード】
{task_keywords}

【見つかったチケット（上位5件）】
{summary_text}

これらのチケットを見て、手順書作成のためにさらに調べるべきことを3つ提案してください。

考慮すべき観点:
1. トラブルや失敗事例（「{task_keywords} トラブル」など）
2. 関連するシステムや設定（例: DNSなら「ネームサーバー」「ゾーンファイル」など）
3. 既存システムへの影響（「{task_keywords} 影響」など）
4. 前提条件や準備（「{task_keywords} 準備」など）

JSON形式で出力:
```json
{{
  "additional_queries": ["検索クエリ1", "検索クエリ2", "検索クエリ3"]
}}
```

重要: 「手順書」「作成」などは含めず、作業内容に関連するキーワードのみ。
"""

        try:
            response = self.llm_service.provider.client.chat.completions.create(
                model=self.llm_service.provider.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                response_format={"type": "json_object"}
            )

            import json
            result = json.loads(response.choices[0].message.content)
            return result.get("additional_queries", [])

        except Exception as e:
            print(f"  追加調査項目の特定エラー: {e}")
            # フォールバック: 基本的な追加検索
            return [
                task_keywords + " トラブル",
                task_keywords + " 設定"
            ]

    def _search_tickets(self, query: str, limit: int = 10, score_threshold: float = 0.3) -> List[Dict]:
        """
        シンプルなベクトル検索
        """
        try:
            tickets = self.vector_service.search_similar_tickets(
                alert_message=query,
                limit=limit,
                score_threshold=score_threshold
            )

            # Redmineから詳細取得
            enriched = []
            for ticket in tickets:
                ticket_id = ticket.get("ticket_id")
                detail = self.redmine_service.get_ticket_details_with_comments(ticket_id)
                if detail:
                    enriched.append({
                        **ticket,
                        **detail
                    })

            return enriched

        except Exception as e:
            print(f"  検索エラー: {e}")
            return []

    def _analyze_relationships(self, ticket_ids: Set[int]) -> Dict:
        """
        チケット間の関係性を分析
        """
        relationships = {
            "related": [],
            "parent_child": {},
            "references": {}
        }

        for ticket_id in list(ticket_ids)[:10]:  # 最大10件まで
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
        LLMで各チケットを深く分析し、重要度順にソート
        """
        analyzed = []

        for ticket in tickets[:10]:  # 最大10件を詳細分析
            ticket_id = ticket.get("ticket_id")
            subject = ticket.get("subject", "")
            description = ticket.get("description", "")
            comments = ticket.get("comments", [])

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
            for idx, c in enumerate(comments[:10], 1):
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

    def _generate_recommendations(
        self,
        query: str,
        context: Optional[str],
        tickets: List[Dict],
        relationships: Dict,
        task_keywords: str,
        search_process: Dict
    ) -> str:
        """
        総合的な推奨を生成（反復的検索の結果を統合）
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
主なポイント: {', '.join(ticket.get('key_points', [])[:3]) if ticket.get('key_points') else 'なし'}
注意点: {', '.join(ticket.get('cautions', [])[:2]) if ticket.get('cautions') else 'なし'}
"""
            top_tickets_info.append(info.strip())

        tickets_summary = "\n\n".join(top_tickets_info)

        context_str = f"\n\n追加コンテキスト: {context}" if context else ""

        prompt = f"""あなたは運用保守のエキスパートAIアシスタントです。
以下の作業について手順書を作成しようとしているユーザーに、具体的で実用的なアドバイスを提供してください。

【作業内容】
{query}{context_str}

【検索プロセス】
- 初回検索キーワード: {task_keywords}
- 初回検索結果: {search_process.get('initial_count')}件
- 追加検索: {', '.join(search_process.get('additional_queries', []))}
- 最終的に見つかったチケット: {search_process.get('total_count')}件

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
5. 次に確認すべきこと

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
        検索結果がない場合の推奨
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
