#!/usr/bin/env python3
"""
既存のチケットをコメント付きで再インデックス化するスクリプト（Phase 2対応）

Phase 1でインデックスされたチケットには、コメント（ジャーナル）が含まれていません。
このスクリプトは、すべてのクローズ済みチケットを取得し、コメント付きで再インデックスします。

使い方:
    python scripts/reindex_tickets_with_comments.py [--limit N] [--batch-size N]

オプション:
    --limit N: インデックスする最大件数（省略時は全件）
    --batch-size N: バッチサイズ（デフォルト: 50）
    --dry-run: 実際のインデックスを行わず、処理内容のみ表示
"""

import sys
import os
import argparse
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.vector_service import VectorService
from app.services.redmine_service import RedmineService
from tqdm import tqdm


def reindex_tickets_with_comments(
    limit: int = None,
    batch_size: int = 50,
    dry_run: bool = False
):
    """
    クローズ済みチケットをコメント付きで再インデックス

    Args:
        limit: インデックスする最大件数（Noneの場合は全件）
        batch_size: Redmineから一度に取得する件数
        dry_run: Trueの場合、実際のインデックスは行わない
    """
    print("=" * 70)
    print("MindAIgis - Phase 2 チケット再インデックス")
    print("=" * 70)
    print()

    if dry_run:
        print("⚠️  DRY RUN MODE: 実際のインデックスは行いません")
        print()

    # サービスの初期化
    try:
        print("[1/4] サービスを初期化中...")
        vector_service = VectorService()
        redmine_service = RedmineService()
        print("  ✓ Vector Service initialized")
        print("  ✓ Redmine Service initialized")
        print()
    except Exception as e:
        print(f"  ✗ サービスの初期化に失敗: {e}")
        return

    # Redmine接続テスト
    print("[2/4] Redmine接続をテスト中...")
    if not redmine_service.test_connection():
        print("  ✗ Redmine接続に失敗しました")
        return
    print("  ✓ Redmine connected")
    print()

    # コレクション情報を表示
    print("[3/4] 現在のコレクション情報を取得中...")
    collection_info = vector_service.get_collection_info()
    print(f"  Collection: {collection_info.get('name')}")
    print(f"  Points count: {collection_info.get('points_count')}")
    print(f"  Vectors count: {collection_info.get('vectors_count')}")
    print()

    # クローズ済みチケットを取得してインデックス
    print("[4/4] チケットを再インデックス中...")

    indexed_count = 0
    error_count = 0
    skipped_count = 0
    start_time = datetime.now()

    try:
        # イテレータを使用して大量データに対応
        ticket_iter = redmine_service.get_all_closed_tickets_iter(batch_size=batch_size)

        # 全体の件数取得のための一時的なフィルタ（概算）
        total_tickets = redmine_service.get_closed_tickets(limit=1, offset=0)
        total_count = len(total_tickets) if total_tickets else 0

        # 実際の件数がわからないため、limitがある場合はそれを使用
        max_tickets = limit if limit else "All"
        print(f"  対象チケット数: {max_tickets}")
        print()

        with tqdm(total=limit if limit else None, desc="Indexing tickets") as pbar:
            for ticket in ticket_iter:
                # 件数制限チェック
                if limit and indexed_count + error_count + skipped_count >= limit:
                    break

                try:
                    # チケット詳細を取得（コメント付き）
                    ticket_details = redmine_service.get_ticket_details_with_comments(ticket.id)

                    if not ticket_details:
                        print(f"  ⚠️  チケット #{ticket.id} の詳細取得に失敗")
                        skipped_count += 1
                        pbar.update(1)
                        continue

                    # DRY RUNモードの場合は表示のみ
                    if dry_run:
                        print(f"  [DRY RUN] Would index ticket #{ticket_details['ticket_id']}: {ticket_details['subject']}")
                        print(f"            Comments: {len(ticket_details.get('comments', []))}")
                        indexed_count += 1
                        pbar.update(1)
                        continue

                    # コメント付きでインデックス
                    metadata = {
                        "server_names": ticket_details.get("server_names", []),
                        "category": ticket_details.get("category"),
                        "assigned_to": ticket_details.get("assigned_to"),
                        "status": ticket_details.get("status"),
                        "priority": ticket_details.get("priority"),
                        "created_on": ticket_details.get("created_on"),
                        "closed_on": ticket_details.get("closed_on"),
                        "tracker": ticket_details.get("tracker"),
                        "project": ticket_details.get("project")
                    }

                    vector_service.index_ticket_with_comments(
                        ticket_id=ticket_details["ticket_id"],
                        subject=ticket_details["subject"],
                        description=ticket_details["description"],
                        resolution=ticket_details["resolution"],
                        comments=ticket_details.get("comments", []),
                        metadata=metadata
                    )

                    indexed_count += 1
                    pbar.update(1)

                except Exception as e:
                    print(f"  ✗ チケット #{ticket.id} のインデックスに失敗: {e}")
                    error_count += 1
                    pbar.update(1)
                    continue

    except KeyboardInterrupt:
        print("\n\n⚠️  ユーザーによって中断されました")
    except Exception as e:
        print(f"\n\n✗ エラーが発生しました: {e}")

    # 結果サマリー
    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()

    print()
    print("=" * 70)
    print("再インデックス完了")
    print("=" * 70)
    print(f"  処理時間: {elapsed:.1f}秒")
    print(f"  成功: {indexed_count} 件")
    print(f"  エラー: {error_count} 件")
    print(f"  スキップ: {skipped_count} 件")
    print()

    if not dry_run:
        # 更新後のコレクション情報を表示
        print("更新後のコレクション情報:")
        updated_collection_info = vector_service.get_collection_info()
        print(f"  Collection: {updated_collection_info.get('name')}")
        print(f"  Points count: {updated_collection_info.get('points_count')}")
        print(f"  Vectors count: {updated_collection_info.get('vectors_count')}")
        print()
    else:
        print("⚠️  DRY RUN MODE だったため、実際のインデックスは行われていません")
        print("   実際にインデックスするには、--dry-run オプションを外して実行してください")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="既存のチケットをコメント付きで再インデックス化（Phase 2対応）"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="インデックスする最大件数（デフォルト: 全件）"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Redmineから一度に取得する件数（デフォルト: 50）"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実際のインデックスを行わず、処理内容のみ表示"
    )

    args = parser.parse_args()

    reindex_tickets_with_comments(
        limit=args.limit,
        batch_size=args.batch_size,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()
