#!/bin/bash
# MindAIgis 起動スクリプト

set -e

echo "========================================"
echo "  MindAIgis 起動スクリプト"
echo "========================================"

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 環境変数チェック
if [ ! -f .env ]; then
    echo -e "${RED}✗ .env ファイルが見つかりません${NC}"
    echo "  .env.example をコピーして .env を作成してください"
    echo "  cp .env.example .env"
    exit 1
fi

echo -e "${GREEN}✓ .env ファイルを検出${NC}"

# Qdrantコンテナ起動
echo ""
echo "[1/3] Qdrantコンテナ起動中..."
docker compose up -d

# 起動待機
echo "  Qdrantの起動を待機中..."
sleep 5

# ヘルスチェック
if curl -s http://localhost:6333/collections > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Qdrant起動成功${NC}"
else
    echo -e "${RED}✗ Qdrant起動失敗${NC}"
    echo "  docker logs mindaigis-qdrant で確認してください"
    exit 1
fi

# FastAPI起動
echo ""
echo "[2/3] FastAPI起動中..."
source venv/bin/activate 2>/dev/null || echo "仮想環境が見つかりません（スキップ）"

# バックグラウンドでAPIサーバー起動
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > logs/api.log 2>&1 &
API_PID=$!
echo $API_PID > .api.pid

# 起動待機
echo "  API起動を待機中..."
sleep 3

# ヘルスチェック
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ FastAPI起動成功 (PID: $API_PID)${NC}"
else
    echo -e "${RED}✗ FastAPI起動失敗${NC}"
    echo "  logs/api.log を確認してください"
    exit 1
fi

# Streamlit起動
echo ""
echo "[3/3] Streamlit起動中..."
nohup streamlit run ui/streamlit_app.py --server.port 8501 > logs/streamlit.log 2>&1 &
STREAMLIT_PID=$!
echo $STREAMLIT_PID > .streamlit.pid

sleep 3
echo -e "${GREEN}✓ Streamlit起動成功 (PID: $STREAMLIT_PID)${NC}"

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
echo "========================================"
