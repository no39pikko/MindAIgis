import os
import importlib
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod


class BasePlugin(ABC):
    """プラグインの基底クラス"""

    @abstractmethod
    def get_name(self) -> str:
        """プラグイン名を返す"""
        pass

    @abstractmethod
    def is_enabled(self) -> bool:
        """プラグインが有効かどうかを返す"""
        pass

    @abstractmethod
    def fetch_data(self, **kwargs) -> Dict:
        """
        データを取得する

        Args:
            **kwargs: プラグイン固有のパラメータ

        Returns:
            取得したデータ
        """
        pass


class IntegrationService:
    """外部データソース統合サービス"""

    def __init__(self):
        self.plugins: Dict[str, BasePlugin] = {}
        self._load_plugins()

    def _load_plugins(self):
        """app/plugins/ 配下のプラグインを動的にロード"""
        plugin_dir = "app/plugins"
        plugins_abs_path = os.path.join(os.getcwd(), plugin_dir)

        # プラグインディレクトリが存在しない場合は作成
        if not os.path.exists(plugins_abs_path):
            os.makedirs(plugins_abs_path)
            print(f"Created plugin directory: {plugins_abs_path}")

            # __init__.pyを作成してパッケージ化
            init_file = os.path.join(plugins_abs_path, "__init__.py")
            if not os.path.exists(init_file):
                with open(init_file, "w") as f:
                    f.write("# Plugin package\n")

            return

        # プラグインファイルをロード
        for filename in os.listdir(plugins_abs_path):
            if filename.endswith("_plugin.py") and not filename.startswith("__"):
                module_name = filename[:-3]  # .pyを除く

                try:
                    # モジュールをインポート
                    module = importlib.import_module(f"app.plugins.{module_name}")

                    # Pluginクラスを取得
                    plugin_class = getattr(module, "Plugin", None)

                    if plugin_class and issubclass(plugin_class, BasePlugin):
                        plugin = plugin_class()

                        # 有効なプラグインのみ登録
                        if plugin.is_enabled():
                            self.plugins[plugin.get_name()] = plugin
                            print(f"✓ Loaded plugin: {plugin.get_name()}")
                        else:
                            print(f"✗ Plugin disabled: {plugin.get_name()}")
                    else:
                        print(f"✗ Invalid plugin format: {module_name} (missing Plugin class)")

                except Exception as e:
                    print(f"✗ Failed to load plugin {module_name}: {e}")

    def get_server_info(self, server_names: List[str]) -> Dict:
        """
        CMDB連携でサーバー情報を取得

        Args:
            server_names: サーバー名のリスト

        Returns:
            サーバー情報の辞書
            {
                "web-prod-01": {
                    "serial_number": "ABC123456",
                    "vendor": "Dell",
                    "maintenance_contract": "2025-12-31まで",
                    "support_email": "support@vendor.com"
                }
            }
        """
        if "cmdb" in self.plugins:
            try:
                return self.plugins["cmdb"].fetch_data(server_names=server_names)
            except Exception as e:
                print(f"Error fetching CMDB data: {e}")
                return {}
        else:
            print("CMDB plugin not available")
            return {}

    def get_email_template(self, template_name: str, **kwargs) -> Optional[str]:
        """
        Emailテンプレートを取得

        Args:
            template_name: テンプレート名（例: "vendor_escalation"）
            **kwargs: テンプレート変数（server_name, vendor, issue_descriptionなど）

        Returns:
            テンプレート文字列（変数展開済み）またはNone
        """
        if "email_template" in self.plugins:
            try:
                result = self.plugins["email_template"].fetch_data(
                    template_name=template_name,
                    **kwargs
                )
                return result.get("template")
            except Exception as e:
                print(f"Error fetching email template: {e}")
                return None
        else:
            print("Email template plugin not available")
            return None

    def list_available_plugins(self) -> List[str]:
        """
        利用可能なプラグイン一覧を取得

        Returns:
            プラグイン名のリスト
        """
        return list(self.plugins.keys())

    def get_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """
        特定のプラグインを取得

        Args:
            plugin_name: プラグイン名

        Returns:
            プラグインインスタンスまたはNone
        """
        return self.plugins.get(plugin_name)

    def is_plugin_available(self, plugin_name: str) -> bool:
        """
        プラグインが利用可能かチェック

        Args:
            plugin_name: プラグイン名

        Returns:
            利用可能ならTrue
        """
        return plugin_name in self.plugins
