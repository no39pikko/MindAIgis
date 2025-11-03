# ローカル環境セットアップ（WSL/Linux）

Dockerなしでテスト起動する方法

---

## 前提条件チェック

```bash
# Python確認
python3 --version
# Python 3.9以上が必要

# pip確認
pip3 --version
```

---

## セットアップ手順

### 1. プロジェクトディレクトリへ移動

```bash
cd /mnt/c/Users/aotoh/Documents/ClaudeCode/MindAIgis
```

### 2. 環境変数設定

```bash
# .envファイル作成
cp .env.example .env

# エディタで編集
nano .env
# または
vim .env
```

**最低限必要な設定:**

```bash
# OpenAI API Key（必須）
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxx

# Redmine設定（友達のサーバー）
REDMINE_URL=http://友達のサーバーIP:ポート番号
REDMINE_API_KEY=xxxxxxxxxxxxxxxxxxxx

# Qdrant設定（ローカルテスト時はDockerなしも可）
QDRANT_URL=http://localhost:6333
```

**Redmine API Keyの取得方法:**

1. Redmineにログイン
2. 右上のアカウント名 → 「個人設定」
3. 「APIアクセスキー」セクション
4. 「表示」をクリック
5. キーをコピー

### 3. Python仮想環境構築

```bash
# 仮想環境作成
python3 -m venv venv

# 有効化
source venv/bin/activate

# 依存関係インストール
pip install -r requirements.txt
```

### 4. Qdrant準備

#### オプションA: Dockerなし（テスト用）

Qdrantを使わずにテストする場合は、スキップして次へ。
※ベクトル検索は使えませんが、Redmine接続テストは可能

#### オプションB: Dockerあり（本格テスト）

```bash
# Docker起動
docker-compose up -d

# 確認
curl http://localhost:6333/collections
# {"result":{"collections":[]}} が返ればOK
```

### 5. Redmine接続テスト

```bash
# Pythonインタラクティブシェル起動
python3

# テストコード実行
>>> from app.services.redmine_service import RedmineService
>>> redmine = RedmineService()
>>> redmine.test_connection()

# "Connected to Redmine as: ○○ ○○" と表示されればOK
>>> exit()
```

### 6. API起動テスト

```bash
# APIサーバー起動
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

別ターミナルで確認:

```bash
# ヘルスチェック
curl http://localhost:8000/health
```

### 7. UI起動（オプション）

```bash
# 新しいターミナルで
cd /mnt/c/Users/aotoh/Documents/ClaudeCode/MindAIgis
source venv/bin/activate

streamlit run ui/streamlit_app.py --server.port 8501
```

ブラウザで http://localhost:8501 にアクセス

---

## トラブルシューティング

### Redmine接続エラー

```bash
# 手動でRedmine APIテスト
curl -H "X-Redmine-API-Key: あなたのAPIキー" \
  http://RedmineサーバーIP:ポート/issues.json?limit=1
```

成功例:
```json
{
  "issues": [
    {"id": 1, "subject": "テストチケット"}
  ],
  "total_count": 100
}
```

失敗例:
```
Unauthorized
→ APIキーが間違っている
```

### OpenAI接続エラー

```bash
# APIキーテスト
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Qdrantなしでテスト

Qdrantを使わずにRedmine接続だけテストする場合:

```python
# test_redmine.py
from dotenv import load_dotenv
load_dotenv()

from app.services.redmine_service import RedmineService

# Redmine接続
redmine = RedmineService()

# 接続テスト
if redmine.test_connection():
    print("✓ Redmine接続成功")
else:
    print("✗ Redmine接続失敗")

# チケット取得テスト
tickets = redmine.get_closed_tickets(limit=5)
print(f"\n取得したチケット数: {len(tickets)}")

for ticket in tickets:
    print(f"#{ticket.id}: {ticket.subject}")
```

実行:
```bash
python test_redmine.py
```

---

## 次のステップ

ローカルで動作確認できたら:

1. `DEPLOY_SERVER.md` を参照してサーバーへデプロイ
2. 初期データ投入: `python scripts/index_tickets.py --limit 10`
3. 実際に検索テスト
