import os
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class BaseLLMProvider(ABC):
    """LLMプロバイダーの基底クラス"""

    @abstractmethod
    def analyze_query(self, query: str) -> Dict:
        """
        自然言語クエリを解析して構造化データに変換

        Args:
            query: 自然言語クエリ

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
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY must be set in environment variables")

        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def analyze_query(self, query: str) -> Dict:
        """
        OpenAI Function Callingを使用してクエリを解析

        Args:
            query: 自然言語クエリ

        Returns:
            構造化されたクエリ情報
        """
        try:
            # Function Calling用のスキーマ定義
            functions = [
                {
                    "name": "parse_maintenance_query",
                    "description": "保守運用に関する自然言語クエリを構造化データに変換する",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "検索に使用するキーワード（例: ディスク容量, アラート, エラー）"
                            },
                            "server_names": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "特定されたサーバー名のリスト（例: web-prod-01）"
                            },
                            "date_expression": {
                                "type": "string",
                                "description": "日付表現（例: 先月, 昨日, 2024年10月, null）"
                            },
                            "intent": {
                                "type": "string",
                                "enum": ["search_past_resolution", "search_similar_issues", "general_search"],
                                "description": "クエリの意図"
                            }
                        },
                        "required": ["keywords", "intent"]
                    }
                }
            ]

            # OpenAI APIを呼び出し
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """あなたは保守運用チケット検索システムのクエリアナライザーです。
ユーザーの自然言語クエリを解析して、検索に必要な構造化データを抽出してください。

重要な抽出項目:
1. キーワード: エラー内容、システム名、症状など
2. サーバー名: web-prod-01のような具体的なホスト名
3. 日付表現: 「先月」「昨日」「2024年10月」など
4. 意図: 過去の解決策を探しているのか、類似事例を探しているのか"""
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                functions=functions,
                function_call={"name": "parse_maintenance_query"}
            )

            # 関数呼び出し結果を取得
            function_call = response.choices[0].message.function_call
            if function_call and function_call.arguments:
                parsed_data = json.loads(function_call.arguments)

                # 日付表現を具体的な日付範囲に変換
                date_range = None
                if parsed_data.get("date_expression"):
                    date_range = self._parse_date_expression(parsed_data["date_expression"])

                return {
                    "keywords": parsed_data.get("keywords", []),
                    "server_names": parsed_data.get("server_names", []),
                    "date_range": date_range,
                    "intent": parsed_data.get("intent", "general_search"),
                    "original_query": query
                }

            # Fallback: 関数呼び出しが失敗した場合
            return {
                "keywords": [query],
                "server_names": [],
                "date_range": None,
                "intent": "general_search",
                "original_query": query
            }

        except Exception as e:
            print(f"Error analyzing query: {e}")
            # エラー時はクエリ全体をキーワードとして扱う
            return {
                "keywords": [query],
                "server_names": [],
                "date_range": None,
                "intent": "general_search",
                "original_query": query,
                "error": str(e)
            }

    def _parse_date_expression(self, date_expression: str) -> Optional[Dict[str, str]]:
        """
        相対日付表現を具体的な日付範囲に変換

        Args:
            date_expression: 日付表現（先月、昨日、2024年10月など）

        Returns:
            {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"} または None
        """
        try:
            today = datetime.now()
            date_expression_lower = date_expression.lower()

            # 今日
            if "今日" in date_expression_lower or "本日" in date_expression_lower:
                return {
                    "start": today.strftime("%Y-%m-%d"),
                    "end": today.strftime("%Y-%m-%d")
                }

            # 昨日
            if "昨日" in date_expression_lower:
                yesterday = today - timedelta(days=1)
                return {
                    "start": yesterday.strftime("%Y-%m-%d"),
                    "end": yesterday.strftime("%Y-%m-%d")
                }

            # 先週
            if "先週" in date_expression_lower:
                last_week_end = today - timedelta(days=today.weekday() + 1)
                last_week_start = last_week_end - timedelta(days=6)
                return {
                    "start": last_week_start.strftime("%Y-%m-%d"),
                    "end": last_week_end.strftime("%Y-%m-%d")
                }

            # 先月
            if "先月" in date_expression_lower:
                first_day_this_month = today.replace(day=1)
                last_day_last_month = first_day_this_month - timedelta(days=1)
                first_day_last_month = last_day_last_month.replace(day=1)
                return {
                    "start": first_day_last_month.strftime("%Y-%m-%d"),
                    "end": last_day_last_month.strftime("%Y-%m-%d")
                }

            # 今月
            if "今月" in date_expression_lower or "本月" in date_expression_lower:
                first_day = today.replace(day=1)
                return {
                    "start": first_day.strftime("%Y-%m-%d"),
                    "end": today.strftime("%Y-%m-%d")
                }

            # YYYY年MM月形式
            import re
            year_month_match = re.search(r'(\d{4})年(\d{1,2})月', date_expression)
            if year_month_match:
                year = int(year_month_match.group(1))
                month = int(year_month_match.group(2))
                first_day = datetime(year, month, 1)

                # 月末を計算
                if month == 12:
                    last_day = datetime(year, 12, 31)
                else:
                    last_day = datetime(year, month + 1, 1) - timedelta(days=1)

                return {
                    "start": first_day.strftime("%Y-%m-%d"),
                    "end": last_day.strftime("%Y-%m-%d")
                }

            # 直近N日
            days_match = re.search(r'直近(\d+)日|過去(\d+)日', date_expression_lower)
            if days_match:
                days = int(days_match.group(1) or days_match.group(2))
                start_date = today - timedelta(days=days)
                return {
                    "start": start_date.strftime("%Y-%m-%d"),
                    "end": today.strftime("%Y-%m-%d")
                }

            return None

        except Exception as e:
            print(f"Error parsing date expression '{date_expression}': {e}")
            return None

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
        if not tickets:
            return "検索条件に一致する過去のチケットは見つかりませんでした。"

        try:
            # チケット情報をJSON形式で整形
            tickets_data = []
            for ticket in tickets:
                ticket_info = {
                    "ticket_id": ticket.get("ticket_id"),
                    "subject": ticket.get("subject"),
                    "description": ticket.get("description", ""),
                    "resolution": ticket.get("resolution", ""),
                    "created_on": ticket.get("created_on"),
                    "closed_on": ticket.get("closed_on"),
                    "similarity": f"{ticket.get('similarity', 0) * 100:.1f}%",
                    "assigned_to": ticket.get("assigned_to"),
                    "status": ticket.get("status")
                }

                # コメントがある場合は追加
                if ticket.get("comments"):
                    ticket_info["comments"] = [
                        {
                            "user": c.get("user"),
                            "created_on": c.get("created_on"),
                            "notes": c.get("notes")
                        }
                        for c in ticket.get("comments", [])
                    ]

                tickets_data.append(ticket_info)

            # システムプロンプト
            system_prompt = """あなたは保守運用チケットの記録係です。

重要な制約:
1. 提供されたチケット情報のみを使用してください
2. 推測や一般的なアドバイスは絶対に含めないでください
3. すべての情報に出典（チケット番号）を明記してください
4. 過去形で記述してください（「〜すべき」ではなく「〜でした」「〜しました」）
5. チケットに記載がない情報は「記載なし」と明記してください
6. 複数のチケットがある場合、共通パターンを抽出してください（必ず出典を明記）

出力形式:
## 検索結果
[検索条件の要約と見つかったチケット数]

## 過去の対応事例
### チケット#XXXXX (YYYY-MM-DD)
- **問題**: ...
- **対応**: ...
- **結果**: ...
- **対応時間**: ...
- **担当**: ...

（複数チケットがある場合は繰り返し）

## 共通パターン
[複数チケットから見られる共通点。必ずチケット番号を引用]

## 注意点
[過去の対応で特筆すべき点。必ずチケット番号を引用]

回答は日本語で、プロの保守運用担当者が読むことを想定してください。"""

            # ユーザーメッセージ
            user_message = f"""ユーザーの質問:
{query}

検索で見つかったチケット情報（JSON形式）:
{json.dumps(tickets_data, ensure_ascii=False, indent=2)}"""

            # コンテキスト情報を追加
            if context:
                user_message += f"\n\n追加情報（CMDB等）:\n{json.dumps(context, ensure_ascii=False, indent=2)}"

            # OpenAI APIで要約生成
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,  # 低めの温度で事実に基づいた出力を重視
                max_tokens=2000
            )

            summary = response.choices[0].message.content

            return summary

        except Exception as e:
            print(f"Error synthesizing facts: {e}")
            # エラー時は簡易的な要約を返す
            return self._fallback_summary(query, tickets)

    def _fallback_summary(self, query: str, tickets: List[Dict]) -> str:
        """
        LLM APIエラー時のフォールバック要約生成

        Args:
            query: ユーザーの質問
            tickets: チケットリスト

        Returns:
            簡易的な要約
        """
        summary_parts = [
            f"## 検索結果\n",
            f"クエリ「{query}」に対して、{len(tickets)}件のチケットが見つかりました。\n",
            f"\n## 過去の対応事例\n"
        ]

        for ticket in tickets[:5]:  # 最大5件まで表示
            ticket_id = ticket.get("ticket_id")
            subject = ticket.get("subject", "N/A")
            similarity = ticket.get("similarity", 0)
            closed_on = ticket.get("closed_on", "N/A")

            summary_parts.append(f"### チケット#{ticket_id} ({closed_on})\n")
            summary_parts.append(f"- **件名**: {subject}\n")
            summary_parts.append(f"- **類似度**: {similarity * 100:.1f}%\n")

            if ticket.get("resolution"):
                summary_parts.append(f"- **解決策**: {ticket['resolution'][:200]}...\n")

            summary_parts.append("\n")

        return "".join(summary_parts)


class LLaMAProvider(BaseLLMProvider):
    """将来のローカルLLaMA実装用（現在はNotImplemented）"""

    def __init__(self):
        self.endpoint = os.getenv("LLAMA_ENDPOINT", "http://localhost:8080")
        print("Warning: LLaMAProvider is not yet implemented. Please use OpenAIProvider.")

    def analyze_query(self, query: str) -> Dict:
        raise NotImplementedError("LLaMAProvider is not yet implemented")

    def synthesize_facts(
        self,
        query: str,
        tickets: List[Dict],
        context: Optional[Dict] = None
    ) -> str:
        raise NotImplementedError("LLaMAProvider is not yet implemented")


class LLMService:
    """LLMサービスのファサード"""

    def __init__(self):
        provider_type = os.getenv("LLM_PROVIDER", "openai").lower()

        if provider_type == "openai":
            self.provider = OpenAIProvider()
        elif provider_type == "llama":
            self.provider = LLaMAProvider()
        else:
            raise ValueError(f"Unknown LLM provider: {provider_type}. Supported: openai, llama")

        print(f"LLM Service initialized with provider: {provider_type}")

    def analyze_query(self, query: str) -> Dict:
        """
        自然言語クエリを解析

        Args:
            query: 自然言語クエリ

        Returns:
            構造化されたクエリ情報
        """
        return self.provider.analyze_query(query)

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
            context: 追加コンテキスト

        Returns:
            事実ベースの要約
        """
        return self.provider.synthesize_facts(query, tickets, context)
