# MindAIgis

**保守運用特化型AIアシスタント - MVP版**

ZabbixアラートをトリガーにRedmineの過去対応事例を**意味的類似検索**で自動発見するシステム

---

## 概要

MindAIgisは、インフラ保守運用の現場で使える垂直統合型AIアシスタントです。

### 主な機能

- **Zabbixアラート受信**: Webhookでアラートを自動受信
- **意味的類似検索**: OpenAI Embeddings + Qdrantによるベクトル検索
- **Redmine連携**: 過去の障害対応チケットから類似事例を検索
- **Web UI**: Streamlitによる直感的な検索インターフェース

### システム構成

```
┌─────────────┐
│   Zabbix    │──┐
└─────────────┘  │
                 │ Webhook
┌─────────────┐  │
│  Operator   │──┼──> ┌──────────────────┐
└─────────────┘  │    │  MindAIgis API   │
                 │    │   (FastAPI)      │
                 └──> └──────────────────┘
                             │
                    ┌────────┼────────┐
                    │        │        │
              ┌─────▼───┐ ┌─▼──────┐ │
              │ Qdrant  │ │Redmine │ │
              │(Vector) │ │  API   │ │
              └─────────┘ └────────┘ │
                                     │
                        ┌────────────▼───┐
                        │  Streamlit UI  │
                        └────────────────┘
```

---

## 技術スタック

| レイヤー | 技術 |
|---------|------|
| **API** | FastAPI 0.104+ |
| **ベクトルDB** | Qdrant (Docker) |
| **Embedding** | OpenAI text-embedding-3-large |
| **UI** | Streamlit 1.28+ |
| **外部連携** | Redmine REST API, Zabbix Webhook |
| **デプロイ** | Docker Compose |

---

## セットアップ

### 前提条件

- Python 3.9+
- Docker & Docker Compose
- Redmine (API有効化済み)
- Zabbix (Webhook設定可能)
- OpenAI API Key

### 1. リポジトリクローン

```bash
git clone <repository-url>
cd MindAIgis
```

### 2. 環境変数設定

```bash
# .env.exampleをコピーして編集
cp .env.example .env
```

**.env の設定例:**

```bash
# OpenAI API
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=maintenance_tickets

# Redmine
REDMINE_URL=https://your-redmine.example.com
REDMINE_API_KEY=xxxxxxxxxxxxxxxxxx
REDMINE_PROJECT_ID=infrastructure
REDMINE_TRACKER_ID=1

# API設定
API_HOST=0.0.0.0
API_PORT=8000

# Streamlit
STREAMLIT_PORT=8501
API_BASE_URL=http://localhost:8000
```

### 3. Qdrant起動

```bash
docker-compose up -d
```

確認:
```bash
docker ps
# mindaigis-qdrant が Running であることを確認

curl http://localhost:6333/collections
# {"result":{"collections":[]}} が返ればOK
```

### 4. Python依存関係インストール

```bash
# 仮想環境作成（推奨）
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# パッケージインストール
pip install -r requirements.txt
```

### 5. Redmineチケットのインデックス

初回セットアップ時に過去チケットをベクトルDBへインデックスします。

```bash
# DRY-RUNで動作確認（実際にはインデックスしない）
python scripts/index_tickets.py --dry-run --limit 10

# 本番実行（全クローズ済みチケットをインデックス）
python scripts/index_tickets.py

# オプション指定例
python scripts/index_tickets.py --limit 1000 --batch-size 50
```

**オプション:**
- `--limit N`: インデックスする最大件数
- `--batch-size N`: 1回のAPIコールで取得する件数（デフォルト: 100）
- `--dry-run`: テスト実行（実際にインデックスしない）
- `--force`: エラーが発生しても処理を継続

### 6. APIサーバー起動

```bash
# 開発モード（ホットリロード有効）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# または
python -m app.main
```

動作確認:
```bash
curl http://localhost:8000/health
```

### 7. Streamlit UI起動

別ターミナルで:

```bash
streamlit run ui/streamlit_app.py --server.port 8501
```

ブラウザで http://localhost:8501 にアクセス

---

## 使い方

### Web UI経由で検索

1. ブラウザで http://localhost:8501 を開く
2. サイドバーで「ヘルスチェック」を実行
3. 「アラート検索」タブでアラート内容を入力
4. 検索ボタンをクリック
5. 類似度の高い過去チケットが表示される

**例:**
```
disk usage over 90% on web-prod-01
```

### API直接呼び出し

**類似検索:**
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "alert_text": "disk usage over 90% on web-prod-01",
    "limit": 5
  }'
```

**Zabbix Webhook用:**
```bash
curl -X POST http://localhost:8000/webhook/zabbix \
  -H "Content-Type: application/json" \
  -d '{
    "trigger_name": "disk usage over 90%",
    "hostname": "web-prod-01",
    "severity": "High",
    "item_value": "92%",
    "event_id": 12345
  }'
```

**手動インデックス:**
```bash
# チケット#100をインデックス
curl -X POST http://localhost:8000/index/ticket/100
```

---

## Zabbix連携設定

### Zabbix側のWebhook設定

1. **Administration → Media types → Create media type**
2. 以下を設定:
   - **Name:** MindAIgis Webhook
   - **Type:** Webhook
   - **Script:**
     ```javascript
     var params = JSON.parse(value);
     var req = new HttpRequest();
     req.addHeader('Content-Type: application/json');

     var payload = JSON.stringify({
         trigger_name: params.trigger_name,
         hostname: params.hostname,
         severity: params.severity,
         item_value: params.item_value,
         event_id: params.event_id
     });

     var response = req.post('http://your-api-server:8000/webhook/zabbix', payload);
     return response;
     ```
   - **Parameters:** (必要に応じてマクロを設定)
     - `trigger_name`: `{TRIGGER.NAME}`
     - `hostname`: `{HOST.NAME}`
     - `severity`: `{TRIGGER.SEVERITY}`
     - `item_value`: `{ITEM.VALUE}`
     - `event_id`: `{EVENT.ID}`

3. **Configuration → Actions** でアクション設定
4. トリガー条件に応じてWebhookを実行

---

## ディレクトリ構成

```
MindAIgis/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI エントリーポイント
│   ├── models/
│   │   ├── __init__.py
│   │   ├── alert.py            # アラートモデル
│   │   └── ticket.py           # チケットモデル
│   └── services/
│       ├── __init__.py
│       ├── vector_service.py   # Qdrant + OpenAI連携
│       └── redmine_service.py  # Redmine API連携
├── ui/
│   └── streamlit_app.py        # Streamlit UI
├── scripts/
│   └── index_tickets.py        # 初期データ投入スクリプト
├── docker-compose.yml          # Qdrantコンテナ定義
├── requirements.txt            # Python依存関係
├── .env.example                # 環境変数テンプレート
├── .gitignore
└── README.md
```

---

## トラブルシューティング

### Qdrantに接続できない

```bash
# コンテナ状態確認
docker ps

# ログ確認
docker logs mindaigis-qdrant

# 再起動
docker-compose restart
```

### Redmine接続エラー

- `.env` の `REDMINE_URL` と `REDMINE_API_KEY` を確認
- Redmine側でREST APIが有効化されているか確認
- APIキーの権限が適切か確認

### OpenAI API エラー

- API Keyが正しいか確認
- レート制限に達していないか確認
- クレジット残高を確認

### インデックスが遅い

- `--batch-size` を調整（デフォルト: 100）
- OpenAI APIのレート制限により時間がかかる場合あり
- 大量チケットの場合は `--limit` で段階的にインデックス

---

## 今後の拡張予定

### Phase 2: 本格運用化
- [ ] React/Vue.jsによるプロダクションUI
- [ ] サーバー情報マスタDB（CMDB）
- [ ] メールテンプレート管理
- [ ] ベンダー別エスカレーション機能
- [ ] 対応アクション分類（静観/ベンダー手配/故障予兆）

### Phase 3: LLM内製化
- [ ] LLaMA 3.1ローカルデプロイ
- [ ] ファインチューニング基盤構築
- [ ] vLLM推論サーバー構築
- [ ] A/Bテスト環境

---

## ライセンス

TBD

---

## 開発者向け

### 開発環境セットアップ

```bash
# 開発用依存関係インストール
pip install -r requirements.txt
pip install pytest black flake8

# コード整形
black app/ ui/ scripts/

# Linter実行
flake8 app/

# テスト実行（実装予定）
pytest
```

### API仕様書

FastAPI起動後、以下URLでSwagger UIにアクセス可能:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## お問い合わせ

プロジェクト管理者: TBD
