#!/usr/bin/env python3
"""
MindAIgis 接続テストスクリプト

.env の設定が正しいか確認します
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()

print("=" * 60)
print("MindAIgis 接続テスト")
print("=" * 60)

# カラーコード
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def print_success(msg):
    print(f"{GREEN}✓{RESET} {msg}")

def print_error(msg):
    print(f"{RED}✗{RESET} {msg}")

def print_warning(msg):
    print(f"{YELLOW}⚠{RESET} {msg}")

# 1. 環境変数チェック
print("\n[1/4] 環境変数チェック")
print("-" * 60)

env_vars = {
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    "REDMINE_URL": os.getenv("REDMINE_URL"),
    "REDMINE_API_KEY": os.getenv("REDMINE_API_KEY"),
    "QDRANT_URL": os.getenv("QDRANT_URL", "http://localhost:6333"),
}

for key, value in env_vars.items():
    if value:
        # APIキーは一部マスク
        if "KEY" in key:
            masked = value[:10] + "..." + value[-4:] if len(value) > 14 else "***"
            print_success(f"{key}: {masked}")
        else:
            print_success(f"{key}: {value}")
    else:
        print_error(f"{key}: 未設定")

# 2. OpenAI接続テスト
print("\n[2/4] OpenAI API 接続テスト")
print("-" * 60)

try:
    from openai import OpenAI
    client = OpenAI(api_key=env_vars["OPENAI_API_KEY"])

    # モデル一覧取得（軽量なテスト）
    models = client.models.list()
    print_success("OpenAI API 接続成功")
    print(f"  利用可能なモデル数: {len(models.data)}")

except Exception as e:
    print_error(f"OpenAI API 接続失敗: {e}")

# 3. Qdrant接続テスト
print("\n[3/4] Qdrant 接続テスト")
print("-" * 60)

try:
    from qdrant_client import QdrantClient

    qdrant_url = env_vars["QDRANT_URL"]
    qdrant = QdrantClient(url=qdrant_url)

    # コレクション一覧取得
    collections = qdrant.get_collections()
    print_success(f"Qdrant 接続成功 ({qdrant_url})")
    print(f"  コレクション数: {len(collections.collections)}")

    # コレクション詳細
    if collections.collections:
        for col in collections.collections:
            print(f"    - {col.name}")
    else:
        print_warning("  コレクションが作成されていません（初回起動時は正常）")

except Exception as e:
    print_error(f"Qdrant 接続失敗: {e}")
    print_warning("  docker-compose up -d を実行しましたか？")

# 4. Redmine接続テスト
print("\n[4/4] Redmine API 接続テスト")
print("-" * 60)

try:
    from app.services.redmine_service import RedmineService

    redmine = RedmineService()

    # 接続テスト
    if redmine.test_connection():
        print_success("Redmine API 接続成功")

        # チケット取得テスト
        tickets = redmine.get_closed_tickets(limit=5)
        print(f"  クローズ済みチケット取得: {len(tickets)} 件")

        if tickets:
            print("  最新のチケット:")
            for ticket in tickets[:3]:
                print(f"    - #{ticket.id}: {ticket.subject[:50]}")
        else:
            print_warning("  クローズ済みチケットが見つかりません")
    else:
        print_error("Redmine API 接続失敗")

except Exception as e:
    print_error(f"Redmine 接続エラー: {e}")
    print_warning("  REDMINE_URLとREDMINE_API_KEYを確認してください")

# サマリー
print("\n" + "=" * 60)
print("テスト完了")
print("=" * 60)

print("\n次のステップ:")
print("1. すべて成功した場合:")
print("   → python scripts/index_tickets.py --limit 10")
print("   → uvicorn app.main:app --reload")
print("")
print("2. エラーがある場合:")
print("   → .env ファイルを確認")
print("   → SETUP_LOCAL.md を参照")
print("")
