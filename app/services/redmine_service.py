import os
from typing import List, Optional
from redminelib import Redmine
from redminelib.resources import Issue
from dotenv import load_dotenv

load_dotenv()


class RedmineService:
    """Redmine API連携サービス"""

    def __init__(self):
        self.redmine_url = os.getenv("REDMINE_URL")
        self.api_key = os.getenv("REDMINE_API_KEY")
        self.project_id = os.getenv("REDMINE_PROJECT_ID", "infrastructure")
        self.tracker_id = int(os.getenv("REDMINE_TRACKER_ID", "1"))

        if not self.redmine_url or not self.api_key:
            raise ValueError("REDMINE_URL and REDMINE_API_KEY must be set in environment variables")

        self.redmine = Redmine(self.redmine_url, key=self.api_key)

    def get_ticket(self, ticket_id: int) -> Optional[Issue]:
        """
        チケットの詳細情報を取得

        Args:
            ticket_id: チケットID

        Returns:
            Redmineチケットオブジェクト
        """
        try:
            issue = self.redmine.issue.get(ticket_id)
            return issue
        except Exception as e:
            print(f"Error fetching ticket {ticket_id}: {e}")
            return None

    def get_ticket_details(self, ticket_id: int) -> Optional[dict]:
        """
        チケットの詳細情報を辞書形式で取得

        Args:
            ticket_id: チケットID

        Returns:
            チケット情報の辞書
        """
        issue = self.get_ticket(ticket_id)
        if not issue:
            return None

        # ジャーナル（履歴）から最終コメントを取得
        resolution = ""
        if hasattr(issue, 'journals') and issue.journals:
            for journal in reversed(issue.journals):
                if hasattr(journal, 'notes') and journal.notes:
                    resolution = journal.notes
                    break

        return {
            "ticket_id": issue.id,
            "subject": issue.subject,
            "description": getattr(issue, 'description', '') or '',
            "resolution": resolution,
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

    def get_closed_tickets(self, limit: Optional[int] = None, offset: int = 0) -> List[Issue]:
        """
        クローズ済みチケットを取得

        Args:
            limit: 取得件数上限（Noneの場合は全件）
            offset: オフセット

        Returns:
            チケットのリスト
        """
        try:
            params = {
                'status_id': 'closed',
                'sort': 'updated_on:desc',
                'offset': offset
            }

            # プロジェクト指定がある場合
            if self.project_id:
                params['project_id'] = self.project_id

            # トラッカー指定がある場合
            if self.tracker_id:
                params['tracker_id'] = self.tracker_id

            if limit:
                params['limit'] = limit

            issues = self.redmine.issue.filter(**params)
            return list(issues)

        except Exception as e:
            print(f"Error fetching closed tickets: {e}")
            return []

    def get_all_closed_tickets_iter(self, batch_size: int = 100):
        """
        すべてのクローズ済みチケットをイテレータで取得（大量データ対応）

        Args:
            batch_size: 1回のAPIコールで取得する件数

        Yields:
            チケットオブジェクト
        """
        offset = 0
        while True:
            tickets = self.get_closed_tickets(limit=batch_size, offset=offset)
            if not tickets:
                break

            for ticket in tickets:
                yield ticket

            offset += batch_size

            # 全件取得完了チェック
            if len(tickets) < batch_size:
                break

    def search_tickets_by_keyword(self, keyword: str, limit: int = 10) -> List[Issue]:
        """
        キーワードでチケットを検索（従来型検索）

        Args:
            keyword: 検索キーワード
            limit: 取得件数上限

        Returns:
            チケットのリスト
        """
        try:
            params = {
                'subject': f'~{keyword}',  # 件名に含む
                'limit': limit,
                'sort': 'updated_on:desc'
            }

            if self.project_id:
                params['project_id'] = self.project_id

            issues = self.redmine.issue.filter(**params)
            return list(issues)

        except Exception as e:
            print(f"Error searching tickets: {e}")
            return []

    def create_ticket(
        self,
        subject: str,
        description: str,
        priority_id: int = 2,  # Normal
        assigned_to_id: Optional[int] = None
    ) -> Optional[int]:
        """
        新規チケットを作成

        Args:
            subject: 件名
            description: 説明
            priority_id: 優先度ID
            assigned_to_id: 担当者ID

        Returns:
            作成されたチケットID
        """
        try:
            issue_data = {
                'project_id': self.project_id,
                'tracker_id': self.tracker_id,
                'subject': subject,
                'description': description,
                'priority_id': priority_id
            }

            if assigned_to_id:
                issue_data['assigned_to_id'] = assigned_to_id

            issue = self.redmine.issue.create(**issue_data)
            print(f"Created ticket #{issue.id}: {subject}")
            return issue.id

        except Exception as e:
            print(f"Error creating ticket: {e}")
            return None

    def test_connection(self) -> bool:
        """
        Redmine接続テスト

        Returns:
            接続成功の場合True
        """
        try:
            user = self.redmine.user.get('current')
            print(f"Connected to Redmine as: {user.firstname} {user.lastname}")
            return True
        except Exception as e:
            print(f"Failed to connect to Redmine: {e}")
            return False

    def get_ticket_details_with_comments(self, ticket_id: int) -> Optional[dict]:
        """
        チケットの詳細情報をコメント付きで取得（Phase 2拡張機能）

        Args:
            ticket_id: チケットID

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

        # サーバー名を説明文とコメントから抽出
        full_text = issue.subject + " " + getattr(issue, 'description', '')
        for comment in comments:
            full_text += " " + comment.get("notes", "")

        server_names = self._extract_server_names(full_text)

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
            "created_on": issue.created_on.isoformat() if hasattr(issue, 'created_on') else None,
            "updated_on": issue.updated_on.isoformat() if hasattr(issue, 'updated_on') else None,
            "closed_on": issue.closed_on.isoformat() if hasattr(issue, 'closed_on') else None,
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

        if not text:
            return []

        # サーバー名パターン（環境に合わせてカスタマイズ可能）
        patterns = [
            r'\b[a-z]+-[a-z]+-\d+\b',  # web-prod-01形式
            r'\b[a-z]+[_-][a-z]+[_-]\d+\b',  # web_prod_01形式
            r'\b[a-z]+\d+\b',          # server01形式
            r'\b[a-z]+-\d+\b',         # web-01形式
        ]

        server_names = set()
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            server_names.update(matches)

        # 一般的すぎる単語を除外（環境に応じて調整）
        exclude_words = {'localhost', 'admin', 'user', 'root', 'test', 'example'}
        server_names = {name.lower() for name in server_names if name.lower() not in exclude_words}

        return list(server_names)
