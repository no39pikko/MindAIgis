# MindAIgis クイックスタートガイド（AlmaLinux 9）

## 初回セットアップ

```bash
# 1. 仮想環境作成
cd /path/to/MindAIgis
python3 -m venv venv

# 2. 依存パッケージインストール
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 3. 環境変数設定
cp .env.example .env
nano .env  # OPENAI_API_KEY, REDMINE_URL などを設定

# 4. スクリプトに実行権限を付与
chmod +x start.sh stop.sh

# 5. Qdrantデータのインデックス（初回のみ）
python scripts/index_redmine_tickets.py
```

## サービスの起動・停止

```bash
# 起動
./start.sh

# 停止
./stop.sh

# 再起動
./stop.sh && ./start.sh
```

## アクセス

- **Web UI**: http://localhost:8501
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## ログの確認

```bash
# APIログ
tail -f logs/api.log

# Streamlitログ
tail -f logs/streamlit.log

# Qdrantログ
docker logs mindaigis-qdrant
```

## トラブルシューティング

### 1. start.sh がエラーになる

```bash
# 実行権限を確認
ls -l start.sh

# 実行権限がない場合
chmod +x start.sh
```

### 2. 仮想環境が見つからない

```bash
# 仮想環境を作成
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. uvicorn/streamlit がインストールされていない

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Docker権限エラー

```bash
# Dockerグループに追加（要root）
sudo usermod -aG docker $USER

# ログアウト・ログインして反映

# 確認
docker ps
```

### 5. ポートが使用中

```bash
# 使用中のポートを確認
ss -tlnp | grep -E ':(6333|8000|8501)'

# プロセスを特定して停止
kill <PID>
```

### 6. 検索結果が0件

```bash
# Qdrantのデータを確認
curl http://localhost:6333/collections/maintenance_tickets

# vectors_count が 0 の場合、インデックスを実行
source venv/bin/activate
python scripts/index_redmine_tickets.py
```

## 本番運用（systemd）

systemd で自動起動したい場合は、別途サービスファイルを作成してください。

```bash
# サンプル: /etc/systemd/system/mindaigis.service
# （詳細は別途作成）
```

## よくある質問

**Q: 仮想環境を毎回作り直す必要がある？**

A: いいえ。一度作成すれば、`source venv/bin/activate` で有効化するだけです。

**Q: requirements.txt を更新したら？**

A: `source venv/bin/activate && pip install -r requirements.txt --upgrade`

**Q: start.sh が "set -e" でエラーで止まる**

A: 新しい start.sh では set -e を削除し、適切なエラーハンドリングをしています。

**Q: curl がインストールされていない**

A: ヘルスチェックはスキップされますが、起動自体は可能です。インストールする場合: `sudo dnf install curl`
