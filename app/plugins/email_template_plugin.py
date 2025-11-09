"""
Emailテンプレートプラグイン（サンプル実装）

ベンダーエスカレーション用のEmailテンプレートを提供するプラグイン。
現在は組み込みテンプレートを返す実装。

環境変数:
    EMAIL_TEMPLATE_ENABLED: プラグインの有効/無効（true/false）
    EMAIL_TEMPLATE_DB_PATH: テンプレートDBのパス（将来実装）
"""

import os
from typing import Dict, Optional
from app.services.integration_service import BasePlugin


class Plugin(BasePlugin):
    """Emailテンプレートプラグイン"""

    def __init__(self):
        self.template_db_path = os.getenv("EMAIL_TEMPLATE_DB_PATH", "")

        # 組み込みテンプレート
        self.builtin_templates = {
            "vendor_escalation": {
                "subject": "障害エスカレーション - {server_name}",
                "body": """
{vendor}サポート御中

以下の障害について、エスカレーションいたします。

【サーバー情報】
- サーバー名: {server_name}
- シリアル番号: {serial_number}
- 保守契約: {maintenance_contract}
- 設置場所: {location}

【障害内容】
{issue_description}

【対応履歴】
{resolution_history}

【緊急度】
{priority}

お手数ですが、早急にご対応いただけますようお願いいたします。

---
本メールは自動生成されました
""".strip()
            },
            "vendor_inquiry": {
                "subject": "お問い合わせ - {server_name}",
                "body": """
{vendor}サポート御中

以下の件についてお問い合わせいたします。

【サーバー情報】
- サーバー名: {server_name}
- シリアル番号: {serial_number}
- 保守契約: {maintenance_contract}

【お問い合わせ内容】
{inquiry_content}

ご確認のほど、よろしくお願いいたします。

---
本メールは自動生成されました
""".strip()
            },
            "internal_notification": {
                "subject": "【{priority}】{server_name}で障害発生",
                "body": """
運用チーム各位

以下の障害が発生しました。

【サーバー情報】
- サーバー名: {server_name}
- 緊急度: {priority}

【障害内容】
{issue_description}

【類似事例】
{similar_cases}

【推奨対応】
{recommended_action}

詳細は Redmine チケット #{ticket_id} を参照してください。

---
本メールは MindAIgis により自動生成されました
""".strip()
            }
        }

    def get_name(self) -> str:
        return "email_template"

    def is_enabled(self) -> bool:
        """環境変数でプラグインの有効/無効を制御"""
        return os.getenv("EMAIL_TEMPLATE_ENABLED", "false").lower() == "true"

    def fetch_data(self, **kwargs) -> Dict:
        """
        Emailテンプレートを取得

        Args:
            template_name: テンプレート名（例: "vendor_escalation"）
            その他のキーワード引数: テンプレート変数として使用

        Returns:
            {
                "template": "フォーマット済みテンプレート文字列",
                "subject": "件名",
                "body": "本文"
            }
        """
        template_name = kwargs.get("template_name")

        if not template_name:
            return {"error": "template_name is required"}

        # テンプレートを取得（組み込みまたはDB）
        template = self._get_template(template_name)

        if not template:
            return {"error": f"Template '{template_name}' not found"}

        # テンプレート変数を展開
        try:
            # デフォルト値を設定
            template_vars = {
                "server_name": "N/A",
                "serial_number": "N/A",
                "vendor": "N/A",
                "maintenance_contract": "N/A",
                "location": "N/A",
                "issue_description": "N/A",
                "resolution_history": "N/A",
                "priority": "通常",
                "inquiry_content": "N/A",
                "similar_cases": "N/A",
                "recommended_action": "N/A",
                "ticket_id": "N/A"
            }

            # 引数で上書き
            template_vars.update({k: v for k, v in kwargs.items() if k != "template_name"})

            # 変数展開
            subject = template["subject"].format(**template_vars)
            body = template["body"].format(**template_vars)

            return {
                "template": f"{subject}\n\n{body}",
                "subject": subject,
                "body": body
            }

        except KeyError as e:
            return {"error": f"Missing template variable: {e}"}

    def _get_template(self, template_name: str) -> Optional[Dict]:
        """
        テンプレートを取得（組み込みまたはDB）

        Args:
            template_name: テンプレート名

        Returns:
            テンプレート辞書 {"subject": "...", "body": "..."}
        """
        # まず組み込みテンプレートを確認
        if template_name in self.builtin_templates:
            return self.builtin_templates[template_name]

        # TODO: データベースやファイルからテンプレートを読み込む
        # if self.template_db_path:
        #     return self._load_from_db(template_name)

        return None

    def list_templates(self) -> list:
        """
        利用可能なテンプレート一覧を取得

        Returns:
            テンプレート名のリスト
        """
        return list(self.builtin_templates.keys())
