#!/usr/bin/env python3
"""
Redmineチケットを取得してQdrantにインデックス

使い方:
    source venv/bin/activate
    python scripts/index_redmine_tickets.py
"""

import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from app.services.redmine_service import RedmineService
from app.services.vector_service import VectorService

# 環境変数読み込み
load_dotenv()


def main():
    print("=" * 60)
    print("  Redmine → Qdrant インデックス作成")
    print("=" * 60)
    print()

    # サービス初期化
    try:
        print("1. サービス初期化中...")
        redmine_service = RedmineService()
        vector_service = VectorService()
        print("   ✓ サービス初期化完了")
        print()
    except Exception as e:
        print(f"   ✗ エラー: {e}")
        print()
        print("環境変数を確認してください:")
        print("  - REDMINE_URL")
        print("  - REDMINE_API_KEY")
        print("  - OPENAI_API_KEY")
        sys.exit(1)

    # Qdrantコレクション確認
    print("2. Qdrantコレクション確認中...")
    try:
        # コレクション情報取得
        collection_info = vector_service.qdrant.get_collection(
            collection_name=vector_service.collection_name
        )
        current_count = collection_info.points_count
        print(f"   ✓ コレクション '{vector_service.collection_name}' 存在")
        print(f"   現在のベクトル数: {current_count}")
        print()
    except Exception as e:
        print(f"   ✗ コレクションエラー: {e}")
        print("   Qdrantが起動しているか確認してください:")
        print("     docker compose up -d")
        sys.exit(1)

    # Redmineからチケット取得
    print("3. Redmineからチケット取得中...")
    try:
        # 取得するチケット数（環境変数で指定可能）
        limit = int(os.getenv("INDEX_LIMIT", "100"))
        print(f"   取得上限: {limit}件")

        # チケット検索（完了済みのチケット）
        # Redmine APIを直接使用
        project_id = os.getenv("REDMINE_PROJECT_ID")
        params = {
            'status_id': 'closed',  # 完了済み
            'limit': limit,
            'sort': 'updated_on:desc'  # 更新日時の降順
        }

        if project_id:
            params['project_id'] = project_id

        issues = redmine_service.redmine.issue.filter(**params)
        tickets = list(issues)

        print(f"   ✓ {len(tickets)}件のチケットを取得")
        print()

        if not tickets:
            print("   ⚠ チケットが見つかりませんでした")
            print("   Redmineに完了済みチケットがあるか確認してください")
            sys.exit(0)

    except Exception as e:
        print(f"   ✗ エラー: {e}")
        print()
        print("Redmine接続を確認してください:")
        print("  - REDMINE_URL が正しいか")
        print("  - REDMINE_API_KEY が有効か")
        print("  - ネットワーク接続")
        sys.exit(1)

    # Qdrantにインデックス
    print("4. Qdrantにインデックス中...")
    print(f"   (OpenAI APIを使用してベクトル化します)")
    print()

    success_count = 0
    error_count = 0

    for idx, issue in enumerate(tickets, 1):
        ticket_id = issue.id
        subject = getattr(issue, 'subject', '')
        description = getattr(issue, 'description', '')

        # 解決策（最後のコメント）を取得
        resolution = ""
        if hasattr(issue, 'journals') and issue.journals:
            for journal in reversed(issue.journals):
                if hasattr(journal, 'notes') and journal.notes:
                    resolution = journal.notes
                    break

        # プログレス表示
        if idx % 10 == 0 or idx == 1:
            print(f"   処理中: {idx}/{len(tickets)} (成功: {success_count}, エラー: {error_count})")

        try:
            # メタデータ
            metadata = {
                "category": getattr(issue.tracker, 'name', '') if hasattr(issue, 'tracker') else '',
                "assigned_to": getattr(issue.assigned_to, 'name', '') if hasattr(issue, 'assigned_to') else '',
                "status": getattr(issue.status, 'name', '') if hasattr(issue, 'status') else '',
                "priority": getattr(issue.priority, 'name', '') if hasattr(issue, 'priority') else '',
                "created_on": str(getattr(issue, 'created_on', ''))[:10],
                "closed_on": str(getattr(issue, 'closed_on', ''))[:10] if hasattr(issue, 'closed_on') else ''
            }

            # チケットをベクトル化してQdrantに保存
            vector_service.index_ticket(
                ticket_id=ticket_id,
                subject=subject,
                description=description,
                resolution=resolution,
                metadata=metadata
            )
            success_count += 1

        except Exception as e:
            error_count += 1
            print(f"   ⚠ チケット#{ticket_id} のインデックスに失敗: {e}")

    print()
    print(f"   ✓ インデックス完了")
    print(f"     成功: {success_count}件")
    print(f"     エラー: {error_count}件")
    print()

    # 最終確認
    print("5. インデックス結果確認...")
    try:
        collection_info = vector_service.qdrant.get_collection(
            collection_name=vector_service.collection_name
        )
        final_count = collection_info.points_count
        print(f"   ✓ 最終ベクトル数: {final_count}")
        print(f"   増加分: +{final_count - current_count}")
        print()
    except Exception as e:
        print(f"   ⚠ 確認エラー: {e}")
        print()

    print("=" * 60)
    print("  インデックス作成完了！")
    print("=" * 60)
    print()
    print("次のステップ:")
    print("  1. ./start.sh でサービスを起動")
    print("  2. http://localhost:8501 でWeb UIにアクセス")
    print("  3. 検索を試してみてください")
    print()


if __name__ == "__main__":
    main()
