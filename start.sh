#!/bin/bash
# MindAIgis 起動スクリプト (AlmaLinux 9 対応)

echo "========================================"
echo "  MindAIgis 起動スクリプト"
echo "========================================"

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# エラーハンドリング関数
error_exit() {
    echo -e "${RED}✗ エラー: $1${NC}"
    exit 1
}

# 環境変数チェック
if [ ! -f .env ]; then
    error_exit ".env ファイルが見つかりません。cp .env.example .env で作成してください"
fi
echo -e "${GREEN}✓ .env ファイルを検出${NC}"

# logsディレクトリ作成
mkdir -p logs
echo -e "${GREEN}✓ logsディレクトリを作成${NC}"

# 仮想環境のチェック
if [ ! -d "venv" ]; then
    error_exit "仮想環境が見つかりません。python3 -m venv venv で作成してください"
fi
echo -e "${GREEN}✓ 仮想環境を検出${NC}"

# 仮想環境のパスを取得
VENV_PATH="$(pwd)/venv"
PYTHON_BIN="${VENV_PATH}/bin/python"
UVICORN_BIN="${VENV_PATH}/bin/uvicorn"
STREAMLIT_BIN="${VENV_PATH}/bin/streamlit"

# バイナリの存在確認
if [ ! -f "$PYTHON_BIN" ]; then
    error_exit "Pythonが仮想環境に見つかりません"
fi

if [ ! -f "$UVICORN_BIN" ]; then
    error_exit "uvicornがインストールされていません。pip install -r requirements.txt を実行してください"
fi

if [ ! -f "$STREAMLIT_BIN" ]; then
    error_exit "streamlitがインストールされていません。pip install -r requirements.txt を実行してください"
fi

echo -e "${GREEN}✓ 必要なコマンドを確認${NC}"

# ========================================
# [1/3] Qdrantコンテナ起動
# ========================================
echo ""
echo "[1/3] Qdrantコンテナ起動中..."

# Dockerが利用可能かチェック
if ! command -v docker &> /dev/null; then
    error_exit "dockerコマンドが見つかりません"
fi

# Docker Composeの起動
if docker compose up -d 2>/dev/null; then
    echo -e "${GREEN}✓ Docker Compose起動成功${NC}"
else
    error_exit "Docker Composeの起動に失敗しました。docker compose logs で確認してください"
fi

# 起動待機
echo "  Qdrantの起動を待機中..."
for i in {1..10}; do
    if command -v curl &> /dev/null; then
        if curl -s http://localhost:6333/collections > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Qdrant起動成功${NC}"
            break
        fi
    else
        # curlがない場合はsleepのみ
        if [ $i -eq 10 ]; then
            echo -e "${YELLOW}⚠ curlがないためQdrantのヘルスチェックをスキップ${NC}"
            break
        fi
    fi
    sleep 1
done

# ========================================
# [2/3] FastAPI起動
# ========================================
echo ""
echo "[2/3] FastAPI起動中..."

# 既存のプロセスをチェック
if [ -f .api.pid ]; then
    OLD_PID=$(cat .api.pid)
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠ 既存のAPIプロセス (PID: $OLD_PID) を停止中...${NC}"
        kill $OLD_PID 2>/dev/null || true
        sleep 2
    fi
    rm -f .api.pid
fi

# APIサーバー起動
nohup "$UVICORN_BIN" app.main:app --host 0.0.0.0 --port 8000 > logs/api.log 2>&1 &
API_PID=$!
echo $API_PID > .api.pid

# プロセスが起動したか確認
sleep 2
if ! ps -p $API_PID > /dev/null 2>&1; then
    error_exit "FastAPIの起動に失敗しました。logs/api.log を確認してください"
fi

# ヘルスチェック
echo "  API起動を待機中..."
for i in {1..15}; do
    if command -v curl &> /dev/null; then
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}✓ FastAPI起動成功 (PID: $API_PID)${NC}"
            break
        fi
    fi
    if [ $i -eq 15 ]; then
        echo -e "${YELLOW}⚠ APIのヘルスチェックに失敗しましたが、プロセスは起動中です${NC}"
        echo "  logs/api.log でログを確認してください"
    fi
    sleep 1
done

# ========================================
# [3/3] Streamlit起動
# ========================================
echo ""
echo "[3/3] Streamlit起動中..."

# 既存のプロセスをチェック
if [ -f .streamlit.pid ]; then
    OLD_PID=$(cat .streamlit.pid)
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠ 既存のStreamlitプロセス (PID: $OLD_PID) を停止中...${NC}"
        kill $OLD_PID 2>/dev/null || true
        sleep 2
    fi
    rm -f .streamlit.pid
fi

# Streamlit起動
nohup "$STREAMLIT_BIN" run ui/streamlit_app.py --server.port 8501 --server.headless true > logs/streamlit.log 2>&1 &
STREAMLIT_PID=$!
echo $STREAMLIT_PID > .streamlit.pid

# プロセスが起動したか確認
sleep 2
if ! ps -p $STREAMLIT_PID > /dev/null 2>&1; then
    error_exit "Streamlitの起動に失敗しました。logs/streamlit.log を確認してください"
fi

echo -e "${GREEN}✓ Streamlit起動成功 (PID: $STREAMLIT_PID)${NC}"

# ========================================
# 完了
# ========================================
echo ""
echo "========================================"
echo -e "${GREEN}  MindAIgis起動完了！${NC}"
echo "========================================"
echo ""
echo "  Web UI: http://localhost:8501"
echo "  API:    http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "停止するには: ./stop.sh"
echo ""
echo "ログの確認:"
echo "  API:       tail -f logs/api.log"
echo "  Streamlit: tail -f logs/streamlit.log"
echo "========================================"
