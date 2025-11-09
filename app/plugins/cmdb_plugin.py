"""
CMDBプラグイン（サンプル実装）

将来的に実際のCMDB APIに接続するためのプラグイン。
現在はダミーデータを返す実装。

環境変数:
    CMDB_ENABLED: プラグインの有効/無効（true/false）
    CMDB_API_URL: CMDB APIのURL（将来実装）
    CMDB_API_KEY: CMDB APIキー（将来実装）
"""

import os
from typing import Dict, List
from app.services.integration_service import BasePlugin


class Plugin(BasePlugin):
    """CMDBプラグイン"""

    def __init__(self):
        self.api_url = os.getenv("CMDB_API_URL", "")
        self.api_key = os.getenv("CMDB_API_KEY", "")

    def get_name(self) -> str:
        return "cmdb"

    def is_enabled(self) -> bool:
        """環境変数でCMDB連携の有効/無効を制御"""
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
                    "model": "PowerEdge R740",
                    "maintenance_contract": "2025-12-31まで",
                    "support_email": "support@vendor.com",
                    "support_phone": "03-1234-5678",
                    "location": "Tokyo DC-1 Rack-A-10"
                }
            }
        """
        server_names = kwargs.get("server_names", [])

        if not server_names:
            return {}

        # TODO: 実際のCMDB APIを呼び出す
        # 以下はダミーデータ実装
        result = {}

        for server_name in server_names:
            # サンプルデータ（実際にはCMDB APIから取得）
            result[server_name] = {
                "serial_number": f"SN-{server_name.upper()}-001",
                "vendor": "Dell" if "web" in server_name else "HP",
                "model": "PowerEdge R740" if "web" in server_name else "ProLiant DL380",
                "maintenance_contract": "2025-12-31まで",
                "support_email": "support@vendor.com",
                "support_phone": "03-1234-5678",
                "location": "Tokyo DC-1 Rack-A-10",
                "os": "AlmaLinux 9",
                "cpu": "Intel Xeon Gold 6248R",
                "memory": "128GB",
                "storage": "SSD 1TB x 4 (RAID10)"
            }

        return result

    def _call_cmdb_api(self, server_names: List[str]) -> Dict:
        """
        実際のCMDB APIを呼び出す（将来実装）

        Args:
            server_names: サーバー名のリスト

        Returns:
            CMDB APIレスポンス
        """
        # TODO: requests等で実際のCMDB APIを呼び出す
        # import requests
        # response = requests.get(
        #     f"{self.api_url}/servers",
        #     headers={"Authorization": f"Bearer {self.api_key}"},
        #     params={"names": ",".join(server_names)}
        # )
        # return response.json()

        raise NotImplementedError("CMDB API integration not yet implemented")
