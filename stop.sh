#!/bin/bash
# MindAIgis 停止スクリプト (AlmaLinux 9 対応)

echo "========================================"
echo "  MindAIgis 停止中..."
echo "========================================"

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# FastAPI停止
if [ -f .api.pid ]; then
    API_PID=$(cat .api.pid)
    if ps -p $API_PID > /dev/null 2>&1; then
        echo "FastAPI停止中 (PID: $API_PID)..."
        kill $API_PID 2>/dev/null

        # プロセスが終了するまで待機
        for i in {1..5}; do
            if ! ps -p $API_PID > /dev/null 2>&1; then
                break
            fi
            sleep 1
        done

        # まだ生きている場合は強制終了
        if ps -p $API_PID > /dev/null 2>&1; then
            echo -e "${YELLOW}⚠ プロセスが終了しないため強制終了します${NC}"
            kill -9 $API_PID 2>/dev/null
        fi

        echo -e "${GREEN}✓ FastAPI停止完了${NC}"
    else
        echo -e "${YELLOW}⚠ FastAPIプロセスが見つかりません${NC}"
    fi
    rm -f .api.pid
else
    echo -e "${YELLOW}⚠ FastAPI PIDファイルが見つかりません${NC}"
fi

# Streamlit停止
if [ -f .streamlit.pid ]; then
    STREAMLIT_PID=$(cat .streamlit.pid)
    if ps -p $STREAMLIT_PID > /dev/null 2>&1; then
        echo "Streamlit停止中 (PID: $STREAMLIT_PID)..."
        kill $STREAMLIT_PID 2>/dev/null

        # プロセスが終了するまで待機
        for i in {1..5}; do
            if ! ps -p $STREAMLIT_PID > /dev/null 2>&1; then
                break
            fi
            sleep 1
        done

        # まだ生きている場合は強制終了
        if ps -p $STREAMLIT_PID > /dev/null 2>&1; then
            echo -e "${YELLOW}⚠ プロセスが終了しないため強制終了します${NC}"
            kill -9 $STREAMLIT_PID 2>/dev/null
        fi

        echo -e "${GREEN}✓ Streamlit停止完了${NC}"
    else
        echo -e "${YELLOW}⚠ Streamlitプロセスが見つかりません${NC}"
    fi
    rm -f .streamlit.pid
else
    echo -e "${YELLOW}⚠ Streamlit PIDファイルが見つかりません${NC}"
fi

# Qdrantコンテナ停止
echo "Qdrantコンテナ停止中..."
if command -v docker &> /dev/null; then
    if docker compose down 2>/dev/null; then
        echo -e "${GREEN}✓ Qdrant停止完了${NC}"
    else
        echo -e "${YELLOW}⚠ Docker Composeの停止に失敗しました${NC}"
    fi
else
    echo -e "${YELLOW}⚠ dockerコマンドが見つかりません${NC}"
fi

echo ""
echo "========================================"
echo -e "${GREEN}  すべてのサービスを停止しました${NC}"
echo "========================================"
