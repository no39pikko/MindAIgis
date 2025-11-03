#!/usr/bin/env python3
"""
Redmineの過去チケットをQdrantにインデックスするスクリプト

使用方法:
    python scripts/index_tickets.py [オプション]

オプション:
    --limit N       インデックスする最大件数（デフォルト: 全件）
    --batch-size N  バッチサイズ（デフォルト: 100）
    --project-id ID プロジェクトIDでフィルタ
    --dry-run       実際にインデックスせずテスト実行
"""

import sys
import os
import argparse
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tqdm import tqdm
from dotenv import load_dotenv

from app.services.vector_service import VectorService
from app.services.redmine_service import RedmineService

load_dotenv()


def parse_args():
    """コマンドライン引数をパース"""
    parser = argparse.ArgumentParser(
        description="Redmineチケットをベクトルデータベースにインデックス"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="インデックスする最大件数"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="1回のAPIコールで取得するチケット数"
    )
    parser.add_argument(
        "--project-id",
        type=str,
        default=None,
        help="特定のプロジェクトIDでフィルタ"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実際にインデックスせずテスト実行"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="エラーが発生しても処理を継続"
    )

    return parser.parse_args()


def index_all_tickets(args):
    """すべてのクローズ済みチケットをインデックス"""

    print("=" * 60)
    print("MindAIgis - Redmineチケットインデックス")
    print("=" * 60)

    # サービス初期化
    print("\n[1/4] サービス初期化中...")
    try:
        vector_service = VectorService()
        redmine_service = RedmineService()

        # プロジェクトID設定があれば上書き
        if args.project_id:
            redmine_service.project_id = args.project_id
            print(f"  ✓ プロジェクトID: {args.project_id}")

        print("  ✓ Vector Service: 起動完了")
        print("  ✓ Redmine Service: 起動完了")

    except Exception as e:
        print(f"  ✗ 初期化エラー: {e}")
        return

    # 接続テスト
    print("\n[2/4] Redmine接続テスト...")
    if not redmine_service.test_connection():
        print("  ✗ Redmine接続失敗")
        return
    print("  ✓ Redmine接続成功")

    # コレクション情報取得
    print("\n[3/4] Qdrantコレクション情報...")
    collection_info = vector_service.get_collection_info()
    print(f"  コレクション名: {collection_info.get('name')}")
    print(f"  既存インデックス数: {collection_info.get('points_count', 0)} 件")

    # チケット取得とインデックス
    print("\n[4/4] チケットインデックス処理開始...")

    if args.dry_run:
        print("  ⚠️  DRY-RUN モード: 実際にはインデックスしません\n")

    indexed_count = 0
    error_count = 0
    skipped_count = 0

    try:
        # チケット取得イテレータ
        ticket_iter = redmine_service.get_all_closed_tickets_iter(
            batch_size=args.batch_size
        )

        # プログレスバー付きで処理
        with tqdm(desc="インデックス中", unit="tickets") as pbar:
            for ticket in ticket_iter:
                # 件数制限チェック
                if args.limit and indexed_count >= args.limit:
                    print(f"\n  制限数 {args.limit} 件に到達")
                    break

                try:
                    # チケット詳細取得
                    detail = redmine_service.get_ticket_details(ticket.id)

                    if not detail:
                        skipped_count += 1
                        pbar.update(1)
                        continue

                    # 説明文または解決策が空の場合はスキップ
                    if not detail.get("description") and not detail.get("resolution"):
                        skipped_count += 1
                        pbar.update(1)
                        continue

                    # DRY-RUNでない場合のみインデックス
                    if not args.dry_run:
                        vector_service.index_ticket(
                            ticket_id=detail["ticket_id"],
                            subject=detail["subject"],
                            description=detail.get("description", ""),
                            resolution=detail.get("resolution", ""),
                            metadata={
                                "category": detail.get("category"),
                                "assigned_to": detail.get("assigned_to"),
                                "status": detail.get("status"),
                                "priority": detail.get("priority"),
                                "closed_on": detail.get("closed_on").isoformat() if detail.get("closed_on") else None
                            }
                        )

                    indexed_count += 1
                    pbar.update(1)

                except Exception as e:
                    error_count += 1
                    if args.force:
                        pbar.write(f"  ⚠️  チケット #{ticket.id} エラー: {e}")
                        pbar.update(1)
                        continue
                    else:
                        print(f"\n  ✗ チケット #{ticket.id} でエラー発生: {e}")
                        raise

    except KeyboardInterrupt:
        print("\n\n  ⚠️  ユーザーによる中断")

    except Exception as e:
        print(f"\n  ✗ 処理エラー: {e}")

    # 結果サマリー
    print("\n" + "=" * 60)
    print("処理完了")
    print("=" * 60)
    print(f"  インデックス成功: {indexed_count} 件")
    print(f"  スキップ: {skipped_count} 件")
    print(f"  エラー: {error_count} 件")

    if args.dry_run:
        print("\n  ℹ️  DRY-RUNモードのため、実際にはインデックスされていません")

    # 最終的なコレクション情報
    if not args.dry_run:
        print("\n最終コレクション情報:")
        collection_info = vector_service.get_collection_info()
        print(f"  総インデックス数: {collection_info.get('points_count', 0)} 件")


def main():
    """メイン処理"""
    args = parse_args()

    try:
        index_all_tickets(args)
    except Exception as e:
        print(f"\n致命的エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
