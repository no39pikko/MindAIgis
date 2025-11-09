# MindAIgis セットアップガイド

## 仮想環境のセットアップ（推奨）

### 新規セットアップ

```bash
# リポジトリをクローン
cd ~/Documents/ClaudeCode  # または任意のディレクトリ
git clone <your-git-url> MindAIgis
cd MindAIgis

# 仮想環境を作成
python3 -m venv venv

# 仮想環境を有効化
source venv/bin/activate

# 依存パッケージを一括インストール
pip install --upgrade pip
pip install -r requirements.txt

# .env ファイルを作成
cp .env.example .env
nano .env  # 環境変数を設定
```

### 既存環境の更新

```bash
cd MindAIgis

# 最新のコードを取得
git pull

# 仮想環境を有効化
source venv/bin/activate

# 依存パッケージを更新
pip install --upgrade pip
pip install -r requirements.txt --upgrade
```

### 仮想環境の削除と再作成

```bash
cd MindAIgis

# 仮想環境を削除
rm -rf venv

# 新規作成
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 環境変数の設定

`.env` ファイルを編集して、以下を設定してください：

### 必須設定

```bash
# OpenAI API
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Redmine
REDMINE_URL=http://your-redmine-server.com
REDMINE_API_KEY=your_redmine_api_key_here
REDMINE_PROJECT_ID=infrastructure
REDMINE_TRACKER_ID=1

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=maintenance_tickets
```

### Phase 3 機能を有効化

```bash
# 手順書作成補佐を有効化
PROCEDURE_ASSIST_ENABLED=true
```

## データのインデックス

チケットをベクトルDBにインデックスする：

```bash
# 仮想環境を有効化
source venv/bin/activate

# インデックススクリプトを実行
python scripts/index_redmine_tickets.py
```

## サービスの起動

### 開発環境（手動起動）

```bash
# 仮想環境を有効化
source venv/bin/activate

# Qdrant起動（Docker Compose）
docker compose up -d

# FastAPI起動（ターミナル1）
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Streamlit起動（ターミナル2）
streamlit run ui/streamlit_app.py --server.port 8501
```

### 本番環境（スクリプト起動）

```bash
# すべてのサービスを起動
./start.sh

# すべてのサービスを停止
./stop.sh
```

## トラブルシューティング

### 検索結果が0件の場合

1. **Qdrantにデータがあるか確認**

```bash
curl http://localhost:6333/collections/maintenance_tickets
```

`vectors_count` が 0 の場合は、インデックスが必要です：

```bash
python scripts/index_redmine_tickets.py
```

2. **検索のデバッグ**

FastAPIのログを確認：

```bash
tail -f logs/api.log
```

検索クエリと取得件数が表示されます。

3. **score_threshold の調整**

`app/services/procedure_assistant_service.py` の `_search_tickets` メソッドで、
`score_threshold=0.3` を `0.1` や `0.0` に下げてみてください。

### Docker Compose のエラー

```bash
# 古い docker-compose コマンドの場合
docker-compose up -d

# 新しい Docker Compose V2 の場合
docker compose up -d
```

### 仮想環境が見つからない

```bash
# 仮想環境を作り直す
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### OpenAI API エラー

- API キーが正しいか確認
- API の利用制限に達していないか確認
- `.env` ファイルが正しい場所にあるか確認

## 開発時のヒント

### requirements.txt の更新

新しいパッケージを追加した場合：

```bash
# 仮想環境内で
pip freeze > requirements.txt
```

### Git での管理

```bash
# .env は Git に含めない（.gitignore に記載済み）
# venv/ も Git に含めない（.gitignore に記載済み）

# コミット前に確認
git status

# 変更をコミット
git add .
git commit -m "Update: 機能追加"
git push
```

## systemd での自動起動（本番環境）

AlmaLinux 9 で systemd サービスとして起動する場合は、別途サービスファイルを作成してください。

詳細は `docs/systemd-setup.md` を参照。
