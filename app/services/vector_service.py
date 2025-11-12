import os
from typing import List, Optional
from datetime import datetime
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class VectorService:
    """ベクトル検索サービス（Qdrant + OpenAI Embeddings）"""

    def __init__(self):
        self.qdrant = QdrantClient(
            url=os.getenv("QDRANT_URL", "http://localhost:6333")
        )
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.collection_name = os.getenv("QDRANT_COLLECTION_NAME", "maintenance_tickets")
        self.embedding_model = "text-embedding-3-large"
        self.vector_size = 3072

        # コレクションの初期化
        self._ensure_collection()

    def _ensure_collection(self):
        """コレクションが存在しない場合は作成"""
        try:
            collections = self.qdrant.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name not in collection_names:
                print(f"Creating collection: {self.collection_name}")
                from qdrant_client.models import OptimizersConfigDiff
                self.qdrant.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    ),
                    optimizers_config=OptimizersConfigDiff(
                        indexing_threshold=1  # 1件からインデックス化
                    )
                )
                print(f"Collection '{self.collection_name}' created successfully")
            else:
                print(f"Collection '{self.collection_name}' already exists")
        except Exception as e:
            print(f"Error ensuring collection: {e}")
            raise

    def embed_text(self, text: str) -> List[float]:
        """
        テキストをベクトル化

        Args:
            text: ベクトル化するテキスト

        Returns:
            ベクトル（3072次元の数値配列）
        """
        try:
            response = self.openai.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error creating embedding: {e}")
            raise

    def index_ticket(
        self,
        ticket_id: int,
        subject: str,
        description: str = "",
        resolution: str = "",
        metadata: dict = None
    ):
        """
        Redmineチケットをインデックス

        Args:
            ticket_id: チケットID
            subject: 件名
            description: 説明
            resolution: 解決策
            metadata: 追加メタデータ（カテゴリ、担当者など）
        """
        # 検索対象となる全文を結合
        full_text = f"件名: {subject}\n説明: {description}\n解決策: {resolution}"

        try:
            # ベクトル化
            vector = self.embed_text(full_text)

            # ペイロード作成
            payload = {
                "ticket_id": ticket_id,
                "subject": subject,
                "description": description,
                "resolution": resolution,
                "indexed_at": datetime.now().isoformat()
            }

            # メタデータを追加
            if metadata:
                payload.update(metadata)

            # Qdrantに保存
            self.qdrant.upsert(
                collection_name=self.collection_name,
                points=[PointStruct(
                    id=ticket_id,
                    vector=vector,
                    payload=payload
                )]
            )

            print(f"Indexed ticket #{ticket_id}: {subject}")

        except Exception as e:
            print(f"Error indexing ticket {ticket_id}: {e}")
            raise

    def search_similar_tickets(
        self,
        alert_message: str,
        limit: int = 5,
        score_threshold: float = 0.3
    ) -> List[dict]:
        """
        類似チケット検索

        Args:
            alert_message: 検索クエリ（アラートメッセージ）
            limit: 取得する最大件数
            score_threshold: 類似度の閾値（0.0-1.0）

        Returns:
            類似チケットのリスト
        """
        try:
            # クエリをベクトル化
            query_vector = self.embed_text(alert_message)

            # Qdrantで検索
            search_results = self.qdrant.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True
            )

            # 結果を整形
            results = []
            for hit in search_results:
                results.append({
                    "ticket_id": hit.payload.get("ticket_id"),
                    "similarity": hit.score,
                    "subject": hit.payload.get("subject"),
                    "description": hit.payload.get("description", ""),
                    "resolution": hit.payload.get("resolution", ""),
                    "category": hit.payload.get("category"),
                    "assigned_to": hit.payload.get("assigned_to"),
                    "closed_on": hit.payload.get("closed_on"),
                    "status": hit.payload.get("status")
                })

            return results

        except Exception as e:
            print(f"Error searching similar tickets: {e}")
            raise

    def delete_ticket(self, ticket_id: int):
        """
        チケットをインデックスから削除

        Args:
            ticket_id: 削除するチケットID
        """
        try:
            self.qdrant.delete(
                collection_name=self.collection_name,
                points_selector=[ticket_id]
            )
            print(f"Deleted ticket #{ticket_id} from index")
        except Exception as e:
            print(f"Error deleting ticket {ticket_id}: {e}")
            raise

    def get_collection_info(self) -> dict:
        """
        コレクション情報を取得

        Returns:
            コレクションの統計情報
        """
        try:
            collection_info = self.qdrant.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "vectors_count": collection_info.vectors_count,
                "points_count": collection_info.points_count,
                "status": collection_info.status
            }
        except Exception as e:
            print(f"Error getting collection info: {e}")
            return {}

    def index_ticket_with_comments(
        self,
        ticket_id: int,
        subject: str,
        description: str = "",
        resolution: str = "",
        comments: List[dict] = None,
        metadata: dict = None
    ):
        """
        チケットをコメント付きでインデックス（Phase 2拡張機能）

        Args:
            ticket_id: チケットID
            subject: 件名
            description: 説明
            resolution: 解決策
            comments: コメントリスト [{"user": "...", "created_on": "...", "notes": "..."}]
            metadata: 追加メタデータ（category, assigned_to, created_on, closed_onなど）
        """
        # コメントを全文に含める
        comments_text = ""
        if comments:
            comments_text = "\n".join([
                f"コメント ({c.get('user', 'N/A')}, {c.get('created_on', 'N/A')}): {c.get('notes', '')}"
                for c in comments
            ])

        full_text = f"件名: {subject}\n説明: {description}\n解決策: {resolution}\n{comments_text}"

        try:
            # ベクトル化
            vector = self.embed_text(full_text)

            # ペイロード作成（拡張メタデータ）
            payload = {
                "ticket_id": ticket_id,
                "subject": subject,
                "description": description,
                "resolution": resolution,
                "comments": comments or [],
                "indexed_at": datetime.now().isoformat()
            }

            # メタデータを追加
            if metadata:
                payload.update(metadata)

            # Qdrantに保存
            self.qdrant.upsert(
                collection_name=self.collection_name,
                points=[PointStruct(
                    id=ticket_id,
                    vector=vector,
                    payload=payload
                )]
            )

            print(f"Indexed ticket #{ticket_id} with {len(comments or [])} comments: {subject}")

        except Exception as e:
            print(f"Error indexing ticket {ticket_id} with comments: {e}")
            raise

    def search_similar_tickets_advanced(
        self,
        alert_message: str,
        limit: int = 5,
        score_threshold: float = 0.3,
        date_range: Optional[dict] = None,
        server_filter: Optional[List[str]] = None
    ) -> List[dict]:
        """
        高度な類似チケット検索（日付・サーバー名フィルタ対応）（Phase 2拡張機能）

        Args:
            alert_message: 検索クエリ
            limit: 取得件数
            score_threshold: 類似度閾値
            date_range: {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}
            server_filter: サーバー名リスト

        Returns:
            類似チケットのリスト
        """
        try:
            # クエリをベクトル化
            query_vector = self.embed_text(alert_message)

            # フィルタ条件を構築
            filter_conditions = []

            if date_range:
                # 日付範囲フィルタ（closed_onで絞り込み）
                from qdrant_client.models import Range, FieldCondition

                if "start" in date_range and date_range["start"]:
                    filter_conditions.append(
                        FieldCondition(
                            key="closed_on",
                            range=Range(
                                gte=date_range["start"]
                            )
                        )
                    )

                if "end" in date_range and date_range["end"]:
                    filter_conditions.append(
                        FieldCondition(
                            key="closed_on",
                            range=Range(
                                lte=date_range["end"]
                            )
                        )
                    )

            # サーバー名フィルタ（payloadに含まれるserver_names配列で検索）
            # TODO: Qdrantのネストフィールド検索機能を使用
            # 現在は検索後にPythonでフィルタリング

            # 検索パラメータ構築
            search_params = {
                "collection_name": self.collection_name,
                "query_vector": query_vector,
                "limit": limit * 2 if server_filter else limit,  # サーバーフィルタがある場合は多めに取得
                "score_threshold": score_threshold,
                "with_payload": True
            }

            # 日付フィルタを適用
            if filter_conditions:
                search_params["query_filter"] = Filter(must=filter_conditions)

            # Qdrantで検索
            search_results = self.qdrant.search(**search_params)

            # 結果を整形
            results = []
            for hit in search_results:
                result = {
                    "ticket_id": hit.payload.get("ticket_id"),
                    "similarity": hit.score,
                    "subject": hit.payload.get("subject"),
                    "description": hit.payload.get("description", ""),
                    "resolution": hit.payload.get("resolution", ""),
                    "comments": hit.payload.get("comments", []),
                    "server_names": hit.payload.get("server_names", []),
                    "category": hit.payload.get("category"),
                    "assigned_to": hit.payload.get("assigned_to"),
                    "created_on": hit.payload.get("created_on"),
                    "closed_on": hit.payload.get("closed_on"),
                    "status": hit.payload.get("status")
                }

                # サーバー名フィルタ（Pythonレベル）
                if server_filter:
                    ticket_servers = set(result.get("server_names", []))
                    filter_servers = set([s.lower() for s in server_filter])

                    # 交差判定
                    if ticket_servers & filter_servers:
                        results.append(result)
                else:
                    results.append(result)

                # 必要な件数に達したら終了
                if len(results) >= limit:
                    break

            return results

        except Exception as e:
            print(f"Error in advanced search: {e}")
            raise
