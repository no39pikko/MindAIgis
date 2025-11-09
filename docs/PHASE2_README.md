# MindAIgis Phase 2: 自然言語検索・事実ベース要約機能

## 概要

Phase 2では、自然言語でチケットを検索し、LLMによる事実ベースの要約を取得できる機能を追加しました。

### 主要機能

1. **自然言語クエリ処理**: 「先月web-prod-01でディスク容量のアラートが出たときどう対応した？」のような質問で検索
2. **事実ベース要約生成**: 過去のチケット情報のみを使用し、推測や一般的なアドバイスを含まない要約
3. **コメント（ジャーナル）のインデックス化**: チケットの説明だけでなく、すべてのコメントも検索対象に
4. **日付フィルタ**: 「先月」「昨日」などの相対日付と絶対日付の両方に対応
5. **プラグインアーキテクチャ**: CMDB連携、Emailテンプレート等、将来的な拡張に対応

---

## セットアップ

### 1. 環境変数の設定

`.env`ファイルに以下を追加:

```bash
# Phase 2: Intelligent Search を有効化
INTELLIGENT_SEARCH_ENABLED=true

# LLMプロバイダー（現在はopenaiのみ対応）
LLM_PROVIDER=openai

# 使用するOpenAIモデル
OPENAI_MODEL=gpt-4o-mini

# OpenAI API Key（Phase 1で設定済みの場合は不要）
OPENAI_API_KEY=sk-your-api-key-here
```

### 2. 既存データの再インデックス（推奨）

Phase 2ではコメントも検索対象にするため、既存のチケットを再インデックスすることを推奨します。

```bash
# venv有効化
source venv/bin/activate

# 既存データを再インデックス（コメント付き）
python scripts/reindex_tickets_with_comments.py
```

### 3. APIサーバーの起動

```bash
# 開発環境
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 本番環境
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 使い方

### API経由での利用

#### 1. 自然言語検索

**エンドポイント**: `POST /search/intelligent`

**リクエスト例**:

```bash
curl -X POST "http://localhost:8000/search/intelligent" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "先月web-prod-01でディスク容量のアラートが出たときどう対応した？",
    "limit": 10,
    "include_context": true
  }'
```

**レスポンス例**:

```json
{
  "query_analysis": {
    "keywords": ["ディスク容量", "アラート"],
    "server_names": ["web-prod-01"],
    "date_range": {
      "start": "2024-10-01",
      "end": "2024-10-31"
    },
    "intent": "search_past_resolution"
  },
  "search_results": [
    {
      "ticket_id": 12345,
      "similarity": 0.89,
      "subject": "web-prod-01でディスク容量アラート",
      "description": "ディスク使用率が90%を超えました...",
      "resolution": "古いログファイルを削除して対応完了",
      "comments": [
        {
          "user": "山田太郎",
          "created_on": "2024-10-15T10:00:00",
          "notes": "/var/log配下のログを確認中"
        }
      ],
      "server_names": ["web-prod-01"],
      "closed_on": "2024-10-15T10:45:00"
    }
  ],
  "summary": "## 検索結果\n先月（2024年10月）にweb-prod-01サーバーでディスク容量アラートが発生した事例が3件見つかりました...",
  "context": {
    "servers": {
      "web-prod-01": {
        "serial_number": "ABC123456",
        "vendor": "Dell"
      }
    }
  },
  "metadata": {
    "total_results": 3,
    "date_range": {"start": "2024-10-01", "end": "2024-10-31"},
    "keywords": ["ディスク容量", "アラート"]
  }
}
```

#### 2. 既存の検索API（Phase 1互換）

Phase 1の検索APIもそのまま使用できます。

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "alert_text": "ディスク容量アラート",
    "limit": 5
  }'
```

---

## 自然言語クエリの例

Phase 2では以下のような自然言語クエリに対応しています:

### 日付指定の例

- **相対日付**:
  - 「昨日のアラートを教えて」
  - 「先週発生した障害は？」
  - 「先月のディスク容量問題について」
  - 「今月のweb-prod-01の障害」

- **絶対日付**:
  - 「2024年10月のアラート」
  - 「2024年10月15日の障害」

- **期間指定**:
  - 「直近7日間のディスク容量アラート」
  - 「過去30日の障害事例」

### サーバー名指定の例

- 「web-prod-01のディスク容量問題」
- 「db-server-02で発生したエラー」
- 「mail-01のメモリアラート」

### 複合クエリの例

- 「先月web-prod-01でディスク容量のアラートが出たときどう対応した？」
- 「昨日db-server-02でメモリ不足が発生したが、過去に同じ事例はあるか？」
- 「2024年10月にweb-prod-01で発生した障害の解決方法」

---

## 事実ベース要約の特徴

Phase 2の要約機能は、以下の原則に基づいています:

### ✅ やること

1. **過去のチケット情報のみを使用**
   - 提供されたチケットの内容を正確に要約
   - すべての情報にチケット番号を明記

2. **過去形で記述**
   - 「〜でした」「〜しました」
   - 「〜すべき」「〜が推奨される」などの助言は含めない

3. **出典の明記**
   - すべての情報にチケット番号を引用
   - 「チケット#12345によると...」

4. **不明な情報は明記**
   - チケットに記載がない情報は「記載なし」と明示

### ❌ やらないこと

1. **推測や一般的なアドバイス**
   - 「〜すべきです」「〜が推奨されます」
   - 「一般的に〜です」

2. **チケットに記載されていない情報の追加**
   - 外部の知識を使った補足説明
   - LLMの一般的な知識に基づく説明

3. **過度な解釈**
   - チケットに書かれていないことを推測

---

## プラグインシステム

Phase 2では、外部データソース連携のためのプラグインシステムを導入しています。

### 利用可能なプラグイン

#### 1. CMDBプラグイン（サンプル実装）

サーバーのシリアル番号、保守契約情報などを取得。

**有効化**:

```bash
# .env
CMDB_ENABLED=true
CMDB_API_URL=http://your-cmdb-server.com/api
CMDB_API_KEY=your_cmdb_api_key
```

**実装場所**: `app/plugins/cmdb_plugin.py`

#### 2. Emailテンプレートプラグイン（サンプル実装）

ベンダーエスカレーション用のEmailテンプレートを提供。

**有効化**:

```bash
# .env
EMAIL_TEMPLATE_ENABLED=true
EMAIL_TEMPLATE_DB_PATH=/path/to/template/db
```

**実装場所**: `app/plugins/email_template_plugin.py`

### 独自プラグインの作成

`app/plugins/` 配下に `*_plugin.py` 形式でファイルを作成:

```python
from app.services.integration_service import BasePlugin
from typing import Dict

class Plugin(BasePlugin):
    """Your custom plugin"""

    def get_name(self) -> str:
        return "your_plugin_name"

    def is_enabled(self) -> bool:
        return os.getenv("YOUR_PLUGIN_ENABLED", "false").lower() == "true"

    def fetch_data(self, **kwargs) -> Dict:
        # データ取得ロジック
        return {"key": "value"}
```

プラグインは起動時に自動的にロードされます。

---

## チケットのインデックス化（Phase 2拡張）

### コメント付きインデックス化

Phase 2では、チケットのコメント（ジャーナル）も検索対象に含められます。

**手動インデックス**:

```python
from app.services.vector_service import VectorService
from app.services.redmine_service import RedmineService

vector_service = VectorService()
redmine_service = RedmineService()

# チケット詳細を取得（コメント付き）
ticket_details = redmine_service.get_ticket_details_with_comments(ticket_id=12345)

# コメント付きでインデックス
vector_service.index_ticket_with_comments(
    ticket_id=ticket_details["ticket_id"],
    subject=ticket_details["subject"],
    description=ticket_details["description"],
    resolution=ticket_details["resolution"],
    comments=ticket_details["comments"],
    metadata={
        "server_names": ticket_details["server_names"],
        "category": ticket_details["category"],
        "closed_on": ticket_details["closed_on"]
    }
)
```

**バッチインデックス**:

```bash
# 全クローズ済みチケットを再インデックス
python scripts/reindex_tickets_with_comments.py
```

---

## トラブルシューティング

### Intelligent Search が使えない

**症状**: `/search/intelligent` が 503 エラーを返す

**原因**: 環境変数が設定されていない

**解決策**:

```bash
# .env
INTELLIGENT_SEARCH_ENABLED=true
OPENAI_API_KEY=sk-your-api-key-here
```

### LLMがエラーを返す

**症状**: `Error analyzing query` や `Error synthesizing facts`

**考えられる原因**:
1. OpenAI API Keyが無効
2. APIレート制限
3. モデル名が間違っている

**解決策**:

```bash
# APIキーの確認
echo $OPENAI_API_KEY

# モデル名の確認（.env）
OPENAI_MODEL=gpt-4o-mini  # gpt-4o-mini, gpt-4o, gpt-3.5-turbo が利用可能
```

### 日付フィルタが効かない

**症状**: 日付範囲を指定しても、関係ないチケットが返ってくる

**原因**: 古いデータに `closed_on` フィールドがない

**解決策**:

```bash
# データを再インデックス
python scripts/reindex_tickets_with_comments.py
```

---

## パフォーマンス最適化

### 1. LLM APIコールの削減

- クエリ分析と要約生成は別々のAPI呼び出しのため、2回のLLM APIコールが発生
- 頻繁に検索する場合は、結果のキャッシングを検討

### 2. ベクトル検索の最適化

- `DEFAULT_SEARCH_LIMIT` を適切に設定（デフォルト: 10）
- `DEFAULT_SCORE_THRESHOLD` を調整（デフォルト: 0.3）

```bash
# .env
DEFAULT_SEARCH_LIMIT=10
DEFAULT_SCORE_THRESHOLD=0.3
```

### 3. プラグインの選択的有効化

- 使用しないプラグインは無効化してオーバーヘッドを削減

```bash
CMDB_ENABLED=false
EMAIL_TEMPLATE_ENABLED=false
```

---

## 将来の拡張計画（Phase 3）

Phase 2で構築した拡張可能なアーキテクチャを活用し、以下の機能を追加予定:

1. **ローカルLLaMA対応**
   - OpenAI API依存を排除
   - プライベート環境での運用

2. **実CMDB連携**
   - サーバー情報の自動取得
   - シリアル番号、保守契約情報の表示

3. **自動Emailエスカレーション**
   - テンプレートを使用したベンダー宛メール生成
   - 過去の対応履歴を自動挿入

4. **Zabbix Webhook統合**
   - アラート発生時に自動で類似事例を検索
   - Slackへの通知統合

---

## まとめ

Phase 2では、以下の機能を追加しました:

- ✅ 自然言語クエリ処理
- ✅ LLMによる事実ベース要約生成
- ✅ コメント（ジャーナル）のインデックス化
- ✅ 日付フィルタ機能
- ✅ プラグインアーキテクチャ
- ✅ OpenAI/LLaMA切り替え可能な設計

これらの機能により、保守運用担当者がより効率的に過去の対応事例を検索・参照できるようになりました。

---

**問い合わせ**: 不具合や機能要望は GitHub Issues にお願いします。
