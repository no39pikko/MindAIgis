# サーバーデプロイ手順

友達のCentOSサーバーにMindAIgisをインストールする手順

---

## 事前確認

### 1. サーバー情報を確認

```bash
# SSH接続
ssh ユーザー名@サーバーIP

# OS確認
cat /etc/redhat-release
# CentOS Linux release 7.x.xxxx (Core) など

# 現在動いているサービス確認
ps aux | grep -E 'redmine|zabbix'
```

### 2. 必要な権限

- sudo権限（rootでなくてもOK）
- または友達に以下をインストールしてもらう

---

## サーバーに入れるもの

### 必須

1. **Python 3.9以上**
2. **pip3**
3. **Docker & Docker Compose** （Qdrant用）
4. **git**（オプション、ファイル転送でも可）

---

## インストール手順

### ステップ1: Python確認・インストール

```bash
# Python確認
python3 --version

# ない場合はインストール
# CentOS 7/8
sudo yum install -y python3 python3-pip python3-devel

# CentOS 9 / RHEL 9
sudo dnf install -y python3 python3-pip python3-devel
```

### ステップ2: Docker インストール

```bash
# Dockerインストール
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io

# Docker起動
sudo systemctl start docker
sudo systemctl enable docker

# 確認
sudo docker --version
# Docker version 24.x.x
```

### ステップ3: Docker Compose インストール

```bash
# Docker Compose v2
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 確認
docker-compose --version
# Docker Compose version v2.x.x
```

### ステップ4: Git インストール（オプション）

```bash
sudo yum install -y git
```

---

## MindAIgis デプロイ

### 方法A: Git経由（推奨）

```bash
# 作業ディレクトリ作成
sudo mkdir -p /opt/mindaigis
sudo chown $USER:$USER /opt/mindaigis

# クローン
cd /opt/mindaigis
git clone <あなたのリポジトリURL> .
```

### 方法B: ファイル転送

```bash
# ローカル環境から（WSL/PowerShell）
cd /mnt/c/Users/aotoh/Documents/ClaudeCode/MindAIgis

# サーバーに転送（scp）
scp -r * ユーザー名@サーバーIP:/opt/mindaigis/

# または rsync
rsync -avz --exclude 'venv' --exclude '__pycache__' --exclude 'qdrant_storage' \
  ./ ユーザー名@サーバーIP:/opt/mindaigis/
```

---

## 設定

### 1. 環境変数設定

```bash
cd /opt/mindaigis

# .envファイル作成
cp .env.example .env
vim .env
```

**サーバー用の設定:**

```bash
# OpenAI API
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxx

# Redmine（ローカルなので localhost でOK）
REDMINE_URL=http://localhost:ポート番号
# または
REDMINE_URL=http://127.0.0.1:3000
REDMINE_API_KEY=xxxxxxxxxxxxxxxxxxxx

# Qdrant
QDRANT_URL=http://localhost:6333

# API設定
API_HOST=0.0.0.0
API_PORT=8000

# Streamlit
STREAMLIT_PORT=8501
API_BASE_URL=http://localhost:8000
```

### 2. Python環境構築

```bash
# 仮想環境作成
python3 -m venv venv
source venv/bin/activate

# 依存関係インストール
pip install -r requirements.txt

# 完了を確認
pip list | grep -E 'fastapi|streamlit|qdrant'
```

### 3. Qdrant起動

```bash
# Dockerコンテナ起動
sudo docker-compose up -d

# 確認
sudo docker ps
# mindaigis-qdrant が Running

curl http://localhost:6333/collections
# {"result":{"collections":[]}}
```

### 4. 接続テスト

```bash
# Redmine接続テスト
python3 << 'EOF'
from dotenv import load_dotenv
load_dotenv()
from app.services.redmine_service import RedmineService

redmine = RedmineService()
if redmine.test_connection():
    print("✓ Redmine接続成功")
    tickets = redmine.get_closed_tickets(limit=5)
    print(f"取得チケット数: {len(tickets)}")
else:
    print("✗ Redmine接続失敗")
EOF
```

---

## 初期データ投入

```bash
# まず10件でテスト
python scripts/index_tickets.py --dry-run --limit 10

# 問題なければ本番実行（時間かかる）
python scripts/index_tickets.py

# または制限付き
python scripts/index_tickets.py --limit 1000
```

---

## 起動

### オプションA: 手動起動（テスト用）

```bash
# ターミナル1: API
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000

# ターミナル2: Streamlit
source venv/bin/activate
streamlit run ui/streamlit_app.py --server.port 8501 --server.address 0.0.0.0
```

### オプションB: systemdサービス登録（本番用）

詳細は `systemd/INSTALL.md` を参照

```bash
# サービスファイルコピー
sudo cp systemd/mindaigis-api.service /etc/systemd/system/
sudo cp systemd/mindaigis-ui.service /etc/systemd/system/

# ※事前に /etc/systemd/system/mindaigis-*.service を編集
# User=mindaigis → User=実際のユーザー名
# WorkingDirectory=/opt/mindaigis → 実際のパス

sudo systemctl daemon-reload
sudo systemctl enable mindaigis-api.service
sudo systemctl enable mindaigis-ui.service
sudo systemctl start mindaigis-api.service
sudo systemctl start mindaigis-ui.service

# 確認
sudo systemctl status mindaigis-api.service
```

---

## ファイアウォール設定

サーバーの外からアクセスする場合:

```bash
# ファイアウォール確認
sudo firewall-cmd --state

# ポート開放
sudo firewall-cmd --permanent --add-port=8000/tcp  # API
sudo firewall-cmd --permanent --add-port=8501/tcp  # Streamlit
sudo firewall-cmd --reload

# 確認
sudo firewall-cmd --list-ports
```

---

## 動作確認

### サーバー内から

```bash
# API
curl http://localhost:8000/health

# Streamlit
curl http://localhost:8501
```

### 外部から（あなたのPC）

```bash
# ブラウザで
http://サーバーIP:8501

# または
curl http://サーバーIP:8000/health
```

---

## トラブルシューティング

### ポートが使用中

```bash
# ポート確認
sudo netstat -tlnp | grep -E '8000|8501|6333'

# プロセス確認
sudo lsof -i :8000
```

### Redmine接続エラー

```bash
# サーバー内でRedmineにアクセスできるか
curl http://localhost:3000  # Redmineのポート

# APIキーテスト
curl -H "X-Redmine-API-Key: APIキー" \
  http://localhost:3000/issues.json?limit=1
```

### Docker権限エラー

```bash
# 現在のユーザーをdockerグループに追加
sudo usermod -aG docker $USER

# セッション再ログイン
exit
# 再度SSH接続

# Docker確認
docker ps  # sudoなしで実行できればOK
```

### SELinux問題（CentOS 7/8）

```bash
# SELinuxステータス確認
getenforce
# Enforcing の場合は制限あり

# 一時的に無効化（テスト用）
sudo setenforce 0

# 恒久的に無効化（本番環境では非推奨）
sudo vim /etc/selinux/config
# SELINUX=disabled

# または適切にコンテキスト設定
sudo semanage fcontext -a -t httpd_sys_content_t "/opt/mindaigis(/.*)?"
sudo restorecon -R /opt/mindaigis
```

---

## 最小構成で動かすチェックリスト

- [ ] Python 3.9+ インストール済み
- [ ] pip インストール済み
- [ ] Docker インストール済み
- [ ] Docker Compose インストール済み
- [ ] /opt/mindaigis にファイル配置
- [ ] .env ファイル設定（OpenAI API Key, Redmine設定）
- [ ] venv 作成 & pip install -r requirements.txt
- [ ] docker-compose up -d 実行
- [ ] Redmine接続テスト成功
- [ ] python scripts/index_tickets.py --limit 10 成功
- [ ] uvicorn app.main:app 起動
- [ ] curl http://localhost:8000/health → 正常

---

## 次のステップ

1. 実際に検索テスト
2. オペレーターに使ってもらう
3. フィードバック収集
4. 必要に応じてZabbix統合
