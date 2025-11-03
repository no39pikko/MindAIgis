# CentOS Systemd セットアップ手順

本番環境でMindAIgisをsystemdサービスとして起動する手順

---

## 前提条件

- CentOS 7/8/9
- root権限またはsudo権限
- Docker & Docker Composeインストール済み

---

## 1. ユーザー作成

```bash
# mindaigis専用ユーザーを作成
sudo useradd -m -s /bin/bash mindaigis

# アプリケーションディレクトリ作成
sudo mkdir -p /opt/mindaigis
sudo chown mindaigis:mindaigis /opt/mindaigis
```

---

## 2. アプリケーションデプロイ

```bash
# mindaigisユーザーに切り替え
sudo su - mindaigis

# アプリケーションをデプロイ
cd /opt/mindaigis
git clone <repository-url> .

# 仮想環境作成
python3 -m venv venv
source venv/bin/activate

# 依存関係インストール
pip install -r requirements.txt

# 環境変数設定
cp .env.example .env
vim .env  # 本番用の設定を記述

# ログディレクトリ作成
mkdir -p logs

# 権限設定
chmod 755 /opt/mindaigis
```

---

## 3. Dockerグループ設定

mindaigisユーザーがDockerを操作できるようにします。

```bash
# rootに戻る
exit

# mindaigisをdockerグループに追加
sudo usermod -aG docker mindaigis

# 確認
groups mindaigis
```

---

## 4. Systemdサービスファイル配置

```bash
# サービスファイルをコピー
sudo cp /opt/mindaigis/systemd/mindaigis-api.service /etc/systemd/system/
sudo cp /opt/mindaigis/systemd/mindaigis-ui.service /etc/systemd/system/

# 権限設定
sudo chmod 644 /etc/systemd/system/mindaigis-api.service
sudo chmod 644 /etc/systemd/system/mindaigis-ui.service

# systemd設定リロード
sudo systemctl daemon-reload
```

---

## 5. Qdrant起動

```bash
# mindaigisユーザーで実行
sudo su - mindaigis
cd /opt/mindaigis

# Qdrantコンテナ起動
docker-compose up -d

# 確認
docker ps
curl http://localhost:6333/collections
```

---

## 6. サービス起動

```bash
# rootに戻る
exit

# サービス有効化
sudo systemctl enable mindaigis-api.service
sudo systemctl enable mindaigis-ui.service

# サービス起動
sudo systemctl start mindaigis-api.service
sudo systemctl start mindaigis-ui.service

# ステータス確認
sudo systemctl status mindaigis-api.service
sudo systemctl status mindaigis-ui.service
```

---

## 7. 動作確認

```bash
# APIヘルスチェック
curl http://localhost:8000/health

# ログ確認
sudo journalctl -u mindaigis-api.service -f
sudo journalctl -u mindaigis-ui.service -f

# または
tail -f /opt/mindaigis/logs/api.log
tail -f /opt/mindaigis/logs/streamlit.log
```

---

## 8. ファイアウォール設定（必要に応じて）

```bash
# ポート開放
sudo firewall-cmd --permanent --add-port=8000/tcp  # API
sudo firewall-cmd --permanent --add-port=8501/tcp  # Streamlit
sudo firewall-cmd --reload

# 確認
sudo firewall-cmd --list-ports
```

---

## 9. 初期データインデックス

```bash
# mindaigisユーザーで実行
sudo su - mindaigis
cd /opt/mindaigis
source venv/bin/activate

# Redmineチケットをインデックス
python scripts/index_tickets.py
```

---

## 管理コマンド

### サービス再起動
```bash
sudo systemctl restart mindaigis-api.service
sudo systemctl restart mindaigis-ui.service
```

### サービス停止
```bash
sudo systemctl stop mindaigis-api.service
sudo systemctl stop mindaigis-ui.service
sudo systemctl stop mindaigis-qdrant.service
```

### ログ確認
```bash
# systemd journal
sudo journalctl -u mindaigis-api.service --since "1 hour ago"
sudo journalctl -u mindaigis-ui.service --since "1 hour ago"

# アプリケーションログ
tail -f /opt/mindaigis/logs/api.log
tail -f /opt/mindaigis/logs/streamlit.log
```

### 自動起動無効化
```bash
sudo systemctl disable mindaigis-api.service
sudo systemctl disable mindaigis-ui.service
```

---

## トラブルシューティング

### サービスが起動しない

```bash
# ステータス詳細確認
sudo systemctl status mindaigis-api.service -l

# ログ確認
sudo journalctl -xe

# 環境変数確認
sudo systemctl show mindaigis-api.service | grep Environment

# 手動起動テスト
sudo su - mindaigis
cd /opt/mindaigis
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 権限エラー

```bash
# ファイル所有者確認
ls -la /opt/mindaigis

# 権限修正
sudo chown -R mindaigis:mindaigis /opt/mindaigis
sudo chmod -R 755 /opt/mindaigis
```

### Docker権限エラー

```bash
# mindaigisユーザーがdockerグループに所属しているか確認
groups mindaigis

# セッションをリフレッシュ
sudo su - mindaigis
docker ps
```

---

## セキュリティ推奨事項

1. **ファイアウォール設定**
   - 外部公開が不要なポートは閉じる
   - 必要に応じてVPN経由でのアクセスに制限

2. **SELinux設定（CentOS 7/8）**
   ```bash
   # SELinuxコンテキスト設定が必要な場合
   sudo semanage fcontext -a -t httpd_sys_content_t "/opt/mindaigis(/.*)?"
   sudo restorecon -R /opt/mindaigis
   ```

3. **定期バックアップ**
   - Qdrantデータ: `/opt/mindaigis/qdrant_storage/`
   - 環境変数: `/opt/mindaigis/.env`
   - ログ: `/opt/mindaigis/logs/`

4. **ログローテーション設定**
   ```bash
   sudo vim /etc/logrotate.d/mindaigis
   ```
   ```
   /opt/mindaigis/logs/*.log {
       daily
       rotate 14
       compress
       delaycompress
       notifempty
       create 0644 mindaigis mindaigis
   }
   ```

---

## アンインストール

```bash
# サービス停止
sudo systemctl stop mindaigis-api.service mindaigis-ui.service
sudo systemctl disable mindaigis-api.service mindaigis-ui.service

# サービスファイル削除
sudo rm /etc/systemd/system/mindaigis-api.service
sudo rm /etc/systemd/system/mindaigis-ui.service
sudo systemctl daemon-reload

# Dockerコンテナ停止・削除
cd /opt/mindaigis
docker-compose down -v

# アプリケーション削除
sudo rm -rf /opt/mindaigis

# ユーザー削除
sudo userdel -r mindaigis
```
