# MindAIgis クイックスタート

最速でMindAIgisを起動して試す手順

---

## 1. 環境変数設定（5分）

```bash
cd MindAIgis

# .envファイル作成
cp .env.example .env
```

**.env を編集:**
```bash
# 必須項目のみ設定
OPENAI_API_KEY=sk-your-openai-api-key-here
REDMINE_URL=http://your-redmine-server.com
REDMINE_API_KEY=your_redmine_api_key_here
```

---

## 2. Qdrant起動（1分）

```bash
# Dockerコンテナ起動
docker-compose up -d

# 確認
docker ps
# mindaigis-qdrant が Running であること
```

---

## 3. Python環境構築（3分）

```bash
# 仮想環境作成
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt
```

---

## 4. 初期データ投入（時間は件数次第）

```bash
# テスト実行（最初の10件のみ）
python scripts/index_tickets.py --limit 10

# 問題なければ全件実行
python scripts/index_tickets.py
```

---

## 5. サービス起動（2分）

### 方法A: スクリプト使用（推奨）

```bash
./start.sh
```

### 方法B: 個別起動

**ターミナル1（API）:**
```bash
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**ターミナル2（UI）:**
```bash
source venv/bin/activate
streamlit run ui/streamlit_app.py --server.port 8501
```

---

## 6. 動作確認（1分）

### ブラウザで確認

- **Streamlit UI**: http://localhost:8501
- **API Docs**: http://localhost:8000/docs

### cURLで確認

```bash
# ヘルスチェック
curl http://localhost:8000/health

# 検索テスト
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "alert_text": "disk usage over 90%",
    "limit": 3
  }'
```

---

## 7. 実際に使ってみる

### Streamlit UIで検索

1. http://localhost:8501 にアクセス
2. 「ヘルスチェック」ボタンをクリック
3. 「アラート検索」タブで以下を入力:
   ```
   disk usage over 90% on web-prod-01
   ```
4. 「検索」ボタンをクリック
5. 類似チケットが表示されます

---

## トラブルシューティング

### Qdrantに接続できない

```bash
# コンテナ確認
docker ps

# ログ確認
docker logs mindaigis-qdrant

# 再起動
docker-compose restart
```

### Redmine接続エラー

```bash
# 接続テスト
curl -H "X-Redmine-API-Key: your_api_key" \
  http://your-redmine-server.com/issues.json?limit=1

# .envの設定を再確認
cat .env | grep REDMINE
```

### OpenAI APIエラー

```bash
# APIキー確認
echo $OPENAI_API_KEY

# テスト
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

---

## 停止方法

```bash
# スクリプトで停止
./stop.sh

# または個別停止
# Ctrl+C で各プロセスを停止
docker-compose down  # Qdrant停止
```

---

## 次のステップ

- [README.md](README.md) - 詳細なドキュメント
- [systemd/INSTALL.md](systemd/INSTALL.md) - CentOS本番環境構築
- Zabbix Webhook設定（README参照）
- メールテンプレート機能の追加（Phase 2）

---

## よくある質問

### Q: インデックスにどれくらい時間がかかりますか？

A: OpenAI APIのレート制限により、1000件あたり約5-10分程度かかります。

### Q: コストはどれくらいですか？

A: 主にOpenAI APIのコストです。Embedding（text-embedding-3-large）は1000トークンあたり$0.00013と非常に安価です。

### Q: オフラインで動きますか？

A: 現在のMVP版はOpenAI APIを使用するため、インターネット接続が必要です。Phase 3でローカルLLM（LLaMA）対応予定です。

### Q: 既存のZabbix/Redmineに影響はありますか？

A: APIを使用するのみで、既存システムに変更を加えることはありません。読み取り専用の操作のみです。

---

## サポート

問題が発生した場合:

1. ログを確認: `logs/api.log`, `logs/streamlit.log`
2. Issueを作成: GitHub Issues
3. README.mdのトラブルシューティングセクションを参照
